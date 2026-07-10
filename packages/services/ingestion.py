from collections.abc import Sequence
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.base import ProviderBar
from packages.services.daily_bar_sources import (
    STRICT_POLICY,
    DailyBarFetchCoordinator,
    DailyBarSource,
)
from packages.services.data_quality import DataQualityStatus, check_daily_bar_quality
from packages.services.market_data import get_market_snapshot, get_provider, resolve_market_data_provider_name
from packages.services.market_data import serialize_bar
from packages.services.platform_settings import get_platform_settings


MARKET_META = {
    "CN": {"name": "China A Share", "timezone": "Asia/Shanghai", "currency": "CNY"},
    "HK": {"name": "Hong Kong Stock", "timezone": "Asia/Hong_Kong", "currency": "HKD"},
    "US": {"name": "US Stock", "timezone": "America/New_York", "currency": "USD"},
}


def _get_or_create_market(session: Session, code: str) -> Market:
    market = session.query(Market).filter(Market.code == code).one_or_none()
    if market is not None:
        return market
    meta = MARKET_META.get(code, {"name": code, "timezone": "UTC", "currency": "USD"})
    market = Market(
        code=code,
        name=meta["name"],
        timezone=meta["timezone"],
        currency=meta["currency"],
    )
    session.add(market)
    session.flush()
    return market


def _get_or_create_instrument(
    session: Session,
    market: Market,
    symbol: str,
    name: str,
    asset_type: str,
    currency: str,
) -> Instrument:
    instrument = (
        session.query(Instrument)
        .filter(Instrument.market_id == market.id)
        .filter(Instrument.symbol == symbol)
        .one_or_none()
    )
    if instrument is not None:
        return instrument
    instrument = Instrument(
        symbol=symbol,
        name=name,
        market=market,
        asset_type=asset_type,
        currency=currency,
    )
    session.add(instrument)
    session.flush()
    return instrument


def _get_serialized_instruments(snapshot: dict[str, object]) -> list[dict[str, object]]:
    serialized_instruments = snapshot.get("instruments")
    if not isinstance(serialized_instruments, list):
        msg = "Serialized market snapshot must contain an instruments list."
        raise ValueError(msg)

    for serialized_instrument in serialized_instruments:
        if not isinstance(serialized_instrument, dict):
            msg = "Serialized market snapshot instruments must be objects."
            raise ValueError(msg)

    return serialized_instruments


def _get_serialized_bars(serialized_instrument: dict[str, object]) -> list[dict[str, object]]:
    serialized_bars = serialized_instrument.get("bars", [])
    if not isinstance(serialized_bars, list):
        symbol = serialized_instrument.get("symbol", "<unknown>")
        msg = f"Serialized instrument {symbol!r} must contain a bars list."
        raise ValueError(msg)

    for serialized_bar in serialized_bars:
        if not isinstance(serialized_bar, dict):
            symbol = serialized_instrument.get("symbol", "<unknown>")
            msg = f"Serialized bars for instrument {symbol!r} must be objects."
            raise ValueError(msg)

    return serialized_bars


def _get_required_string(serialized_payload: dict[str, object], field_name: str) -> str:
    value = serialized_payload.get(field_name)
    if isinstance(value, str) and value:
        return value

    msg = f"Serialized payload field {field_name!r} must be a non-empty string."
    raise ValueError(msg)


def _parse_serialized_bar_date(serialized_timestamp: object) -> date:
    if isinstance(serialized_timestamp, datetime):
        return serialized_timestamp.date()
    if isinstance(serialized_timestamp, date):
        return serialized_timestamp
    if isinstance(serialized_timestamp, str):
        try:
            return date.fromisoformat(serialized_timestamp)
        except ValueError:
            try:
                return datetime.fromisoformat(
                    serialized_timestamp.replace("Z", "+00:00")
                ).date()
            except ValueError as timestamp_error:
                msg = f"Unsupported serialized bar timestamp: {serialized_timestamp!r}"
                raise ValueError(msg) from timestamp_error

    msg = f"Unsupported serialized bar timestamp: {serialized_timestamp!r}"
    raise ValueError(msg)


def _parse_serialized_decimal(serialized_value: object, field_name: str) -> Decimal:
    if serialized_value is None:
        msg = f"Serialized bar field {field_name!r} is required."
        raise ValueError(msg)

    try:
        parsed_value = Decimal(str(serialized_value))
    except (InvalidOperation, ValueError) as decimal_error:
        msg = f"Unsupported serialized numeric value for {field_name!r}: {serialized_value!r}"
        raise ValueError(msg) from decimal_error

    if not parsed_value.is_finite():
        msg = f"Unsupported serialized numeric value for {field_name!r}: {serialized_value!r}"
        raise ValueError(msg)

    return parsed_value


def _parse_optional_serialized_decimal(
    serialized_value: object,
    field_name: str,
) -> Decimal | None:
    if serialized_value is None:
        return None
    return _parse_serialized_decimal(serialized_value, field_name)


def _count_serialized_snapshot_bars(snapshot: dict[str, object]) -> int:
    return sum(
        len(_get_serialized_bars(serialized_instrument))
        for serialized_instrument in _get_serialized_instruments(snapshot)
    )


def _normalize_optional_provider_name(provider_name: str | None) -> str | None:
    if provider_name is None:
        return None
    normalized = provider_name.strip().lower()
    return normalized or None


def _normalize_optional_exchange(exchange: str | None, market_code: str) -> str:
    if exchange is None or not exchange.strip():
        return market_code
    return exchange.strip().upper()


def _normalize_asset_type(asset_type: str | None) -> str:
    normalized = (asset_type or "stock").strip().lower()
    if normalized in {"stock", "etf"}:
        return normalized
    msg = f"Unsupported asset_type for symbol daily bars: {asset_type}"
    raise ValueError(msg)


def normalize_symbol_list(symbols: str | Sequence[str]) -> list[str]:
    raw_symbols = symbols.split(",") if isinstance(symbols, str) else symbols
    normalized_symbols: list[str] = []
    seen_symbols: set[str] = set()
    for symbol in raw_symbols:
        normalized_symbol = str(symbol).strip().upper()
        if not normalized_symbol or normalized_symbol in seen_symbols:
            continue
        normalized_symbols.append(normalized_symbol)
        seen_symbols.add(normalized_symbol)

    if not normalized_symbols:
        msg = "At least one symbol is required for batch daily bar ingestion."
        raise ValueError(msg)

    return normalized_symbols


def _get_market_currency(market_code: str) -> str:
    return MARKET_META.get(market_code, {"currency": "USD"})["currency"]


def _build_symbol_daily_bars_snapshot(
    *,
    symbol: str,
    market: str,
    exchange: str | None,
    timeframe: str,
    asset_type: str,
    start: date,
    end: date,
    requested_provider: str | None,
    effective_provider: str,
    source: str,
    adjustment: str,
    source_priority: int,
    daily_bar_policy: str,
    fallback_used: bool,
    source_attempts: list[dict[str, object]],
    bars: list[ProviderBar],
) -> dict[str, object]:
    serialized_bars = [serialize_bar(bar) for bar in bars]
    return {
        "market": market,
        "provider": effective_provider,
        "requested_provider": requested_provider,
        "effective_provider": effective_provider,
        "source": source,
        "adjustment": adjustment,
        "source_priority": source_priority,
        "daily_bar_policy": daily_bar_policy,
        "fallback_used": fallback_used,
        "source_attempts": source_attempts,
        "timeframe": timeframe,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "instrument_count": 1,
        "instruments": [
            {
                "symbol": symbol,
                "name": symbol,
                "exchange": _normalize_optional_exchange(exchange, market),
                "asset_type": asset_type,
                "currency": _get_market_currency(market),
                "bars": serialized_bars,
            }
        ],
    }


def _write_serialized_snapshot_to_database(
    market_code: str,
    snapshot: dict[str, object],
    session: Session,
) -> int:
    market = _get_or_create_market(session, market_code)
    daily_bars_by_key: dict[tuple[int, date], DailyBar] = {}
    bar_count = 0
    incoming_provider = str(snapshot.get("effective_provider") or "legacy_unknown")
    incoming_source = str(snapshot.get("source") or "legacy_unknown")
    incoming_adjustment = str(snapshot.get("adjustment") or "legacy_unknown")
    incoming_priority = int(snapshot.get("source_priority", 99))
    for serialized_instrument in _get_serialized_instruments(snapshot):
        instrument = _get_or_create_instrument(
            session=session,
            market=market,
            symbol=_get_required_string(serialized_instrument, "symbol"),
            name=_get_required_string(serialized_instrument, "name"),
            asset_type=_get_required_string(serialized_instrument, "asset_type"),
            currency=_get_required_string(serialized_instrument, "currency"),
        )
        for serialized_bar in _get_serialized_bars(serialized_instrument):
            trade_date = _parse_serialized_bar_date(serialized_bar.get("timestamp"))
            daily_bar_key = (instrument.id, trade_date)
            daily_bar = daily_bars_by_key.get(daily_bar_key)
            if daily_bar is None:
                daily_bar = session.get(DailyBar, daily_bar_key)
            if daily_bar is None:
                daily_bar = DailyBar(instrument_id=instrument.id, trade_date=trade_date)
                session.add(daily_bar)
            daily_bars_by_key[daily_bar_key] = daily_bar
            existing_priority = (
                int(daily_bar.source_priority) if daily_bar.source_priority is not None else 99
            )
            if daily_bar.open is not None and existing_priority < incoming_priority:
                bar_count += 1
                continue
            daily_bar.open = _parse_serialized_decimal(serialized_bar.get("open"), "open")
            daily_bar.high = _parse_serialized_decimal(serialized_bar.get("high"), "high")
            daily_bar.low = _parse_serialized_decimal(serialized_bar.get("low"), "low")
            daily_bar.close = _parse_serialized_decimal(serialized_bar.get("close"), "close")
            daily_bar.volume = _parse_serialized_decimal(serialized_bar.get("volume"), "volume")
            daily_bar.amount = _parse_optional_serialized_decimal(
                serialized_bar.get("amount"),
                "amount",
            )
            daily_bar.provider = incoming_provider
            daily_bar.source = incoming_source
            daily_bar.adjustment = incoming_adjustment
            daily_bar.source_priority = incoming_priority
            daily_bar.ingested_at = datetime.now(timezone.utc)
            bar_count += 1
    session.commit()
    return bar_count


def _combine_quality_statuses(quality_statuses: list[DataQualityStatus]) -> DataQualityStatus:
    if not quality_statuses:
        return "FAIL"
    if "FAIL" in quality_statuses:
        return "FAIL"
    if "WARN" in quality_statuses:
        return "WARN"
    return "OK"


def _build_quality_diagnostics(snapshot: dict[str, object]) -> dict[str, object]:
    instrument_diagnostics: list[dict[str, object]] = []
    quality_statuses: list[DataQualityStatus] = []
    serialized_instruments = snapshot["instruments"]

    if not serialized_instruments:
        return {
            "status": "FAIL",
            "instrument_count": 0,
            "instruments": [],
            "quality_error": "No instruments available for quality diagnostics.",
        }

    for serialized_instrument in serialized_instruments:
        serialized_bars = serialized_instrument.get("bars", [])
        try:
            quality_result_payload = check_daily_bar_quality(serialized_bars).to_dict()
        except Exception as quality_error:
            # Diagnostics should surface quality-check failures without interrupting ingestion.
            quality_result_payload = {
                "checked_bars": len(serialized_bars) if isinstance(serialized_bars, list) else 0,
                "missing_dates": [],
                "invalid_ohlc": [],
                "volume_warnings": [],
                "status": "FAIL",
                "quality_error": str(quality_error),
            }

        quality_status = quality_result_payload["status"]
        quality_statuses.append(quality_status)
        instrument_diagnostics.append(
            {
                "symbol": serialized_instrument.get("symbol"),
                **quality_result_payload,
            }
        )

    return {
        "status": _combine_quality_statuses(quality_statuses),
        "instrument_count": len(instrument_diagnostics),
        "instruments": instrument_diagnostics,
    }


def ingest_mock_market_snapshot(
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    return ingest_market_snapshot(
        market=market,
        start=start,
        end=end,
        session=session,
        provider_name=provider_name,
    )


def ingest_market_snapshot(
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    provider_name = provider_name.lower()
    snapshot = get_market_snapshot(market, start, end, provider_name=provider_name)
    bar_count = (
        _write_serialized_snapshot_to_database(market, snapshot, session)
        if session is not None
        else _count_serialized_snapshot_bars(snapshot)
    )
    return {
        **snapshot,
        "bar_count": bar_count,
        "quality_diagnostics": _build_quality_diagnostics(snapshot),
        "status": "ingested",
    }


def ingest_symbol_daily_bars(
    symbol: str,
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str | None = None,
    exchange: str | None = None,
    timeframe: str = "1d",
    asset_type: str | None = "stock",
    daily_bar_policy: str = STRICT_POLICY,
    fetch_coordinator: DailyBarFetchCoordinator | None = None,
) -> dict[str, object]:
    normalized_symbol = symbol.strip().upper()
    normalized_market = market.strip().upper()
    normalized_timeframe = timeframe.strip().lower()
    if normalized_timeframe != "1d":
        msg = f"Only daily bar ingestion is supported. Received timeframe: {timeframe}"
        raise ValueError(msg)

    requested_provider_name = _normalize_optional_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)
    normalized_asset_type = _normalize_asset_type(asset_type)
    coordinator = fetch_coordinator or build_daily_bar_fetch_coordinator(effective_provider_name)
    fetch_result = coordinator.fetch(
        normalized_symbol,
        normalized_timeframe,
        start,
        end,
        policy=daily_bar_policy,
    )
    if fetch_result.status == "failed":
        raise ConnectionError("All eligible daily-bar sources failed validation or retrieval.")
    bars = fetch_result.bars
    snapshot = _build_symbol_daily_bars_snapshot(
        symbol=normalized_symbol,
        market=normalized_market,
        exchange=exchange,
        timeframe=normalized_timeframe,
        asset_type=normalized_asset_type,
        start=start,
        end=end,
        requested_provider=requested_provider_name,
        effective_provider=fetch_result.effective_provider or effective_provider_name,
        source=fetch_result.source or "none",
        adjustment=fetch_result.adjustment or "unknown",
        source_priority=fetch_result.source_priority if fetch_result.source_priority is not None else 99,
        daily_bar_policy=fetch_result.policy,
        fallback_used=fetch_result.fallback_used,
        source_attempts=fetch_result.attempts,
        bars=bars,
    )
    bar_count = (
        _write_serialized_snapshot_to_database(normalized_market, snapshot, session)
        if session is not None
        else _count_serialized_snapshot_bars(snapshot)
    )
    no_data_reason = None if bars else "Provider returned no daily bars for the requested symbol/date range."
    return {
        **snapshot,
        "symbol": normalized_symbol,
        "bar_count": bar_count,
        "quality_diagnostics": _build_quality_diagnostics(snapshot),
        "status": "ingested" if bars else "no_data",
        "no_data_reason": no_data_reason,
    }


def build_daily_bar_fetch_coordinator(provider_name: str) -> DailyBarFetchCoordinator:
    normalized_provider = resolve_market_data_provider_name(provider_name)
    primary = get_provider(normalized_provider)
    primary_source = {
        "akshare": "akshare.stock_zh_a_hist",
        "tushare": "tushare.pro.daily",
    }.get(normalized_provider, f"{normalized_provider}.fetch_bars")
    sources = [
        DailyBarSource(
            provider=normalized_provider,
            source=primary_source,
            adjustment="qfq" if normalized_provider in {"akshare", "tushare"} else "provider_default",
            priority=0,
            fetch=primary.fetch_bars,
            min_interval_seconds=0.25 if normalized_provider == "akshare" else 0.0,
        )
    ]
    if normalized_provider == "akshare":
        sina = AkShareProvider(downloader=AkShareProvider.download_sina_daily_bars)
        settings_payload = get_platform_settings()
        tushare_configured = bool(str(settings_payload.get("tushare_token", "") or "").strip())
        tushare = get_provider("tushare")
        sources.extend(
            [
                DailyBarSource(
                    provider="akshare",
                    source="akshare.stock_zh_a_daily",
                    adjustment="qfq",
                    priority=1,
                    fetch=sina.fetch_bars,
                    min_interval_seconds=0.5,
                ),
                DailyBarSource(
                    provider="tushare",
                    source="tushare.pro.daily",
                    adjustment="qfq",
                    priority=2,
                    fetch=tushare.fetch_bars,
                    configured=tushare_configured,
                    min_interval_seconds=0.25,
                ),
            ]
        )
    return DailyBarFetchCoordinator(sources)


def _build_batch_status(
    *,
    symbol_count: int,
    succeeded_count: int,
    no_data_count: int,
    failed_count: int,
) -> str:
    if succeeded_count == symbol_count:
        return "ingested"
    if failed_count == symbol_count:
        return "failed"
    if no_data_count == symbol_count:
        return "no_data"
    return "partial"


def ingest_symbol_daily_bars_batch(
    symbols: str | Sequence[str],
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str | None = None,
    exchange: str | None = None,
    timeframe: str = "1d",
    asset_type: str | None = "stock",
) -> dict[str, object]:
    normalized_symbols = normalize_symbol_list(symbols)
    normalized_market = market.strip().upper()
    normalized_timeframe = timeframe.strip().lower()
    if normalized_timeframe != "1d":
        msg = f"Only daily bar ingestion is supported. Received timeframe: {timeframe}"
        raise ValueError(msg)

    normalized_asset_type = _normalize_asset_type(asset_type)
    requested_provider_name = _normalize_optional_provider_name(provider_name)
    items: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    succeeded_count = 0
    no_data_count = 0
    failed_count = 0
    total_bar_count = 0

    for normalized_symbol in normalized_symbols:
        try:
            result = ingest_symbol_daily_bars(
                symbol=normalized_symbol,
                market=normalized_market,
                start=start,
                end=end,
                session=session,
                provider_name=requested_provider_name,
                exchange=exchange,
                timeframe=normalized_timeframe,
                asset_type=normalized_asset_type,
            )
        except Exception as exc:
            if session is not None:
                session.rollback()
            failed_count += 1
            error_message = str(exc)
            diagnostics.append(
                {
                    "symbol": normalized_symbol,
                    "code": "SYMBOL_DAILY_BAR_INGESTION_FAILED",
                    "message": error_message,
                }
            )
            items.append(
                {
                    "symbol": normalized_symbol,
                    "market": normalized_market,
                    "asset_type": normalized_asset_type,
                    "status": "failed",
                    "instrument_count": 0,
                    "bar_count": 0,
                    "error": error_message,
                }
            )
            continue

        item_bar_count = int(result["bar_count"])
        item_status = str(result["status"])
        total_bar_count += item_bar_count
        if item_status == "ingested":
            succeeded_count += 1
        elif item_status == "no_data":
            no_data_count += 1
        else:
            failed_count += 1

        items.append(
            {
                "symbol": str(result["symbol"]),
                "market": str(result["market"]),
                "asset_type": str(result["instruments"][0]["asset_type"]),
                "status": item_status,
                "instrument_count": int(result["instrument_count"]),
                "bar_count": item_bar_count,
                "provider": str(result["provider"]),
                "requested_provider": result.get("requested_provider"),
                "effective_provider": str(result["effective_provider"]),
                "timeframe": str(result["timeframe"]),
                "no_data_reason": result.get("no_data_reason"),
                "quality_diagnostics": result["quality_diagnostics"],
            }
        )

    symbol_count = len(normalized_symbols)
    return {
        "symbols": normalized_symbols,
        "market": normalized_market,
        "asset_type": normalized_asset_type,
        "provider": requested_provider_name or resolve_market_data_provider_name(provider_name),
        "requested_provider": requested_provider_name,
        "timeframe": normalized_timeframe,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "symbol_count": symbol_count,
        "succeeded_count": succeeded_count,
        "no_data_count": no_data_count,
        "failed_count": failed_count,
        "total_bar_count": total_bar_count,
        "status": _build_batch_status(
            symbol_count=symbol_count,
            succeeded_count=succeeded_count,
            no_data_count=no_data_count,
            failed_count=failed_count,
        ),
        "items": items,
        "diagnostics": diagnostics,
    }
