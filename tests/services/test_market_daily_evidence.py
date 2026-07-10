from copy import deepcopy
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.domain.models import Base, MarketDailyEvidenceEvent
from packages.services.market_daily_evidence import (
    MarketDailyEvidenceImportInput,
    MarketDailyEvidenceValidationError,
    import_market_daily_evidence,
    list_citable_market_daily_evidence_citations,
    list_market_daily_evidence,
)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine)()
    try:
        yield test_session
    finally:
        test_session.close()
        Base.metadata.drop_all(engine)


def _provider_payload(*, items, source="fake_source", data_mode="delayed", status="ok"):
    return {
        "status": status,
        "data_mode": data_mode,
        "source": source,
        "provider": "fake",
        "requested_provider": "fake",
        "effective_provider": "fake",
        "market": "CN",
        "as_of": "2026-07-10T08:00:00+00:00",
        "availability": {"status": "delayed"},
        "provider_capabilities": {"ranking": {"status": "delayed"}},
        "count": len(items),
        "items": items,
    }


def _all_event_payloads():
    return {
        "stock_fund_flow": _provider_payload(
            items=[
                {
                    "symbol": "000001",
                    "name": "Ping An Bank",
                    "rank": 1,
                    "main_net_flow_amount": 123.4,
                    "provider": "fake",
                    "source": "fake_stock_flow",
                    "api_key": "must-not-persist",
                    "provider_note": "token=must-not-persist",
                }
            ]
        ),
        "limit_up_reason": {
            **_provider_payload(
                items=[
                    {
                        "symbol": "000002",
                        "name": "Vanke",
                        "rank": 2,
                        "trade_date": "2026-07-10",
                        "reason": "Reviewed provider reason",
                    }
                ],
                status="degraded",
            ),
            "trade_date": "2026-07-10",
            "message": "Reason coverage is partial.",
        },
        "dragon_tiger_list": {
            **_provider_payload(
                items=[
                    {
                        "symbol": "000003",
                        "name": "Test Dragon Tiger",
                        "rank": 3,
                        "trade_date": "2026-07-10",
                        "net_buy_amount": 88.0,
                    }
                ]
            ),
            "trade_date": "2026-07-10",
        },
        "block_trade": {
            **_provider_payload(
                items=[
                    {
                        "symbol": "000004",
                        "name": "Test Block Trade",
                        "rank": 4,
                        "trade_date": "2026-07-10",
                        "amount": 500.0,
                        "buyer": "Buyer seat",
                        "seller": "Seller seat",
                    }
                ]
            ),
            "trade_date": "2026-07-10",
        },
        "hot_sector": {
            **_provider_payload(
                items=[
                    {
                        "sector_id": "semiconductor",
                        "name": "Semiconductor",
                        "rank": 1,
                        "fund_flow": 999.0,
                    }
                ]
            ),
            "sector_type": "industry",
            "window": "today",
        },
    }


def _import_input(*event_types):
    return MarketDailyEvidenceImportInput(
        trade_date=date(2026, 7, 10),
        market="CN",
        provider_name="fake",
        event_types=tuple(event_types) or (
            "stock_fund_flow",
            "limit_up_reason",
            "dragon_tiger_list",
            "block_trade",
            "hot_sector",
        ),
        limit=20,
    )


def test_import_upserts_all_event_types_and_builds_stored_citations(session):
    payloads = _all_event_payloads()

    first = import_market_daily_evidence(
        _import_input(),
        session=session,
        normalized_payloads=payloads,
    )

    assert first["status"] == "ok"
    assert first["inserted"] == 5
    assert first["updated"] == 0
    assert first["skipped"] == 0

    listing = list_market_daily_evidence(session=session, limit=20)
    assert listing["summary"]["total"] == 5
    assert listing["summary"]["counts_by_event_type"] == {
        "block_trade": 1,
        "dragon_tiger_list": 1,
        "hot_sector": 1,
        "limit_up_reason": 1,
        "stock_fund_flow": 1,
    }
    assert len(listing["citations"]) == 5
    assert all(citation["id"].startswith("market_daily_event:") for citation in listing["citations"])
    stored_stock_flow = session.query(MarketDailyEvidenceEvent).filter_by(event_type="stock_fund_flow").one()
    assert "api_key" not in stored_stock_flow.payload_json
    assert stored_stock_flow.payload_json["provider_note"] == "token=[redacted]"
    assert stored_stock_flow.is_citable is True

    second = import_market_daily_evidence(
        _import_input(),
        session=session,
        normalized_payloads=payloads,
    )
    assert second["inserted"] == 0
    assert second["updated"] == 0
    assert second["skipped"] == 5
    assert session.query(MarketDailyEvidenceEvent).count() == 5

    changed_payloads = deepcopy(payloads)
    changed_payloads["stock_fund_flow"]["items"][0]["main_net_flow_amount"] = 456.7
    changed = import_market_daily_evidence(
        _import_input("stock_fund_flow"),
        session=session,
        normalized_payloads=changed_payloads,
    )
    assert changed["updated"] == 1
    assert session.query(MarketDailyEvidenceEvent).filter_by(event_type="stock_fund_flow").one().payload_json[
        "main_net_flow_amount"
    ] == 456.7


def test_mock_or_unavailable_payloads_never_create_citable_rows(session):
    mock_payload = _provider_payload(
        items=[{"symbol": "000001", "name": "Mock row"}],
        source="static_fixture",
        data_mode="mock",
        status="degraded",
    )
    mock_payload["effective_provider"] = "static"

    result = import_market_daily_evidence(
        _import_input("stock_fund_flow"),
        session=session,
        normalized_payloads={"stock_fund_flow": mock_payload},
    )

    assert result["status"] == "degraded"
    assert result["inserted"] == 0
    assert list_citable_market_daily_evidence_citations(session=session) == []
    assert session.query(MarketDailyEvidenceEvent).count() == 0


def test_block_trade_identity_preserves_multiple_rows_for_one_symbol(session):
    payload = {
        **_provider_payload(
            items=[
                {"symbol": "000004", "rank": 1, "trade_date": "2026-07-10", "amount": 100.0},
                {"symbol": "000004", "rank": 2, "trade_date": "2026-07-10", "amount": 200.0},
            ]
        ),
        "trade_date": "2026-07-10",
    }

    result = import_market_daily_evidence(
        _import_input("block_trade"),
        session=session,
        normalized_payloads={"block_trade": payload},
    )

    assert result["inserted"] == 2
    identities = {
        row.identity
        for row in session.query(MarketDailyEvidenceEvent).order_by(MarketDailyEvidenceEvent.identity).all()
    }
    assert identities == {"000004-rank-1", "000004-rank-2"}
    symbol_listing = list_market_daily_evidence(session=session, symbol="000004")
    assert symbol_listing["summary"]["total"] == 2


def test_import_rejects_unknown_event_types(session):
    with pytest.raises(MarketDailyEvidenceValidationError) as error:
        import_market_daily_evidence(
            _import_input("not_supported"),
            session=session,
            normalized_payloads={},
        )

    assert "not_supported" in str(error.value)
