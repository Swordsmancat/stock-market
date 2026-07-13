from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from packages.services import daily_research_loop as loop
from packages.services.research_shortlists import ResearchShortlistReadinessError


FIXED_NOW = datetime(2026, 7, 13, 13, 30, tzinfo=timezone.utc)


def _ready_watermark() -> dict[str, object]:
    return {
        "status": "ready",
        "verified_completed_through": "2026-07-13",
        "backfill_run_id": str(uuid4()),
        "backfill_task_run_id": str(uuid4()),
        "exact_date_ready_count": 96,
        "active_count": 100,
        "coverage_ratio": 0.96,
    }


def _outcomes(*, failed: int = 0) -> dict[str, object]:
    return {
        "status": "partial_failure" if failed else "completed",
        "candidate_due_run_count": 2,
        "benchmark_due_run_count": 1,
        "processed_run_count": 3,
        "failed_run_count": failed,
        "failures": [] if not failed else [{"code": "OUTCOME_EVALUATION_FAILED"}],
    }


def test_daily_research_loop_defers_without_mutation_when_watermark_not_ready(
    monkeypatch,
) -> None:
    session = MagicMock()
    progress: list[tuple[str, int, int, str]] = []
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: {
            "status": "not_ready",
            "code": "DAILY_BAR_WATERMARK_NOT_READY",
        },
    )
    evaluate = MagicMock()
    generate = MagicMock()
    monkeypatch.setattr(loop, "evaluate_due_research_shortlist_outcomes", evaluate)
    monkeypatch.setattr(loop, "generate_research_shortlist", generate)

    result = loop.run_daily_research_loop(
        loop.DailyResearchLoopInput(),
        session=session,
        task_run_id=uuid4(),
        now=FIXED_NOW,
        progress=lambda *args: progress.append(args),
    )

    assert result["status"] == "deferred"
    assert result["watermark"]["code"] == "DAILY_BAR_WATERMARK_NOT_READY"
    assert result["outcomes"] == {"status": "skipped", "code": "WATERMARK_NOT_READY"}
    assert result["publication"] == {"status": "skipped", "code": "WATERMARK_NOT_READY"}
    assert result["research_signal_only"] is True
    assert progress[0][:3] == ("watermark", 0, 3)
    assert progress[-1][:3] == ("completed", 3, 3)
    evaluate.assert_not_called()
    generate.assert_not_called()


def test_daily_research_loop_evaluates_due_runs_and_publishes_exact_watermark(
    monkeypatch,
) -> None:
    session = MagicMock()
    task_run_id = uuid4()
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: _ready_watermark(),
    )

    def evaluate(**kwargs):
        captured["evaluation"] = kwargs
        return _outcomes()

    def generate(payload, *, session):
        captured["generation"] = payload
        return {
            "status": "ok",
            "run": {
                "id": str(uuid4()),
                "generation_task_run_id": str(task_run_id),
                "generation_key": "a" * 64,
                "decision_date": "2026-07-13",
                "diagnostics": [],
            },
            "items": [{"symbol": "600519"}],
        }

    monkeypatch.setattr(loop, "evaluate_due_research_shortlist_outcomes", evaluate)
    monkeypatch.setattr(loop, "generate_research_shortlist", generate)

    result = loop.run_daily_research_loop(
        loop.DailyResearchLoopInput(outcome_run_limit=12, use_llm=False),
        session=session,
        task_run_id=task_run_id,
        now=FIXED_NOW,
    )

    assert result["status"] == "completed"
    assert result["publication"]["status"] == "created"
    assert result["publication"]["decision_date"] == "2026-07-13"
    assert result["publication"]["item_count"] == 1
    evaluation = captured["evaluation"]
    assert evaluation["verified_completed_through"] == date(2026, 7, 13)
    assert evaluation["evaluation_task_run_id"] == task_run_id
    assert evaluation["run_limit"] == 12
    generation = captured["generation"]
    assert generation.verified_decision_date == date(2026, 7, 13)
    assert generation.generation_task_run_id == task_run_id
    assert generation.use_llm is False


def test_daily_research_loop_keeps_matured_outcomes_when_publication_is_not_ready(
    monkeypatch,
) -> None:
    session = MagicMock()
    session.in_transaction.return_value = True
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: _ready_watermark(),
    )
    monkeypatch.setattr(
        loop,
        "evaluate_due_research_shortlist_outcomes",
        lambda **_kwargs: _outcomes(),
    )

    def not_ready(*_args, **_kwargs):
        raise ResearchShortlistReadinessError(
            "EVIDENCE_COVERAGE_NOT_READY",
            "not ready",
            details={"thresholds": {"daily_bars": 0.95}},
        )

    monkeypatch.setattr(loop, "generate_research_shortlist", not_ready)

    result = loop.run_daily_research_loop(
        loop.DailyResearchLoopInput(),
        session=session,
        task_run_id=uuid4(),
        now=FIXED_NOW,
    )

    assert result["status"] == "completed_with_deferred_generation"
    assert result["outcomes"]["processed_run_count"] == 3
    assert result["publication"]["status"] == "deferred"
    assert result["publication"]["code"] == "EVIDENCE_COVERAGE_NOT_READY"
    session.rollback.assert_called_once()


def test_daily_research_loop_reports_partial_failure_after_attempting_publication(
    monkeypatch,
) -> None:
    task_run_id = uuid4()
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: _ready_watermark(),
    )
    monkeypatch.setattr(
        loop,
        "evaluate_due_research_shortlist_outcomes",
        lambda **_kwargs: _outcomes(failed=1),
    )
    generate = MagicMock(
        return_value={
            "status": "ok",
            "run": {
                "id": str(uuid4()),
                "generation_task_run_id": str(task_run_id),
                "decision_date": "2026-07-13",
                "diagnostics": [],
            },
            "items": [],
        }
    )
    monkeypatch.setattr(loop, "generate_research_shortlist", generate)

    result = loop.run_daily_research_loop(
        loop.DailyResearchLoopInput(),
        session=MagicMock(),
        task_run_id=task_run_id,
        now=FIXED_NOW,
    )

    assert result["status"] == "partial_failure"
    assert result["outcomes"]["failed_run_count"] == 1
    assert result["publication"]["status"] == "created"
    generate.assert_called_once()


def test_daily_research_loop_rejects_publication_outside_verified_date(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: _ready_watermark(),
    )
    monkeypatch.setattr(
        loop,
        "evaluate_due_research_shortlist_outcomes",
        lambda **_kwargs: _outcomes(),
    )
    monkeypatch.setattr(
        loop,
        "generate_research_shortlist",
        lambda *_args, **_kwargs: {
            "status": "ok",
            "run": {"id": str(uuid4()), "decision_date": "2026-07-14"},
            "items": [],
        },
    )

    with pytest.raises(loop.DailyResearchLoopExecutionError) as exc_info:
        loop.run_daily_research_loop(
            loop.DailyResearchLoopInput(),
            session=MagicMock(),
            task_run_id=uuid4(),
            now=FIXED_NOW,
        )

    assert exc_info.value.phase == "publication"
    assert exc_info.value.error_type == "RuntimeError"
    partial = exc_info.value.partial_result
    assert partial["status"] == "failed"
    assert partial["outcomes"]["processed_run_count"] == 3
    assert partial["publication"] == {
        "status": "failed",
        "code": "SHORTLIST_PUBLICATION_FAILED",
        "error_type": "RuntimeError",
    }


def test_daily_research_loop_bounds_publication_readiness_details(monkeypatch) -> None:
    session = MagicMock()
    session.in_transaction.return_value = True
    monkeypatch.setattr(
        loop,
        "resolve_completed_daily_bar_watermark",
        lambda **_kwargs: _ready_watermark(),
    )
    monkeypatch.setattr(
        loop,
        "evaluate_due_research_shortlist_outcomes",
        lambda **_kwargs: _outcomes(),
    )

    def not_aligned(*_args, **_kwargs):
        raise ResearchShortlistReadinessError(
            "NO_DECISION_DATE_ALIGNED_CANDIDATES",
            "not aligned",
            details={
                "decision_date": "2026-07-13",
                "stale_symbols": [f"{index:06d}" for index in range(100)],
                "diagnostics": [
                    {"code": "STALE_ENTRY_BAR", "message": "x" * 500}
                    for _ in range(40)
                ],
            },
        )

    monkeypatch.setattr(loop, "generate_research_shortlist", not_aligned)

    result = loop.run_daily_research_loop(
        loop.DailyResearchLoopInput(),
        session=session,
        task_run_id=uuid4(),
        now=FIXED_NOW,
    )

    details = result["publication"]["details"]
    assert details["stale_symbols"]["count"] == 100
    assert len(details["stale_symbols"]["sample"]) == loop.MAX_DETAIL_ITEMS
    assert details["diagnostics"]["count"] == 40
    assert len(details["diagnostics"]["sample"]) == loop.MAX_DETAIL_ITEMS
    assert len(details["diagnostics"]["sample"][0]["message"]) == 256


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (loop.DailyResearchLoopInput(market="US"), "market"),
        (loop.DailyResearchLoopInput(asset_type="index"), "asset type"),
        (loop.DailyResearchLoopInput(shortlist_limit=0), "shortlist_limit"),
        (loop.DailyResearchLoopInput(outcome_run_limit=101), "outcome_run_limit"),
    ],
)
def test_daily_research_loop_validates_fixed_product_boundary(payload, message) -> None:
    with pytest.raises(ValueError, match=message):
        loop.run_daily_research_loop(
            payload,
            session=MagicMock(),
            task_run_id=uuid4(),
        )
