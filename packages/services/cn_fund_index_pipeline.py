from collections import Counter
from collections.abc import Callable
from datetime import date
import time

from sqlalchemy.orm import Session

from packages.domain.models import Instrument, Market
from packages.providers.base import InstrumentUniverseProvider
from packages.services.daily_bar_sources import CN_RESILIENT_POLICY
from packages.services.ingestion import ingest_symbol_daily_bars
from packages.services.instrument_universe import sync_instrument_universe


CN_FUND_INDEX_PIPELINE_TASK_NAME = "ingestion.sync_cn_fund_index_data"
CN_FUND_INDEX_ASSET_TYPES = ("etf", "index")
ProgressCallback = Callable[[str, int, int, str], None]
BarIngestor = Callable[..., dict[str, object]]


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
    symbols_by_type: dict[str, list[str]] = {}
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
        symbols_by_type[asset_type] = _active_symbols(
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

    total_symbols = sum(len(symbols) for symbols in symbols_by_type.values())
    processed = 0
    asset_results: dict[str, dict[str, object]] = {}
    _progress(progress_callback, "daily_bars", 0, total_symbols, "Ingesting daily bars.")
    for asset_type in CN_FUND_INDEX_ASSET_TYPES:
        symbols = symbols_by_type[asset_type]
        counts = Counter({"ingested": 0, "no_data": 0, "failed": 0})
        source_counts: Counter[str] = Counter()
        diagnostic_codes: Counter[str] = Counter()
        bar_count = 0
        for symbol_index, symbol in enumerate(symbols, start=1):
            try:
                result = bar_ingestor(
                    symbol=symbol,
                    market="CN",
                    start=start,
                    end=end,
                    session=session,
                    provider_name="akshare",
                    timeframe="1d",
                    asset_type=asset_type,
                    daily_bar_policy=CN_RESILIENT_POLICY,
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
                f"{asset_type} {symbol_index}/{len(symbols)} processed.",
            )
            if processed < total_symbols and request_delay_seconds > 0:
                sleeper(request_delay_seconds)

        if symbols and counts["ingested"] == 0:
            raise CnFundIndexPipelineError(
                f"CN_{asset_type.upper()}_DAILY_BARS_PROVIDER_WIDE_FAILURE"
            )
        asset_results[asset_type] = {
            "catalog_count": len(symbols),
            "bar_count": bar_count,
            "counts": dict(counts),
            "source_counts": dict(sorted(source_counts.items())),
            "diagnostic_codes": dict(sorted(diagnostic_codes.items())),
        }

    degraded = any(_asset_result_is_degraded(result) for result in asset_results.values())
    return {
        "status": "degraded" if degraded else "ok",
        "provider": "akshare",
        "pipeline": "cn_fund_index_data",
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


def _active_symbols(session: Session, *, asset_type: str, limit: int) -> list[str]:
    return [
        str(symbol)
        for (symbol,) in session.query(Instrument.symbol)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == "CN")
        .filter(Instrument.asset_type == asset_type)
        .filter(Instrument.is_active.is_(True))
        .order_by(Instrument.symbol.asc())
        .limit(limit)
        .all()
    ]


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
