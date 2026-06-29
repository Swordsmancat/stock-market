from datetime import date, timedelta
from decimal import Decimal

from packages.providers.base import ProviderBar, ProviderInstrument


class MockProvider:
    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        fixtures = {
            "CN": [ProviderInstrument("600519", "Kweichow Moutai", "CN", "SSE", "stock", "CNY")],
            "HK": [ProviderInstrument("0700", "Tencent Holdings", "HK", "HKEX", "stock", "HKD")],
            "US": [ProviderInstrument("AAPL", "Apple Inc.", "US", "NASDAQ", "stock", "USD")],
        }
        instruments = fixtures.get(market, [])
        if exchange is None:
            return instruments
        return [instrument for instrument in instruments if instrument.exchange == exchange]

    def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
        if timeframe not in {"1d", "1m"}:
            msg = f"Unsupported timeframe: {timeframe}"
            raise ValueError(msg)

        bars: list[ProviderBar] = []
        current = start
        price = Decimal("100.00")
        while current <= end:
            bars.append(
                ProviderBar(
                    symbol=symbol,
                    timestamp=current,
                    open=price,
                    high=price + Decimal("2.00"),
                    low=price - Decimal("1.00"),
                    close=price + Decimal("1.00"),
                    volume=Decimal("1000000"),
                    amount=Decimal("101000000"),
                )
            )
            current += timedelta(days=1)
            price += Decimal("1.00")
        return bars
