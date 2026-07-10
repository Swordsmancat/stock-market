from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    FundamentalSnapshot,
    Instrument,
    Market,
    TechnicalIndicator,
)
from packages.services import stock_discovery as discovery_service
from packages.services.stock_discovery import discover_local_stocks
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_candidate(session, symbol: str) -> None:
    market = session.query(Market).filter(Market.code == "CN").one_or_none()
    if market is None:
        market = Market(code="CN", name="China", timezone="Asia/Shanghai", currency="CNY")
        session.add(market)
        session.flush()
    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        asset_type="stock",
        currency="CNY",
    )
    session.add(instrument)
    session.flush()
    session.add(
        DailyBar(
            instrument_id=instrument.id,
            trade_date=date(2026, 1, 20),
            open=Decimal("100"),
            high=Decimal("112"),
            low=Decimal("99"),
            close=Decimal("110"),
            volume=Decimal("1000000"),
            amount=Decimal("110000000"),
        )
    )
    as_of = datetime(2026, 1, 20, tzinfo=timezone.utc)
    session.add_all(
        [
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=as_of,
                indicator_code="ma",
                params={"window": 20},
                value_json={"value": 100.0},
            ),
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=as_of,
                indicator_code="rsi",
                params={"window": 14},
                value_json={"value": 55.0},
            ),
        ]
    )
    session.add(
        FundamentalSnapshot(
            symbol=symbol,
            as_of=date(2026, 1, 19),
            currency="CNY",
            pe_ratio=Decimal("25"),
            revenue_growth=Decimal("0.12"),
            net_margin=Decimal("0.20"),
            debt_to_assets=Decimal("0.30"),
            source="fixture",
        )
    )
    session.commit()


def _configured_llm_settings() -> dict[str, str]:
    return {"llm_provider": "openai", "llm_api_key": "configured"}


def test_stock_discovery_uses_deterministic_shortlist_and_fallback():
    session = make_session()
    seed_candidate(session, "600519")
    seed_candidate(session, "000001")

    payload = discover_local_stocks(session=session, locale="en", use_llm=False)

    assert payload["status"] == "degraded"
    assert [item["symbol"] for item in payload["shortlist"]] == ["600519", "000001"]
    assert payload["coverage"]["candidate_count"] == 2
    assert payload["model"]["used_llm"] is False
    assert "cannot trigger automated trades" in payload["explanation_markdown"]
    assert payload["safety"]["ai_cannot_change_membership_or_ranking"] is True


def test_stock_discovery_accepts_valid_llm_explanation(monkeypatch):
    session = make_session()
    seed_candidate(session, "600519")

    class FakeLLM:
        def generate(self, prompt: str) -> str:
            assert "candidate membership and ranking are final" in prompt
            return "`600519` matched the profile. [bars_1d:600519:2026-01-20]"

    monkeypatch.setattr(discovery_service, "get_platform_settings", _configured_llm_settings)
    monkeypatch.setattr(discovery_service, "get_llm_provider", FakeLLM)

    payload = discover_local_stocks(session=session, locale="en")

    assert payload["status"] == "ok"
    assert payload["model"]["used_llm"] is True
    assert payload["explanation_markdown"].startswith("`600519`")
    assert [item["symbol"] for item in payload["shortlist"]] == ["600519"]


def test_stock_discovery_falls_back_on_llm_provider_failure(monkeypatch):
    session = make_session()
    seed_candidate(session, "600519")

    class FailingLLM:
        def generate(self, _prompt: str) -> str:
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(discovery_service, "get_platform_settings", _configured_llm_settings)
    monkeypatch.setattr(discovery_service, "get_llm_provider", FailingLLM)

    payload = discover_local_stocks(session=session, locale="en")

    assert payload["status"] == "degraded"
    assert payload["model"]["fallback_reason"] == "LLM generation failed: RuntimeError."
    assert any(item.get("code") == "FALLBACK_USED" for item in payload["diagnostics"])


def test_stock_discovery_returns_explicit_empty_shortlist_without_llm():
    session = make_session()
    seed_candidate(session, "600519")

    payload = discover_local_stocks(
        session=session,
        overrides={"max_pe_ratio": 1.0},
        locale="en",
    )

    assert payload["status"] == "no_matches"
    assert payload["shortlist"] == []
    assert payload["model"]["used_llm"] is False
    assert "No locally evidenced candidate matched" in payload["explanation_markdown"]


def test_stock_discovery_rejects_unknown_llm_citation(monkeypatch):
    session = make_session()
    seed_candidate(session, "600519")

    class HallucinatingLLM:
        def generate(self, _prompt: str) -> str:
            return "`600519` is listed. [bars_1d:FAKE:2099-01-01]"

    monkeypatch.setattr(discovery_service, "get_platform_settings", _configured_llm_settings)
    monkeypatch.setattr(discovery_service, "get_llm_provider", HallucinatingLLM)

    payload = discover_local_stocks(session=session, locale="en")

    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == (
        "LLM citation validation failed: unknown citation id."
    )
    diagnostic = next(item for item in payload["diagnostics"] if item.get("code") == "CITATION_UNKNOWN_ID")
    assert diagnostic["details"]["unknown_ids"] == ["bars_1d:FAKE:2099-01-01"]


def test_stock_discovery_rejects_unknown_llm_symbol(monkeypatch):
    session = make_session()
    seed_candidate(session, "600519")

    class HallucinatingLLM:
        def generate(self, _prompt: str) -> str:
            return "Compare `600519` with `000001`. [bars_1d:600519:2026-01-20]"

    monkeypatch.setattr(discovery_service, "get_platform_settings", _configured_llm_settings)
    monkeypatch.setattr(discovery_service, "get_llm_provider", HallucinatingLLM)

    payload = discover_local_stocks(session=session, locale="en")

    assert payload["model"]["used_llm"] is False
    assert payload["model"]["fallback_reason"] == (
        "LLM shortlist validation failed: unknown candidate symbol."
    )
    diagnostic = next(
        item for item in payload["diagnostics"] if item.get("code") == "SHORTLIST_UNKNOWN_SYMBOL"
    )
    assert diagnostic["details"]["unknown_symbols"] == ["000001"]
