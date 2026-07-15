from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pandas as pd

from packages.providers.base import ProviderBar, ProviderInstrument
from packages.providers.cn_market_helpers import tushare_ts_code

Downloader = Callable[[str, date, date], pd.DataFrame]


class TushareProvider:
    """Tushare data provider for Chinese markets (CN stocks).
    Requires tushare_token in platform settings.
    """

    def __init__(self, downloader: Downloader | None = None, token: str = "") -> None:
        self._token = token
        self._downloader = downloader or self._download

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        fixtures = {
            "CN": [
                ProviderInstrument("000001", "Ping An Bank", "CN", "SZ", "stock", "CNY"),
                ProviderInstrument("600519", "Kweichow Moutai", "CN", "SSE", "stock", "CNY"),
                ProviderInstrument("000858", "Wuliangye", "CN", "SZ", "stock", "CNY"),
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
            ts = row["timestamp"]
            trade_date = ts.date() if hasattr(ts, "date") else ts
            bars.append(
                ProviderBar(
                    symbol=symbol,
                    timestamp=trade_date,
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
            import tushare as ts
        except ImportError as exc:
            raise RuntimeError("tushare package is not installed.") from exc

        import os

        token = ""
        http_url = ""
        try:
            from packages.services.platform_settings import get_platform_settings
        except ImportError:
            pass
        else:
            settings_payload = get_platform_settings()
            token = str(settings_payload.get("tushare_token", "") or "").strip()
            http_url = str(settings_payload.get("tushare_http_url", "") or "").strip()

        if not token:
            token = os.environ.get("TUSHARE_TOKEN", "").strip()
        if not http_url:
            http_url = os.environ.get("TUSHARE_HTTP_URL", "").strip()

        if not token:
            return pd.DataFrame()

        ts.set_token(token)
        pro = ts.pro_api(http_url) if http_url else ts.pro_api()

        start_str = start.isoformat().replace("-", "")
        end_str = end.isoformat().replace("-", "")
        df = pro.daily(
            ts_code=tushare_ts_code(symbol),
            start_date=start_str,
            end_date=end_str,
        )
        if df is None or df.empty:
            return pd.DataFrame()

        df = df.rename(
            columns={
                "trade_date": "timestamp",
                "open": "open",
                "close": "close",
                "high": "high",
                "low": "low",
                "vol": "volume",
                "amount": "amount",
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        else:
            df["amount"] = 0
        return df.dropna(subset=numeric_cols)
