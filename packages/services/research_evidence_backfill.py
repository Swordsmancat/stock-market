from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
import time
from uuid import UUID

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from packages.domain.models import (
    DailyBar,
    Exchange,
    FundamentalSnapshot,
    Instrument,
    InstrumentUniverseSync,
    Market,
    ResearchEvidenceBackfill,
    TechnicalIndicator,
)
from packages.services.daily_bar_completion import (
    DAILY_BAR_COMPLETION_TIME,
    as_shanghai_datetime,
    completed_daily_bar_predicate,
)
from packages.services.daily_bar_sources import (
    STRICT_POLICY,
    SUPPORTED_DAILY_BAR_POLICIES,
    DailyBarFetchCoordinator,
)
from packages.services.fundamentals import ingest_fundamentals
from packages.services.indicators import calculate_and_store_daily_indicators
from packages.services.ingestion import (
    build_daily_bar_fetch_coordinator,
    ingest_symbol_daily_bars,
)


BACKFILL_TASK_NAME = "ingestion.backfill_a_share_research_evidence"
SUPPORTED_MARKET = "CN"
SUPPORTED_PROVIDER = "akshare"
DEFAULT_BATCH_SIZE = 25
SUPPORTED_EVIDENCE_KINDS = (
    "daily_bars",
    "fundamentals",
    "technical_indicators",
)
SUPPORTED_RUN_KINDS = {
    "baseline",
    "incremental",
    "fundamental_shard",
    "canary",
    "retry_failed",
}
ACTIVE_RUN_STATUSES = {"queued", "running", "cancel_requested"}
TERMINAL_RESUMABLE_STATUSES = {"failed", "cancelled"}
WATERMARK_RUN_KINDS = {"baseline", "incremental"}
WATERMARK_RUN_STATUSES = {"succeeded", "partial"}
WATERMARK_REQUIRED_EXCHANGES = ("SSE", "SZSE", "BSE")
WATERMARK_SCAN_DAYS = 31
MAX_DIAGNOSTICS = 100
CRITICAL_INDICATOR_CODES = {"ma", "rsi", "mfi"}
EVIDENCE_THRESHOLDS = {
    "daily_bars": 0.95,
    "technical_indicators": 0.90,
    "fundamentals": 0.80,
}


@dataclass(frozen=True)
class BackfillRequest:
    run_kind: str = "baseline"
    market: str = SUPPORTED_MARKET
    provider: str = SUPPORTED_PROVIDER
    daily_bar_policy: str = STRICT_POLICY
    evidence_kinds: tuple[str, ...] = SUPPORTED_EVIDENCE_KINDS
    start_date: date | None = None
    end_date: date | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    cohort_size: int | None = None
    shard_index: int | None = None
    shard_count: int | None = None


BackfillProgressCallback = Callable[[str, int, int, str], None]


def create_backfill_run(
    request: BackfillRequest,
    *,
    session: Session,
) -> dict[str, object]:
    normalized = _normalize_request(request)
    existing = get_active_research_evidence_backfill(
        session=session,
        market=normalized.market,
        provider=normalized.provider,
    )
    if existing is not None:
        return {"status": "already_running", "item": serialize_backfill(existing)}

    sync = _latest_usable_universe_sync(
        session,
        market=normalized.market,
        provider=normalized.provider,
    )
    scope_symbols = _active_scope_symbols(session, market=normalized.market)
    if not scope_symbols:
        raise ValueError("No active A-share instruments are available for backfill.")
    if normalized.run_kind == "canary":
        scope_symbols = _stratified_canary_scope(
            session,
            scope_symbols,
            cohort_size=normalized.cohort_size or 50,
        )
    if normalized.run_kind == "fundamental_shard":
        scope_symbols = _sharded_scope(
            scope_symbols,
            shard_index=normalized.shard_index or 0,
            shard_count=normalized.shard_count or 5,
        )

    first_phase = normalized.evidence_kinds[0]
    now = _utc_now()
    run = ResearchEvidenceBackfill(
        market=normalized.market,
        provider=normalized.provider,
        daily_bar_policy=normalized.daily_bar_policy,
        source_stats_json={},
        run_kind=normalized.run_kind,
        status="queued",
        universe_sync_id=sync.id if sync is not None else None,
        universe_as_of=(sync.as_of or sync.created_at) if sync is not None else None,
        evidence_kinds_json=list(normalized.evidence_kinds),
        scope_symbols_json=scope_symbols,
        start_date=normalized.start_date,
        end_date=normalized.end_date,
        batch_size=normalized.batch_size,
        cohort_size=normalized.cohort_size,
        shard_index=normalized.shard_index,
        shard_count=normalized.shard_count,
        phase=first_phase,
        cursor=0,
        phase_total=len(scope_symbols),
        processed_count=0,
        counters_json=_empty_counters(normalized.evidence_kinds),
        retry_json={kind: [] for kind in normalized.evidence_kinds},
        diagnostics_json=[],
        heartbeat_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return {"status": "created", "item": serialize_backfill(run)}


def create_resume_backfill_run(
    run_id: str,
    *,
    session: Session,
) -> dict[str, object]:
    original = _get_backfill(run_id, session)
    if original.status not in TERMINAL_RESUMABLE_STATUSES:
        raise ValueError("Only failed or cancelled backfills can be resumed.")
    existing = get_active_research_evidence_backfill(
        session=session,
        market=original.market,
        provider=original.provider,
    )
    if existing is not None:
        return {"status": "already_running", "item": serialize_backfill(existing)}

    now = _utc_now()
    resumed = ResearchEvidenceBackfill(
        parent_run_id=original.id,
        market=original.market,
        provider=original.provider,
        daily_bar_policy=original.daily_bar_policy,
        source_stats_json=dict(original.source_stats_json or {}),
        run_kind=original.run_kind,
        status="queued",
        universe_sync_id=original.universe_sync_id,
        universe_as_of=original.universe_as_of,
        evidence_kinds_json=list(original.evidence_kinds_json),
        scope_symbols_json=list(original.scope_symbols_json),
        start_date=original.start_date,
        end_date=original.end_date,
        batch_size=original.batch_size,
        cohort_size=original.cohort_size,
        shard_index=original.shard_index,
        shard_count=original.shard_count,
        phase=original.phase,
        cursor=original.cursor,
        phase_total=original.phase_total,
        processed_count=original.processed_count,
        counters_json=dict(original.counters_json),
        retry_json={kind: list(symbols) for kind, symbols in dict(original.retry_json).items()},
        diagnostics_json=list(original.diagnostics_json),
        heartbeat_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(resumed)
    session.commit()
    session.refresh(resumed)
    return {"status": "created", "item": serialize_backfill(resumed)}


def create_retry_failed_backfill_run(
    run_id: str,
    *,
    session: Session,
) -> dict[str, object]:
    original = _get_backfill(run_id, session)
    existing = get_active_research_evidence_backfill(
        session=session,
        market=original.market,
        provider=original.provider,
    )
    if existing is not None:
        return {"status": "already_running", "item": serialize_backfill(existing)}
    retry_by_kind = {
        kind: _normalized_symbols(symbols)
        for kind, symbols in dict(original.retry_json or {}).items()
        if _normalized_symbols(symbols)
    }
    if not retry_by_kind:
        raise ValueError("The selected backfill has no retryable symbols.")
    retry_scope = _normalized_symbols(
        symbol for symbols in retry_by_kind.values() for symbol in symbols
    )
    evidence_kinds = [kind for kind in SUPPORTED_EVIDENCE_KINDS if kind in retry_by_kind]
    now = _utc_now()
    retry_run = ResearchEvidenceBackfill(
        parent_run_id=original.id,
        market=original.market,
        provider=original.provider,
        daily_bar_policy=original.daily_bar_policy,
        source_stats_json={},
        run_kind="retry_failed",
        status="queued",
        universe_sync_id=original.universe_sync_id,
        universe_as_of=original.universe_as_of,
        evidence_kinds_json=evidence_kinds,
        scope_symbols_json=retry_scope,
        start_date=original.start_date,
        end_date=original.end_date,
        batch_size=original.batch_size,
        phase=evidence_kinds[0],
        cursor=0,
        phase_total=len(retry_scope),
        processed_count=0,
        counters_json=_empty_counters(evidence_kinds),
        retry_json=retry_by_kind,
        diagnostics_json=[],
        heartbeat_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(retry_run)
    session.commit()
    session.refresh(retry_run)
    return {"status": "created", "item": serialize_backfill(retry_run)}


def request_cancel_backfill(
    run_id: str,
    *,
    session: Session,
) -> dict[str, object]:
    run = _get_backfill(run_id, session)
    if run.status not in ACTIVE_RUN_STATUSES:
        raise ValueError("Only queued or running backfills can be cancelled.")
    now = _utc_now()
    run.status = "cancel_requested"
    run.cancel_requested_at = now
    run.updated_at = now
    session.commit()
    session.refresh(run)
    return {"status": "cancel_requested", "item": serialize_backfill(run)}


def fail_backfill_run(
    run_id: str,
    *,
    session: Session,
    code: str = "BACKFILL_EXECUTION_FAILED",
) -> dict[str, object]:
    run = _get_backfill(run_id, session)
    now = _utc_now()
    run.status = "failed"
    run.finished_at = now
    run.heartbeat_at = now
    run.updated_at = now
    diagnostics = list(run.diagnostics_json or [])[: MAX_DIAGNOSTICS - 1]
    diagnostics.append(
        {
            "source": "backfill",
            "status": "failed",
            "code": code,
            "message": "The research evidence backfill did not complete.",
        }
    )
    run.diagnostics_json = diagnostics
    session.commit()
    session.refresh(run)
    return serialize_backfill(run)


def link_backfill_task_run(
    run_id: str,
    task_run_id: str,
    *,
    session: Session,
) -> dict[str, object]:
    run = _get_backfill(run_id, session)
    parsed_task_run_id = _parse_uuid(task_run_id, "task run")
    if run.task_run_id is not None and run.task_run_id != parsed_task_run_id:
        raise ValueError("Backfill is already linked to another TaskRun.")
    run.task_run_id = parsed_task_run_id
    run.updated_at = _utc_now()
    session.commit()
    session.refresh(run)
    return serialize_backfill(run)


def get_backfill_payload(run_id: str, *, session: Session) -> dict[str, object] | None:
    try:
        run_uuid = UUID(run_id)
    except ValueError:
        return None
    run = session.get(ResearchEvidenceBackfill, run_uuid)
    if run is None:
        return None
    return {"source": "database", "item": serialize_backfill(run)}


def resolve_completed_daily_bar_watermark(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    provider: str = SUPPORTED_PROVIDER,
    now: datetime | None = None,
) -> dict[str, object]:
    """Resolve the latest completed, full-market daily-bar date from local evidence."""
    normalized_market, normalized_provider = _normalize_backfill_scope(market, provider)
    current = as_shanghai_datetime(now or _utc_now())
    candidate_ceiling = current.date()
    if current.timetz().replace(tzinfo=None) < DAILY_BAR_COMPLETION_TIME:
        candidate_ceiling -= timedelta(days=1)

    base: dict[str, object] = {
        "market": normalized_market,
        "provider": normalized_provider,
        "verified_completed_through": None,
        "timezone": "Asia/Shanghai",
        "evaluated_at": current.isoformat(),
        "candidate_date_ceiling": candidate_ceiling.isoformat(),
        "scan_window_days": WATERMARK_SCAN_DAYS,
        "scan_start_date": None,
        "scan_end_date": None,
        "threshold": EVIDENCE_THRESHOLDS["daily_bars"],
        "eligible_backfill_count": 0,
        "backfill_run_id": None,
        "backfill_task_run_id": None,
        "backfill": None,
        "coverage": None,
        "active_backfill": None,
        "diagnostics": [],
        "safety": {
            "stored_evidence_only": True,
            "no_provider_or_network_calls": True,
            "no_silent_provider_fallback": True,
            "no_automated_trading": True,
        },
    }

    active = get_active_research_evidence_backfill(
        session=session,
        market=normalized_market,
        provider=normalized_provider,
    )
    if active is not None:
        return {
            **base,
            "status": "not_ready",
            "code": "ACTIVE_EVIDENCE_BACKFILL",
            "active_backfill": _watermark_backfill_summary(active),
            "diagnostics": ["ACTIVE_EVIDENCE_BACKFILL"],
        }

    terminal_runs = (
        session.query(ResearchEvidenceBackfill)
        .filter(ResearchEvidenceBackfill.market == normalized_market)
        .filter(ResearchEvidenceBackfill.provider == normalized_provider)
        .filter(ResearchEvidenceBackfill.run_kind.in_(WATERMARK_RUN_KINDS))
        .filter(ResearchEvidenceBackfill.status.in_(WATERMARK_RUN_STATUSES))
        .filter(ResearchEvidenceBackfill.finished_at.is_not(None))
        .filter(ResearchEvidenceBackfill.end_date <= current.date())
        .filter(ResearchEvidenceBackfill.start_date <= candidate_ceiling)
        .order_by(
            ResearchEvidenceBackfill.finished_at.desc(),
            ResearchEvidenceBackfill.created_at.desc(),
            ResearchEvidenceBackfill.id.desc(),
        )
        .all()
    )
    eligible_runs = [
        run
        for run in terminal_runs
        if "daily_bars"
        in {
            str(kind).strip().lower()
            for kind in (run.evidence_kinds_json or [])
        }
    ]
    base["eligible_backfill_count"] = len(eligible_runs)
    if not eligible_runs:
        return {
            **base,
            "status": "no_data",
            "code": "NO_ELIGIBLE_DAILY_BAR_BACKFILL",
            "diagnostics": ["NO_ELIGIBLE_DAILY_BAR_BACKFILL"],
        }

    universe_rows = (
        session.query(Exchange.code, func.count(func.distinct(Instrument.id)))
        .select_from(Instrument)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == normalized_market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .group_by(Exchange.code)
        .all()
    )
    universe_by_exchange = {
        str(exchange or "UNKNOWN"): int(total)
        for exchange, total in universe_rows
    }
    universe_count = sum(universe_by_exchange.values())
    if universe_count == 0:
        return {
            **base,
            "status": "no_data",
            "code": "NO_ACTIVE_CN_STOCK_UNIVERSE",
            "diagnostics": ["NO_ACTIVE_CN_STOCK_UNIVERSE"],
        }

    latest_date = min(
        candidate_ceiling,
        max(run.end_date for run in eligible_runs),
    )
    earliest_date = latest_date - timedelta(days=WATERMARK_SCAN_DAYS - 1)
    base["scan_start_date"] = earliest_date.isoformat()
    base["scan_end_date"] = latest_date.isoformat()
    candidate_runs = [
        run
        for run in eligible_runs
        if run.start_date <= latest_date and run.end_date >= earliest_date
    ]
    completed_bar = completed_daily_bar_predicate(session, DailyBar)
    date_rows = (
        session.query(
            DailyBar.trade_date,
            Exchange.code,
            func.count(func.distinct(Instrument.id)),
            func.count(
                func.distinct(
                    case((completed_bar, Instrument.id), else_=None)
                )
            ),
        )
        .select_from(DailyBar)
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == normalized_market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(DailyBar.trade_date >= earliest_date)
        .filter(DailyBar.trade_date <= latest_date)
        .group_by(DailyBar.trade_date, Exchange.code)
        .order_by(DailyBar.trade_date.desc(), Exchange.code)
        .all()
    )
    coverage_by_date: dict[date, dict[str, dict[str, int]]] = {}
    for trade_date, exchange, stored_count, ready_count in date_rows:
        if not _date_has_eligible_provenance(trade_date, candidate_runs):
            continue
        exchange_code = str(exchange or "UNKNOWN")
        date_coverage = coverage_by_date.setdefault(
            trade_date,
            {"stored": {}, "ready": {}},
        )
        date_coverage["stored"][exchange_code] = int(stored_count)
        date_coverage["ready"][exchange_code] = int(ready_count)

    if not coverage_by_date:
        return {
            **base,
            "status": "no_data",
            "code": "NO_DAILY_BAR_CANDIDATES",
            "diagnostics": ["NO_DAILY_BAR_CANDIDATES"],
        }

    watermark_date: date | None = None
    watermark_coverage: dict[str, object] | None = None
    latest_candidate_coverage: dict[str, object] | None = None
    skipped_newer_date_count = 0
    for trade_date in sorted(coverage_by_date, reverse=True):
        coverage = _exact_date_watermark_coverage(
            coverage_by_date[trade_date],
            universe_by_exchange=universe_by_exchange,
            threshold=EVIDENCE_THRESHOLDS["daily_bars"],
        )
        coverage["trade_date"] = trade_date.isoformat()
        if latest_candidate_coverage is None:
            latest_candidate_coverage = coverage
        if coverage["passes_threshold"] and coverage["passes_exchange_representation"]:
            watermark_date = trade_date
            watermark_coverage = coverage
            break
        skipped_newer_date_count += 1

    if watermark_date is None or watermark_coverage is None:
        diagnostics = ["DAILY_BAR_WATERMARK_NOT_READY"]
        if latest_candidate_coverage and not latest_candidate_coverage[
            "passes_exchange_representation"
        ]:
            diagnostics.append("MISSING_REQUIRED_EXCHANGE_REPRESENTATION")
        return {
            **base,
            "status": "not_ready",
            "code": "DAILY_BAR_WATERMARK_NOT_READY",
            "coverage": latest_candidate_coverage,
            "diagnostics": diagnostics,
        }

    provenance = next(
        run
        for run in candidate_runs
        if run.start_date <= watermark_date <= run.end_date
    )
    diagnostics = []
    if skipped_newer_date_count:
        diagnostics.append("NEWER_DAILY_BAR_DATE_NOT_READY")
    return {
        **base,
        "status": "ready",
        "code": "DAILY_BAR_WATERMARK_READY",
        "verified_completed_through": watermark_date.isoformat(),
        "backfill_run_id": str(provenance.id),
        "backfill_task_run_id": str(provenance.task_run_id)
        if provenance.task_run_id is not None
        else None,
        "backfill": _watermark_backfill_summary(provenance),
        "coverage": watermark_coverage,
        "skipped_newer_date_count": skipped_newer_date_count,
        "diagnostics": diagnostics,
    }


def get_evidence_coverage(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    provider: str = SUPPORTED_PROVIDER,
    as_of: date | None = None,
) -> dict[str, object]:
    normalized_market, normalized_provider = _normalize_backfill_scope(market, provider)
    effective_as_of = as_of or date.today()
    horizon_start = _subtract_months(effective_as_of, 18)
    freshness_cutoff = date.fromordinal(effective_as_of.toordinal() - 10)
    point_in_time_cutoff = datetime.combine(
        effective_as_of + timedelta(days=1),
        datetime_time.min,
        tzinfo=timezone.utc,
    )

    instrument_rows = (
        session.query(Instrument.id, Instrument.symbol, Exchange.code)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == normalized_market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .order_by(Exchange.code, Instrument.symbol)
        .all()
    )
    instrument_ids = [instrument_id for instrument_id, _, _ in instrument_rows]
    symbols = [str(symbol).upper() for _, symbol, _ in instrument_rows]
    exchange_by_id = {
        instrument_id: str(exchange or "UNKNOWN") for instrument_id, _, exchange in instrument_rows
    }
    exchange_counts: dict[str, int] = {}
    for exchange in exchange_by_id.values():
        exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1

    bar_ready: set = set()
    bar_source_distribution: list[dict[str, object]] = []
    indicator_ready: set = set()
    fundamental_ready: set[str] = set()
    if instrument_ids:
        bar_rows = (
            session.query(
                DailyBar.instrument_id,
                DailyBar.provider,
                DailyBar.source,
                func.count(DailyBar.trade_date),
                func.max(DailyBar.trade_date),
            )
            .filter(DailyBar.instrument_id.in_(instrument_ids))
            .filter(DailyBar.trade_date >= horizon_start)
            .filter(DailyBar.trade_date <= effective_as_of)
            .group_by(DailyBar.instrument_id, DailyBar.provider, DailyBar.source)
            .all()
        )
        bar_totals: dict[object, tuple[int, date]] = {}
        source_totals: dict[tuple[str, str], dict[str, object]] = {}
        for instrument_id, source_provider, source, row_count, latest_date in bar_rows:
            prior_count, prior_latest = bar_totals.get(instrument_id, (0, latest_date))
            bar_totals[instrument_id] = (
                prior_count + int(row_count),
                max(prior_latest, latest_date),
            )
            source_key = (
                str(source_provider or "legacy_unknown"),
                str(source or "legacy_unknown"),
            )
            source_total = source_totals.setdefault(
                source_key,
                {"row_count": 0, "instrument_ids": set()},
            )
            source_total["row_count"] = int(source_total["row_count"]) + int(row_count)
            source_total["instrument_ids"].add(instrument_id)
        bar_ready = {
            instrument_id
            for instrument_id, (row_count, latest_date) in bar_totals.items()
            if int(row_count) >= 35 and latest_date >= freshness_cutoff
        }
        bar_source_distribution = [
            {
                "provider": source_provider,
                "source": source,
                "row_count": int(values["row_count"]),
                "instrument_count": len(values["instrument_ids"]),
            }
            for (source_provider, source), values in sorted(source_totals.items())
        ]

        latest_indicator_subquery = (
            session.query(
                TechnicalIndicator.instrument_id.label("instrument_id"),
                func.max(TechnicalIndicator.as_of).label("latest_as_of"),
            )
            .filter(TechnicalIndicator.instrument_id.in_(instrument_ids))
            .filter(TechnicalIndicator.timeframe == "1d")
            .filter(TechnicalIndicator.indicator_code.in_(CRITICAL_INDICATOR_CODES))
            .filter(TechnicalIndicator.as_of < point_in_time_cutoff)
            .group_by(TechnicalIndicator.instrument_id)
            .subquery()
        )
        indicator_rows = (
            session.query(
                TechnicalIndicator.instrument_id,
                latest_indicator_subquery.c.latest_as_of,
                func.count(func.distinct(TechnicalIndicator.indicator_code)),
            )
            .join(
                latest_indicator_subquery,
                and_(
                    TechnicalIndicator.instrument_id == latest_indicator_subquery.c.instrument_id,
                    TechnicalIndicator.as_of == latest_indicator_subquery.c.latest_as_of,
                ),
            )
            .filter(TechnicalIndicator.timeframe == "1d")
            .filter(TechnicalIndicator.indicator_code.in_(CRITICAL_INDICATOR_CODES))
            .filter(TechnicalIndicator.as_of < point_in_time_cutoff)
            .group_by(
                TechnicalIndicator.instrument_id,
                latest_indicator_subquery.c.latest_as_of,
            )
            .all()
        )
        indicator_ready = {
            instrument_id
            for instrument_id, indicator_as_of, code_count in indicator_rows
            if int(code_count) == len(CRITICAL_INDICATOR_CODES)
            and indicator_as_of.date() >= freshness_cutoff
        }

    if symbols:
        latest_fundamental_subquery = (
            session.query(
                FundamentalSnapshot.symbol.label("symbol"),
                func.max(FundamentalSnapshot.as_of).label("latest_as_of"),
            )
            .filter(FundamentalSnapshot.symbol.in_(symbols))
            .filter(FundamentalSnapshot.as_of >= horizon_start)
            .filter(FundamentalSnapshot.as_of <= effective_as_of)
            .group_by(FundamentalSnapshot.symbol)
            .subquery()
        )
        fundamental_rows = (
            session.query(
                FundamentalSnapshot.symbol,
                FundamentalSnapshot.as_of,
                FundamentalSnapshot.pe_ratio,
                FundamentalSnapshot.revenue_growth,
                FundamentalSnapshot.net_margin,
            )
            .join(
                latest_fundamental_subquery,
                and_(
                    FundamentalSnapshot.symbol == latest_fundamental_subquery.c.symbol,
                    FundamentalSnapshot.as_of == latest_fundamental_subquery.c.latest_as_of,
                ),
            )
            .filter(FundamentalSnapshot.as_of <= effective_as_of)
            .all()
        )
        for symbol, _, pe_ratio, revenue_growth, net_margin in fundamental_rows:
            normalized_symbol = str(symbol).upper()
            if pe_ratio is not None and revenue_growth is not None and net_margin is not None:
                fundamental_ready.add(normalized_symbol)

    evidence = {
        "daily_bars": _coverage_dimension(
            instrument_rows,
            ready_ids=bar_ready,
            threshold=EVIDENCE_THRESHOLDS["daily_bars"],
        ),
        "technical_indicators": _coverage_dimension(
            instrument_rows,
            ready_ids=indicator_ready,
            threshold=EVIDENCE_THRESHOLDS["technical_indicators"],
        ),
        "fundamentals": _coverage_dimension(
            instrument_rows,
            ready_symbols=fundamental_ready,
            threshold=EVIDENCE_THRESHOLDS["fundamentals"],
        ),
    }
    evidence["daily_bars"]["source_distribution"] = bar_source_distribution
    latest_run = (
        session.query(ResearchEvidenceBackfill)
        .filter(ResearchEvidenceBackfill.market == normalized_market)
        .filter(ResearchEvidenceBackfill.provider == normalized_provider)
        .order_by(ResearchEvidenceBackfill.created_at.desc())
        .first()
    )
    all_pass = bool(instrument_rows) and all(
        dimension["passes_threshold"] for dimension in evidence.values()
    )
    exchange_pass = all(
        dimension["by_exchange"].get(exchange, {}).get("ready_count", 0) > 0
        for dimension in evidence.values()
        for exchange in ("SSE", "SZSE", "BSE")
    )
    return {
        "status": "ok" if all_pass and exchange_pass else "needs_attention",
        "market": normalized_market,
        "provider": normalized_provider,
        "as_of": effective_as_of.isoformat(),
        "universe": {
            "active_count": len(instrument_rows),
            "exchange_counts": dict(sorted(exchange_counts.items())),
        },
        "evidence": evidence,
        "latest_run": _compact_run_summary(latest_run) if latest_run is not None else None,
        "thresholds": EVIDENCE_THRESHOLDS,
        "safety": {
            "stored_evidence_only": True,
            "no_silent_provider_fallback": True,
            "no_automated_trading": True,
        },
    }


def execute_backfill_run(
    run_id: str,
    *,
    session: Session,
    progress_callback: BackfillProgressCallback | None = None,
    request_delay_seconds: float = 0.0,
    max_transient_attempts: int = 1,
    retry_base_seconds: float = 1.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, object]:
    run = _get_backfill(run_id, session)
    if run.status == "cancel_requested":
        return _finish_cancelled(run, session)
    if run.status not in {"queued", "running"}:
        return serialize_backfill(run)

    run.status = "running"
    run.heartbeat_at = _utc_now()
    run.updated_at = run.heartbeat_at
    session.commit()

    evidence_kinds = [kind for kind in run.evidence_kinds_json if kind in SUPPORTED_EVIDENCE_KINDS]
    bar_fetch_coordinator = (
        build_daily_bar_fetch_coordinator(run.provider) if "daily_bars" in evidence_kinds else None
    )
    counters = _copy_counters(run.counters_json, evidence_kinds)
    retry = {
        kind: _normalized_symbols(dict(run.retry_json or {}).get(kind, []))
        for kind in evidence_kinds
    }
    diagnostics = list(run.diagnostics_json or [])[:MAX_DIAGNOSTICS]
    scope_symbols = _normalized_symbols(run.scope_symbols_json)
    start_index = evidence_kinds.index(run.phase) if run.phase in evidence_kinds else 0

    for phase_index in range(start_index, len(evidence_kinds)):
        phase = evidence_kinds[phase_index]
        phase_scope = _phase_scope(run, phase, scope_symbols)
        if phase_index != start_index:
            run.cursor = 0
        run.phase = phase
        run.phase_total = len(phase_scope)
        session.commit()

        while run.cursor < len(phase_scope):
            session.refresh(run)
            if run.status == "cancel_requested" or run.cancel_requested_at is not None:
                run.counters_json = counters
                run.retry_json = retry
                run.diagnostics_json = diagnostics
                return _finish_cancelled(run, session)

            batch_start = run.cursor
            batch_end = min(batch_start + run.batch_size, len(phase_scope))
            batch_symbols = phase_scope[batch_start:batch_end]
            batch_outcomes: list[tuple[str, str, dict[str, object] | None]] = []
            for symbol_index, symbol in enumerate(batch_symbols):
                if (
                    request_delay_seconds > 0
                    and phase in {"daily_bars", "fundamentals"}
                    and (symbol_index > 0 or batch_start > 0)
                ):
                    sleep_fn(max(0.0, request_delay_seconds))
                try:
                    outcome = _process_symbol_with_retry(
                        run,
                        phase,
                        symbol,
                        session,
                        max_attempts=max_transient_attempts,
                        retry_base_seconds=retry_base_seconds,
                        sleep_fn=sleep_fn,
                        bar_fetch_coordinator=bar_fetch_coordinator,
                    )
                    batch_outcomes.append((symbol, outcome, None))
                except Exception as exc:
                    session.rollback()
                    batch_outcomes.append(
                        (symbol, "failed", _exception_diagnostic(phase, symbol, exc))
                    )

            for symbol, outcome, diagnostic in batch_outcomes:
                phase_counts = counters[phase]
                phase_counts["attempted"] += 1
                if outcome in phase_counts:
                    phase_counts[outcome] += 1
                else:
                    phase_counts["failed"] += 1
                if diagnostic is not None:
                    if symbol not in retry[phase]:
                        retry[phase].append(symbol)
                    if len(diagnostics) < MAX_DIAGNOSTICS:
                        diagnostics.append(diagnostic)
                elif outcome == "succeeded" and symbol in retry[phase]:
                    retry[phase].remove(symbol)

            now = _utc_now()
            run.cursor = batch_end
            run.processed_count += len(batch_symbols)
            run.counters_json = counters
            run.retry_json = retry
            run.diagnostics_json = diagnostics
            if bar_fetch_coordinator is not None:
                run.source_stats_json = bar_fetch_coordinator.stats()
            run.heartbeat_at = now
            run.updated_at = now
            session.commit()
            if progress_callback is not None:
                progress_callback(
                    phase,
                    run.cursor,
                    len(phase_scope),
                    f"Processed {run.cursor} of {len(phase_scope)} symbols for {phase}.",
                )

    now = _utc_now()
    run.phase = "completed"
    run.cursor = run.phase_total
    run.status = "partial" if any(retry.values()) else "succeeded"
    run.finished_at = now
    run.heartbeat_at = now
    run.updated_at = now
    run.counters_json = counters
    run.retry_json = retry
    run.diagnostics_json = diagnostics
    if bar_fetch_coordinator is not None:
        run.source_stats_json = bar_fetch_coordinator.stats()
    session.commit()
    session.refresh(run)
    return serialize_backfill(run)


def serialize_backfill(run: ResearchEvidenceBackfill) -> dict[str, object]:
    return {
        "id": str(run.id),
        "task_run_id": str(run.task_run_id) if run.task_run_id else None,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "market": run.market,
        "provider": run.provider,
        "daily_bar_policy": run.daily_bar_policy,
        "source_stats": dict(run.source_stats_json or {}),
        "run_kind": run.run_kind,
        "status": run.status,
        "universe_sync_id": str(run.universe_sync_id) if run.universe_sync_id else None,
        "universe_as_of": _iso_datetime(run.universe_as_of),
        "evidence_kinds": list(run.evidence_kinds_json or []),
        "scope_symbols": list(run.scope_symbols_json or []),
        "start_date": run.start_date.isoformat(),
        "end_date": run.end_date.isoformat(),
        "batch_size": run.batch_size,
        "cohort_size": run.cohort_size,
        "shard_index": run.shard_index,
        "shard_count": run.shard_count,
        "phase": run.phase,
        "cursor": run.cursor,
        "phase_total": run.phase_total,
        "processed_count": run.processed_count,
        "counters": dict(run.counters_json or {}),
        "retry": {kind: list(symbols) for kind, symbols in dict(run.retry_json or {}).items()},
        "diagnostics": list(run.diagnostics_json or []),
        "cancel_requested_at": _iso_datetime(run.cancel_requested_at),
        "heartbeat_at": _iso_datetime(run.heartbeat_at),
        "created_at": _iso_datetime(run.created_at),
        "updated_at": _iso_datetime(run.updated_at),
        "finished_at": _iso_datetime(run.finished_at),
        "safety": {
            "research_signal_only": True,
            "no_silent_provider_fallback": True,
            "no_automated_trading": True,
        },
    }


def _normalize_request(request: BackfillRequest) -> BackfillRequest:
    market = request.market.strip().upper()
    provider = request.provider.strip().lower()
    daily_bar_policy = request.daily_bar_policy.strip().lower()
    run_kind = request.run_kind.strip().lower()
    if market != SUPPORTED_MARKET:
        raise ValueError(f"Unsupported backfill market: {request.market}")
    if provider != SUPPORTED_PROVIDER:
        raise ValueError(f"Unsupported backfill provider: {request.provider}")
    if daily_bar_policy not in SUPPORTED_DAILY_BAR_POLICIES:
        raise ValueError(f"Unsupported daily-bar policy: {request.daily_bar_policy}")
    if run_kind not in SUPPORTED_RUN_KINDS:
        raise ValueError(f"Unsupported backfill run kind: {request.run_kind}")
    evidence_kinds = tuple(
        kind
        for kind in SUPPORTED_EVIDENCE_KINDS
        if kind in {value.strip().lower() for value in request.evidence_kinds}
    )
    if not evidence_kinds:
        raise ValueError("At least one supported evidence kind is required.")
    end_date = request.end_date or date.today()
    default_start = (
        date.fromordinal(end_date.toordinal() - 10)
        if run_kind == "incremental"
        else _subtract_months(end_date, 18)
    )
    start_date = request.start_date or default_start
    if start_date > end_date:
        raise ValueError("Backfill start_date must not be after end_date.")
    if not 1 <= request.batch_size <= 100:
        raise ValueError("Backfill batch_size must be between 1 and 100.")
    cohort_size = request.cohort_size
    if run_kind == "canary" and cohort_size is not None and cohort_size < 3:
        raise ValueError("Canary cohort_size must be at least 3.")
    shard_count = request.shard_count
    shard_index = request.shard_index
    if run_kind == "fundamental_shard":
        shard_count = shard_count or 5
        shard_index = 0 if shard_index is None else shard_index
        if shard_count < 1 or not 0 <= shard_index < shard_count:
            raise ValueError("Fundamental shard index must be within shard_count.")
        evidence_kinds = ("fundamentals",)
    return BackfillRequest(
        run_kind=run_kind,
        market=market,
        provider=provider,
        daily_bar_policy=daily_bar_policy,
        evidence_kinds=evidence_kinds,
        start_date=start_date,
        end_date=end_date,
        batch_size=request.batch_size,
        cohort_size=cohort_size,
        shard_index=shard_index,
        shard_count=shard_count,
    )


def get_active_research_evidence_backfill(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    provider: str = SUPPORTED_PROVIDER,
) -> ResearchEvidenceBackfill | None:
    normalized_market, normalized_provider = _normalize_backfill_scope(market, provider)
    return (
        session.query(ResearchEvidenceBackfill)
        .filter(ResearchEvidenceBackfill.market == normalized_market)
        .filter(ResearchEvidenceBackfill.provider == normalized_provider)
        .filter(ResearchEvidenceBackfill.status.in_(ACTIVE_RUN_STATUSES))
        .order_by(ResearchEvidenceBackfill.created_at.desc())
        .first()
    )


def _normalize_backfill_scope(market: str, provider: str) -> tuple[str, str]:
    normalized_market = market.strip().upper()
    normalized_provider = provider.strip().lower()
    if normalized_market != SUPPORTED_MARKET:
        raise ValueError(f"Unsupported backfill market: {market}")
    if normalized_provider != SUPPORTED_PROVIDER:
        raise ValueError(f"Unsupported backfill provider: {provider}")
    return normalized_market, normalized_provider


def _date_has_eligible_provenance(
    trade_date: date,
    eligible_runs: list[ResearchEvidenceBackfill],
) -> bool:
    return any(run.start_date <= trade_date <= run.end_date for run in eligible_runs)


def _exact_date_watermark_coverage(
    values: dict[str, dict[str, int]],
    *,
    universe_by_exchange: dict[str, int],
    threshold: float,
) -> dict[str, object]:
    stored_by_exchange = values["stored"]
    ready_by_exchange = values["ready"]
    exchanges = sorted(
        set(universe_by_exchange)
        | set(stored_by_exchange)
        | set(WATERMARK_REQUIRED_EXCHANGES)
    )
    by_exchange = {
        exchange: {
            "ready_count": ready_by_exchange.get(exchange, 0),
            "stored_count": stored_by_exchange.get(exchange, 0),
            "total_count": universe_by_exchange.get(exchange, 0),
            "coverage_ratio": (
                ready_by_exchange.get(exchange, 0) / universe_by_exchange[exchange]
                if universe_by_exchange.get(exchange, 0)
                else 0.0
            ),
        }
        for exchange in exchanges
    }
    ready_count = sum(ready_by_exchange.values())
    total_count = sum(universe_by_exchange.values())
    coverage_ratio = ready_count / total_count if total_count else 0.0
    return {
        "ready_count": ready_count,
        "missing_count": total_count - ready_count,
        "stored_count": sum(stored_by_exchange.values()),
        "total_count": total_count,
        "coverage_ratio": coverage_ratio,
        "threshold": threshold,
        "passes_threshold": bool(total_count) and coverage_ratio >= threshold,
        "passes_exchange_representation": all(
            ready_by_exchange.get(exchange, 0) > 0
            for exchange in WATERMARK_REQUIRED_EXCHANGES
        ),
        "by_exchange": by_exchange,
    }


def _watermark_backfill_summary(run: ResearchEvidenceBackfill) -> dict[str, object]:
    return {
        "id": str(run.id),
        "task_run_id": str(run.task_run_id) if run.task_run_id is not None else None,
        "run_kind": run.run_kind,
        "status": run.status,
        "start_date": run.start_date.isoformat(),
        "end_date": run.end_date.isoformat(),
        "finished_at": _iso_datetime(run.finished_at),
    }


def _latest_usable_universe_sync(
    session: Session,
    *,
    market: str,
    provider: str,
) -> InstrumentUniverseSync | None:
    return (
        session.query(InstrumentUniverseSync)
        .filter(InstrumentUniverseSync.market == market)
        .filter(InstrumentUniverseSync.provider == provider)
        .filter(InstrumentUniverseSync.total_count > 0)
        .order_by(InstrumentUniverseSync.created_at.desc())
        .first()
    )


def _active_scope_symbols(session: Session, *, market: str) -> list[str]:
    rows = (
        session.query(Instrument.symbol)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .order_by(Exchange.code, Instrument.symbol)
        .all()
    )
    return [str(symbol).upper() for (symbol,) in rows]


def _stratified_canary_scope(
    session: Session,
    full_scope: list[str],
    *,
    cohort_size: int,
) -> list[str]:
    rows = (
        session.query(Exchange.code, Instrument.symbol)
        .join(Exchange, Instrument.exchange_id == Exchange.id)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == SUPPORTED_MARKET)
        .filter(Instrument.symbol.in_(full_scope))
        .order_by(Exchange.code, Instrument.symbol)
        .all()
    )
    grouped: dict[str, list[str]] = {}
    for exchange, symbol in rows:
        grouped.setdefault(str(exchange), []).append(str(symbol).upper())
    nonempty_groups = [grouped[key] for key in sorted(grouped) if grouped[key]]
    target = min(cohort_size, len(full_scope))
    if not nonempty_groups or target >= len(full_scope):
        return full_scope
    base, remainder = divmod(target, len(nonempty_groups))
    selected: list[str] = []
    for index, symbols in enumerate(nonempty_groups):
        take = min(len(symbols), base + (1 if index < remainder else 0))
        selected.extend(symbols[:take])
    if len(selected) < target:
        selected_set = set(selected)
        selected.extend(symbol for symbol in full_scope if symbol not in selected_set)
    return selected[:target]


def _sharded_scope(
    symbols: list[str],
    *,
    shard_index: int,
    shard_count: int,
) -> list[str]:
    return [
        symbol for ordinal, symbol in enumerate(symbols) if ordinal % shard_count == shard_index
    ]


def _phase_scope(
    run: ResearchEvidenceBackfill,
    phase: str,
    scope_symbols: list[str],
) -> list[str]:
    if run.run_kind != "retry_failed":
        return scope_symbols
    retry_symbols = _normalized_symbols(dict(run.retry_json or {}).get(phase, []))
    return retry_symbols


def _process_symbol(
    run: ResearchEvidenceBackfill,
    phase: str,
    symbol: str,
    session: Session,
    bar_fetch_coordinator: DailyBarFetchCoordinator | None = None,
) -> str:
    if phase == "daily_bars":
        result = ingest_symbol_daily_bars(
            symbol=symbol,
            market=run.market,
            start=run.start_date,
            end=run.end_date,
            session=session,
            provider_name=run.provider,
            asset_type="stock",
            daily_bar_policy=run.daily_bar_policy,
            fetch_coordinator=bar_fetch_coordinator,
        )
        return "succeeded" if result.get("status") == "ingested" else "no_data"
    if phase == "fundamentals":
        result = ingest_fundamentals(
            symbol,
            session=session,
            provider_name=run.provider,
            as_of=run.end_date,
        )
        status = str(result.get("status") or "")
        if status == "ingested":
            return "succeeded"
        if status in {"empty", "no_data"}:
            return "no_data"
        if status == "skipped":
            raise RuntimeError("The configured provider dependency is unavailable.")
        raise RuntimeError("The fundamental provider returned an unsupported status.")
    if phase == "technical_indicators":
        result = calculate_and_store_daily_indicators(
            symbol,
            run.start_date,
            run.end_date,
            session=session,
        )
        status = str(result.get("status") or "")
        if status == "calculated":
            return "succeeded"
        if status == "insufficient_data":
            return "insufficient_data"
        return "no_data"
    raise ValueError(f"Unsupported backfill phase: {phase}")


def _process_symbol_with_retry(
    run: ResearchEvidenceBackfill,
    phase: str,
    symbol: str,
    session: Session,
    *,
    max_attempts: int,
    retry_base_seconds: float,
    sleep_fn: Callable[[float], None],
    bar_fetch_coordinator: DailyBarFetchCoordinator | None = None,
) -> str:
    bounded_attempts = max(1, min(int(max_attempts), 5))
    for attempt in range(1, bounded_attempts + 1):
        try:
            return _process_symbol(
                run,
                phase,
                symbol,
                session,
                bar_fetch_coordinator=bar_fetch_coordinator,
            )
        except Exception as exc:
            if attempt >= bounded_attempts or not _is_transient_error(exc):
                raise
            session.rollback()
            sleep_fn(max(0.0, retry_base_seconds) * (2 ** (attempt - 1)))
    raise RuntimeError("Transient retry loop ended unexpectedly.")


def _is_transient_error(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    category = str(getattr(exc, "category", ""))
    return (
        category in {"timeout", "rate_limited", "unavailable"}
        or isinstance(exc, TimeoutError)
        or "timeout" in name
        or "timeout" in message
        or "ratelimit" in name
        or "rate_limit" in name
        or "rate limit" in message
        or "temporarily unavailable" in message
    )


def _exception_diagnostic(
    phase: str,
    symbol: str,
    exc: Exception,
) -> dict[str, object]:
    exception_name = type(exc).__name__
    normalized_name = exception_name.lower()
    normalized_message = str(exc).lower()
    category = str(getattr(exc, "category", ""))
    if category == "timeout" or isinstance(exc, TimeoutError) or "timeout" in normalized_name:
        code = "TIMEOUT"
    elif category == "rate_limited" or (
        "ratelimit" in normalized_name
        or "rate_limit" in normalized_name
        or "rate limit" in normalized_message
    ):
        code = "RATE_LIMITED"
    elif category == "malformed_payload" or isinstance(exc, (KeyError, TypeError)):
        code = "SCHEMA_INVALID"
    elif (
        category == "unavailable"
        or isinstance(exc, (ImportError, ModuleNotFoundError))
        or "dependency is unavailable" in normalized_message
    ):
        code = "PROVIDER_UNAVAILABLE"
    else:
        code = "PROCESSING_FAILED"
    return {
        "source": phase,
        "status": "failed",
        "code": code,
        "message": "A backfill symbol could not be processed.",
        "details": {
            "symbol": symbol,
            "exception_type": exception_name,
        },
    }


def _empty_counters(evidence_kinds: tuple[str, ...] | list[str]) -> dict[str, dict[str, int]]:
    return {
        kind: {
            "attempted": 0,
            "succeeded": 0,
            "no_data": 0,
            "insufficient_data": 0,
            "failed": 0,
        }
        for kind in evidence_kinds
    }


def _copy_counters(
    raw_counters: dict,
    evidence_kinds: list[str],
) -> dict[str, dict[str, int]]:
    counters = _empty_counters(evidence_kinds)
    for kind in evidence_kinds:
        raw_kind = raw_counters.get(kind, {}) if isinstance(raw_counters, dict) else {}
        if not isinstance(raw_kind, dict):
            continue
        for key in counters[kind]:
            counters[kind][key] = max(0, int(raw_kind.get(key, 0)))
    return counters


def _coverage_dimension(
    instrument_rows,
    *,
    threshold: float,
    ready_ids: set | None = None,
    ready_symbols: set[str] | None = None,
) -> dict[str, object]:
    ready_ids = ready_ids or set()
    ready_symbols = ready_symbols or set()
    exchange_totals: dict[str, int] = {}
    exchange_ready: dict[str, int] = {}
    ready_count = 0
    for instrument_id, symbol, exchange in instrument_rows:
        exchange_code = str(exchange or "UNKNOWN")
        exchange_totals[exchange_code] = exchange_totals.get(exchange_code, 0) + 1
        is_ready = instrument_id in ready_ids or str(symbol).upper() in ready_symbols
        if is_ready:
            ready_count += 1
            exchange_ready[exchange_code] = exchange_ready.get(exchange_code, 0) + 1
    total_count = len(instrument_rows)
    coverage_ratio = ready_count / total_count if total_count else 0.0
    by_exchange = {
        exchange: {
            "ready_count": exchange_ready.get(exchange, 0),
            "total_count": total,
            "coverage_ratio": exchange_ready.get(exchange, 0) / total if total else 0.0,
        }
        for exchange, total in sorted(exchange_totals.items())
    }
    return {
        "ready_count": ready_count,
        "missing_count": total_count - ready_count,
        "total_count": total_count,
        "coverage_ratio": coverage_ratio,
        "threshold": threshold,
        "passes_threshold": bool(total_count) and coverage_ratio >= threshold,
        "by_exchange": by_exchange,
    }


def _compact_run_summary(run: ResearchEvidenceBackfill) -> dict[str, object]:
    retry = {
        kind: _normalized_symbols(symbols) for kind, symbols in dict(run.retry_json or {}).items()
    }
    return {
        "id": str(run.id),
        "task_run_id": str(run.task_run_id) if run.task_run_id else None,
        "run_kind": run.run_kind,
        "daily_bar_policy": run.daily_bar_policy,
        "source_stats": dict(run.source_stats_json or {}),
        "status": run.status,
        "phase": run.phase,
        "cursor": run.cursor,
        "phase_total": run.phase_total,
        "processed_count": run.processed_count,
        "heartbeat_at": _iso_datetime(run.heartbeat_at),
        "finished_at": _iso_datetime(run.finished_at),
        "retry": {
            kind: {"count": len(symbols), "preview": symbols[:10]}
            for kind, symbols in retry.items()
        },
        "diagnostics": list(run.diagnostics_json or [])[:20],
    }


def _normalized_symbols(symbols) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for symbol in symbols or []:
        value = str(symbol).strip().upper()
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def _finish_cancelled(
    run: ResearchEvidenceBackfill,
    session: Session,
) -> dict[str, object]:
    now = _utc_now()
    run.status = "cancelled"
    run.finished_at = now
    run.heartbeat_at = now
    run.updated_at = now
    session.commit()
    session.refresh(run)
    return serialize_backfill(run)


def _get_backfill(run_id: str, session: Session) -> ResearchEvidenceBackfill:
    run_uuid = _parse_uuid(run_id, "backfill run")
    run = session.get(ResearchEvidenceBackfill, run_uuid)
    if run is None:
        raise ValueError("Research evidence backfill was not found.")
    return run


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {label} id.") from exc


def _subtract_months(value: date, months: int) -> date:
    month_index = value.year * 12 + (value.month - 1) - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    month_lengths = (31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return date(year, month, min(value.day, month_lengths[month - 1]))


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
