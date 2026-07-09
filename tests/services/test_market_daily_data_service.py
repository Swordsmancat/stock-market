from datetime import date

from packages.services.market_daily_data import (
    BlockTradeProviderItem,
    DragonTigerProviderItem,
    LimitUpReasonProviderItem,
    MarketDailyProviderResult,
    StockFundFlowProviderItem,
    get_block_trades_payload,
    get_dragon_tiger_list_payload,
    get_limit_up_reasons_payload,
    get_stock_fund_flow_payload,
)


class FakeMarketDailyDataProvider:
    provider_name = "fake_daily"

    def fetch_stock_fund_flow(self, *, limit: int, window: str) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="ok",
            data_mode="delayed",
            source="fake_stock_fund_flow",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of="2026-07-09T09:30:00+00:00",
            market="CN",
            window=window,
            message="Fake stock fund-flow rows.",
            availability={
                "status": "delayed",
                "reason": None,
                "ranking": "available",
                "fund_flow": "available",
                "price": "available",
            },
            provider_capabilities={
                "stock_fund_flow": {"status": "delayed"},
                "ranking": {"status": "delayed"},
                "citation": {"status": "not_citable"},
            },
            items=[
                StockFundFlowProviderItem(
                    symbol="600519",
                    name="Kweichow Moutai",
                    latest_price=1688.5,
                    change_percent=1.25,
                    main_net_flow_amount=123456789.0,
                    super_large_net_flow_amount=80000000.0,
                    large_net_flow_amount=40000000.0,
                    medium_net_flow_amount=-1000000.0,
                    small_net_flow_amount=-2000000.0,
                    flow_window=window,
                    provider=self.provider_name,
                    source="fake_stock_fund_flow",
                )
            ],
        )

    def fetch_limit_up_reasons(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="ok",
            data_mode="delayed",
            source="fake_limit_up_reasons",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of="2026-07-09T09:30:00+00:00",
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Fake limit-up reason rows.",
            availability={
                "status": "delayed",
                "reason": None,
                "limit_up_pool": "available",
                "reason_detail": "available",
            },
            provider_capabilities={
                "limit_up_pool": {"status": "delayed"},
                "limit_up_reasons": {"status": "delayed"},
                "citation": {"status": "not_citable"},
            },
            items=[
                LimitUpReasonProviderItem(
                    symbol="002001",
                    name="Test Limit",
                    trade_date=trade_date.isoformat(),
                    latest_price=12.34,
                    change_percent=10.0,
                    reason="AI computing",
                    detail="Provider supplied a structured reason.",
                    sector="Software",
                    limit_up_count=2,
                    consecutive_limit_up_count=2,
                    first_limit_up_time="09:35:00",
                    last_limit_up_time="14:55:00",
                    turnover_rate=8.2,
                    market_cap=12300000000.0,
                    provider=self.provider_name,
                    source="fake_limit_up_reasons",
                )
            ],
        )

    def fetch_dragon_tiger_list(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="ok",
            data_mode="delayed",
            source="fake_dragon_tiger_list",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of="2026-07-09T09:30:00+00:00",
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Fake Dragon Tiger List rows.",
            availability={
                "status": "delayed",
                "reason": None,
                "dragon_tiger_list": "available",
            },
            provider_capabilities={
                "dragon_tiger_list": {"status": "delayed"},
                "citation": {"status": "not_citable"},
            },
            items=[
                DragonTigerProviderItem(
                    symbol="600519",
                    name="Kweichow Moutai",
                    trade_date=trade_date.isoformat(),
                    close_price=1688.5,
                    change_percent=3.2,
                    turnover_rate=1.8,
                    amount=456000000.0,
                    net_buy_amount=123000000.0,
                    buy_amount=300000000.0,
                    sell_amount=177000000.0,
                    reason="Daily price deviation reached threshold.",
                    interpretation="Institutional net buy.",
                    department_name="Test brokerage seat",
                    department_rank=1,
                    provider=self.provider_name,
                    source="fake_dragon_tiger_list",
                )
            ],
        )

    def fetch_block_trades(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="ok",
            data_mode="delayed",
            source="fake_block_trades",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of="2026-07-09T09:30:00+00:00",
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Fake block-trade rows.",
            availability={
                "status": "delayed",
                "reason": None,
                "block_trades": "available",
            },
            provider_capabilities={
                "block_trades": {"status": "delayed"},
                "citation": {"status": "not_citable"},
            },
            items=[
                BlockTradeProviderItem(
                    symbol="000001",
                    name="Ping An Bank",
                    trade_date=trade_date.isoformat(),
                    trade_price=11.8,
                    close_price=12.0,
                    change_percent=0.9,
                    discount_percent=-1.67,
                    volume=1000000.0,
                    amount=11800000.0,
                    buyer="Buyer seat",
                    seller="Seller seat",
                    market="A股",
                    provider=self.provider_name,
                    source="fake_block_trades",
                )
            ],
        )


class EmptyMarketDailyDataProvider(FakeMarketDailyDataProvider):
    provider_name = "empty_daily"

    def fetch_stock_fund_flow(self, *, limit: int, window: str) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="degraded",
            data_mode="none",
            source="empty_stock_fund_flow",
            provider=self.provider_name,
            as_of=None,
            market="CN",
            window=window,
            message="Provider returned no stock fund-flow rows.",
            availability={"status": "no_data", "reason": "Provider returned no rows."},
            items=[],
        )

    def fetch_dragon_tiger_list(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="degraded",
            data_mode="none",
            source="empty_dragon_tiger_list",
            provider=self.provider_name,
            as_of=None,
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Provider returned no Dragon Tiger List rows.",
            availability={"status": "no_data", "reason": "Provider returned no rows."},
            items=[],
        )

    def fetch_block_trades(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="degraded",
            data_mode="none",
            source="empty_block_trades",
            provider=self.provider_name,
            as_of=None,
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Provider returned no block-trade rows.",
            availability={"status": "no_data", "reason": "Provider returned no rows."},
            items=[],
        )


class LimitUpPoolOnlyProvider(FakeMarketDailyDataProvider):
    provider_name = "pool_only"

    def fetch_limit_up_reasons(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        return MarketDailyProviderResult(
            status="degraded",
            data_mode="delayed",
            source="fake_limit_up_pool",
            provider=self.provider_name,
            as_of="2026-07-09T09:30:00+00:00",
            market="CN",
            window="today",
            trade_date=trade_date.isoformat(),
            message="Provider returned limit-up pool rows without reason fields.",
            availability={
                "status": "delayed",
                "reason": "Provider returned limit-up pool rows without reason fields.",
                "limit_up_pool": "available",
                "reason_detail": "unavailable",
            },
            provider_capabilities={
                "limit_up_pool": {"status": "delayed"},
                "limit_up_reasons": {"status": "unavailable"},
            },
            items=[
                LimitUpReasonProviderItem(
                    symbol="002002",
                    name="Pool Only",
                    trade_date=trade_date.isoformat(),
                    sector="Industrial",
                    provider=self.provider_name,
                    source="fake_limit_up_pool",
                )
            ],
        )


class FailingMarketDailyDataProvider(FakeMarketDailyDataProvider):
    provider_name = "failing_daily"

    def fetch_stock_fund_flow(self, *, limit: int, window: str) -> MarketDailyProviderResult:
        raise RuntimeError("provider failed token=secret123")

    def fetch_dragon_tiger_list(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        raise RuntimeError("provider failed token=secret123")

    def fetch_block_trades(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        raise RuntimeError("provider failed token=secret123")


def test_stock_fund_flow_payload_normalizes_provider_rows():
    payload = get_stock_fund_flow_payload(
        market="CN",
        window="today",
        limit=10,
        provider_name="fake_daily",
        provider=FakeMarketDailyDataProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "delayed"
    assert payload["provider"] == "fake_daily"
    assert payload["requested_provider"] == "fake_daily"
    assert payload["effective_provider"] == "fake_daily"
    assert payload["market"] == "CN"
    assert payload["window"] == "today"
    assert payload["provider_capabilities"]["citation"]["status"] == "not_citable"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["rank"] == 1
    assert item["symbol"] == "600519"
    assert item["main_net_flow_amount"] == 123456789.0
    assert item["net_flow_amount"] == 123456789.0
    assert item["flow_window"] == "today"


def test_stock_fund_flow_empty_provider_returns_no_data_without_fabricated_rows():
    payload = get_stock_fund_flow_payload(
        market="CN",
        window="5d",
        limit=10,
        provider_name="empty_daily",
        provider=EmptyMarketDailyDataProvider(),
    )

    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "none"
    assert payload["availability"]["status"] == "no_data"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_stock_fund_flow_provider_failure_is_sanitized():
    payload = get_stock_fund_flow_payload(
        market="CN",
        window="today",
        limit=10,
        provider_name="failing_daily",
        provider=FailingMarketDailyDataProvider(),
    )

    assert payload["status"] == "unavailable"
    assert payload["source"] == "provider_error"
    assert "RuntimeError" in payload["message"]
    assert "secret123" not in payload["message"]


def test_stock_fund_flow_unknown_provider_returns_unavailable_payload():
    payload = get_stock_fund_flow_payload(provider_name="unknown_provider")

    assert payload["status"] == "unavailable"
    assert payload["data_mode"] == "none"
    assert payload["requested_provider"] == "unknown_provider"
    assert payload["provider_capabilities"]["stock_fund_flow"]["status"] == "unavailable"
    assert payload["items"] == []


def test_stock_fund_flow_unsupported_window_returns_unavailable_payload():
    payload = get_stock_fund_flow_payload(window="20d", provider_name="akshare")

    assert payload["status"] == "unavailable"
    assert payload["window"] == "20d"
    assert "not supported" in payload["message"]


def test_limit_up_reasons_payload_normalizes_provider_rows():
    payload = get_limit_up_reasons_payload(
        trade_date="2026-07-09",
        limit=10,
        provider_name="fake_daily",
        provider=FakeMarketDailyDataProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "delayed"
    assert payload["trade_date"] == "2026-07-09"
    assert payload["provider_capabilities"]["limit_up_reasons"]["status"] == "delayed"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["rank"] == 1
    assert item["symbol"] == "002001"
    assert item["reason"] == "AI computing"
    assert item["detail"] == "Provider supplied a structured reason."
    assert item["consecutive_limit_up_count"] == 2


def test_limit_up_pool_without_reason_fields_is_visible_but_degraded():
    payload = get_limit_up_reasons_payload(
        trade_date="20260709",
        provider_name="pool_only",
        provider=LimitUpPoolOnlyProvider(),
    )

    assert payload["status"] == "degraded"
    assert payload["availability"]["reason_detail"] == "unavailable"
    assert payload["provider_capabilities"]["limit_up_reasons"]["status"] == "unavailable"
    assert payload["count"] == 1
    assert payload["items"][0]["reason"] is None


def test_limit_up_reasons_invalid_date_returns_unavailable_payload():
    payload = get_limit_up_reasons_payload(
        trade_date="2026/07/09",
        provider_name="akshare",
    )

    assert payload["status"] == "unavailable"
    assert payload["trade_date"] == "2026/07/09"
    assert "Invalid trade date" in payload["message"]


def test_dragon_tiger_list_payload_normalizes_provider_rows():
    payload = get_dragon_tiger_list_payload(
        trade_date="2026-07-09",
        limit=10,
        provider_name="fake_daily",
        provider=FakeMarketDailyDataProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "delayed"
    assert payload["trade_date"] == "2026-07-09"
    assert payload["provider_capabilities"]["dragon_tiger_list"]["status"] == "delayed"
    assert payload["provider_capabilities"]["citation"]["status"] == "not_citable"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["rank"] == 1
    assert item["symbol"] == "600519"
    assert item["net_buy_amount"] == 123000000.0
    assert item["buy_amount"] == 300000000.0
    assert item["sell_amount"] == 177000000.0
    assert item["reason"] == "Daily price deviation reached threshold."
    assert item["department_name"] == "Test brokerage seat"


def test_dragon_tiger_empty_provider_returns_no_data_without_fabricated_rows():
    payload = get_dragon_tiger_list_payload(
        trade_date="20260709",
        provider_name="empty_daily",
        provider=EmptyMarketDailyDataProvider(),
    )

    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "none"
    assert payload["availability"]["status"] == "no_data"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_dragon_tiger_invalid_date_returns_unavailable_payload():
    payload = get_dragon_tiger_list_payload(
        trade_date="2026/07/09",
        provider_name="akshare",
    )

    assert payload["status"] == "unavailable"
    assert payload["trade_date"] == "2026/07/09"
    assert "Invalid trade date" in payload["message"]


def test_dragon_tiger_provider_failure_is_sanitized():
    payload = get_dragon_tiger_list_payload(
        trade_date="2026-07-09",
        provider_name="failing_daily",
        provider=FailingMarketDailyDataProvider(),
    )

    assert payload["status"] == "unavailable"
    assert payload["source"] == "provider_error"
    assert "RuntimeError" in payload["message"]
    assert "secret123" not in payload["message"]


def test_block_trades_payload_normalizes_provider_rows():
    payload = get_block_trades_payload(
        trade_date="2026-07-09",
        limit=10,
        provider_name="fake_daily",
        provider=FakeMarketDailyDataProvider(),
    )

    assert payload["status"] == "ok"
    assert payload["data_mode"] == "delayed"
    assert payload["trade_date"] == "2026-07-09"
    assert payload["provider_capabilities"]["block_trades"]["status"] == "delayed"
    assert payload["provider_capabilities"]["citation"]["status"] == "not_citable"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["rank"] == 1
    assert item["symbol"] == "000001"
    assert item["trade_price"] == 11.8
    assert item["discount_percent"] == -1.67
    assert item["buyer"] == "Buyer seat"
    assert item["seller"] == "Seller seat"


def test_block_trades_empty_provider_returns_no_data_without_fabricated_rows():
    payload = get_block_trades_payload(
        trade_date="20260709",
        provider_name="empty_daily",
        provider=EmptyMarketDailyDataProvider(),
    )

    assert payload["status"] == "degraded"
    assert payload["data_mode"] == "none"
    assert payload["availability"]["status"] == "no_data"
    assert payload["count"] == 0
    assert payload["items"] == []


def test_block_trades_provider_failure_is_sanitized():
    payload = get_block_trades_payload(
        trade_date="2026-07-09",
        provider_name="failing_daily",
        provider=FailingMarketDailyDataProvider(),
    )

    assert payload["status"] == "unavailable"
    assert payload["source"] == "provider_error"
    assert "RuntimeError" in payload["message"]
    assert "secret123" not in payload["message"]


def test_block_trades_unsupported_market_returns_unavailable_payload():
    payload = get_block_trades_payload(
        trade_date="2026-07-09",
        market="US",
        provider_name="akshare",
    )

    assert payload["status"] == "unavailable"
    assert payload["market"] == "US"
    assert "not supported" in payload["message"]


def test_block_trades_invalid_date_returns_unavailable_payload():
    payload = get_block_trades_payload(
        trade_date="2026/07/09",
        provider_name="akshare",
    )

    assert payload["status"] == "unavailable"
    assert payload["trade_date"] == "2026/07/09"
    assert "Invalid trade date" in payload["message"]
