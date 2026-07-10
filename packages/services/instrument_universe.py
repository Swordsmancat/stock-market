from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.domain.models import Exchange, Instrument, InstrumentUniverseSync, Market
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.base import InstrumentUniverseProvider, ProviderInstrumentUniverseSnapshot

SUPPORTED_UNIVERSE_MARKET = "CN"
SUPPORTED_UNIVERSE_PROVIDER = "akshare"
MARKET_NAME = "China"
MARKET_TIMEZONE = "Asia/Shanghai"
MARKET_CURRENCY = "CNY"
EXCHANGE_NAMES = {
    "SSE": "Shanghai Stock Exchange",
    "SZSE": "Shenzhen Stock Exchange",
    "BSE": "Beijing Stock Exchange",
}


def sync_instrument_universe(
    *,
    session: Session,
    market: str = SUPPORTED_UNIVERSE_MARKET,
    provider_name: str = SUPPORTED_UNIVERSE_PROVIDER,
    provider: InstrumentUniverseProvider | None = None,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    normalized_provider = provider_name.strip().lower()
    if normalized_market != SUPPORTED_UNIVERSE_MARKET:
        raise ValueError(f"Unsupported instrument universe market: {market}")
    if normalized_provider != SUPPORTED_UNIVERSE_PROVIDER:
        raise ValueError(f"Unsupported instrument universe provider: {provider_name}")

    resolved_provider = provider or AkShareProvider()
    try:
        snapshot = resolved_provider.fetch_instrument_universe(normalized_market)
    except Exception as exc:
        return _record_unavailable_sync(
            session=session,
            market=normalized_market,
            provider=normalized_provider,
            source="akshare.stock_info_a_code_name",
            status="failed",
            availability={
                "status": "unavailable",
                "reason": "The instrument-universe provider request failed.",
            },
            diagnostics=[
                {
                    "code": "INSTRUMENT_UNIVERSE_PROVIDER_FAILED",
                    "message": "The provider could not return an A-share universe snapshot.",
                    "details": {"exception_type": type(exc).__name__},
                }
            ],
        )

    if not snapshot.items:
        return _record_unavailable_sync(
            session=session,
            market=normalized_market,
            provider=snapshot.provider or normalized_provider,
            source=snapshot.source,
            status=snapshot.status,
            availability=snapshot.availability,
            diagnostics=snapshot.diagnostics,
            as_of=snapshot.as_of,
        )

    return _reconcile_snapshot(session=session, snapshot=snapshot)


def get_instrument_universe_status(
    *,
    session: Session,
    market: str = SUPPORTED_UNIVERSE_MARKET,
    provider_name: str = SUPPORTED_UNIVERSE_PROVIDER,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    normalized_provider = provider_name.strip().lower()
    if normalized_market != SUPPORTED_UNIVERSE_MARKET:
        raise ValueError(f"Unsupported instrument universe market: {market}")
    if normalized_provider != SUPPORTED_UNIVERSE_PROVIDER:
        raise ValueError(f"Unsupported instrument universe provider: {provider_name}")
    latest = (
        session.query(InstrumentUniverseSync)
        .filter(InstrumentUniverseSync.market == normalized_market)
        .filter(InstrumentUniverseSync.provider == normalized_provider)
        .order_by(InstrumentUniverseSync.created_at.desc())
        .first()
    )
    market_row = session.query(Market).filter(Market.code == normalized_market).one_or_none()
    active_count = 0
    managed_count = 0
    if market_row is not None:
        active_count = (
            session.query(Instrument)
            .filter(Instrument.market_id == market_row.id)
            .filter(Instrument.asset_type == "stock")
            .filter(Instrument.is_active.is_(True))
            .count()
        )
        managed_count = (
            session.query(Instrument)
            .filter(Instrument.market_id == market_row.id)
            .filter(Instrument.asset_type == "stock")
            .filter(Instrument.universe_provider == normalized_provider)
            .count()
        )
    return {
        "market": normalized_market,
        "provider": normalized_provider,
        "status": latest.status if latest is not None else "not_synced",
        "active_instrument_count": active_count,
        "managed_instrument_count": managed_count,
        "latest_sync": serialize_instrument_universe_sync(latest) if latest is not None else None,
        "safety": {
            "local_evidence_only": True,
            "failed_refresh_preserves_last_good_universe": True,
            "no_automated_trading": True,
        },
    }


def serialize_instrument_universe_sync(sync: InstrumentUniverseSync) -> dict[str, object]:
    return {
        "id": str(sync.id),
        "market": sync.market,
        "provider": sync.provider,
        "source": sync.source,
        "as_of": _isoformat(sync.as_of),
        "status": sync.status,
        "total_count": sync.total_count,
        "inserted_count": sync.inserted_count,
        "updated_count": sync.updated_count,
        "unchanged_count": sync.unchanged_count,
        "reactivated_count": sync.reactivated_count,
        "deactivated_count": sync.deactivated_count,
        "skipped_count": sync.skipped_count,
        "availability": sync.availability_json,
        "diagnostics": sync.diagnostics_json,
        "created_at": _isoformat(sync.created_at),
    }


def _reconcile_snapshot(
    *,
    session: Session,
    snapshot: ProviderInstrumentUniverseSnapshot,
) -> dict[str, object]:
    provider = snapshot.provider.strip().lower()
    synced_at = _as_utc(snapshot.as_of) or datetime.now(timezone.utc)
    counts = {
        "inserted_count": 0,
        "updated_count": 0,
        "unchanged_count": 0,
        "reactivated_count": 0,
        "deactivated_count": 0,
        "skipped_count": _skipped_count(snapshot.diagnostics),
    }
    try:
        market = _get_or_create_market(session)
        exchanges = _get_or_create_exchanges(session, market)
        existing_rows = (
            session.query(Instrument)
            .filter(Instrument.market_id == market.id)
            .filter(Instrument.asset_type == "stock")
            .all()
        )
        existing_by_symbol = {row.symbol: row for row in existing_rows}
        seen_symbols: set[str] = set()

        for provider_instrument in snapshot.items:
            symbol = provider_instrument.symbol
            seen_symbols.add(symbol)
            exchange = exchanges[provider_instrument.exchange]
            instrument = existing_by_symbol.get(symbol)
            if instrument is None:
                instrument = Instrument(
                    symbol=symbol,
                    name=provider_instrument.name,
                    market=market,
                    exchange=exchange,
                    asset_type=provider_instrument.asset_type,
                    currency=provider_instrument.currency,
                    is_active=True,
                    universe_provider=provider,
                    universe_synced_at=synced_at,
                )
                session.add(instrument)
                existing_by_symbol[symbol] = instrument
                counts["inserted_count"] += 1
                continue

            was_active = instrument.is_active
            changed = any(
                (
                    instrument.name != provider_instrument.name,
                    instrument.exchange_id != exchange.id,
                    instrument.asset_type != provider_instrument.asset_type,
                    instrument.currency != provider_instrument.currency,
                    instrument.universe_provider != provider,
                )
            )
            instrument.name = provider_instrument.name
            instrument.exchange = exchange
            instrument.asset_type = provider_instrument.asset_type
            instrument.currency = provider_instrument.currency
            instrument.is_active = True
            instrument.universe_provider = provider
            instrument.universe_synced_at = synced_at
            if not was_active:
                counts["reactivated_count"] += 1
            elif changed:
                counts["updated_count"] += 1
            else:
                counts["unchanged_count"] += 1

        if snapshot.is_complete:
            for instrument in existing_rows:
                if (
                    instrument.universe_provider == provider
                    and instrument.is_active
                    and instrument.symbol not in seen_symbols
                ):
                    instrument.is_active = False
                    counts["deactivated_count"] += 1

        sync = InstrumentUniverseSync(
            market=SUPPORTED_UNIVERSE_MARKET,
            provider=provider,
            source=snapshot.source,
            as_of=synced_at,
            status=snapshot.status,
            total_count=len(snapshot.items),
            availability_json=_sanitize_mapping(snapshot.availability),
            diagnostics_json=_sanitize_diagnostics(snapshot.diagnostics),
            created_at=datetime.now(timezone.utc),
            **counts,
        )
        session.add(sync)
        session.commit()
        session.refresh(sync)
    except SQLAlchemyError as exc:
        session.rollback()
        raise RuntimeError("Instrument universe storage failed.") from exc

    return {
        "status": snapshot.status,
        "market": SUPPORTED_UNIVERSE_MARKET,
        "provider": provider,
        "source": snapshot.source,
        "is_complete": snapshot.is_complete,
        "counts": {"total_count": len(snapshot.items), **counts},
        "diagnostics": _sanitize_diagnostics(snapshot.diagnostics),
        "sync": serialize_instrument_universe_sync(sync),
        "safety": {
            "failed_refresh_preserves_last_good_universe": True,
            "no_automated_trading": True,
        },
    }


def _record_unavailable_sync(
    *,
    session: Session,
    market: str,
    provider: str,
    source: str,
    status: str,
    availability: dict[str, object],
    diagnostics: list[dict[str, object]],
    as_of: datetime | None = None,
) -> dict[str, object]:
    sync = InstrumentUniverseSync(
        market=market,
        provider=provider,
        source=source,
        as_of=_as_utc(as_of),
        status=status,
        total_count=0,
        inserted_count=0,
        updated_count=0,
        unchanged_count=0,
        reactivated_count=0,
        deactivated_count=0,
        skipped_count=0,
        availability_json=_sanitize_mapping(availability),
        diagnostics_json=_sanitize_diagnostics(diagnostics),
        created_at=datetime.now(timezone.utc),
    )
    try:
        session.add(sync)
        session.commit()
        session.refresh(sync)
    except SQLAlchemyError as exc:
        session.rollback()
        raise RuntimeError("Instrument universe status storage failed.") from exc
    return {
        "status": status,
        "market": market,
        "provider": provider,
        "source": source,
        "is_complete": False,
        "counts": {
            "total_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "unchanged_count": 0,
            "reactivated_count": 0,
            "deactivated_count": 0,
            "skipped_count": 0,
        },
        "diagnostics": sync.diagnostics_json,
        "sync": serialize_instrument_universe_sync(sync),
        "safety": {
            "failed_refresh_preserves_last_good_universe": True,
            "no_automated_trading": True,
        },
    }


def _get_or_create_market(session: Session) -> Market:
    market = session.query(Market).filter(Market.code == SUPPORTED_UNIVERSE_MARKET).one_or_none()
    if market is None:
        market = Market(
            code=SUPPORTED_UNIVERSE_MARKET,
            name=MARKET_NAME,
            timezone=MARKET_TIMEZONE,
            currency=MARKET_CURRENCY,
            trading_calendar_code="XSHG",
        )
        session.add(market)
        session.flush()
    return market


def _get_or_create_exchanges(session: Session, market: Market) -> dict[str, Exchange]:
    rows = session.query(Exchange).filter(Exchange.market_id == market.id).all()
    exchanges = {row.code: row for row in rows}
    for code, name in EXCHANGE_NAMES.items():
        if code not in exchanges:
            exchange = Exchange(market=market, code=code, name=name)
            session.add(exchange)
            session.flush()
            exchanges[code] = exchange
    return exchanges


def _sanitize_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): _sanitize_value(item)
        for key, item in value.items()
        if not _sensitive_key(str(key))
    }


def _sanitize_diagnostics(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [_sanitize_mapping(item) for item in value if isinstance(item, dict)]


def _sanitize_value(value: object) -> object:
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, datetime):
        return _isoformat(value)
    if isinstance(value, str):
        return value[:1000]
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)[:1000]


def _sensitive_key(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(token in normalized for token in ("api_key", "token", "secret", "password", "cookie"))


def _skipped_count(diagnostics: list[dict[str, object]]) -> int:
    for diagnostic in diagnostics:
        if diagnostic.get("code") != "INSTRUMENT_UNIVERSE_ROWS_SKIPPED":
            continue
        details = diagnostic.get("details")
        if isinstance(details, dict):
            try:
                return max(0, int(details.get("skipped_count", 0)))
            except (TypeError, ValueError):
                return 0
    return 0


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _isoformat(value: datetime | None) -> str | None:
    normalized = _as_utc(value)
    return normalized.isoformat() if normalized is not None else None
