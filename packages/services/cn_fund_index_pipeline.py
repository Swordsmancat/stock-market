from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
import time

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.base import InstrumentUniverseProvider
from packages.services.daily_bar_sources import CN_RESILIENT_POLICY
from packages.services.ingestion import (
    AKSHARE_ETF_HIST_EM_SOURCE,
    AKSHARE_ETF_HIST_SINA_SOURCE,
    AKSHARE_INDEX_DAILY_SOURCE,
    build_daily_bar_fetch_coordinator,
    ingest_symbol_daily_bars,
)
from packages.services.instrument_universe import sync_instrument_universe


CN_FUND_INDEX_PIPELINE_TASK_NAME = "ingestion.sync_cn_fund_index_data"
CN_FUND_INDEX_ASSET_TYPES = ("etf", "index")
CN_FUND_INDEX_INCREMENTAL_OVERLAP_DAYS = 7
ProgressCallback = Callable[[str, int, int, str], None]
BarIngestor = Callable[..., dict[str, object]]

EXPECTED_SOURCE_ADJUSTMENTS = {
    ("etf", AKSHARE_ETF_HIST_EM_SOURCE): "qfq",
    ("etf", AKSHARE_ETF_HIST_SINA_SOURCE): "raw",
    ("index", AKSHARE_INDEX_DAILY_SOURCE): "raw",
}


@dataclass(frozen=True)
class InstrumentRefreshState:
    symbol: str
    latest_date: date | None = None
    source: str | None = None
    adjustment: str | None = None


class CnFundIndexPipelineError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sync_cn_fund_index_data(
    *,
    session: Session,
    start: date,
    end: date,
    max_symbols_per_type: int,
    request_delay_seconds: float,
    incremental: bool = True,
    progress_callback: ProgressCallback | None = None,
    provider: InstrumentUniverseProvider | None = None,
    bar_ingestor: BarIngestor = ingest_symbol_daily_bars,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    if start > end:
        raise ValueError("CN fund/index pipeline start must not be after end.")
    if not 1 <= max_symbols_per_type <= 5_000:
        raise ValueError("CN fund/index pipeline symbol limit must be between 1 and 5000.")
    if request_delay_seconds < 0:
        raise ValueError("CN fund/index pipeline request delay cannot be negative.")

    catalog_results: dict[str, dict[str, object]] = {}
    states_by_type: dict[str, list[InstrumentRefreshState]] = {}
    _progress(progress_callback, "catalogs", 0, len(CN_FUND_INDEX_ASSET_TYPES), "Syncing catalogs.")
    for index, asset_type in enumerate(CN_FUND_INDEX_ASSET_TYPES, start=1):
        catalog_result = sync_instrument_universe(
            session=session,
            market="CN",
            provider_name="akshare",
            asset_type=asset_type,
            provider=provider,
        )
        catalog_results[asset_type] = catalog_result
        counts = catalog_result.get("counts")
        total_count = int(counts.get("total_count", 0)) if isinstance(counts, dict) else 0
        if total_count == 0:
            raise CnFundIndexPipelineError(
                f"CN_{asset_type.upper()}_CATALOG_UNAVAILABLE"
            )
        states_by_type[asset_type] = _active_refresh_states(
            session,
            asset_type=asset_type,
            limit=max_symbols_per_type,
        )
        _progress(
            progress_callback,
            "catalogs",
            index,
            len(CN_FUND_INDEX_ASSET_TYPES),
            f"{asset_type} catalog persisted.",
        )

    total_symbols = sum(len(states) for states in states_by_type.values())
    processed = 0
    asset_results: dict[str, dict[str, object]] = {}
    _progress(progress_callback, "daily_bars", 0, total_symbols, "Ingesting daily bars.")
    for asset_type in CN_FUND_INDEX_ASSET_TYPES:
        states = states_by_type[asset_type]
        counts = Counter({"ingested": 0, "no_data": 0, "failed": 0, "current": 0})
        window_counts = Counter(
            {"full_seed": 0, "full_refresh": 0, "incremental": 0, "current": 0}
        )
        source_counts: Counter[str] = Counter()
        diagnostic_codes: Counter[str] = Counter()
        bar_count = 0
        attempted_count = 0
        for symbol_index, state in enumerate(states, start=1):
            window_mode = _refresh_window_mode(
                state,
                end=end,
                incremental=incremental,
            )
            window_counts[window_mode] += 1
            if window_mode == "current":
                counts["current"] += 1
                processed += 1
                _progress(
                    progress_callback,
                    "daily_bars",
                    processed,
                    total_symbols,
                    f"{asset_type} {symbol_index}/{len(states)} processed.",
                )
                continue

            attempted_count += 1
            try:
                exact_source = _locked_incremental_source(
                    state,
                    asset_type=asset_type,
                )
                result = bar_ingestor(
                    symbol=state.symbol,
                    market="CN",
                    start=_refresh_start_date(
                        state,
                        start=start,
                        incremental=incremental,
                    ),
                    end=end,
                    session=session,
                    provider_name="akshare",
                    timeframe="1d",
                    asset_type=asset_type,
                    daily_bar_policy=CN_RESILIENT_POLICY,
                    fetch_coordinator=build_daily_bar_fetch_coordinator(
                        "akshare",
                        asset_type,
                        exact_source=exact_source,
                    ),
                )
            except Exception as exc:
                session.rollback()
                counts["failed"] += 1
                diagnostic_codes[f"{asset_type.upper()}_{type(exc).__name__.upper()}"] += 1
            else:
                status = str(result.get("status") or "failed")
                normalized_status = status if status in counts else "failed"
                counts[normalized_status] += 1
                raw_bar_count = result.get("bar_count")
                bar_count += raw_bar_count if isinstance(raw_bar_count, int) else 0
                source_counts[str(result.get("source") or "unknown")] += 1
            processed += 1
            _progress(
                progress_callback,
                "daily_bars",
                processed,
                total_symbols,
                f"{asset_type} {symbol_index}/{len(states)} processed.",
            )
            if processed < total_symbols and request_delay_seconds > 0:
                sleeper(request_delay_seconds)

        if attempted_count and counts["ingested"] == 0:
            raise CnFundIndexPipelineError(
                f"CN_{asset_type.upper()}_DAILY_BARS_PROVIDER_WIDE_FAILURE"
            )
        asset_results[asset_type] = {
            "catalog_count": len(states),
            "bar_count": bar_count,
            "counts": dict(counts),
            "overlap_days": CN_FUND_INDEX_INCREMENTAL_OVERLAP_DAYS,
            "window_counts": dict(window_counts),
            "source_counts": dict(sorted(source_counts.items())),
            "diagnostic_codes": dict(sorted(diagnostic_codes.items())),
        }

    degraded = any(_asset_result_is_degraded(result) for result in asset_results.values())
    return {
        "status": "degraded" if degraded else "ok",
        "provider": "akshare",
        "pipeline": "cn_fund_index_data",
        "refresh_mode": "incremental" if incremental else "full",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "asset_types": list(CN_FUND_INDEX_ASSET_TYPES),
        "catalogs": {
            asset_type: {
                "status": catalog_results[asset_type]["status"],
                "source": catalog_results[asset_type]["source"],
                "counts": catalog_results[asset_type]["counts"],
            }
            for asset_type in CN_FUND_INDEX_ASSET_TYPES
        },
        "assets": asset_results,
        "safety": {
            "sequential_provider_calls": True,
            "stored_evidence_only": True,
            "no_automated_trading": True,
        },
    }


def _active_refresh_states(
    session: Session,
    *,
    asset_type: str,
    limit: int,
) -> list[InstrumentRefreshState]:
    instruments = (
        session.query(Instrument.id, Instrument.symbol)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == "CN")
        .filter(Instrument.asset_type == asset_type)
        .filter(Instrument.is_active.is_(True))
        .order_by(Instrument.symbol.asc())
        .limit(limit)
        .all()
    )
    if not instruments:
        return []

    instrument_ids = [row.id for row in instruments]
    latest_dates = (
        session.query(
            DailyBar.instrument_id.label("instrument_id"),
            func.max(DailyBar.trade_date).label("latest_date"),
        )
        .filter(DailyBar.instrument_id.in_(instrument_ids))
        .group_by(DailyBar.instrument_id)
        .subquery()
    )
    latest_rows = (
        session.query(
            DailyBar.instrument_id,
            DailyBar.trade_date,
            DailyBar.source,
            DailyBar.adjustment,
        )
        .join(
            latest_dates,
            and_(
                DailyBar.instrument_id == latest_dates.c.instrument_id,
                DailyBar.trade_date == latest_dates.c.latest_date,
            ),
        )
        .all()
    )
    latest_by_instrument = {row.instrument_id: row for row in latest_rows}
    states: list[InstrumentRefreshState] = []
    for instrument in instruments:
        latest = latest_by_instrument.get(instrument.id)
        states.append(
            InstrumentRefreshState(
                symbol=str(instrument.symbol),
                latest_date=(latest.trade_date if latest is not None else None),
                source=(str(latest.source) if latest is not None else None),
                adjustment=(str(latest.adjustment) if latest is not None else None),
            )
        )
    return states


def _refresh_window_mode(
    state: InstrumentRefreshState,
    *,
    end: date,
    incremental: bool,
) -> str:
    if state.latest_date is None:
        return "full_seed"
    if not incremental:
        return "full_refresh"
    if state.latest_date >= end:
        return "current"
    return "incremental"


def _refresh_start_date(
    state: InstrumentRefreshState,
    *,
    start: date,
    incremental: bool,
) -> date:
    if state.latest_date is None or not incremental:
        return start
    return max(
        start,
        state.latest_date - timedelta(days=CN_FUND_INDEX_INCREMENTAL_OVERLAP_DAYS),
    )


def _locked_incremental_source(
    state: InstrumentRefreshState,
    *,
    asset_type: str,
) -> str | None:
    if state.latest_date is None:
        return None
    expected_adjustment = EXPECTED_SOURCE_ADJUSTMENTS.get(
        (asset_type, state.source or "")
    )
    if expected_adjustment is None or state.adjustment != expected_adjustment:
        raise ValueError("Stored daily-bar provenance is unsupported for incremental refresh.")
    return state.source


def _asset_result_is_degraded(result: dict[str, object]) -> bool:
    counts = result.get("counts")
    return bool(
        isinstance(counts, dict)
        and (counts.get("failed", 0) or counts.get("no_data", 0))
    )


def _progress(
    callback: ProgressCallback | None,
    phase: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is not None:
        callback(phase, current, total, message)
