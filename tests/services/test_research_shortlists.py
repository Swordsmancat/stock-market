from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
import threading
import time

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    FundamentalSnapshot,
    Instrument,
    Market,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    TaskRun,
)
from packages.services import research_shortlists
from packages.services.research_shortlists import (
    ResearchShortlistGenerateInput,
    ResearchShortlistReadinessError,
    build_research_shortlist_generation_key,
    generate_research_shortlist,
    get_latest_research_shortlist,
    get_research_shortlist,
    score_research_shortlist_candidate,
)
from packages.shared.database import Base


DECISION_DATE = date(2026, 7, 10)


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def score_one(code: str, actual: object, threshold: object) -> dict[str, object]:
    return score_research_shortlist_candidate(
        {
            "matched_rules": [
                {
                    "code": code,
                    "field": code,
                    "status": "matched",
                    "actual": actual,
                    "threshold": threshold,
                }
            ]
        },
        effective_criteria={code: threshold if code != "require_price_above_ma" else True},
    )


@pytest.mark.parametrize(
    ("code", "actual", "threshold", "expected"),
    [
        ("max_pe_ratio", 10.0, 20.0, 0.75),
        ("min_revenue_growth", 0.15, 0.05, 0.75),
        ("min_rsi", 60.0, 50.0, 0.60),
        ("max_rsi", 30.0, 60.0, 0.75),
        ("min_william_r", -25.0, -50.0, 0.75),
        ("max_william_r", -75.0, -50.0, 0.75),
        ("min_chip_benefit_ratio", 0.75, 0.5, 0.75),
        ("max_chip_benefit_ratio", 0.25, 0.5, 0.75),
        ("min_latest_volume", 10_000.0, 1_000.0, 1.0),
        ("require_price_above_ma", 110.0, 100.0, 1.0),
        ("required_news_sentiment", "positive", "positive", 0.75),
    ],
)
def test_score_normalization_families(code, actual, threshold, expected):
    result = score_one(code, actual, threshold)

    assert result["total_score"] == pytest.approx(expected)
    assert result["factor_scores"][0]["buffer"] == pytest.approx(expected)


@pytest.mark.parametrize(
    ("code", "actual", "threshold"),
    [
        ("min_rsi", 100.0, 100.0),
        ("max_rsi", 0.0, 0.0),
        ("min_mfi", 100.0, 100.0),
        ("max_mfi", 0.0, 0.0),
        ("min_william_r", 0.0, 0.0),
        ("max_william_r", -100.0, -100.0),
        ("min_chip_benefit_ratio", 1.0, 1.0),
        ("max_chip_benefit_ratio", 0.0, 0.0),
        ("min_news_sentiment_confidence", 1.0, 1.0),
        ("min_latest_volume", 0.0, 0.0),
        ("min_traded_amount", 0.0, 0.0),
        ("min_news_article_count", 0.0, 0.0),
    ],
)
def test_score_degenerate_thresholds_are_safe_boundaries(code, actual, threshold):
    result = score_one(code, actual, threshold)

    assert result["total_score"] == 0.5


def test_score_renormalizes_active_dimensions_and_fails_unknown_rules():
    result = score_research_shortlist_candidate(
        {
            "matched_rules": [
                {
                    "code": "max_pe_ratio",
                    "field": "pe_ratio",
                    "status": "matched",
                    "actual": 10.0,
                    "threshold": 20.0,
                },
                {
                    "code": "min_latest_volume",
                    "field": "latest_bar.volume",
                    "status": "matched",
                    "actual": 10_000.0,
                    "threshold": 1_000.0,
                },
            ]
        },
        effective_criteria={"max_pe_ratio": 20.0, "min_latest_volume": 1_000.0},
    )

    assert result["dimension_weights"] == {
        "fundamental": pytest.approx(2 / 3, abs=1e-6),
        "liquidity": pytest.approx(1 / 3, abs=1e-6),
    }
    assert result["total_score"] == pytest.approx(0.8333)
    assert len(result["invalidation_conditions"]) == 2

    with pytest.raises(ValueError, match="Unknown daily research score rule"):
        score_research_shortlist_candidate(
            {
                "matched_rules": [
                    {
                        "code": "invented_rule",
                        "status": "matched",
                        "actual": 1,
                        "threshold": 1,
                    }
                ]
            },
            effective_criteria={"invented_rule": 1},
        )


def test_generation_key_is_canonical_for_criteria_order():
    first = build_research_shortlist_generation_key(
        market="CN",
        asset_type="stock",
        profile_id="quality_value",
        effective_criteria={"max_pe_ratio": 20.0, "min_net_margin": 0.1},
        decision_date=DECISION_DATE,
        shortlist_limit=10,
    )
    second = build_research_shortlist_generation_key(
        market="cn",
        asset_type="STOCK",
        profile_id="QUALITY_VALUE",
        effective_criteria={"min_net_margin": 0.1, "max_pe_ratio": 20.0},
        decision_date=DECISION_DATE,
        shortlist_limit=10,
    )

    assert first == second
    assert len(first) == 64


def test_generate_persists_ranked_snapshot_and_reuses_idempotent_run(monkeypatch):
    session = make_session()
    instruments = seed_instruments_with_entry_bars(session)
    calls = {"coverage": 0, "selection": 0, "explanation": 0}

    def coverage(**_):
        calls["coverage"] += 1
        return ready_coverage()

    def selection(**_):
        calls["selection"] += 1
        return selection_payload()

    def explanation(**_):
        calls["explanation"] += 1
        return "### Research shortlist\nDeterministic evidence comparison.", {
            "provider": "deterministic",
            "name": "test",
            "used_llm": False,
            "fallback_reason": "test",
        }

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", coverage)
    monkeypatch.setattr(research_shortlists, "screen_local_stock_selection", selection)
    monkeypatch.setattr(
        research_shortlists,
        "generate_stock_discovery_explanation",
        explanation,
    )

    request = ResearchShortlistGenerateInput(
        profile_id="quality_value",
        shortlist_limit=2,
        use_llm=True,
    )
    first = generate_research_shortlist(request, session=session)
    second = generate_research_shortlist(request, session=session)

    assert first["run"]["id"] == second["run"]["id"]
    assert session.in_transaction() is False
    assert calls == {"coverage": 1, "selection": 1, "explanation": 1}
    assert [item["symbol"] for item in first["items"]] == ["000001", "000002"]
    assert first["items"][0]["total_score"] > first["items"][1]["total_score"]
    assert [item["rank"] for item in first["items"]] == [1, 2]
    assert first["items"][0]["entry_observation"]["trade_date"] == DECISION_DATE.isoformat()
    assert first["items"][0]["entry_observation"]["source"] == "akshare.stock_zh_a_hist"
    assert first["items"][0]["invalidation_conditions"]
    assert first["items"][0]["allowed_citation_ids"]
    assert first["run"]["counts"] == {
        "candidate_count": 2,
        "evaluated_count": 2,
        "matched_count": 2,
        "eligible_count": 2,
        "decision_date_aligned_count": 2,
        "returned_count": 2,
    }
    assert session.query(ResearchShortlistRun).count() == 1
    assert session.query(ResearchShortlistCandidate).count() == 2
    assert {candidate.instrument_id for candidate in session.query(ResearchShortlistCandidate)} == {
        instrument.id for instrument in instruments
    }

    latest = get_latest_research_shortlist(
        session=session,
        market="CN",
        profile_id="quality_value",
    )
    detail = get_research_shortlist(first["run"]["id"], session=session)
    assert latest["run"]["id"] == first["run"]["id"]
    assert detail == first


def test_verified_date_and_original_task_run_lineage_survive_reuse(monkeypatch):
    session = make_session()
    instruments = seed_instruments_with_entry_bars(session)
    newer_partial_date = date(2026, 7, 11)
    session.add(
        DailyBar(
            instrument_id=instruments[0].id,
            trade_date=newer_partial_date,
            open=Decimal("11"),
            high=Decimal("13"),
            low=Decimal("10"),
            close=Decimal("12"),
            volume=Decimal("10000000"),
            amount=Decimal("120000000"),
            provider="akshare",
            source="akshare.stock_zh_a_hist",
            adjustment="qfq",
            source_priority=0,
            ingested_at=datetime(2026, 7, 11, 10, tzinfo=timezone.utc),
        )
    )
    first_task_run = TaskRun(
        task_name="research.run_daily_research_loop",
        status="running",
        started_at=datetime(2026, 7, 13, 13, 30, tzinfo=timezone.utc),
    )
    retry_task_run = TaskRun(
        task_name="research.run_daily_research_loop",
        status="running",
        started_at=datetime(2026, 7, 13, 14, 30, tzinfo=timezone.utc),
    )
    session.add_all([first_task_run, retry_task_run])
    session.commit()

    captured: dict[str, list[date]] = {"coverage": [], "selection": []}

    def coverage(**kwargs):
        captured["coverage"].append(kwargs["as_of"])
        return ready_coverage()

    def selection(**kwargs):
        captured["selection"].append(kwargs["as_of"])
        return selection_payload()

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", coverage)
    monkeypatch.setattr(research_shortlists, "screen_local_stock_selection", selection)
    monkeypatch.setattr(
        research_shortlists,
        "generate_stock_discovery_explanation",
        lambda **_: (
            "### Verified research shortlist",
            {
                "provider": "deterministic",
                "name": "test",
                "used_llm": False,
                "fallback_reason": "test",
            },
        ),
    )

    first = generate_research_shortlist(
        ResearchShortlistGenerateInput(
            profile_id="quality_value",
            shortlist_limit=2,
            use_llm=False,
            verified_decision_date=DECISION_DATE,
            generation_task_run_id=str(first_task_run.id),
        ),
        session=session,
    )
    reused = generate_research_shortlist(
        ResearchShortlistGenerateInput(
            profile_id="quality_value",
            shortlist_limit=2,
            use_llm=False,
            verified_decision_date=DECISION_DATE,
            generation_task_run_id=retry_task_run.id,
        ),
        session=session,
    )

    assert first["run"]["decision_date"] == DECISION_DATE.isoformat()
    assert first["run"]["generation_task_run_id"] == str(first_task_run.id)
    assert reused["run"]["id"] == first["run"]["id"]
    assert reused["run"]["generation_task_run_id"] == str(first_task_run.id)
    assert captured == {
        "coverage": [DECISION_DATE],
        "selection": [DECISION_DATE],
    }
    persisted = (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.generation_key == first["run"]["generation_key"])
        .one()
    )
    assert persisted.generation_task_run_id == first_task_run.id

    latest = get_latest_research_shortlist(
        session=session,
        market="CN",
        profile_id="quality_value",
    )
    detail = get_research_shortlist(first["run"]["id"], session=session)
    assert latest["run"]["generation_task_run_id"] == str(first_task_run.id)
    assert detail["run"]["generation_task_run_id"] == str(first_task_run.id)


def test_generate_rejects_invalid_task_run_lineage():
    session = make_session()

    with pytest.raises(ValueError, match="Invalid generation_task_run_id"):
        generate_research_shortlist(
            ResearchShortlistGenerateInput(
                generation_task_run_id="not-a-uuid",
            ),
            session=session,
        )

    assert session.query(ResearchShortlistRun).count() == 0


def test_semantically_equivalent_set_like_criteria_share_generation_key(monkeypatch):
    session = make_session()
    seed_instruments_with_entry_bars(session)
    calls = {"selection": 0, "explanation": 0}

    def selection(**_):
        calls["selection"] += 1
        payload = deepcopy(selection_payload())
        for item in payload["items"]:
            item["matched_rules"].extend(
                [
                    {
                        "code": "required_pattern_codes",
                        "field": "candlestick_patterns.patterns",
                        "status": "matched",
                        "actual": ["doji", "hammer"],
                        "threshold": ["doji", "hammer"],
                    },
                    {
                        "code": "required_news_sentiment",
                        "field": "news.latest_sentiment",
                        "status": "matched",
                        "actual": "positive",
                        "threshold": "positive",
                    },
                ]
            )
            item["news_sentiment"] = {
                "article_count": 1,
                "latest_sentiment": "positive",
                "latest_confidence": 0.9,
                "latest_published_at": "2026-07-10T08:00:00+00:00",
                "latest_sentiment_created_at": "2026-07-10T09:00:00+00:00",
            }
        return payload

    def explanation(**_):
        calls["explanation"] += 1
        return "### Canonical research shortlist", {
            "provider": "deterministic",
            "name": "test",
            "used_llm": False,
            "fallback_reason": "test",
        }

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())
    monkeypatch.setattr(research_shortlists, "screen_local_stock_selection", selection)
    monkeypatch.setattr(
        research_shortlists,
        "generate_stock_discovery_explanation",
        explanation,
    )

    first = generate_research_shortlist(
        ResearchShortlistGenerateInput(
            profile_id="quality_value",
            overrides={
                "required_pattern_codes": [" Hammer ", "DOJI", "hammer"],
                "required_news_sentiment": " Positive ",
            },
            use_llm=True,
        ),
        session=session,
    )
    second = generate_research_shortlist(
        ResearchShortlistGenerateInput(
            profile_id="quality_value",
            overrides={
                "required_pattern_codes": ["doji", " HAMMER "],
                "required_news_sentiment": "positive",
            },
            use_llm=True,
        ),
        session=session,
    )

    assert first["run"]["id"] == second["run"]["id"]
    assert first["run"]["generation_key"] == second["run"]["generation_key"]
    assert first["run"]["overrides"] == {
        "required_pattern_codes": ["doji", "hammer"],
        "required_news_sentiment": "positive",
    }
    assert first["run"]["effective_criteria"]["required_pattern_codes"] == [
        "doji",
        "hammer",
    ]
    assert calls == {"selection": 1, "explanation": 1}
    assert session.query(ResearchShortlistRun).count() == 1


def test_generate_uses_real_local_eligibility_without_provider_calls(monkeypatch):
    session = make_session()
    seed_instruments_with_entry_bars(session)
    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())

    payload = generate_research_shortlist(
        ResearchShortlistGenerateInput(
            profile_id="quality_value",
            shortlist_limit=2,
            use_llm=False,
        ),
        session=session,
    )

    assert payload["status"] == "ok"
    assert [item["symbol"] for item in payload["items"]] == ["000001", "000002"]
    assert payload["run"]["coverage"]["status"] == "ok"
    assert payload["run"]["model"]["used_llm"] is False
    assert payload["items"][0]["total_score"] > payload["items"][1]["total_score"]


def test_not_ready_and_stale_only_generation_leave_no_rows(monkeypatch):
    session = make_session()
    seed_instruments_with_entry_bars(session)
    monkeypatch.setattr(
        research_shortlists,
        "get_evidence_coverage",
        lambda **_: {"status": "needs_attention", "evidence": {}},
    )

    with pytest.raises(ResearchShortlistReadinessError) as not_ready:
        generate_research_shortlist(
            ResearchShortlistGenerateInput(profile_id="quality_value"),
            session=session,
        )
    assert not_ready.value.code == "EVIDENCE_COVERAGE_NOT_READY"
    assert session.in_transaction() is False
    assert session.query(ResearchShortlistRun).count() == 0

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())
    stale = selection_payload()
    for item in stale["items"]:
        item["latest_bar"]["trade_date"] = "2026-07-09"
    monkeypatch.setattr(research_shortlists, "screen_local_stock_selection", lambda **_: stale)

    with pytest.raises(ResearchShortlistReadinessError) as stale_error:
        generate_research_shortlist(
            ResearchShortlistGenerateInput(profile_id="quality_value"),
            session=session,
        )
    assert stale_error.value.code == "NO_DECISION_DATE_ALIGNED_CANDIDATES"
    assert session.in_transaction() is False
    assert session.query(ResearchShortlistRun).count() == 0
    assert session.query(ResearchShortlistCandidate).count() == 0


def test_no_in_scope_bars_fails_before_coverage_or_persistence(monkeypatch):
    session = make_session()
    coverage_called = False

    def coverage(**_):
        nonlocal coverage_called
        coverage_called = True
        return ready_coverage()

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", coverage)

    with pytest.raises(ResearchShortlistReadinessError) as error:
        generate_research_shortlist(
            ResearchShortlistGenerateInput(profile_id="quality_value"),
            session=session,
        )

    assert error.value.code == "NO_IN_SCOPE_DAILY_BARS"
    assert coverage_called is False
    assert session.in_transaction() is False
    assert session.query(ResearchShortlistRun).count() == 0


def test_candidate_insert_failure_rolls_back_run_and_candidates(monkeypatch):
    session = make_session()
    seed_instruments_with_entry_bars(session)
    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())
    monkeypatch.setattr(
        research_shortlists,
        "generate_stock_discovery_explanation",
        lambda **_: (
            "### Research shortlist\nDeterministic evidence comparison.",
            {
                "provider": "deterministic",
                "name": "test",
                "used_llm": False,
                "fallback_reason": "test",
            },
        ),
    )

    def fail_candidate_insert(*_):
        raise RuntimeError("simulated candidate insert failure")

    event.listen(ResearchShortlistCandidate, "before_insert", fail_candidate_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated candidate insert failure"):
            generate_research_shortlist(
                ResearchShortlistGenerateInput(
                    profile_id="quality_value",
                    shortlist_limit=2,
                    use_llm=False,
                ),
                session=session,
            )
    finally:
        event.remove(ResearchShortlistCandidate, "before_insert", fail_candidate_insert)

    assert session.query(ResearchShortlistRun).count() == 0
    assert session.query(ResearchShortlistCandidate).count() == 0


def test_generation_defensively_rejects_post_decision_candidate_evidence(monkeypatch):
    session = make_session()
    seed_instruments_with_entry_bars(session)
    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())
    contaminated = selection_payload()
    for item in contaminated["items"]:
        item["technical_indicators_as_of"] = "2026-07-11T01:00:00+00:00"
    monkeypatch.setattr(
        research_shortlists,
        "screen_local_stock_selection",
        lambda **_: contaminated,
    )

    with pytest.raises(ResearchShortlistReadinessError) as error:
        generate_research_shortlist(
            ResearchShortlistGenerateInput(profile_id="quality_value"),
            session=session,
        )

    assert error.value.code == "NO_DECISION_DATE_ALIGNED_CANDIDATES"
    assert error.value.details["post_decision_symbols"] == ["000001", "000002"]
    assert error.value.details["diagnostics"][0]["code"] == "POST_DECISION_EVIDENCE"
    assert session.query(ResearchShortlistRun).count() == 0
    assert session.query(ResearchShortlistCandidate).count() == 0


def test_concurrent_sqlite_generation_serializes_before_explanation(monkeypatch, tmp_path):
    database_path = tmp_path / "research-shortlist-concurrency.sqlite"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    seed_session = session_factory()
    try:
        seed_instruments_with_entry_bars(seed_session)
    finally:
        seed_session.close()

    explanation_count = 0
    counter_lock = threading.Lock()
    start_barrier = threading.Barrier(2)

    def explanation(**_):
        nonlocal explanation_count
        with counter_lock:
            explanation_count += 1
        time.sleep(0.1)
        return "### Research shortlist\nConcurrent deterministic explanation.", {
            "provider": "deterministic",
            "name": "test",
            "used_llm": False,
            "fallback_reason": "test",
        }

    monkeypatch.setattr(research_shortlists, "get_evidence_coverage", lambda **_: ready_coverage())
    monkeypatch.setattr(
        research_shortlists,
        "generate_stock_discovery_explanation",
        explanation,
    )

    def generate_in_session():
        session = session_factory()
        try:
            start_barrier.wait(timeout=5)
            return generate_research_shortlist(
                ResearchShortlistGenerateInput(
                    profile_id="quality_value",
                    shortlist_limit=2,
                    use_llm=True,
                ),
                session=session,
            )
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: generate_in_session(), range(2)))

        verification_session = session_factory()
        try:
            assert responses[0]["run"]["id"] == responses[1]["run"]["id"]
            assert explanation_count == 1
            assert verification_session.query(ResearchShortlistRun).count() == 1
            assert verification_session.query(ResearchShortlistCandidate).count() == 2
        finally:
            verification_session.close()
    finally:
        engine.dispose()


def seed_instruments_with_entry_bars(session):
    market = Market(
        code="CN",
        name="China A-share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    instruments = [
        Instrument(
            symbol="000001",
            name="Alpha",
            market=market,
            asset_type="stock",
            currency="CNY",
            is_active=True,
        ),
        Instrument(
            symbol="000002",
            name="Beta",
            market=market,
            asset_type="stock",
            currency="CNY",
            is_active=True,
        ),
    ]
    session.add_all([market, *instruments])
    session.flush()
    for index, instrument in enumerate(instruments):
        session.add(
            DailyBar(
                instrument_id=instrument.id,
                trade_date=DECISION_DATE,
                open=Decimal("10"),
                high=Decimal("12"),
                low=Decimal("9"),
                close=Decimal(str(11 + index)),
                volume=Decimal("10000000"),
                amount=Decimal("110000000"),
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
                source_priority=0,
                ingested_at=datetime(2026, 7, 10, 10, tzinfo=timezone.utc),
            )
        )
    session.add_all(
        [
            FundamentalSnapshot(
                symbol="000001",
                as_of=date(2026, 6, 30),
                currency="CNY",
                pe_ratio=Decimal("10"),
                revenue_growth=Decimal("0.20"),
                net_margin=Decimal("0.20"),
                debt_to_assets=Decimal("0.30"),
                source="akshare",
            ),
            FundamentalSnapshot(
                symbol="000002",
                as_of=date(2026, 6, 30),
                currency="CNY",
                pe_ratio=Decimal("24"),
                revenue_growth=Decimal("0.09"),
                net_margin=Decimal("0.11"),
                debt_to_assets=Decimal("0.40"),
                source="akshare",
            ),
        ]
    )
    session.commit()
    return instruments


def ready_coverage():
    return {
        "status": "ok",
        "market": "CN",
        "as_of": DECISION_DATE.isoformat(),
        "thresholds": {
            "daily_bars": 0.95,
            "technical_indicators": 0.90,
            "fundamentals": 0.80,
        },
        "evidence": {},
    }


def selection_payload():
    return {
        "status": "ok",
        "candidate_scope": {
            "symbols": [],
            "market": "CN",
            "asset_type": "stock",
            "watchlist_only": False,
        },
        "coverage": {
            "candidate_count": 2,
            "evaluated_count": 2,
            "matched_count": 2,
            "returned_count": 2,
        },
        "diagnostics": [],
        "items": [
            selection_item("000001", "Alpha", pe=10.0, growth=0.20, margin=0.20),
            selection_item("000002", "Beta", pe=24.0, growth=0.09, margin=0.11),
        ],
    }


def selection_item(symbol: str, name: str, *, pe: float, growth: float, margin: float):
    return {
        "symbol": symbol,
        "name": name,
        "market": "CN",
        "asset_type": "stock",
        "latest_bar": {
            "trade_date": DECISION_DATE.isoformat(),
            "close": 11.0,
            "provider": "akshare",
            "source": "akshare.stock_zh_a_hist",
            "adjustment": "qfq",
            "source_priority": 0,
            "ingested_at": "2026-07-10T10:00:00+00:00",
        },
        "fundamentals": {
            "as_of": "2026-06-30",
            "pe_ratio": pe,
            "revenue_growth": growth,
            "net_margin": margin,
            "source": "akshare",
        },
        "technical_indicators_as_of": "2026-07-10T08:00:00+00:00",
        "technical_indicators": {},
        "matched_rules": [
            {
                "code": "max_pe_ratio",
                "field": "pe_ratio",
                "status": "matched",
                "actual": pe,
                "threshold": 25.0,
            },
            {
                "code": "min_revenue_growth",
                "field": "revenue_growth",
                "status": "matched",
                "actual": growth,
                "threshold": 0.08,
            },
            {
                "code": "min_net_margin",
                "field": "net_margin",
                "status": "matched",
                "actual": margin,
                "threshold": 0.10,
            },
        ],
        "evidence_citations": [
            f"bars_1d:{symbol}:{DECISION_DATE.isoformat()}",
            f"fundamental_metrics:{symbol}:2026-06-30",
        ],
        "research_signal_only": True,
    }
