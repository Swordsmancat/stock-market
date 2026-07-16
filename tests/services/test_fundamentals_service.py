from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.analytics.fundamentals import FundamentalSnapshot
from packages.domain.models import FundamentalSnapshot as FundamentalSnapshotModel
from packages.providers.eastmoney_public_fundamentals import (
    EastmoneyPublicCompany,
    EastmoneyPublicFundamentalsSnapshot,
    EastmoneyPublicFundamentalsProviderError,
)
from packages.services.fundamentals import get_fundamental_payload, upsert_fundamental_snapshot
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_eastmoney_snapshot():
    return EastmoneyPublicFundamentalsSnapshot(
        symbol="600519",
        as_of=date(2026, 6, 30),
        currency="CNY",
        pe_ratio=None,
        revenue_growth=0.125,
        net_margin=0.5125,
        debt_to_assets=0.1875,
        company=EastmoneyPublicCompany(
            name="Kweichow Moutai",
            industry="Beverage manufacturing",
            business_scope="Production and sale of spirits.",
            profile="Premium spirits producer.",
        ),
        status="ok",
        provider="eastmoney_public",
        upstream_sources=(
            "eastmoney.RPT_F10_FINANCE_MAINFINADATA",
            "eastmoney.PC_HSF10.CompanySurvey.PageAjax",
        ),
        retrieved_at=datetime(2026, 7, 16, tzinfo=timezone.utc),
        diagnostics=(),
    )


def test_get_fundamental_payload_returns_mock_metrics_with_citation():
    payload = get_fundamental_payload("AAPL", as_of=date(2026, 1, 20))

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "mock_fundamentals"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-20"
    assert payload["item"]["pe_ratio"] == 28.4
    assert "PE 28.40" in payload["item"]["summary"]


def test_get_fundamental_payload_prefers_database_snapshot():
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="AAPL",
            as_of=date(2026, 1, 19),
            currency="USD",
            pe_ratio=30.5,
            revenue_growth=0.12,
            net_margin=0.25,
            debt_to_assets=0.29,
        ),
        session=session,
        source="test_fixture",
    )

    payload = get_fundamental_payload("AAPL", as_of=date(2026, 1, 20), session=session)

    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "database"
    assert payload["as_of"] == "2026-01-19"
    assert payload["citation"] == "fundamental_metrics:AAPL:2026-01-19"
    assert payload["item"]["pe_ratio"] == 30.5
    assert "PE 30.50" in payload["item"]["summary"]


def test_stored_a_share_projects_missing_pe_and_enriches_company_without_writes(
    monkeypatch,
):
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 7, 13),
            currency="CNY",
            pe_ratio=0.0,
            revenue_growth=0.0654,
            net_margin=0.5222,
            debt_to_assets=0.1212,
        ),
        session=session,
        source="akshare",
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: None,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.set",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_company",
        lambda _symbol: EastmoneyPublicCompany(
            name="贵州茅台酒股份有限公司",
            industry="酒、饮料和精制茶制造业",
            business_scope="茅台酒系列产品的生产与销售。",
            profile="主要从事贵州茅台酒及系列酒的生产和销售。",
        ),
    )

    payload = get_fundamental_payload(
        "600519",
        as_of=date(2026, 7, 16),
        session=session,
    )

    assert payload["source"] == "database"
    assert payload["as_of"] == "2026-07-13"
    assert payload["item"]["pe_ratio"] is None
    assert payload["item"]["revenue_growth"] == 0.0654
    assert payload["item"]["net_margin"] == 0.5222
    assert payload["item"]["debt_to_assets"] == 0.1212
    assert payload["item"]["summary"] is None
    assert payload["item"]["company"]["name"] == "贵州茅台酒股份有限公司"
    assert payload["citation"] == "fundamental_metrics:600519:2026-07-13"
    assert session.query(FundamentalSnapshotModel).count() == 1


def test_get_fundamental_payload_uses_read_only_eastmoney_for_a_share_gap(
    monkeypatch,
):
    session = make_session()
    snapshot = make_eastmoney_snapshot()
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        lambda symbol, *, as_of: snapshot,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: None,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.set",
        lambda *_args, **_kwargs: True,
    )

    payload = get_fundamental_payload(
        "600519",
        as_of=date(2026, 7, 16),
        session=session,
    )

    assert payload["source"] == "eastmoney_public"
    assert payload["status"] == "ok"
    assert payload["as_of"] == "2026-06-30"
    assert payload["item"]["pe_ratio"] is None
    assert payload["item"]["revenue_growth"] == 0.125
    assert payload["item"]["company"]["industry"] == "Beverage manufacturing"
    assert payload["citation"] == "fundamental_metrics:600519:2026-06-30"
    assert session.query(FundamentalSnapshotModel).count() == 0


def test_stored_a_share_skips_company_enrichment_when_gate_is_disabled(monkeypatch):
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=25.0,
            revenue_growth=0.1,
            net_margin=0.5,
            debt_to_assets=0.18,
        ),
        session=session,
        source="stored",
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": False},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: (_ for _ in ()).throw(AssertionError("cache must not run")),
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_company",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("provider must not run")
        ),
    )

    payload = get_fundamental_payload(
        "600519",
        as_of=date(2026, 7, 16),
        session=session,
    )

    assert payload["source"] == "database"
    assert payload["as_of"] == "2026-06-30"
    assert payload["item"]["pe_ratio"] == 25.0


def test_stored_a_share_company_enrichment_uses_normalized_cache(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.value = None

        def get(self, _key):
            return self.value

        def set(self, _key, value, **_kwargs):
            self.value = value
            return True

    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=25.0,
            revenue_growth=0.1,
            net_margin=0.5,
            debt_to_assets=0.18,
        ),
        session=session,
        source="stored",
    )
    calls = 0

    def fetch(_symbol):
        nonlocal calls
        calls += 1
        return make_eastmoney_snapshot().company

    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr("packages.services.fundamentals.redis_client", FakeRedis())
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_company",
        fetch,
    )

    first = get_fundamental_payload("600519", session=session)
    second = get_fundamental_payload("600519", session=session)

    assert calls == 1
    assert first["item"]["pe_ratio"] == 25.0
    assert first["item"]["company"]["industry"] == "Beverage manufacturing"
    assert second == first


def test_stored_a_share_company_no_data_is_cached(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.value = None

        def get(self, _key):
            return self.value

        def set(self, _key, value, **_kwargs):
            self.value = value
            return True

    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=25.0,
            revenue_growth=0.1,
            net_margin=0.5,
            debt_to_assets=0.18,
        ),
        session=session,
        source="stored",
    )
    calls = 0

    def fetch(_symbol):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr("packages.services.fundamentals.redis_client", FakeRedis())
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_company",
        fetch,
    )

    first = get_fundamental_payload("600519", session=session)
    second = get_fundamental_payload("600519", session=session)

    assert calls == 1
    assert first["status"] == "degraded"
    assert first["item"]["company"] is None
    assert first["diagnostics"] == ["EASTMONEY_COMPANY_NO_DATA"]
    assert second == first


def test_stored_company_failure_keeps_database_metrics(monkeypatch):
    session = make_session()
    upsert_fundamental_snapshot(
        FundamentalSnapshot(
            symbol="600519",
            as_of=date(2026, 6, 30),
            currency="CNY",
            pe_ratio=25.0,
            revenue_growth=0.1,
            net_margin=0.5,
            debt_to_assets=0.18,
        ),
        session=session,
        source="stored",
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: None,
    )

    def fail(_symbol):
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_TIMEOUT",
            "sanitized",
        )

    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_company",
        fail,
    )

    payload = get_fundamental_payload("600519", session=session)

    assert payload["source"] == "database"
    assert payload["status"] == "degraded"
    assert payload["item"]["pe_ratio"] == 25.0
    assert payload["item"]["company"] is None
    assert payload["diagnostics"] == ["EASTMONEY_FUNDAMENTALS_TIMEOUT"]


def test_eastmoney_normalized_cache_prevents_second_provider_call(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.value = None

        def get(self, _key):
            return self.value

        def set(self, _key, value, **_kwargs):
            self.value = value
            return True

    calls = 0

    def fetch(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return make_eastmoney_snapshot()

    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr("packages.services.fundamentals.redis_client", FakeRedis())
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        fetch,
    )

    first = get_fundamental_payload("600519", as_of=date(2026, 7, 16))
    second = get_fundamental_payload("600519", as_of=date(2026, 7, 16))

    assert calls == 1
    assert second == first


def test_eastmoney_explicit_no_data_is_cached(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.value = None

        def get(self, _key):
            return self.value

        def set(self, _key, value, **_kwargs):
            self.value = value
            return True

    calls = 0

    def fetch(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr("packages.services.fundamentals.redis_client", FakeRedis())
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        fetch,
    )

    first = get_fundamental_payload("600519", as_of=date(2026, 7, 16))
    second = get_fundamental_payload("600519", as_of=date(2026, 7, 16))

    assert calls == 1
    assert first["status"] == "no_data"
    assert second == first


def test_eastmoney_cache_failure_is_non_blocking(monkeypatch):
    class FailingRedis:
        def get(self, _key):
            raise ConnectionError("unavailable")

        def set(self, *_args, **_kwargs):
            raise ConnectionError("unavailable")

    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr("packages.services.fundamentals.redis_client", FailingRedis())
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        lambda *_args, **_kwargs: make_eastmoney_snapshot(),
    )

    payload = get_fundamental_payload("600519", as_of=date(2026, 7, 16))

    assert payload["status"] == "ok"
    assert payload["item"]["pe_ratio"] is None


def test_eastmoney_empty_and_failure_do_not_fall_back_to_fixture(monkeypatch):
    monkeypatch.setattr(
        "packages.services.fundamentals.get_platform_settings",
        lambda: {"akshare_enabled": True},
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.get",
        lambda _key: None,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.redis_client.set",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        lambda *_args, **_kwargs: None,
    )

    empty = get_fundamental_payload("600519", as_of=date(2026, 7, 16))

    assert empty["status"] == "no_data"
    assert empty["item"] is None

    def fail(*_args, **_kwargs):
        raise EastmoneyPublicFundamentalsProviderError(
            "EASTMONEY_FUNDAMENTALS_TIMEOUT",
            "sanitized",
        )

    monkeypatch.setattr(
        "packages.services.fundamentals.fetch_eastmoney_public_fundamentals",
        fail,
    )
    failed = get_fundamental_payload("600519", as_of=date(2026, 7, 16))

    assert failed["status"] == "unavailable"
    assert failed["item"] is None
    assert failed["diagnostics"] == ["EASTMONEY_FUNDAMENTALS_TIMEOUT"]
