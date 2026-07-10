from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import Instrument, Market, MarketDailyEvidenceEvent
from packages.providers.base import ProviderCorporateActionSnapshot
from packages.services.corporate_actions import (
    CorporateActionSyncInput,
    sync_corporate_action_evidence,
)
from packages.shared.database import Base


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db_session = sessionmaker(bind=engine)()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def seed_symbols(session: Session, *symbols: str) -> None:
    market = Market(code="CN", name="China", timezone="Asia/Shanghai", currency="CNY")
    session.add(market)
    session.flush()
    session.add_all(
        [
            Instrument(
                symbol=symbol,
                name=symbol,
                market=market,
                asset_type="stock",
                currency="CNY",
                is_active=True,
            )
            for symbol in symbols
        ]
    )
    session.commit()


class FakeCorporateActionProvider:
    def __init__(self, *, degrade_rights: bool = False, fail_dividend: bool = False) -> None:
        self.degrade_rights = degrade_rights
        self.fail_dividend = fail_dividend
        self.calls: list[tuple[str, list[str]]] = []

    def fetch_corporate_actions(
        self,
        event_type: str,
        report_period: date,
        symbols: list[str],
    ) -> ProviderCorporateActionSnapshot:
        self.calls.append((event_type, symbols))
        if event_type == "dividend_bonus" and self.fail_dividend:
            raise RuntimeError("provider unavailable")
        if event_type == "dividend_bonus":
            items = [
                {
                    "symbol": symbol,
                    "name": symbol,
                    "report_period": report_period.isoformat(),
                    "trade_date": "2026-06-26",
                    "cash_dividend_per_10": float(index + 1),
                    "provider": "akshare",
                    "source": "akshare.fixture.dividend",
                }
                for index, symbol in enumerate(symbols)
            ]
            status = "ok"
            diagnostics = []
        else:
            items = [
                {
                    "symbol": symbols[0],
                    "name": symbols[0],
                    "report_period": report_period.isoformat(),
                    "trade_date": "2026-05-01",
                    "rights_code": "080001",
                    "rights_ratio": 0.3,
                    "rights_price": 8.5,
                    "provider": "akshare",
                    "source": "akshare.fixture.rights",
                }
            ]
            status = "degraded" if self.degrade_rights else "ok"
            diagnostics = (
                [
                    {
                        "code": "RIGHTS_ALLOTMENT_SYMBOL_FAILED",
                        "message": "A symbol request failed.",
                        "details": {"symbol": symbols[-1], "exception_type": "RuntimeError"},
                    }
                ]
                if self.degrade_rights
                else []
            )
        return ProviderCorporateActionSnapshot(
            provider="akshare",
            source=f"akshare.fixture.{event_type}",
            event_type=event_type,
            report_period=report_period,
            as_of=datetime(2026, 7, 10, tzinfo=timezone.utc),
            status=status,
            items=items,
            availability={"status": status, "row_count": len(items)},
            diagnostics=diagnostics,
        )


def test_corporate_action_sync_uses_deterministic_cursor_and_keeps_partial_results(
    session: Session,
):
    seed_symbols(session, "600519", "000001", "300750")
    provider = FakeCorporateActionProvider(degrade_rights=True)
    progress: list[tuple[str, int, int]] = []

    result = sync_corporate_action_evidence(
        CorporateActionSyncInput(
            report_period=date(2025, 12, 31),
            cursor=0,
            batch_size=2,
        ),
        session=session,
        provider=provider,
        progress_callback=lambda phase, current, total, _message: progress.append(
            (phase, current, total)
        ),
    )

    assert result["status"] == "partial"
    assert result["symbols"] == ["000001", "300750"]
    assert result["next_cursor"] == 2
    assert result["complete"] is False
    assert result["evidence"]["inserted"] == 3
    assert result["retry"]["degraded_event_types"] == ["rights_allotment"]
    assert result["retry"]["failed_symbols"] == ["300750"]
    assert provider.calls == [
        ("dividend_bonus", ["000001", "300750"]),
        ("rights_allotment", ["000001", "300750"]),
    ]
    assert progress[-1] == ("persisted", 3, 3)
    assert session.query(MarketDailyEvidenceEvent).count() == 3


def test_corporate_action_sync_can_continue_from_next_cursor(session: Session):
    seed_symbols(session, "600519", "000001", "300750")
    provider = FakeCorporateActionProvider()

    result = sync_corporate_action_evidence(
        CorporateActionSyncInput(
            report_period=date(2025, 12, 31),
            cursor=2,
            batch_size=2,
            event_types=("dividend_bonus",),
        ),
        session=session,
        provider=provider,
    )

    assert result["symbols"] == ["600519"]
    assert result["next_cursor"] is None
    assert result["complete"] is True
    assert result["evidence"]["inserted"] == 1


def test_corporate_action_sync_reports_retryable_event_failure(session: Session):
    seed_symbols(session, "600519")
    provider = FakeCorporateActionProvider(fail_dividend=True)

    result = sync_corporate_action_evidence(
        CorporateActionSyncInput(
            report_period=date(2025, 12, 31),
            symbols=("600519",),
        ),
        session=session,
        provider=provider,
    )

    assert result["status"] == "partial"
    assert result["retry"]["failed_event_types"] == ["dividend_bonus"]
    assert result["evidence"]["inserted"] == 1
    diagnostic = next(
        item for item in result["diagnostics"] if item["code"] == "CORPORATE_ACTION_PROVIDER_FAILED"
    )
    assert diagnostic["details"] == {
        "event_type": "dividend_bonus",
        "exception_type": "RuntimeError",
    }


def test_corporate_action_sync_returns_no_data_for_cursor_past_universe(session: Session):
    seed_symbols(session, "600519")

    result = sync_corporate_action_evidence(
        CorporateActionSyncInput(
            report_period=date(2025, 12, 31),
            cursor=10,
        ),
        session=session,
        provider=FakeCorporateActionProvider(),
    )

    assert result["status"] == "no_data"
    assert result["symbols"] == []
    assert result["diagnostics"][0]["code"] == "CORPORATE_ACTION_BATCH_EMPTY"
