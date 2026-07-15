from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import math
from statistics import median
import threading
from typing import Iterable, Literal
from uuid import UUID

from sqlalchemy import (
    and_,
    case,
    func,
    or_,
    select,
    text,
    union_all,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, joinedload

from packages.domain.models import (
    DailyBar,
    Instrument,
    Market,
    ResearchCandidateOutcome,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
)
from packages.services.daily_bar_completion import (
    DAILY_BAR_COMPLETION_TIME,
    SHANGHAI_TIMEZONE,
    completed_daily_bar_predicate,
    daily_bar_is_complete,
    daily_bar_timestamp_is_complete,
)
from packages.services.daily_bar_sources import resolve_daily_bar_adjustment


OUTCOME_HORIZONS = (5, 20, 60)
OUTCOME_METHODOLOGY_VERSION = "research_candidate_outcome_v1"
BENCHMARK_CODE = "cn_csi_300"
SHANGHAI = SHANGHAI_TIMEZONE
BAR_COMPLETION_TIME = DAILY_BAR_COMPLETION_TIME
SAFETY_PAYLOAD = {
    "research_signal_only": True,
    "disclaimer": (
        "Shortlist outcomes are historical research observations only, are not "
        "investment advice, and cannot trigger automated trading."
    ),
    "not_investment_advice": True,
    "no_buy_sell_hold": True,
    "no_target_price": True,
    "no_position_sizing": True,
    "no_automated_trading": True,
    "outcomes_do_not_change_shortlist_ranking": True,
}
_EVALUATION_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))
MAX_DUE_RUN_LIMIT = 100


DueResearchShortlistReason = Literal["candidate_terminal", "benchmark_repair"]


@dataclass(frozen=True)
class DueResearchShortlistRun:
    run_id: UUID
    due_since: date
    reasons: frozenset[DueResearchShortlistReason]


@dataclass
class _CandidateBarWindow:
    bars: list[DailyBar]
    has_incomplete_forward: bool = False


@dataclass(frozen=True)
class _OutcomeRunState:
    terminal_keys: frozenset[tuple[UUID, int]]
    benchmark_statuses: dict[UUID, str]


def get_research_shortlist_outcomes(
    run_id: str | UUID,
    *,
    session: Session,
    as_of: date | None = None,
    now: datetime | None = None,
    verified_completed_through: date | None = None,
) -> dict[str, object] | None:
    effective_as_of = _resolve_as_of(
        as_of=as_of,
        now=now,
        verified_completed_through=verified_completed_through,
    )
    run = _committed_run(session, run_id)
    if run is None:
        return None
    candidates = _candidates_for_runs(session, [run.id]).get(run.id, [])
    bars = _candidate_bars(
        session,
        candidates=candidates,
        as_of=effective_as_of,
    )
    outcomes = _outcomes_for_candidates(session, candidates)
    benchmark = _canonical_benchmark(session)
    return _serialize_run(
        run,
        candidates=candidates,
        candidate_bars=bars,
        terminal_outcomes=outcomes,
        benchmark=benchmark,
        as_of=effective_as_of,
    )


def evaluate_research_shortlist_outcomes(
    run_id: str | UUID,
    *,
    session: Session,
    as_of: date | None = None,
    now: datetime | None = None,
    verified_completed_through: date | None = None,
    evaluation_task_run_id: str | UUID | None = None,
) -> dict[str, object] | None:
    effective_as_of = _resolve_as_of(
        as_of=as_of,
        now=now,
        verified_completed_through=verified_completed_through,
    )
    parsed_run_id = _parse_uuid(run_id)
    if parsed_run_id is None:
        return None
    parsed_task_run_id = _optional_uuid(
        evaluation_task_run_id,
        label="evaluation_task_run_id",
    )
    evaluated_at = _aware_utc(now or datetime.now(timezone.utc))

    with _serialized_evaluation(session, parsed_run_id):
        run = _committed_run(session, parsed_run_id)
        if run is None:
            return None
        candidates = _candidates_for_runs(session, [run.id]).get(run.id, [])
        bars = _candidate_bars(
            session,
            candidates=candidates,
            as_of=effective_as_of,
        )
        existing = _outcomes_for_candidates(session, candidates)
        benchmark = _canonical_benchmark(session)
        benchmark_bars = _benchmark_bars(
            session,
            benchmark=benchmark,
            trade_dates=_required_benchmark_dates(
                candidates=candidates,
                candidate_bars=bars,
                existing=existing,
                as_of=effective_as_of,
            ),
        )

        staged = _stage_terminal_outcomes(
            candidates=candidates,
            candidate_bars=bars,
            existing=existing,
            benchmark=benchmark,
            benchmark_bars=benchmark_bars,
            as_of=effective_as_of,
            evaluated_at=evaluated_at,
            evaluation_task_run_id=parsed_task_run_id,
        )
        if staged:
            _insert_outcomes_ignore_conflicts(session, staged)
        _enrich_pending_benchmarks(
            session,
            outcomes=list(existing.values()),
            candidates=candidates,
            benchmark=benchmark,
            benchmark_bars=benchmark_bars,
            completed_at=evaluated_at,
        )
        session.flush()
        refreshed = _outcomes_for_candidates(session, candidates)
        result = _serialize_run(
            run,
            candidates=candidates,
            candidate_bars=bars,
            terminal_outcomes=refreshed,
            benchmark=benchmark,
            as_of=effective_as_of,
        )
        session.commit()
        return result


def select_due_research_shortlist_runs(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    run_limit: int = 25,
) -> list[DueResearchShortlistRun]:
    normalized_market, normalized_profile = _normalize_due_scope(
        market=market,
        profile_id=profile_id,
        run_limit=run_limit,
    )
    selected, _ = _select_due_research_shortlist_runs(
        session=session,
        market=normalized_market,
        profile_id=normalized_profile,
        completed_through=completed_through,
        run_limit=run_limit,
    )
    return selected


def evaluate_due_research_shortlist_outcomes(
    *,
    session: Session,
    market: str,
    profile_id: str,
    verified_completed_through: date,
    evaluation_task_run_id: str | UUID | None,
    run_limit: int = 25,
    now: datetime | None = None,
    progress: Callable[[str, int, int, str], None] | None = None,
) -> dict[str, object]:
    normalized_market, normalized_profile = _normalize_due_scope(
        market=market,
        profile_id=profile_id,
        run_limit=run_limit,
    )
    completed_through = _resolve_as_of(
        as_of=verified_completed_through,
        now=now,
        verified_completed_through=verified_completed_through,
    )
    parsed_task_run_id = _optional_uuid(
        evaluation_task_run_id,
        label="evaluation_task_run_id",
    )
    selected, has_more = _select_due_research_shortlist_runs(
        session=session,
        market=normalized_market,
        profile_id=normalized_profile,
        completed_through=completed_through,
        run_limit=run_limit,
    )

    processed_run_ids: list[str] = []
    succeeded_run_ids: list[str] = []
    failures: list[dict[str, object]] = []
    run_results: list[dict[str, object]] = []
    concurrent_reuse_count = 0
    final_evaluated_horizon_count = 0
    final_blocked_horizon_count = 0
    final_pending_horizon_count = 0

    for position, due_run in enumerate(selected, start=1):
        run_id = str(due_run.run_id)
        processed_run_ids.append(run_id)
        message = f"Processed research outcome cohort {run_id}."
        try:
            before = _outcome_run_state(session, due_run.run_id)
            payload = evaluate_research_shortlist_outcomes(
                due_run.run_id,
                session=session,
                as_of=completed_through,
                now=now,
                verified_completed_through=completed_through,
                evaluation_task_run_id=parsed_task_run_id,
            )
            after = _outcome_run_state(session, due_run.run_id)
            new_terminal_keys = after.terminal_keys - before.terminal_keys
            repaired_benchmark_ids = {
                outcome_id
                for outcome_id, status in before.benchmark_statuses.items()
                if status == "pending"
                and after.benchmark_statuses.get(outcome_id) in {"evaluated", "blocked"}
            }
            final_counts = _final_horizon_counts(payload)
            final_evaluated_horizon_count += final_counts["evaluated"]
            final_blocked_horizon_count += final_counts["blocked"]
            final_pending_horizon_count += final_counts["pending"]
            diagnostics: list[str] = []
            status = "processed"
            if not new_terminal_keys and not repaired_benchmark_ids:
                remaining_reasons = _due_reasons_for_run(
                    session=session,
                    run_id=due_run.run_id,
                    market=normalized_market,
                    profile_id=normalized_profile,
                    completed_through=completed_through,
                )
                if not remaining_reasons and _payload_has_terminal_reason(
                    payload,
                    due_run.reasons,
                ):
                    status = "concurrent_reuse"
                    concurrent_reuse_count += 1
                else:
                    status = "no_progress"
                    diagnostics.append("DUE_RUN_NO_PROGRESS")
            run_results.append(
                {
                    "run_id": run_id,
                    "due_since": due_run.due_since.isoformat(),
                    "reasons": sorted(due_run.reasons),
                    "status": status,
                    "new_terminal_horizon_count": len(new_terminal_keys),
                    "new_benchmark_terminal_count": len(repaired_benchmark_ids),
                    "final_evaluated_horizon_count": final_counts["evaluated"],
                    "final_blocked_horizon_count": final_counts["blocked"],
                    "final_pending_horizon_count": final_counts["pending"],
                    "diagnostics": diagnostics,
                }
            )
            succeeded_run_ids.append(run_id)
        except Exception as exc:
            session.rollback()
            message = f"Research outcome cohort {run_id} failed."
            failures.append(
                {
                    "run_id": run_id,
                    "code": "OUTCOME_EVALUATION_FAILED",
                    "error_type": type(exc).__name__[:128],
                    "message": "Research shortlist outcome evaluation failed.",
                }
            )
        if progress is not None:
            progress("outcomes", position, len(selected), message)

    return {
        "status": "partial_failure" if failures else "completed",
        "market": normalized_market,
        "profile_id": normalized_profile,
        "verified_completed_through": completed_through.isoformat(),
        "run_limit": run_limit,
        "considered_run_count": len(selected),
        "selected_run_count": len(selected),
        "candidate_due_run_count": sum(
            "candidate_terminal" in item.reasons for item in selected
        ),
        "benchmark_due_run_count": sum(
            "benchmark_repair" in item.reasons for item in selected
        ),
        "processed_run_count": len(processed_run_ids),
        "succeeded_run_count": len(succeeded_run_ids),
        "failed_run_count": len(failures),
        "concurrent_reuse_count": concurrent_reuse_count,
        "has_more": has_more,
        "remaining_due_estimate": None,
        "selected_run_ids": [str(item.run_id) for item in selected],
        "processed_run_ids": processed_run_ids,
        "succeeded_run_ids": succeeded_run_ids,
        "failures": failures,
        "run_results": run_results,
        "final_evaluated_horizon_count": final_evaluated_horizon_count,
        "final_blocked_horizon_count": final_blocked_horizon_count,
        "final_pending_horizon_count": final_pending_horizon_count,
        "research_signal_only": True,
    }


def get_research_shortlist_outcome_tracking(
    *,
    session: Session,
    market: str = "CN",
    profile_id: str = "balanced_research",
    limit: int = 10,
    offset: int = 0,
    as_of: date | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    if normalized_market != "CN":
        raise ValueError(f"Unsupported research shortlist market: {market}")
    normalized_profile = profile_id.strip().lower()
    if not normalized_profile:
        raise ValueError("Research shortlist profile_id is required.")
    if limit < 1 or limit > 50:
        raise ValueError("Outcome tracking limit must be between 1 and 50.")
    if offset < 0:
        raise ValueError("Outcome tracking offset cannot be negative.")
    effective_as_of = _resolve_as_of(
        as_of=as_of,
        now=now,
        verified_completed_through=None,
    )
    base_query = (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.status == "committed")
        .filter(ResearchShortlistRun.market == normalized_market)
        .filter(ResearchShortlistRun.asset_type == "stock")
        .filter(ResearchShortlistRun.profile_id == normalized_profile)
        .order_by(
            ResearchShortlistRun.decision_date.desc(),
            ResearchShortlistRun.generated_at.desc(),
            ResearchShortlistRun.id.desc(),
        )
    )
    latest_run = base_query.first()
    if latest_run is None:
        return _tracking_no_data(
            market=normalized_market,
            profile_id=normalized_profile,
            limit=limit,
            offset=offset,
            as_of=effective_as_of,
        )
    history_query = base_query.filter(ResearchShortlistRun.id != latest_run.id)
    page_with_sentinel = history_query.offset(offset).limit(limit + 1).all()
    history_runs = page_with_sentinel[:limit]
    has_more = len(page_with_sentinel) > limit
    run_by_id = {run.id: run for run in [latest_run, *history_runs]}
    candidates_by_run = _candidates_for_runs(session, list(run_by_id))
    candidates = [
        candidate for run_id in run_by_id for candidate in candidates_by_run.get(run_id, [])
    ]
    bars = _candidate_bars(session, candidates=candidates, as_of=effective_as_of)
    outcomes = _outcomes_for_candidates(session, candidates)
    benchmark = _canonical_benchmark(session)
    details = {
        run_id: _serialize_run(
            run,
            candidates=candidates_by_run.get(run_id, []),
            candidate_bars=bars,
            terminal_outcomes=outcomes,
            benchmark=benchmark,
            as_of=effective_as_of,
        )
        for run_id, run in run_by_id.items()
    }
    return {
        "status": "ok",
        "as_of": effective_as_of.isoformat(),
        "market": normalized_market,
        "profile_id": normalized_profile,
        "latest": details[latest_run.id],
        "history": [
            {
                "run": details[run.id]["run"],
                "summaries": details[run.id]["summaries"],
            }
            for run in history_runs
        ],
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "research_signal_only": True,
        "safety": dict(SAFETY_PAYLOAD),
    }


def _resolve_as_of(
    *,
    as_of: date | None,
    now: datetime | None,
    verified_completed_through: date | None,
) -> date:
    current = _aware_utc(now or datetime.now(timezone.utc)).astimezone(SHANGHAI)
    public_upper_bound = current.date() - timedelta(days=1)
    upper_bound = public_upper_bound
    if verified_completed_through is not None:
        if verified_completed_through > current.date():
            raise ValueError("Verified completed-through date cannot be in the future.")
        if (
            verified_completed_through == current.date()
            and current.timetz().replace(tzinfo=None) < BAR_COMPLETION_TIME
        ):
            raise ValueError("The current Shanghai date is not complete before 16:00.")
        upper_bound = verified_completed_through

    effective = as_of or upper_bound
    if effective > upper_bound:
        raise ValueError(f"Outcome as_of must be on or before {upper_bound.isoformat()}.")
    return effective


def _parse_uuid(value: str | UUID) -> UUID | None:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError):
        return None


def _optional_uuid(value: str | UUID | None, *, label: str) -> UUID | None:
    if value is None:
        return None
    parsed = _parse_uuid(value)
    if parsed is None:
        raise ValueError(f"Invalid {label}.")
    return parsed


def _normalize_due_scope(
    *,
    market: str,
    profile_id: str,
    run_limit: int,
) -> tuple[str, str]:
    normalized_market = market.strip().upper()
    if normalized_market != "CN":
        raise ValueError(f"Unsupported research shortlist market: {market}")
    normalized_profile = profile_id.strip().lower()
    if not normalized_profile:
        raise ValueError("Research shortlist profile_id is required.")
    if run_limit < 1 or run_limit > MAX_DUE_RUN_LIMIT:
        raise ValueError(
            f"Outcome due-run limit must be between 1 and {MAX_DUE_RUN_LIMIT}."
        )
    return normalized_market, normalized_profile


def _select_due_research_shortlist_runs(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    run_limit: int,
) -> tuple[list[DueResearchShortlistRun], bool]:
    candidate_rows = session.execute(
        _candidate_due_run_query(
            session=session,
            market=market,
            profile_id=profile_id,
            completed_through=completed_through,
        ).limit(run_limit + 1)
    ).all()
    candidate_has_more = len(candidate_rows) > run_limit
    candidate_rows = candidate_rows[:run_limit]

    selected: dict[UUID, tuple[date, set[DueResearchShortlistReason]]] = {
        run_id: (due_since, {"candidate_terminal"})
        for run_id, due_since in candidate_rows
    }
    candidate_run_ids = list(selected)
    benchmark = _canonical_benchmark(session)
    if benchmark is not None and candidate_run_ids:
        overlap_rows = session.execute(
            _benchmark_due_run_query(
                session=session,
                market=market,
                profile_id=profile_id,
                completed_through=completed_through,
                benchmark=benchmark,
                include_run_ids=candidate_run_ids,
            )
        ).all()
        for run_id, due_since in overlap_rows:
            candidate_due_since, reasons = selected[run_id]
            selected[run_id] = (
                min(candidate_due_since, due_since),
                reasons | {"benchmark_repair"},
            )

    has_more = candidate_has_more
    if benchmark is not None and not candidate_has_more:
        remaining = run_limit - len(selected)
        benchmark_rows = session.execute(
            _benchmark_due_run_query(
                session=session,
                market=market,
                profile_id=profile_id,
                completed_through=completed_through,
                benchmark=benchmark,
                exclude_run_ids=candidate_run_ids,
            ).limit(remaining + 1)
        ).all()
        has_more = len(benchmark_rows) > remaining
        for run_id, due_since in benchmark_rows[:remaining]:
            selected[run_id] = (due_since, {"benchmark_repair"})

    return (
        [
            DueResearchShortlistRun(
                run_id=run_id,
                due_since=due_since,
                reasons=frozenset(reasons),
            )
            for run_id, (due_since, reasons) in selected.items()
        ],
        has_more,
    )


def _candidate_due_run_query(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    run_id: UUID | None = None,
):
    completed_bar = _completed_bar_predicate(session, DailyBar)
    horizon_queries = []
    for horizon_sessions in OUTCOME_HORIZONS:
        nth_completed_date = (
            select(DailyBar.trade_date)
            .where(DailyBar.instrument_id == ResearchShortlistCandidate.instrument_id)
            .where(DailyBar.trade_date > ResearchShortlistCandidate.entry_trade_date)
            .where(DailyBar.trade_date <= completed_through)
            .where(completed_bar)
            .order_by(DailyBar.trade_date)
            .offset(horizon_sessions - 1)
            .limit(1)
            .correlate(ResearchShortlistCandidate)
            .scalar_subquery()
        )
        terminal_exists = (
            select(ResearchCandidateOutcome.id)
            .where(
                ResearchCandidateOutcome.candidate_id
                == ResearchShortlistCandidate.id
            )
            .where(
                ResearchCandidateOutcome.horizon_sessions == horizon_sessions
            )
            .correlate(ResearchShortlistCandidate)
            .exists()
        )
        horizon_query = (
            select(
                ResearchShortlistCandidate.run_id.label("run_id"),
                nth_completed_date.label("due_since"),
            )
            .join(
                ResearchShortlistRun,
                ResearchShortlistRun.id == ResearchShortlistCandidate.run_id,
            )
            .where(ResearchShortlistRun.status == "committed")
            .where(ResearchShortlistRun.market == market)
            .where(ResearchShortlistRun.asset_type == "stock")
            .where(ResearchShortlistRun.profile_id == profile_id)
            .where(~terminal_exists)
        )
        if run_id is not None:
            horizon_query = horizon_query.where(
                ResearchShortlistCandidate.run_id == run_id
            )
        horizon_queries.append(horizon_query)

    due_rows = union_all(*horizon_queries).subquery("candidate_due_rows")
    grouped = (
        select(
            due_rows.c.run_id,
            func.min(due_rows.c.due_since).label("due_since"),
        )
        .group_by(due_rows.c.run_id)
        .subquery("candidate_due_runs")
    )
    return (
        select(grouped.c.run_id, grouped.c.due_since)
        .join(ResearchShortlistRun, ResearchShortlistRun.id == grouped.c.run_id)
        .where(grouped.c.due_since.is_not(None))
        .order_by(
            grouped.c.due_since,
            ResearchShortlistRun.decision_date,
            ResearchShortlistRun.generated_at,
            ResearchShortlistRun.id,
        )
    )


def _benchmark_due_run_query(
    *,
    session: Session,
    market: str,
    profile_id: str,
    completed_through: date,
    benchmark: Instrument,
    include_run_ids: list[UUID] | None = None,
    exclude_run_ids: list[UUID] | None = None,
):
    entry_bar = aliased(DailyBar, name="benchmark_entry_bar")
    maturity_bar = aliased(DailyBar, name="benchmark_maturity_bar")
    statement = (
        select(
            ResearchShortlistCandidate.run_id.label("run_id"),
            func.min(ResearchCandidateOutcome.maturity_trade_date).label(
                "due_since"
            ),
        )
        .select_from(ResearchCandidateOutcome)
        .join(
            ResearchShortlistCandidate,
            ResearchShortlistCandidate.id
            == ResearchCandidateOutcome.candidate_id,
        )
        .join(
            ResearchShortlistRun,
            ResearchShortlistRun.id == ResearchShortlistCandidate.run_id,
        )
        .join(
            entry_bar,
            and_(
                entry_bar.instrument_id == benchmark.id,
                entry_bar.trade_date
                == ResearchShortlistCandidate.entry_trade_date,
                _completed_bar_predicate(session, entry_bar),
            ),
        )
        .join(
            maturity_bar,
            and_(
                maturity_bar.instrument_id == benchmark.id,
                maturity_bar.trade_date
                == ResearchCandidateOutcome.maturity_trade_date,
                _completed_bar_predicate(session, maturity_bar),
            ),
        )
        .where(ResearchCandidateOutcome.status == "evaluated")
        .where(ResearchCandidateOutcome.benchmark_status == "pending")
        .where(
            ResearchCandidateOutcome.maturity_trade_date <= completed_through
        )
        .where(ResearchShortlistRun.status == "committed")
        .where(ResearchShortlistRun.market == market)
        .where(ResearchShortlistRun.asset_type == "stock")
        .where(ResearchShortlistRun.profile_id == profile_id)
    )
    if include_run_ids is not None:
        statement = statement.where(
            ResearchShortlistCandidate.run_id.in_(include_run_ids)
        )
    if exclude_run_ids:
        statement = statement.where(
            ~ResearchShortlistCandidate.run_id.in_(exclude_run_ids)
        )
    return statement.group_by(
        ResearchShortlistCandidate.run_id,
        ResearchShortlistRun.decision_date,
        ResearchShortlistRun.generated_at,
        ResearchShortlistRun.id,
    ).order_by(
        func.min(ResearchCandidateOutcome.maturity_trade_date),
        ResearchShortlistRun.decision_date,
        ResearchShortlistRun.generated_at,
        ResearchShortlistRun.id,
    )


def _due_reasons_for_run(
    *,
    session: Session,
    run_id: UUID,
    market: str,
    profile_id: str,
    completed_through: date,
) -> frozenset[DueResearchShortlistReason]:
    reasons: set[DueResearchShortlistReason] = set()
    candidate_due = session.execute(
        _candidate_due_run_query(
            session=session,
            market=market,
            profile_id=profile_id,
            completed_through=completed_through,
            run_id=run_id,
        ).limit(1)
    ).first()
    if candidate_due is not None:
        reasons.add("candidate_terminal")
    benchmark = _canonical_benchmark(session)
    if benchmark is not None:
        benchmark_due = session.execute(
            _benchmark_due_run_query(
                session=session,
                market=market,
                profile_id=profile_id,
                completed_through=completed_through,
                benchmark=benchmark,
                include_run_ids=[run_id],
            ).limit(1)
        ).first()
        if benchmark_due is not None:
            reasons.add("benchmark_repair")
    return frozenset(reasons)


def _outcome_run_state(session: Session, run_id: UUID) -> _OutcomeRunState:
    rows = (
        session.query(ResearchCandidateOutcome)
        .join(
            ResearchShortlistCandidate,
            ResearchShortlistCandidate.id
            == ResearchCandidateOutcome.candidate_id,
        )
        .filter(ResearchShortlistCandidate.run_id == run_id)
        .all()
    )
    return _OutcomeRunState(
        terminal_keys=frozenset(
            (row.candidate_id, row.horizon_sessions) for row in rows
        ),
        benchmark_statuses={row.id: row.benchmark_status for row in rows},
    )


def _final_horizon_counts(payload: dict[str, object] | None) -> dict[str, int]:
    counts = {"evaluated": 0, "blocked": 0, "pending": 0}
    if payload is None:
        return counts
    items = payload.get("items")
    if not isinstance(items, list):
        return counts
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("horizons"), list):
            continue
        for horizon in item["horizons"]:
            if not isinstance(horizon, dict):
                continue
            status = horizon.get("status")
            if status in counts:
                counts[status] += 1
    return counts


def _payload_has_terminal_reason(
    payload: dict[str, object] | None,
    reasons: frozenset[DueResearchShortlistReason],
) -> bool:
    if payload is None:
        return False
    items = payload.get("items")
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("horizons"), list):
            continue
        for horizon in item["horizons"]:
            if not isinstance(horizon, dict):
                continue
            if (
                "candidate_terminal" in reasons
                and horizon.get("status") in {"evaluated", "blocked"}
            ):
                return True
            benchmark = horizon.get("benchmark")
            if (
                "benchmark_repair" in reasons
                and isinstance(benchmark, dict)
                and benchmark.get("status") in {"evaluated", "blocked"}
            ):
                return True
    return False


def _committed_run(
    session: Session,
    run_id: str | UUID,
) -> ResearchShortlistRun | None:
    parsed = _parse_uuid(run_id)
    if parsed is None:
        return None
    run = session.get(ResearchShortlistRun, parsed)
    if run is None or run.status != "committed":
        return None
    return run


def _candidates_for_runs(
    session: Session,
    run_ids: list[UUID],
) -> dict[UUID, list[ResearchShortlistCandidate]]:
    if not run_ids:
        return {}
    rows = (
        session.query(ResearchShortlistCandidate)
        .options(joinedload(ResearchShortlistCandidate.instrument))
        .filter(ResearchShortlistCandidate.run_id.in_(run_ids))
        .order_by(
            ResearchShortlistCandidate.run_id,
            ResearchShortlistCandidate.rank,
        )
        .all()
    )
    grouped: dict[UUID, list[ResearchShortlistCandidate]] = {run_id: [] for run_id in run_ids}
    for row in rows:
        grouped.setdefault(row.run_id, []).append(row)
    return grouped


def _candidate_bars(
    session: Session,
    *,
    candidates: list[ResearchShortlistCandidate],
    as_of: date,
) -> dict[UUID, _CandidateBarWindow]:
    candidate_ids = [candidate.id for candidate in candidates]
    if not candidate_ids:
        return {}

    candidate_scope = (
        select(
            ResearchShortlistCandidate.id.label("candidate_id"),
            ResearchShortlistCandidate.instrument_id.label("instrument_id"),
            ResearchShortlistCandidate.entry_trade_date.label("entry_trade_date"),
        )
        .where(ResearchShortlistCandidate.id.in_(candidate_ids))
        .cte("candidate_scope")
    )
    completed_bar = _completed_bar_predicate(session, DailyBar)
    forward_position = (
        func.sum(
            case(
                (DailyBar.trade_date > candidate_scope.c.entry_trade_date, 1),
                else_=0,
            )
        )
        .over(
            partition_by=candidate_scope.c.candidate_id,
            order_by=DailyBar.trade_date,
            rows=(None, 0),
        )
        .label("forward_position")
    )
    ranked_bars = (
        select(
            candidate_scope.c.candidate_id,
            DailyBar.instrument_id.label("instrument_id"),
            DailyBar.trade_date.label("trade_date"),
            forward_position,
        )
        .select_from(candidate_scope)
        .join(
            DailyBar,
            and_(
                DailyBar.instrument_id == candidate_scope.c.instrument_id,
                DailyBar.trade_date >= candidate_scope.c.entry_trade_date,
                DailyBar.trade_date <= as_of,
                or_(
                    DailyBar.trade_date == candidate_scope.c.entry_trade_date,
                    and_(
                        DailyBar.trade_date > candidate_scope.c.entry_trade_date,
                        completed_bar,
                    ),
                ),
            ),
        )
        .subquery()
    )
    candidate_bar_keys = (
        select(
            ranked_bars.c.candidate_id,
            ranked_bars.c.instrument_id,
            ranked_bars.c.trade_date,
            ranked_bars.c.forward_position,
        )
        .where(ranked_bars.c.forward_position <= max(OUTCOME_HORIZONS))
        .subquery()
    )

    incomplete_bar = aliased(DailyBar)
    incomplete_candidates = (
        select(candidate_scope.c.candidate_id)
        .select_from(candidate_scope)
        .join(
            incomplete_bar,
            and_(
                incomplete_bar.instrument_id == candidate_scope.c.instrument_id,
                incomplete_bar.trade_date > candidate_scope.c.entry_trade_date,
                incomplete_bar.trade_date <= as_of,
                ~_completed_bar_predicate(session, incomplete_bar),
            ),
        )
        .group_by(candidate_scope.c.candidate_id)
        .subquery()
    )
    has_incomplete_forward = (
        incomplete_candidates.c.candidate_id.is_not(None).label("has_incomplete_forward")
    )
    rows = (
        session.execute(
            select(
                candidate_scope.c.candidate_id,
                DailyBar,
                has_incomplete_forward,
            )
            .select_from(candidate_scope)
            .outerjoin(
                candidate_bar_keys,
                candidate_bar_keys.c.candidate_id == candidate_scope.c.candidate_id,
            )
            .outerjoin(
                DailyBar,
                and_(
                    DailyBar.instrument_id == candidate_bar_keys.c.instrument_id,
                    DailyBar.trade_date == candidate_bar_keys.c.trade_date,
                ),
            )
            .outerjoin(
                incomplete_candidates,
                incomplete_candidates.c.candidate_id == candidate_scope.c.candidate_id,
            )
            .order_by(
                candidate_scope.c.candidate_id,
                candidate_bar_keys.c.forward_position,
            )
        )
        .all()
    )
    grouped = {
        candidate_id: _CandidateBarWindow(bars=[])
        for candidate_id in candidate_ids
    }
    for candidate_id, bar, has_incomplete_forward in rows:
        window = grouped[candidate_id]
        window.has_incomplete_forward = bool(has_incomplete_forward)
        if bar is not None:
            window.bars.append(bar)
    return grouped


def _completed_bar_predicate(session: Session, bar):
    return completed_daily_bar_predicate(session, bar)


def _outcomes_for_candidates(
    session: Session,
    candidates: list[ResearchShortlistCandidate],
) -> dict[tuple[UUID, int], ResearchCandidateOutcome]:
    candidate_ids = [candidate.id for candidate in candidates]
    if not candidate_ids:
        return {}
    rows = (
        session.query(ResearchCandidateOutcome)
        .filter(ResearchCandidateOutcome.candidate_id.in_(candidate_ids))
        .all()
    )
    return {(row.candidate_id, row.horizon_sessions): row for row in rows}


def _canonical_benchmark(session: Session) -> Instrument | None:
    return (
        session.query(Instrument)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == "CN")
        .filter(Instrument.asset_type == "index")
        .filter(Instrument.symbol == BENCHMARK_CODE)
        .one_or_none()
    )


def _benchmark_bars(
    session: Session,
    *,
    benchmark: Instrument | None,
    trade_dates: set[date],
) -> dict[date, DailyBar]:
    if benchmark is None or not trade_dates:
        return {}
    rows = (
        session.query(DailyBar)
        .filter(DailyBar.instrument_id == benchmark.id)
        .filter(DailyBar.trade_date.in_(trade_dates))
        .order_by(DailyBar.trade_date)
        .all()
    )
    return {row.trade_date: row for row in rows}


def _required_benchmark_dates(
    *,
    candidates: list[ResearchShortlistCandidate],
    candidate_bars: dict[UUID, _CandidateBarWindow],
    existing: dict[tuple[UUID, int], ResearchCandidateOutcome],
    as_of: date,
) -> set[date]:
    required_dates = {candidate.entry_trade_date for candidate in candidates}
    required_dates.update(
        outcome.maturity_trade_date
        for outcome in existing.values()
        if outcome.status == "evaluated"
        and outcome.benchmark_status == "pending"
        and outcome.maturity_trade_date <= as_of
    )
    for candidate in candidates:
        window = candidate_bars.get(candidate.id)
        bars = window.bars if window is not None else []
        forward_bars = [
            bar
            for bar in bars
            if candidate.entry_trade_date < bar.trade_date <= as_of
            and _bar_is_complete(bar)
        ]
        for horizon_sessions in OUTCOME_HORIZONS:
            if (candidate.id, horizon_sessions) in existing:
                continue
            if len(forward_bars) >= horizon_sessions:
                required_dates.add(
                    forward_bars[horizon_sessions - 1].trade_date
                )
    return required_dates


def _stage_terminal_outcomes(
    *,
    candidates: list[ResearchShortlistCandidate],
    candidate_bars: dict[UUID, _CandidateBarWindow],
    existing: dict[tuple[UUID, int], ResearchCandidateOutcome],
    benchmark: Instrument | None,
    benchmark_bars: dict[date, DailyBar],
    as_of: date,
    evaluated_at: datetime,
    evaluation_task_run_id: UUID | None,
) -> list[dict[str, object]]:
    staged: list[dict[str, object]] = []
    for candidate in candidates:
        window = candidate_bars.get(candidate.id)
        bars = window.bars if window is not None else []
        forward_bars = [
            bar
            for bar in bars
            if candidate.entry_trade_date < bar.trade_date <= as_of and _bar_is_complete(bar)
        ]
        entry_bar = next(
            (bar for bar in bars if bar.trade_date == candidate.entry_trade_date),
            None,
        )
        for horizon_sessions in OUTCOME_HORIZONS:
            if (candidate.id, horizon_sessions) in existing:
                continue
            if len(forward_bars) < horizon_sessions:
                continue
            horizon_bars = forward_bars[:horizon_sessions]
            maturity_bar = horizon_bars[-1]
            status, result_values, diagnostics = _candidate_result_values(
                candidate=candidate,
                entry_bar=entry_bar,
                forward_bars=horizon_bars,
            )
            benchmark_values = _benchmark_result_values(
                candidate_status=status,
                candidate_return=result_values.get("return_ratio"),
                entry_date=candidate.entry_trade_date,
                maturity_date=maturity_bar.trade_date,
                benchmark=benchmark,
                benchmark_bars=benchmark_bars,
                completed_at=evaluated_at,
            )
            staged.append(
                {
                    "candidate_id": candidate.id,
                    "horizon_sessions": horizon_sessions,
                    "methodology_version": OUTCOME_METHODOLOGY_VERSION,
                    "status": status,
                    "evaluation_as_of": as_of,
                    "available_forward_bars": horizon_sessions,
                    "evaluation_task_run_id": evaluation_task_run_id,
                    "maturity_trade_date": maturity_bar.trade_date,
                    **result_values,
                    **benchmark_values,
                    "diagnostics_json": diagnostics,
                    "created_at": evaluated_at,
                    "evaluated_at": evaluated_at,
                }
            )
    return staged


def _candidate_result_values(
    *,
    candidate: ResearchShortlistCandidate,
    entry_bar: DailyBar | None,
    forward_bars: list[DailyBar],
) -> tuple[str, dict[str, object], list[str]]:
    diagnostics: list[str] = []
    if not candidate.instrument.is_active:
        diagnostics.append("INSTRUMENT_INACTIVE")
    if entry_bar is None:
        return "blocked", _empty_candidate_values(), diagnostics + ["ENTRY_BAR_MISSING"]
    if not _timestamp_is_complete(
        candidate.entry_ingested_at,
        candidate.entry_trade_date,
    ) or not _bar_is_complete(entry_bar):
        return "blocked", _empty_candidate_values(), diagnostics + ["ENTRY_BAR_INCOMPLETE"]
    if _price_error(entry_bar) is not None:
        return "blocked", _empty_candidate_values(), diagnostics + ["ENTRY_BAR_REVISED"]

    frozen_adjustment, frozen_corrected = _effective_adjustment(
        candidate.entry_source,
        candidate.entry_adjustment,
    )
    current_adjustment, current_corrected = _effective_adjustment(
        entry_bar.source,
        entry_bar.adjustment,
    )
    if frozen_corrected or current_corrected:
        diagnostics.append("PROVENANCE_ADJUSTMENT_CORRECTED")
    if frozen_adjustment is None or current_adjustment is None:
        return "blocked", _empty_candidate_values(), diagnostics + ["ENTRY_ADJUSTMENT_UNKNOWN"]
    if (
        Decimal(entry_bar.close) != Decimal(candidate.entry_close)
        or current_adjustment != frozen_adjustment
    ):
        return "blocked", _empty_candidate_values(), diagnostics + ["ENTRY_BAR_REVISED"]

    for bar in forward_bars:
        price_error = _price_error(bar)
        if price_error is not None:
            return "blocked", _empty_candidate_values(), diagnostics + [price_error]
        adjustment, corrected = _effective_adjustment(bar.source, bar.adjustment)
        if corrected and "PROVENANCE_ADJUSTMENT_CORRECTED" not in diagnostics:
            diagnostics.append("PROVENANCE_ADJUSTMENT_CORRECTED")
        if adjustment is None:
            return (
                "blocked",
                _empty_candidate_values(),
                diagnostics + ["FORWARD_ADJUSTMENT_UNKNOWN"],
            )
        if adjustment != frozen_adjustment:
            return (
                "blocked",
                _empty_candidate_values(),
                diagnostics + ["FORWARD_ADJUSTMENT_MISMATCH"],
            )

    if frozen_adjustment == "qfq":
        diagnostics.append("QFQ_PROXY_BASIS")
    exit_bar = forward_bars[-1]
    minimum_bar = min(forward_bars, key=lambda bar: (bar.low, bar.trade_date))
    entry_close = Decimal(candidate.entry_close)
    return_ratio = Decimal(exit_bar.close) / entry_close - Decimal("1")
    drawdown_ratio = min(
        Decimal("0"),
        Decimal(minimum_bar.low) / entry_close - Decimal("1"),
    )
    return (
        "evaluated",
        {
            "exit_close": exit_bar.close,
            "minimum_forward_low": minimum_bar.low,
            "minimum_forward_low_trade_date": minimum_bar.trade_date,
            "return_ratio": return_ratio,
            "drawdown_ratio": drawdown_ratio,
            **_candidate_provenance("exit", exit_bar),
            **_candidate_provenance("minimum_low", minimum_bar),
        },
        diagnostics,
    )


def _empty_candidate_values() -> dict[str, object]:
    return {
        "exit_close": None,
        "minimum_forward_low": None,
        "minimum_forward_low_trade_date": None,
        "return_ratio": None,
        "drawdown_ratio": None,
        "exit_provider": None,
        "exit_source": None,
        "exit_adjustment": None,
        "exit_source_priority": None,
        "exit_ingested_at": None,
        "minimum_low_provider": None,
        "minimum_low_source": None,
        "minimum_low_adjustment": None,
        "minimum_low_source_priority": None,
        "minimum_low_ingested_at": None,
    }


def _candidate_provenance(prefix: str, bar: DailyBar) -> dict[str, object]:
    return {
        f"{prefix}_provider": bar.provider,
        f"{prefix}_source": bar.source,
        f"{prefix}_adjustment": _effective_adjustment(bar.source, bar.adjustment)[0],
        f"{prefix}_source_priority": bar.source_priority,
        f"{prefix}_ingested_at": bar.ingested_at,
    }


def _benchmark_result_values(
    *,
    candidate_status: str,
    candidate_return: object,
    entry_date: date,
    maturity_date: date,
    benchmark: Instrument | None,
    benchmark_bars: dict[date, DailyBar],
    completed_at: datetime,
) -> dict[str, object]:
    base = _empty_benchmark_values()
    if candidate_status != "evaluated":
        return {
            **base,
            "benchmark_status": "not_applicable",
            "benchmark_diagnostics_json": [],
        }
    if benchmark is None:
        return {
            **base,
            "benchmark_status": "pending",
            "benchmark_diagnostics_json": ["BENCHMARK_INSTRUMENT_MISSING"],
        }
    base["benchmark_instrument_id"] = benchmark.id
    entry_bar = benchmark_bars.get(entry_date)
    exit_bar = benchmark_bars.get(maturity_date)
    missing: list[str] = []
    if entry_bar is None or not _bar_is_complete(entry_bar):
        missing.append("BENCHMARK_ENTRY_MISSING")
    if exit_bar is None or not _bar_is_complete(exit_bar):
        missing.append("BENCHMARK_EXIT_MISSING")
    if missing:
        return {
            **base,
            "benchmark_status": "pending",
            "benchmark_diagnostics_json": missing,
        }
    assert entry_bar is not None and exit_bar is not None
    if _price_error(entry_bar) is not None or _price_error(exit_bar) is not None:
        return {
            **base,
            "benchmark_status": "blocked",
            "benchmark_diagnostics_json": ["BENCHMARK_PRICE_INVALID"],
            "benchmark_completed_at": completed_at,
        }
    entry_adjustment, entry_corrected = _effective_adjustment(
        entry_bar.source,
        entry_bar.adjustment,
    )
    exit_adjustment, exit_corrected = _effective_adjustment(
        exit_bar.source,
        exit_bar.adjustment,
    )
    corrected = ["PROVENANCE_ADJUSTMENT_CORRECTED"] if entry_corrected or exit_corrected else []
    if entry_adjustment is None or exit_adjustment is None:
        return {
            **base,
            "benchmark_status": "blocked",
            "benchmark_diagnostics_json": corrected + ["BENCHMARK_ADJUSTMENT_UNKNOWN"],
            "benchmark_completed_at": completed_at,
        }
    if entry_adjustment != exit_adjustment:
        return {
            **base,
            "benchmark_status": "blocked",
            "benchmark_diagnostics_json": corrected + ["BENCHMARK_ADJUSTMENT_MISMATCH"],
            "benchmark_completed_at": completed_at,
        }
    benchmark_return = Decimal(exit_bar.close) / Decimal(entry_bar.close) - Decimal("1")
    return {
        **base,
        "benchmark_status": "evaluated",
        "benchmark_entry_trade_date": entry_date,
        "benchmark_entry_close": entry_bar.close,
        **_benchmark_provenance("entry", entry_bar),
        "benchmark_exit_trade_date": maturity_date,
        "benchmark_exit_close": exit_bar.close,
        **_benchmark_provenance("exit", exit_bar),
        "benchmark_return_ratio": benchmark_return,
        "excess_return_ratio": Decimal(str(candidate_return)) - benchmark_return,
        "benchmark_diagnostics_json": corrected,
        "benchmark_completed_at": completed_at,
    }


def _empty_benchmark_values() -> dict[str, object]:
    return {
        "benchmark_code": BENCHMARK_CODE,
        "benchmark_instrument_id": None,
        "benchmark_status": "pending",
        "benchmark_entry_trade_date": None,
        "benchmark_entry_close": None,
        "benchmark_entry_provider": None,
        "benchmark_entry_source": None,
        "benchmark_entry_adjustment": None,
        "benchmark_entry_source_priority": None,
        "benchmark_entry_ingested_at": None,
        "benchmark_exit_trade_date": None,
        "benchmark_exit_close": None,
        "benchmark_exit_provider": None,
        "benchmark_exit_source": None,
        "benchmark_exit_adjustment": None,
        "benchmark_exit_source_priority": None,
        "benchmark_exit_ingested_at": None,
        "benchmark_return_ratio": None,
        "excess_return_ratio": None,
        "benchmark_completed_at": None,
    }


def _benchmark_provenance(prefix: str, bar: DailyBar) -> dict[str, object]:
    return {
        f"benchmark_{prefix}_provider": bar.provider,
        f"benchmark_{prefix}_source": bar.source,
        f"benchmark_{prefix}_adjustment": _effective_adjustment(
            bar.source,
            bar.adjustment,
        )[0],
        f"benchmark_{prefix}_source_priority": bar.source_priority,
        f"benchmark_{prefix}_ingested_at": bar.ingested_at,
    }


def _price_error(bar: DailyBar) -> str | None:
    values = [bar.open, bar.high, bar.low, bar.close]
    if any(not _positive_finite(value) for value in values):
        return "FORWARD_PRICE_INVALID"
    if bar.high < max(bar.open, bar.close, bar.low) or bar.low > min(
        bar.open,
        bar.close,
        bar.high,
    ):
        return "FORWARD_OHLC_INVALID"
    return None


def _positive_finite(value: object) -> bool:
    try:
        decimal = Decimal(str(value))
    except Exception:
        return False
    return decimal.is_finite() and decimal > 0 and math.isfinite(float(decimal))


def _effective_adjustment(source: object, adjustment: object) -> tuple[str | None, bool]:
    return resolve_daily_bar_adjustment(source, adjustment)


def _timestamp_is_complete(value: datetime, trade_date: date) -> bool:
    return daily_bar_timestamp_is_complete(value, trade_date)


def _insert_outcomes_ignore_conflicts(
    session: Session,
    values: list[dict[str, object]],
) -> None:
    dialect_name = session.get_bind().dialect.name
    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as dialect_insert

        statement = dialect_insert(ResearchCandidateOutcome).values(values)
        session.execute(
            statement.on_conflict_do_nothing(index_elements=["candidate_id", "horizon_sessions"])
        )
        return
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert

        statement = dialect_insert(ResearchCandidateOutcome).values(values)
        session.execute(
            statement.on_conflict_do_nothing(index_elements=["candidate_id", "horizon_sessions"])
        )
        return

    for row in values:
        try:
            with session.begin_nested():
                session.add(ResearchCandidateOutcome(**row))
                session.flush()
        except IntegrityError:
            continue


def _enrich_pending_benchmarks(
    session: Session,
    *,
    outcomes: list[ResearchCandidateOutcome],
    candidates: list[ResearchShortlistCandidate],
    benchmark: Instrument | None,
    benchmark_bars: dict[date, DailyBar],
    completed_at: datetime,
) -> None:
    candidates_by_id = {candidate.id: candidate for candidate in candidates}
    for outcome in outcomes:
        if outcome.status != "evaluated" or outcome.benchmark_status != "pending":
            continue
        candidate = candidates_by_id[outcome.candidate_id]
        values = _benchmark_result_values(
            candidate_status=outcome.status,
            candidate_return=outcome.return_ratio,
            entry_date=candidate.entry_trade_date,
            maturity_date=outcome.maturity_trade_date,
            benchmark=benchmark,
            benchmark_bars=benchmark_bars,
            completed_at=completed_at,
        )
        if values["benchmark_status"] == "pending":
            session.execute(
                update(ResearchCandidateOutcome)
                .where(ResearchCandidateOutcome.id == outcome.id)
                .where(ResearchCandidateOutcome.benchmark_status == "pending")
                .values(
                    benchmark_code=values["benchmark_code"],
                    benchmark_instrument_id=values["benchmark_instrument_id"],
                    benchmark_diagnostics_json=values["benchmark_diagnostics_json"],
                )
            )
            continue
        session.execute(
            update(ResearchCandidateOutcome)
            .where(ResearchCandidateOutcome.id == outcome.id)
            .where(ResearchCandidateOutcome.benchmark_status == "pending")
            .values(**values)
        )


@contextmanager
def _serialized_evaluation(session: Session, run_id: UUID) -> Iterator[None]:
    dialect_name = session.get_bind().dialect.name
    local_lock: threading.RLock | None = None
    lock_key = hashlib.sha256(str(run_id).encode("ascii")).hexdigest()
    if dialect_name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _postgres_advisory_lock_key(lock_key)},
        )
    else:
        stripe_index = int(lock_key[:16], 16) % len(_EVALUATION_LOCK_STRIPES)
        local_lock = _EVALUATION_LOCK_STRIPES[stripe_index]
        local_lock.acquire()
        try:
            if session.in_transaction():
                session.rollback()
        except Exception:
            local_lock.release()
            raise
    try:
        yield
    finally:
        try:
            if session.in_transaction():
                session.rollback()
        finally:
            if local_lock is not None:
                local_lock.release()


def _postgres_advisory_lock_key(value: str) -> int:
    unsigned_value = int(value[:16], 16)
    if unsigned_value >= 2**63:
        return unsigned_value - 2**64
    return unsigned_value


def _serialize_run(
    run: ResearchShortlistRun,
    *,
    candidates: list[ResearchShortlistCandidate],
    candidate_bars: dict[UUID, _CandidateBarWindow],
    terminal_outcomes: dict[tuple[UUID, int], ResearchCandidateOutcome],
    benchmark: Instrument | None,
    as_of: date,
) -> dict[str, object]:
    items = [
        _serialize_candidate(
            candidate,
            bar_window=candidate_bars.get(candidate.id),
            terminal_outcomes=terminal_outcomes,
            benchmark=benchmark,
            as_of=as_of,
        )
        for candidate in candidates
    ]
    return {
        "status": "ok",
        "as_of": as_of.isoformat(),
        "run": {
            "id": str(run.id),
            "decision_date": run.decision_date.isoformat(),
            "market": run.market,
            "profile_id": run.profile_id,
        },
        "items": items,
        "summaries": _aggregate_horizons(items),
        "research_signal_only": True,
        "safety": dict(SAFETY_PAYLOAD),
    }


def _serialize_candidate(
    candidate: ResearchShortlistCandidate,
    *,
    bar_window: _CandidateBarWindow | None,
    terminal_outcomes: dict[tuple[UUID, int], ResearchCandidateOutcome],
    benchmark: Instrument | None,
    as_of: date,
) -> dict[str, object]:
    bars = bar_window.bars if bar_window is not None else []
    eligible_forward = [
        bar
        for bar in bars
        if candidate.entry_trade_date < bar.trade_date <= as_of and _bar_is_complete(bar)
    ]
    ignored_incomplete = bool(bar_window and bar_window.has_incomplete_forward)
    horizons: list[dict[str, object]] = []
    for horizon_sessions in OUTCOME_HORIZONS:
        terminal = terminal_outcomes.get((candidate.id, horizon_sessions))
        if terminal is not None and terminal.maturity_trade_date <= as_of:
            horizons.append(_serialize_terminal_outcome(terminal))
            continue
        available = min(len(eligible_forward), horizon_sessions)
        diagnostics = ["INCOMPLETE_FORWARD_BAR_IGNORED"] if ignored_incomplete else []
        horizons.append(
            {
                "horizon_sessions": horizon_sessions,
                "status": "pending",
                "available_forward_bars": available,
                "ready_for_evaluation": available == horizon_sessions,
                "evaluation_task_run_id": None,
                "maturity_date": None,
                "exit_close": None,
                "minimum_forward_low": None,
                "minimum_low_date": None,
                "return_ratio": None,
                "drawdown_ratio": None,
                "benchmark": _pending_benchmark(benchmark),
                "diagnostics": diagnostics,
            }
        )
    return {
        "candidate_id": str(candidate.id),
        "instrument_id": str(candidate.instrument_id),
        "symbol": candidate.symbol,
        "name": candidate.name,
        "rank": candidate.rank,
        "entry_trade_date": candidate.entry_trade_date.isoformat(),
        "horizons": horizons,
    }


def _pending_benchmark(benchmark: Instrument | None) -> dict[str, object]:
    return {
        "code": BENCHMARK_CODE,
        "status": "pending",
        "instrument_id": str(benchmark.id) if benchmark is not None else None,
        "entry_date": None,
        "exit_date": None,
        "entry_close": None,
        "exit_close": None,
        "return_ratio": None,
        "excess_return_ratio": None,
        "diagnostics": [] if benchmark is not None else ["BENCHMARK_INSTRUMENT_MISSING"],
    }


def _serialize_terminal_outcome(
    outcome: ResearchCandidateOutcome,
) -> dict[str, object]:
    return {
        "horizon_sessions": outcome.horizon_sessions,
        "status": outcome.status,
        "available_forward_bars": outcome.available_forward_bars,
        "ready_for_evaluation": False,
        "evaluation_task_run_id": str(outcome.evaluation_task_run_id)
        if outcome.evaluation_task_run_id is not None
        else None,
        "maturity_date": outcome.maturity_trade_date.isoformat(),
        "exit_close": _float_or_none(outcome.exit_close),
        "minimum_forward_low": _float_or_none(outcome.minimum_forward_low),
        "minimum_low_date": _date_iso(outcome.minimum_forward_low_trade_date),
        "return_ratio": _float_or_none(outcome.return_ratio),
        "drawdown_ratio": _float_or_none(outcome.drawdown_ratio),
        "benchmark": {
            "code": outcome.benchmark_code,
            "status": outcome.benchmark_status,
            "instrument_id": str(outcome.benchmark_instrument_id)
            if outcome.benchmark_instrument_id is not None
            else None,
            "entry_date": _date_iso(outcome.benchmark_entry_trade_date),
            "exit_date": _date_iso(outcome.benchmark_exit_trade_date),
            "entry_close": _float_or_none(outcome.benchmark_entry_close),
            "exit_close": _float_or_none(outcome.benchmark_exit_close),
            "return_ratio": _float_or_none(outcome.benchmark_return_ratio),
            "excess_return_ratio": _float_or_none(outcome.excess_return_ratio),
            "diagnostics": _diagnostic_codes(outcome.benchmark_diagnostics_json),
        },
        "diagnostics": _diagnostic_codes(outcome.diagnostics_json),
    }


def _diagnostic_codes(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if isinstance(value, str) and value:
            result.append(value)
        elif isinstance(value, dict) and isinstance(value.get("code"), str):
            result.append(value["code"])
    return result


def _date_iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _bar_is_complete(bar: DailyBar) -> bool:
    return daily_bar_is_complete(bar)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _aggregate_horizons(items: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    for horizon_sessions in OUTCOME_HORIZONS:
        rows = [
            next(
                horizon
                for horizon in item["horizons"]
                if horizon["horizon_sessions"] == horizon_sessions
            )
            for item in items
        ]
        evaluated = [row for row in rows if row["status"] == "evaluated"]
        blocked = [row for row in rows if row["status"] == "blocked"]
        pending = [row for row in rows if row["status"] == "pending"]
        returns = _decimal_values(row.get("return_ratio") for row in evaluated)
        drawdowns = _decimal_values(row.get("drawdown_ratio") for row in evaluated)
        excess_returns = _decimal_values(
            row["benchmark"].get("excess_return_ratio") for row in evaluated
        )
        summaries.append(
            {
                "horizon_sessions": horizon_sessions,
                "total_count": len(rows),
                "evaluated_count": len(evaluated),
                "pending_count": len(pending),
                "blocked_count": len(blocked),
                "return_sample_size": len(returns),
                "benchmark_sample_size": len(excess_returns),
                "positive_return_ratio": _ratio(sum(value > 0 for value in returns), len(returns)),
                "mean_return_ratio": _mean(returns),
                "median_return_ratio": _float_or_none(median(returns)) if returns else None,
                "mean_drawdown_ratio": _mean(drawdowns),
                "mean_excess_return_ratio": _mean(excess_returns),
            }
        )
    return summaries


def _tracking_no_data(
    *,
    market: str,
    profile_id: str,
    limit: int,
    offset: int,
    as_of: date,
) -> dict[str, object]:
    return {
        "status": "no_data",
        "as_of": as_of.isoformat(),
        "market": market,
        "profile_id": profile_id,
        "latest": None,
        "history": [],
        "limit": limit,
        "offset": offset,
        "has_more": False,
        "research_signal_only": True,
        "safety": dict(SAFETY_PAYLOAD),
    }


def _decimal_values(values: Iterable[object]) -> list[Decimal]:
    return [Decimal(str(value)) for value in values if value is not None]


def _mean(values: list[Decimal]) -> float | None:
    if not values:
        return None
    return float(sum(values, Decimal("0")) / len(values))


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _float_or_none(value: object) -> float | None:
    return float(value) if value is not None else None
