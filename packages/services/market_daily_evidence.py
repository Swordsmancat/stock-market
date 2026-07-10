from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Mapping

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session

from packages.domain.models import MarketDailyEvidenceEvent
from packages.services.hot_sectors import get_hot_sectors_payload
from packages.services.market_daily_data import (
    get_block_trades_payload,
    get_dragon_tiger_list_payload,
    get_limit_up_reasons_payload,
    get_stock_fund_flow_payload,
)


MARKET_DAILY_EVIDENCE_CITATION_PREFIX = "market_daily_event:"
DEFAULT_MARKET_DAILY_EVIDENCE_PROVIDER = "akshare"
DEFAULT_MARKET_DAILY_EVIDENCE_EVENT_TYPES = (
    "stock_fund_flow",
    "limit_up_reason",
    "dragon_tiger_list",
    "block_trade",
    "hot_sector",
)
CORPORATE_ACTION_EVENT_TYPES = (
    "dividend_bonus",
    "rights_allotment",
)
SUPPORTED_MARKET_DAILY_EVIDENCE_EVENT_TYPES = (
    *DEFAULT_MARKET_DAILY_EVIDENCE_EVENT_TYPES,
    *CORPORATE_ACTION_EVENT_TYPES,
)
EVENT_TYPE_LABELS = {
    "stock_fund_flow": "Stock fund flow",
    "limit_up_reason": "Limit-up context",
    "dragon_tiger_list": "Dragon Tiger List",
    "block_trade": "Block trade",
    "hot_sector": "Hot sector",
    "dividend_bonus": "Dividend / bonus transfer",
    "rights_allotment": "Rights allotment",
}
IMPORTABLE_DATA_MODES = {"live", "delayed"}
NON_CITABLE_PROVIDERS = {"", "none", "mock", "static", "fixture"}
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "access_token",
    "authorization",
    "cookie",
    "password",
    "secret",
)
MAX_TEXT_LENGTH = 2048


class MarketDailyEvidenceValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class MarketDailyEvidenceImportInput:
    trade_date: date | None = None
    market: str = "CN"
    provider_name: str | None = None
    event_types: tuple[str, ...] = DEFAULT_MARKET_DAILY_EVIDENCE_EVENT_TYPES
    limit: int = 20


def import_market_daily_evidence(
    payload: MarketDailyEvidenceImportInput,
    *,
    session: Session,
    normalized_payloads: Mapping[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    normalized = _normalize_import_input(payload)
    effective_trade_date = normalized.trade_date or date.today()
    imported_at = datetime.now(timezone.utc)
    inserted = 0
    updated = 0
    skipped = 0
    diagnostics: list[dict[str, object]] = []
    event_results: list[dict[str, object]] = []

    try:
        for event_type in normalized.event_types:
            provider_payload = (
                normalized_payloads[event_type]
                if normalized_payloads is not None and event_type in normalized_payloads
                else load_market_daily_evidence_payload(
                    event_type,
                    trade_date=effective_trade_date,
                    market=normalized.market,
                    provider_name=normalized.provider_name,
                    limit=normalized.limit,
                )
            )
            provider_diagnostics = _provider_payload_diagnostics(event_type, provider_payload)
            diagnostics.extend(provider_diagnostics)
            rows = _payload_rows(provider_payload)
            event_result = {
                "event_type": event_type,
                "provider_status": _clean_text(provider_payload.get("status")) or "unavailable",
                "data_mode": _clean_text(provider_payload.get("data_mode")) or "none",
                "source_count": len(rows),
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
            }

            if not _payload_is_importable(provider_payload, rows):
                skipped += len(rows)
                event_result["skipped"] = len(rows)
                event_result["status"] = "skipped"
                event_results.append(event_result)
                continue

            for item in rows:
                row_values = _build_event_values(
                    event_type=event_type,
                    item=item,
                    provider_payload=provider_payload,
                    requested_trade_date=effective_trade_date,
                    imported_at=imported_at,
                )
                if row_values is None:
                    skipped += 1
                    event_result["skipped"] = int(event_result["skipped"]) + 1
                    diagnostics.append(
                        {
                            "source": "market_daily_evidence",
                            "status": "skipped",
                            "severity": "warning",
                            "code": "MARKET_DAILY_EVIDENCE_IDENTITY_INVALID",
                            "event_type": event_type,
                            "message": "A normalized provider row was skipped because its identity or trade date was missing.",
                        }
                    )
                    continue

                existing = (
                    session.query(MarketDailyEvidenceEvent)
                    .filter(
                        MarketDailyEvidenceEvent.provider == row_values["provider"],
                        MarketDailyEvidenceEvent.event_type == event_type,
                        MarketDailyEvidenceEvent.identity == row_values["identity"],
                        MarketDailyEvidenceEvent.market == row_values["market"],
                        MarketDailyEvidenceEvent.trade_date == row_values["trade_date"],
                    )
                    .first()
                )
                if existing is None:
                    session.add(MarketDailyEvidenceEvent(**row_values))
                    inserted += 1
                    event_result["inserted"] = int(event_result["inserted"]) + 1
                    continue

                if _update_existing_event(existing, row_values):
                    updated += 1
                    event_result["updated"] = int(event_result["updated"]) + 1
                else:
                    skipped += 1
                    event_result["skipped"] = int(event_result["skipped"]) + 1

            event_result["status"] = "stored" if int(event_result["inserted"]) + int(event_result["updated"]) else "unchanged"
            event_results.append(event_result)

        session.commit()
    except SQLAlchemyError as error:
        session.rollback()
        return {
            "status": "failed",
            "inserted": 0,
            "updated": 0,
            "skipped": skipped,
            "event_types": list(normalized.event_types),
            "trade_date": effective_trade_date.isoformat(),
            "market": normalized.market,
            "provider": normalized.provider_name,
            "imported_at": imported_at.isoformat(),
            "event_results": event_results,
            "diagnostics": [
                *diagnostics,
                {
                    "source": "market_daily_evidence",
                    "status": "failed",
                    "severity": "error",
                    "code": "MARKET_DAILY_EVIDENCE_STORAGE_FAILED",
                    "message": f"Market daily evidence storage failed: {error.__class__.__name__}.",
                },
            ],
            "safety": _safety_payload(),
        }

    return {
        "status": "ok" if inserted or updated else "degraded",
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "event_types": list(normalized.event_types),
        "trade_date": effective_trade_date.isoformat(),
        "market": normalized.market,
        "provider": normalized.provider_name,
        "imported_at": imported_at.isoformat(),
        "event_results": event_results,
        "diagnostics": diagnostics,
        "safety": _safety_payload(),
    }


def load_market_daily_evidence_payload(
    event_type: str,
    *,
    trade_date: date,
    market: str,
    provider_name: str,
    limit: int,
) -> dict[str, object]:
    if event_type == "stock_fund_flow":
        return get_stock_fund_flow_payload(
            market=market,
            window="today",
            limit=limit,
            provider_name=provider_name,
        )
    if event_type == "limit_up_reason":
        return get_limit_up_reasons_payload(
            trade_date=trade_date,
            market=market,
            limit=limit,
            provider_name=provider_name,
        )
    if event_type == "dragon_tiger_list":
        return get_dragon_tiger_list_payload(
            trade_date=trade_date,
            market=market,
            limit=limit,
            provider_name=provider_name,
        )
    if event_type == "block_trade":
        return get_block_trades_payload(
            trade_date=trade_date,
            market=market,
            limit=limit,
            provider_name=provider_name,
        )
    if event_type == "hot_sector":
        return get_hot_sectors_payload(
            limit=min(limit, 10),
            provider_name=provider_name,
            sector_type="industry",
            window="today",
        )
    if event_type in CORPORATE_ACTION_EVENT_TYPES:
        raise MarketDailyEvidenceValidationError(
            [f"Event type {event_type} must be loaded through the corporate-action batch job."]
        )
    raise MarketDailyEvidenceValidationError([f"Unsupported market daily evidence event type: {event_type}."])


def list_market_daily_evidence(
    *,
    session: Session,
    event_type: str | None = None,
    identity: str | None = None,
    symbol: str | None = None,
    market: str | None = None,
    trade_date: date | None = None,
    citable_only: bool = False,
    limit: int = 50,
) -> dict[str, object]:
    normalized_event_type = _normalize_optional_event_type(event_type)
    normalized_identity = _normalize_identity_token(identity) if identity else None
    normalized_symbol = _normalize_identity_token(symbol, uppercase=True) if symbol else None
    normalized_market = _normalize_market(market) if market else None
    bounded_limit = max(1, min(limit, 200))

    query = _apply_evidence_filters(
        session.query(MarketDailyEvidenceEvent),
        event_type=normalized_event_type,
        identity=normalized_identity,
        symbol=normalized_symbol,
        market=normalized_market,
        trade_date=trade_date,
        citable_only=citable_only,
    )
    total = query.count()
    rows = (
        query.order_by(
            MarketDailyEvidenceEvent.trade_date.desc(),
            MarketDailyEvidenceEvent.imported_at.desc(),
            MarketDailyEvidenceEvent.event_type.asc(),
            MarketDailyEvidenceEvent.identity.asc(),
        )
        .limit(bounded_limit)
        .all()
    )
    counts_query = _apply_evidence_filters(
        session.query(
            MarketDailyEvidenceEvent.event_type,
            func.count(MarketDailyEvidenceEvent.id),
        ),
        event_type=normalized_event_type,
        identity=normalized_identity,
        symbol=normalized_symbol,
        market=normalized_market,
        trade_date=trade_date,
        citable_only=citable_only,
    )
    counts = {
        event_code: count
        for event_code, count in counts_query.group_by(MarketDailyEvidenceEvent.event_type).all()
    }
    latest = rows[0] if rows else None
    return {
        "items": [serialize_market_daily_evidence_event(row) for row in rows],
        "citations": [build_market_daily_evidence_citation(row) for row in rows if row.is_citable],
        "summary": {
            "total": total,
            "returned": len(rows),
            "counts_by_event_type": counts,
            "latest_imported_at": latest.imported_at.isoformat() if latest else None,
            "latest_updated_at": latest.updated_at.isoformat() if latest else None,
            "latest_trade_date": latest.trade_date.isoformat() if latest else None,
        },
        "filters": {
            "event_type": normalized_event_type,
            "identity": normalized_identity,
            "symbol": normalized_symbol,
            "market": normalized_market,
            "trade_date": trade_date.isoformat() if trade_date else None,
            "citable_only": citable_only,
        },
        "safety": _safety_payload(),
    }


def list_citable_market_daily_evidence_citations(
    *,
    session: Session,
    symbols: list[str] | None = None,
    event_types: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, object]]:
    normalized_event_types = [_normalize_optional_event_type(item) for item in event_types or []]
    normalized_symbols = [
        token
        for symbol in symbols or []
        if (token := _normalize_identity_token(symbol, uppercase=True))
    ]
    query = session.query(MarketDailyEvidenceEvent).filter(MarketDailyEvidenceEvent.is_citable.is_(True))
    if normalized_event_types:
        query = query.filter(MarketDailyEvidenceEvent.event_type.in_(normalized_event_types))
    if normalized_symbols:
        symbol_filters = []
        for symbol in normalized_symbols:
            symbol_filters.extend(
                [
                    MarketDailyEvidenceEvent.identity == symbol,
                    MarketDailyEvidenceEvent.identity.like(f"{symbol}-%"),
                ]
            )
        query = query.filter(or_(MarketDailyEvidenceEvent.event_type == "hot_sector", *symbol_filters))
    rows = (
        query.order_by(
            MarketDailyEvidenceEvent.trade_date.desc(),
            MarketDailyEvidenceEvent.imported_at.desc(),
        )
        .limit(max(1, min(limit, 50)))
        .all()
    )
    return [build_market_daily_evidence_citation(row) for row in rows]


def build_market_daily_evidence_citation_id(
    *,
    event_type: str,
    identity: str,
    trade_date: date,
) -> str:
    normalized_event_type = _normalize_optional_event_type(event_type)
    normalized_identity = _normalize_identity_token(identity)
    if not normalized_event_type or not normalized_identity:
        raise MarketDailyEvidenceValidationError(["Citation event type and identity are required."])
    return f"{MARKET_DAILY_EVIDENCE_CITATION_PREFIX}{normalized_event_type}:{normalized_identity}:{trade_date.isoformat()}"


def build_market_daily_evidence_citation(event: MarketDailyEvidenceEvent) -> dict[str, object]:
    return {
        "id": build_market_daily_evidence_citation_id(
            event_type=event.event_type,
            identity=event.identity,
            trade_date=event.trade_date,
        ),
        "label": f"{EVENT_TYPE_LABELS.get(event.event_type, event.event_type)}: {event.identity_name or event.identity}",
        "source": "market_daily_evidence",
        "source_type": "market_daily_event",
        "as_of": event.trade_date.isoformat(),
        "provider": event.provider,
        "retrieved_at": event.imported_at.isoformat(),
        "excerpt": _build_citation_excerpt(event),
        "metadata": {
            "event_type": event.event_type,
            "identity": event.identity,
            "market": event.market,
            "trade_date": event.trade_date.isoformat(),
            "status": event.status,
            "source": event.source,
        },
    }


def serialize_market_daily_evidence_event(event: MarketDailyEvidenceEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "identity": event.identity,
        "identity_name": event.identity_name,
        "market": event.market,
        "trade_date": event.trade_date.isoformat(),
        "provider": event.provider,
        "source": event.source,
        "as_of": event.as_of.isoformat() if event.as_of else None,
        "status": event.status,
        "is_citable": event.is_citable,
        "payload": event.payload_json or {},
        "availability": event.availability_json or {},
        "provider_capabilities": event.provider_capabilities_json or {},
        "diagnostics": event.diagnostics_json or [],
        "imported_at": event.imported_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
        "citation_id": (
            build_market_daily_evidence_citation_id(
                event_type=event.event_type,
                identity=event.identity,
                trade_date=event.trade_date,
            )
            if event.is_citable
            else None
        ),
    }


def _normalize_import_input(payload: MarketDailyEvidenceImportInput) -> MarketDailyEvidenceImportInput:
    market = _normalize_market(payload.market)
    if market != "CN":
        raise MarketDailyEvidenceValidationError(["Market daily evidence currently supports market CN only."])
    provider_name = (_clean_text(payload.provider_name) or DEFAULT_MARKET_DAILY_EVIDENCE_PROVIDER).lower()
    event_types: list[str] = []
    for raw_event_type in payload.event_types:
        event_type = _normalize_optional_event_type(raw_event_type)
        if event_type and event_type not in event_types:
            event_types.append(event_type)
    if not event_types:
        raise MarketDailyEvidenceValidationError(["At least one market daily evidence event type is required."])
    return MarketDailyEvidenceImportInput(
        trade_date=payload.trade_date,
        market=market,
        provider_name=provider_name,
        event_types=tuple(event_types),
        limit=max(1, min(payload.limit, 100)),
    )


def _normalize_optional_event_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_MARKET_DAILY_EVIDENCE_EVENT_TYPES:
        raise MarketDailyEvidenceValidationError([f"Unsupported market daily evidence event type: {value}."])
    return normalized


def _payload_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _payload_is_importable(payload: dict[str, object], rows: list[dict[str, object]]) -> bool:
    status = (_clean_text(payload.get("status")) or "").lower()
    data_mode = (_clean_text(payload.get("data_mode")) or "").lower()
    provider = (
        _clean_text(payload.get("effective_provider"))
        or _clean_text(payload.get("provider"))
        or ""
    ).lower()[:64]
    source = (_clean_text(payload.get("source")) or "").lower()
    return (
        status in {"ok", "degraded"}
        and data_mode in IMPORTABLE_DATA_MODES
        and provider not in NON_CITABLE_PROVIDERS
        and source != "provider_error"
        and bool(rows)
    )


def _build_event_values(
    *,
    event_type: str,
    item: dict[str, object],
    provider_payload: dict[str, object],
    requested_trade_date: date,
    imported_at: datetime,
) -> dict[str, object] | None:
    identity = _build_event_identity(event_type, item)
    trade_date_value = _parse_date(item.get("trade_date")) or _parse_date(provider_payload.get("trade_date"))
    if trade_date_value is None and event_type in {
        "stock_fund_flow",
        "hot_sector",
        *CORPORATE_ACTION_EVENT_TYPES,
    }:
        trade_date_value = requested_trade_date
    if not identity or trade_date_value is None:
        return None

    provider = (
        _clean_text(item.get("provider"))
        or _clean_text(provider_payload.get("effective_provider"))
        or _clean_text(provider_payload.get("provider"))
        or DEFAULT_MARKET_DAILY_EVIDENCE_PROVIDER
    ).lower()
    source = _clip_text(
        (
        _clean_text(item.get("source"))
        or _clean_text(provider_payload.get("source"))
        or "provider_normalized_market_daily_data"
        ),
        512,
    )
    market = _normalize_market(
        _clean_text(item.get("market")) or _clean_text(provider_payload.get("market")) or "CN"
    )
    if not market:
        return None
    diagnostics = _provider_payload_diagnostics(event_type, provider_payload)
    return {
        "event_type": event_type,
        "identity": identity,
        "identity_name": _clip_text(_build_identity_name(event_type, item, identity), 512),
        "market": market,
        "trade_date": trade_date_value,
        "provider": provider,
        "source": source,
        "as_of": _parse_datetime(item.get("as_of")) or _parse_datetime(provider_payload.get("as_of")),
        "status": "verified",
        "is_citable": True,
        "payload_json": _sanitize_json(item),
        "availability_json": _sanitize_json_dict(provider_payload.get("availability")),
        "provider_capabilities_json": _sanitize_json_dict(provider_payload.get("provider_capabilities")),
        "diagnostics_json": diagnostics,
        "imported_at": imported_at,
        "updated_at": imported_at,
    }


def _build_event_identity(event_type: str, item: dict[str, object]) -> str | None:
    if event_type == "hot_sector":
        taxonomy = item.get("taxonomy") if isinstance(item.get("taxonomy"), dict) else {}
        raw_identity = item.get("sector_id") or taxonomy.get("normalized_sector_id") or item.get("name")
        return _normalize_identity_token(raw_identity)

    symbol = _normalize_identity_token(item.get("symbol"), uppercase=True)
    if not symbol:
        return None
    if event_type != "block_trade":
        if event_type not in CORPORATE_ACTION_EVENT_TYPES:
            return symbol
        fingerprint_source = "|".join(
            str(item.get(key) or "")
            for key in (
                "report_period",
                "trade_date",
                "announcement_date",
                "record_date",
                "ex_date",
                "cash_dividend_per_10",
                "bonus_shares_per_10",
                "transfer_shares_per_10",
                "payment_start_date",
                "payment_end_date",
                "rights_code",
                "rights_ratio",
                "rights_price",
            )
        )
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:12]
        return f"{symbol}-{fingerprint}"

    rank = item.get("rank")
    if isinstance(rank, int | float | str) and str(rank).strip():
        return f"{symbol}-rank-{_normalize_identity_token(rank)}"
    fingerprint_source = "|".join(
        str(item.get(key) or "")
        for key in ("buyer", "seller", "trade_price", "amount", "volume")
    )
    fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()[:12]
    return f"{symbol}-{fingerprint}"


def _build_identity_name(event_type: str, item: dict[str, object], identity: str) -> str:
    if event_type == "hot_sector":
        return _clean_text(item.get("name") or item.get("sector_name")) or identity
    name = _clean_text(item.get("name"))
    symbol = _clean_text(item.get("symbol"))
    if name and symbol:
        return f"{name} ({symbol})"
    return name or symbol or identity


def _update_existing_event(event: MarketDailyEvidenceEvent, values: dict[str, object]) -> bool:
    comparable_fields = (
        "identity_name",
        "source",
        "as_of",
        "status",
        "is_citable",
        "payload_json",
        "availability_json",
        "provider_capabilities_json",
        "diagnostics_json",
    )
    changed = any(
        not _stored_values_equal(getattr(event, field_name), values[field_name])
        for field_name in comparable_fields
    )
    if not changed:
        return False
    for field_name in comparable_fields:
        setattr(event, field_name, values[field_name])
    event.imported_at = values["imported_at"]
    event.updated_at = values["updated_at"]
    return True


def _stored_values_equal(left: object, right: object) -> bool:
    if isinstance(left, datetime) and isinstance(right, datetime):
        normalized_left = left if left.tzinfo else left.replace(tzinfo=timezone.utc)
        normalized_right = right if right.tzinfo else right.replace(tzinfo=timezone.utc)
        return normalized_left.astimezone(timezone.utc) == normalized_right.astimezone(timezone.utc)
    return left == right


def _apply_evidence_filters(
    query: Query,
    *,
    event_type: str | None,
    identity: str | None,
    symbol: str | None,
    market: str | None,
    trade_date: date | None,
    citable_only: bool,
) -> Query:
    if event_type:
        query = query.filter(MarketDailyEvidenceEvent.event_type == event_type)
    if identity:
        query = query.filter(MarketDailyEvidenceEvent.identity == identity)
    if symbol:
        query = query.filter(
            or_(
                MarketDailyEvidenceEvent.identity == symbol,
                MarketDailyEvidenceEvent.identity.like(f"{symbol}-%"),
            )
        )
    if market:
        query = query.filter(MarketDailyEvidenceEvent.market == market)
    if trade_date:
        query = query.filter(MarketDailyEvidenceEvent.trade_date == trade_date)
    if citable_only:
        query = query.filter(MarketDailyEvidenceEvent.is_citable.is_(True))
    return query


def _provider_payload_diagnostics(event_type: str, payload: dict[str, object]) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    raw_diagnostics = payload.get("diagnostics")
    if isinstance(raw_diagnostics, list):
        diagnostics.extend(
            item for item in (_sanitize_json(value) for value in raw_diagnostics) if isinstance(item, dict)
        )
    message = _clean_text(payload.get("message"))
    if message:
        diagnostics.append(
            {
                "source": "market_daily_provider",
                "status": _clean_text(payload.get("status")) or "unavailable",
                "severity": "warning" if payload.get("status") != "ok" else "info",
                "code": f"{event_type.upper()}_PROVIDER_STATUS",
                "event_type": event_type,
                "message": message,
            }
        )
    return diagnostics


def _build_citation_excerpt(event: MarketDailyEvidenceEvent) -> str:
    payload = event.payload_json or {}
    label = event.identity_name or event.identity
    if event.event_type == "stock_fund_flow":
        detail = payload.get("main_net_flow_amount") or payload.get("net_flow_amount")
        return _clip_text(f"{label} fund-flow context on {event.trade_date.isoformat()}: {detail if detail is not None else 'value unavailable'}.", 500)
    if event.event_type == "limit_up_reason":
        reason = payload.get("reason") or "provider limit-up pool context; reason unavailable"
        return _clip_text(f"{label} limit-up context on {event.trade_date.isoformat()}: {reason}.", 500)
    if event.event_type == "dragon_tiger_list":
        return _clip_text(
            f"{label} Dragon Tiger List context on {event.trade_date.isoformat()}; net buy amount {payload.get('net_buy_amount', 'unavailable')}.",
            500,
        )
    if event.event_type == "block_trade":
        return _clip_text(
            f"{label} block-trade context on {event.trade_date.isoformat()}; amount {payload.get('amount', 'unavailable')}.",
            500,
        )
    if event.event_type == "dividend_bonus":
        return _clip_text(
            f"{label} dividend/bonus context on {event.trade_date.isoformat()}; cash per 10 shares "
            f"{payload.get('cash_dividend_per_10', 'unavailable')}, bonus shares "
            f"{payload.get('bonus_shares_per_10', 'unavailable')}, transfer shares "
            f"{payload.get('transfer_shares_per_10', 'unavailable')}.",
            500,
        )
    if event.event_type == "rights_allotment":
        return _clip_text(
            f"{label} rights-allotment context on {event.trade_date.isoformat()}; ratio "
            f"{payload.get('rights_ratio', 'unavailable')}, price "
            f"{payload.get('rights_price', 'unavailable')}.",
            500,
        )
    return _clip_text(
        f"{label} hot-sector context on {event.trade_date.isoformat()}; fund flow {payload.get('fund_flow', 'unavailable')}.",
        500,
    )


def _normalize_market(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


def _normalize_identity_token(value: object, *, uppercase: bool = False) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    normalized = re.sub(r"[^A-Za-z0-9_.+\-]+", "-", text).strip("-")
    if not normalized:
        return None
    bounded = normalized[:256]
    return bounded.upper() if uppercase else bounded


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _clean_text(value)
    if not text:
        return None
    normalized = text[:10]
    if len(text) >= 8 and text[:8].isdigit():
        normalized = f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        return None


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = _clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed_date = _parse_date(text)
        return (
            datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=timezone.utc)
            if parsed_date
            else None
        )
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _sanitize_json_dict(value: object) -> dict[str, object]:
    sanitized = _sanitize_json(value)
    return sanitized if isinstance(sanitized, dict) else {}


def _sanitize_json(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_json(item)
            for key, item in value.items()
            if not _is_sensitive_key(str(key))
        }
    if isinstance(value, list | tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, str):
        return _clip_text(_redact_sensitive_text(value), MAX_TEXT_LENGTH)
    if value is None or isinstance(value, bool | int | float):
        return value
    return _clip_text(str(value), MAX_TEXT_LENGTH)


def _is_sensitive_key(value: str) -> bool:
    normalized = value.strip().lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return _clip_text(_redact_sensitive_text(text), MAX_TEXT_LENGTH) if text else None


def _redact_sensitive_text(value: str) -> str:
    return re.sub(
        r"(?i)\b(api[_-]?key|access[_-]?token|token|authorization|cookie|password|secret)\b\s*[:=]\s*[^\s,;]+",
        r"\1=[redacted]",
        value,
    )


def _clip_text(value: str | None, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _safety_payload() -> dict[str, bool]:
    return {
        "persisted_rows_only": True,
        "not_investment_advice": True,
        "no_buy_sell_hold": True,
        "no_automated_trading": True,
    }
