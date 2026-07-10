from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from packages.domain.models import Instrument, Market
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.base import CorporateActionProvider, ProviderCorporateActionSnapshot
from packages.services.market_daily_evidence import (
    CORPORATE_ACTION_EVENT_TYPES,
    MarketDailyEvidenceImportInput,
    import_market_daily_evidence,
)


CorporateActionProgressCallback = Callable[[str, int, int, str], None]


@dataclass(frozen=True)
class CorporateActionSyncInput:
    report_period: date
    market: str = "CN"
    provider_name: str = "akshare"
    symbols: tuple[str, ...] = ()
    event_types: tuple[str, ...] = CORPORATE_ACTION_EVENT_TYPES
    cursor: int = 0
    batch_size: int = 50


def sync_corporate_action_evidence(
    payload: CorporateActionSyncInput,
    *,
    session: Session,
    provider: CorporateActionProvider | None = None,
    progress_callback: CorporateActionProgressCallback | None = None,
) -> dict[str, object]:
    normalized = _normalize_sync_input(payload)
    all_symbols = list(normalized.symbols) or _active_a_share_symbols(session)
    total_symbols = len(all_symbols)
    batch_symbols = all_symbols[
        normalized.cursor : normalized.cursor + normalized.batch_size
    ]
    next_cursor = (
        normalized.cursor + len(batch_symbols)
        if normalized.cursor + len(batch_symbols) < total_symbols
        else None
    )
    total_steps = len(normalized.event_types) + 1
    _report_progress(
        progress_callback,
        "preparing",
        0,
        total_steps,
        "Prepared the deterministic corporate-action symbol batch.",
    )
    if not batch_symbols:
        return {
            "status": "no_data",
            "report_period": normalized.report_period.isoformat(),
            "market": normalized.market,
            "provider": normalized.provider_name,
            "symbols": [],
            "cursor": normalized.cursor,
            "next_cursor": None,
            "total_symbols": total_symbols,
            "event_results": [],
            "evidence": None,
            "diagnostics": [
                {
                    "code": "CORPORATE_ACTION_BATCH_EMPTY",
                    "message": "No symbols are available at the requested batch cursor.",
                }
            ],
            "retry": {"cursor": normalized.cursor, "failed_event_types": []},
            "safety": _safety_payload(),
        }

    resolved_provider = provider or AkShareProvider()
    normalized_payloads: dict[str, dict[str, object]] = {}
    event_results: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    failed_event_types: list[str] = []
    degraded_event_types: list[str] = []
    failed_symbols: set[str] = set()

    for event_index, event_type in enumerate(normalized.event_types, start=1):
        try:
            snapshot = resolved_provider.fetch_corporate_actions(
                event_type,
                normalized.report_period,
                batch_symbols,
            )
            provider_payload = _snapshot_payload(snapshot, normalized.market)
        except Exception as exc:
            failed_event_types.append(event_type)
            provider_payload = _failed_provider_payload(
                event_type=event_type,
                report_period=normalized.report_period,
                market=normalized.market,
                provider_name=normalized.provider_name,
                exception_type=type(exc).__name__,
            )
        normalized_payloads[event_type] = provider_payload
        raw_diagnostics = provider_payload.get("diagnostics")
        if isinstance(raw_diagnostics, list):
            diagnostics.extend(item for item in raw_diagnostics if isinstance(item, dict))
            failed_symbols.update(_failed_symbols(raw_diagnostics))
        provider_status = str(provider_payload.get("status") or "unavailable")
        if provider_status == "unavailable" and event_type not in failed_event_types:
            failed_event_types.append(event_type)
        elif provider_status == "degraded":
            degraded_event_types.append(event_type)
        event_results.append(
            {
                "event_type": event_type,
                "status": provider_status,
                "source": provider_payload.get("source"),
                "item_count": len(provider_payload.get("items", [])),
                "diagnostics": raw_diagnostics if isinstance(raw_diagnostics, list) else [],
            }
        )
        _report_progress(
            progress_callback,
            f"fetching_{event_type}",
            event_index,
            total_steps,
            f"Fetched {event_type} evidence for the current symbol batch.",
        )

    evidence = import_market_daily_evidence(
        MarketDailyEvidenceImportInput(
            trade_date=normalized.report_period,
            market=normalized.market,
            provider_name=normalized.provider_name,
            event_types=normalized.event_types,
            limit=100,
        ),
        session=session,
        normalized_payloads=normalized_payloads,
    )
    _report_progress(
        progress_callback,
        "persisted",
        total_steps,
        total_steps,
        "Persisted citable corporate-action evidence for the current batch.",
    )
    if failed_event_types and len(failed_event_types) == len(normalized.event_types):
        status = "failed"
    elif failed_event_types or degraded_event_types:
        status = "partial"
    else:
        status = str(evidence.get("status") or "degraded")
    return {
        "status": status,
        "report_period": normalized.report_period.isoformat(),
        "market": normalized.market,
        "provider": normalized.provider_name,
        "event_types": list(normalized.event_types),
        "symbols": batch_symbols,
        "cursor": normalized.cursor,
        "next_cursor": next_cursor,
        "batch_size": normalized.batch_size,
        "processed_symbol_count": len(batch_symbols),
        "total_symbols": total_symbols,
        "complete": next_cursor is None,
        "event_results": event_results,
        "evidence": evidence,
        "diagnostics": diagnostics,
        "retry": {
            "cursor": normalized.cursor,
            "next_cursor": next_cursor,
            "failed_event_types": failed_event_types,
            "degraded_event_types": degraded_event_types,
            "failed_symbols": sorted(failed_symbols),
        },
        "safety": _safety_payload(),
    }


def _normalize_sync_input(payload: CorporateActionSyncInput) -> CorporateActionSyncInput:
    market = payload.market.strip().upper()
    provider_name = payload.provider_name.strip().lower()
    if market != "CN":
        raise ValueError(f"Unsupported corporate-action market: {payload.market}")
    if provider_name != "akshare":
        raise ValueError(f"Unsupported corporate-action provider: {payload.provider_name}")
    event_types: list[str] = []
    for raw_event_type in payload.event_types:
        event_type = raw_event_type.strip().lower()
        if event_type not in CORPORATE_ACTION_EVENT_TYPES:
            raise ValueError(f"Unsupported corporate-action event type: {raw_event_type}")
        if event_type not in event_types:
            event_types.append(event_type)
    if not event_types:
        raise ValueError("At least one corporate-action event type is required.")
    symbols = tuple(
        sorted({symbol.strip().upper() for symbol in payload.symbols if symbol.strip()})
    )
    return CorporateActionSyncInput(
        report_period=payload.report_period,
        market=market,
        provider_name=provider_name,
        symbols=symbols,
        event_types=tuple(event_types),
        cursor=max(0, payload.cursor),
        batch_size=max(1, min(payload.batch_size, 100)),
    )


def _active_a_share_symbols(session: Session) -> list[str]:
    rows = (
        session.query(Instrument.symbol)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == "CN")
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .order_by(Instrument.symbol)
        .all()
    )
    return [str(symbol).upper() for (symbol,) in rows]


def _snapshot_payload(
    snapshot: ProviderCorporateActionSnapshot,
    market: str,
) -> dict[str, object]:
    return {
        "status": snapshot.status,
        "data_mode": "delayed",
        "source": snapshot.source,
        "provider": snapshot.provider,
        "requested_provider": snapshot.provider,
        "effective_provider": snapshot.provider,
        "market": market,
        "report_period": snapshot.report_period.isoformat(),
        "as_of": snapshot.as_of.isoformat() if snapshot.as_of else None,
        "availability": snapshot.availability,
        "provider_capabilities": {
            "corporate_actions": {"status": "delayed", "event_type": snapshot.event_type}
        },
        "count": len(snapshot.items),
        "items": snapshot.items,
        "diagnostics": snapshot.diagnostics,
    }


def _failed_provider_payload(
    *,
    event_type: str,
    report_period: date,
    market: str,
    provider_name: str,
    exception_type: str,
) -> dict[str, object]:
    diagnostic = {
        "code": "CORPORATE_ACTION_PROVIDER_FAILED",
        "message": "The corporate-action provider request failed.",
        "details": {"event_type": event_type, "exception_type": exception_type},
    }
    return {
        "status": "unavailable",
        "data_mode": "none",
        "source": "provider_error",
        "provider": provider_name,
        "effective_provider": provider_name,
        "market": market,
        "report_period": report_period.isoformat(),
        "items": [],
        "diagnostics": [diagnostic],
    }


def _failed_symbols(diagnostics: list[object]) -> set[str]:
    symbols: set[str] = set()
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, dict):
            continue
        details = diagnostic.get("details")
        if isinstance(details, dict) and details.get("symbol"):
            symbols.add(str(details["symbol"]).upper())
    return symbols


def _report_progress(
    callback: CorporateActionProgressCallback | None,
    phase: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is not None:
        callback(phase, current, total, message)


def _safety_payload() -> dict[str, bool]:
    return {
        "persisted_rows_only": True,
        "not_investment_advice": True,
        "no_automated_trading": True,
    }
