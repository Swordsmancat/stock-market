from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pandas as pd

from packages.providers.base import ProviderBar, ProviderInstrument

Downloader = Callable[[str, date, date], pd.DataFrame]


class AkShareProvider:
    """AkShare data provider for Chinese markets (CN stocks, indices, futures)."""

    def __init__(self, downloader: Downloader | None = None) -> None:
        self._downloader = downloader or self._download

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        fixtures = {
            "CN": [
                ProviderInstrument("000001", "SZ Component Index", "CN", "SZ", "stock", "CNY"),
                ProviderInstrument("600519", "Kweichow Moutai", "CN", "SSE", "stock", "CNY"),
                ProviderInstrument("000002", "China Vanke", "CN", "SZ", "stock", "CNY"),
            ],
        }
        instruments = fixtures.get(market, [])
        if exchange is None:
            return instruments
        return [instrument for instrument in instruments if instrument.exchange == exchange]

    def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
        df = self._downloader(symbol, start, end)
        if df is None or df.empty:
            return []
        bars: list[ProviderBar] = []
        for _, row in df.iterrows():
            bars.append(
                ProviderBar(
                    timestamp=row["timestamp"],
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=Decimal(str(row["volume"])),
                    amount=Decimal(str(row.get("amount", 0))),
                )
            )
        return bars

    @staticmethod
    def _download(symbol: str, start: date, end: date) -> pd.DataFrame:
        try:
            import akshare as ak

            end_str = end.isoformat().replace("-", "")
            start_str = start.isoformat().replace("-", "")

            if symbol.startswith("6"):
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_str, end_date=end_str, adjust="qfq")

            if df is None or df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "日期": "timestamp",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            numeric_cols = ["open", "high", "low", "close", "volume"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "amount" in df.columns:
                df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
            else:
                df["amount"] = 0
            df = df.dropna(subset=numeric_cols)
            return df
        except ImportError:
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()
