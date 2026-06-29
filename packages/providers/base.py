from dataclasses import dataclass
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
