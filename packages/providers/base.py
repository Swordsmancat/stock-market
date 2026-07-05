from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ProviderInstrument:
    symbol: str
    name: str
    market: str
    exchange: str
    asset_type: str
    currency: str


@dataclass(frozen=True)
class ProviderBar:
    symbol: str
    timestamp: datetime | date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None = None


@dataclass(frozen=True)
class ProviderIntradayBar:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal | None = None
    average_price: Decimal | None = None


@dataclass(frozen=True)
class ProviderOrderBookLevel:
    price: Decimal
    volume: Decimal
    amount: Decimal | None = None
    order_count: int | None = None


@dataclass(frozen=True)
class ProviderRecentTrade:
    timestamp: datetime
    price: Decimal
    volume: Decimal
    amount: Decimal | None = None
    side: str | None = None


@dataclass(frozen=True)
class ProviderFundFlow:
    currency: str | None
    net_inflow: Decimal | None = None
    main_net_inflow: Decimal | None = None
    retail_net_inflow: Decimal | None = None
    source_definition: str | None = None


@dataclass(frozen=True)
class ProviderMarketDepthSnapshot:
    provider: str
    source: str
    as_of: datetime | None
    is_realtime: bool
    is_delayed: bool
    delay_minutes: int | None
    bids: list[ProviderOrderBookLevel] = field(default_factory=list)
    asks: list[ProviderOrderBookLevel] = field(default_factory=list)
    recent_trades: list[ProviderRecentTrade] = field(default_factory=list)
    fund_flow: ProviderFundFlow | None = None
    availability: dict[str, object] = field(default_factory=dict)


class ProviderAdapter(Protocol):
    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        ...

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]:
        ...


class IntradayProviderAdapter(Protocol):
    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]:
        ...


class MarketDepthProviderAdapter(Protocol):
    def fetch_market_depth(
        self,
        symbol: str,
        depth_levels: int,
    ) -> ProviderMarketDepthSnapshot:
        ...
