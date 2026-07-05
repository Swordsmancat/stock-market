from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pandas as pd

from packages.providers.base import ProviderBar
from packages.providers.base import ProviderFundFlow
from packages.providers.base import ProviderInstrument
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.base import ProviderRecentTrade

DailyBarsDownloader = Callable[[str, date, date], pd.DataFrame]
MarketDepthDownloader = Callable[[str, int], dict[str, object]]


class AkShareProvider:
    """AkShare data provider for Chinese markets (CN stocks, indices, futures)."""

    def __init__(
        self,
        downloader: DailyBarsDownloader | None = None,
        market_depth_downloader: MarketDepthDownloader | None = None,
    ) -> None:
        self._downloader = downloader or self._download
        self._market_depth_downloader = market_depth_downloader or self._download_market_depth

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

    def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
        raw_payload = self._market_depth_downloader(symbol, depth_levels)
        bids = _parse_order_book_levels(_dataframe_or_none(raw_payload.get("bids")), depth_levels)
        asks = _parse_order_book_levels(_dataframe_or_none(raw_payload.get("asks")), depth_levels)
        recent_trades = _parse_recent_trades(_dataframe_or_none(raw_payload.get("recent_trades")))
        fund_flow = _parse_fund_flow(raw_payload.get("fund_flow"))
        availability = raw_payload.get("availability")

        if not isinstance(availability, dict):
            has_any_verified_data = bool(bids or asks or recent_trades or fund_flow is not None)
            availability = {
                "status": "ok" if has_any_verified_data else "degraded",
                "reason": None
                if has_any_verified_data
                else "AkShare did not return normalized market-depth rows for this request.",
            }

        return ProviderMarketDepthSnapshot(
            provider="akshare",
            source=str(raw_payload.get("source") or "akshare"),
            as_of=_datetime_or_none(raw_payload.get("as_of")),
            is_realtime=bool(raw_payload.get("is_realtime", False)),
            is_delayed=bool(raw_payload.get("is_delayed", True)),
            delay_minutes=_int_or_none(raw_payload.get("delay_minutes")),
            bids=bids,
            asks=asks,
            recent_trades=recent_trades,
            fund_flow=fund_flow,
            availability=availability,
        )

    @staticmethod
    def _download(symbol: str, start: date, end: date) -> pd.DataFrame:
        try:
            import akshare as ak

            end_str = end.isoformat().replace("-", "")
            start_str = start.isoformat().replace("-", "")
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust="qfq",
            )

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

    @staticmethod
    def _download_market_depth(symbol: str, depth_levels: int) -> dict[str, object]:
        try:
            import akshare as ak

            raw_order_book = ak.stock_bid_ask_em(symbol=symbol)
            return _normalize_stock_bid_ask_em_payload(raw_order_book, depth_levels)
        except ImportError:
            return {
                "availability": {
                    "status": "degraded",
                    "reason": "AkShare is not installed in this environment.",
                }
            }
        except Exception as exc:
            return {
                "source": "akshare.stock_bid_ask_em",
                "availability": {
                    "status": "degraded",
                    "reason": "AkShare market-depth endpoint failed or changed schema.",
                    "exception_type": type(exc).__name__,
                }
            }


def _normalize_stock_bid_ask_em_payload(raw_order_book: pd.DataFrame | None, depth_levels: int) -> dict[str, object]:
    if raw_order_book is None or raw_order_book.empty:
        return {
            "source": "akshare.stock_bid_ask_em",
            "availability": {
                "status": "degraded",
                "reason": "AkShare returned an empty order-book payload.",
                "raw_shape": _dataframe_shape(raw_order_book),
            }
        }

    raw_mapping = _frame_to_key_value_mapping(raw_order_book)
    bids = _levels_from_bid_ask_mapping(raw_mapping, side="bid", depth_levels=depth_levels)
    asks = _levels_from_bid_ask_mapping(raw_mapping, side="ask", depth_levels=depth_levels)
    schema_diagnostics = _schema_diagnostics(raw_order_book, raw_mapping)

    return {
        "source": "akshare.stock_bid_ask_em",
        "bids": bids,
        "asks": asks,
        "is_realtime": False,
        "is_delayed": True,
        "availability": {
            "status": "ok" if not bids.empty or not asks.empty else "degraded",
            "reason": None if not bids.empty or not asks.empty else "AkShare order-book payload could not be normalized.",
            **schema_diagnostics,
        },
    }


def _schema_diagnostics(frame: pd.DataFrame, raw_mapping: dict[str, object]) -> dict[str, object]:
    return {
        "raw_shape": _dataframe_shape(frame),
        "raw_columns": [str(column) for column in list(frame.columns)[:20]],
        "raw_fields_sample": list(raw_mapping)[:20],
    }


def _dataframe_shape(frame: pd.DataFrame | None) -> str | None:
    if frame is None:
        return None
    return f"{frame.shape[0]}x{frame.shape[1]}"


def _frame_to_key_value_mapping(frame: pd.DataFrame) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for _, row in frame.iterrows():
        if "item" in frame.columns and "value" in frame.columns:
            key = row["item"]
            value = row["value"]
        elif len(row) >= 2:
            key = row.iloc[0]
            value = row.iloc[1]
        else:
            continue
        if key is not None:
            mapping[str(key).strip()] = value
    return mapping


def _levels_from_bid_ask_mapping(raw_mapping: dict[str, object], side: str, depth_levels: int) -> pd.DataFrame:
    level_rows: list[dict[str, object]] = []
    chinese_level_names = ["一", "二", "三", "四", "五"]
    for level_number in range(1, depth_levels + 1):
        chinese_level_name = chinese_level_names[level_number - 1] if level_number <= len(chinese_level_names) else str(level_number)
        if side == "bid":
            price = _first_mapping_value(
                raw_mapping,
                [f"buy_{level_number}", f"bid_{level_number}", f"买{level_number}", f"买{chinese_level_name}", f"买{chinese_level_name}价"],
            )
            volume = _first_mapping_value(
                raw_mapping,
                [
                    f"buy_{level_number}_vol",
                    f"bid_{level_number}_volume",
                    f"买{level_number}量",
                    f"买{chinese_level_name}量",
                ],
            )
        else:
            price = _first_mapping_value(
                raw_mapping,
                [f"sell_{level_number}", f"ask_{level_number}", f"卖{level_number}", f"卖{chinese_level_name}", f"卖{chinese_level_name}价"],
            )
            volume = _first_mapping_value(
                raw_mapping,
                [
                    f"sell_{level_number}_vol",
                    f"ask_{level_number}_volume",
                    f"卖{level_number}量",
                    f"卖{chinese_level_name}量",
                ],
            )
        level_rows.append({"price": price, "volume": volume})
    return pd.DataFrame(level_rows)


def _first_mapping_value(raw_mapping: dict[str, object], candidate_keys: list[str]) -> object | None:
    for candidate_key in candidate_keys:
        if candidate_key in raw_mapping:
            return raw_mapping[candidate_key]
    return None


def _dataframe_or_none(value: object) -> pd.DataFrame | None:
    return value if isinstance(value, pd.DataFrame) else None


def _parse_order_book_levels(frame: pd.DataFrame | None, depth_levels: int) -> list[ProviderOrderBookLevel]:
    if frame is None or frame.empty:
        return []

    levels: list[ProviderOrderBookLevel] = []
    for _, row in frame.head(depth_levels).iterrows():
        price = _decimal_from_row(row, ["price", "价格", "委托价格", "买价", "卖价"])
        volume = _decimal_from_row(row, ["volume", "数量", "委托数量", "买量", "卖量"])
        if price is None or volume is None or price <= 0 or volume <= 0:
            continue

        levels.append(
            ProviderOrderBookLevel(
                price=price,
                volume=volume,
                amount=_decimal_from_row(row, ["amount", "金额", "委托金额"]),
                order_count=_int_from_row(row, ["order_count", "委托笔数", "订单数"]),
            )
        )
    return levels


def _parse_recent_trades(frame: pd.DataFrame | None) -> list[ProviderRecentTrade]:
    if frame is None or frame.empty:
        return []

    trades: list[ProviderRecentTrade] = []
    for _, row in frame.iterrows():
        timestamp = _datetime_or_none(_first_row_value(row, ["timestamp", "time", "时间", "成交时间"]))
        price = _decimal_from_row(row, ["price", "价格", "成交价"])
        volume = _decimal_from_row(row, ["volume", "数量", "成交量"])
        if timestamp is None or price is None or volume is None or price <= 0 or volume <= 0:
            continue

        side_value = _first_row_value(row, ["side", "方向", "性质"])
        trades.append(
            ProviderRecentTrade(
                timestamp=timestamp,
                price=price,
                volume=volume,
                amount=_decimal_from_row(row, ["amount", "金额", "成交额"]),
                side=str(side_value).strip().lower() if side_value is not None else None,
            )
        )
    return trades


def _parse_fund_flow(raw_fund_flow: object) -> ProviderFundFlow | None:
    row = _fund_flow_row_or_none(raw_fund_flow)
    if row is None:
        return None

    return ProviderFundFlow(
        currency=str(_first_row_value(row, ["currency", "币种"]) or "CNY"),
        net_inflow=_decimal_from_row(row, ["net_inflow", "净流入"]),
        main_net_inflow=_decimal_from_row(row, ["main_net_inflow", "主力净流入"]),
        retail_net_inflow=_decimal_from_row(row, ["retail_net_inflow", "散户净流入"]),
        source_definition=str(_first_row_value(row, ["source_definition", "口径说明"]) or "AkShare provider-defined fund-flow"),
    )


def _fund_flow_row_or_none(raw_fund_flow: object) -> pd.Series | None:
    if isinstance(raw_fund_flow, pd.DataFrame):
        if raw_fund_flow.empty:
            return None
        return raw_fund_flow.iloc[0]
    if isinstance(raw_fund_flow, dict):
        return pd.Series(raw_fund_flow)
    return None


def _decimal_from_row(row: pd.Series, candidate_columns: list[str]) -> Decimal | None:
    return _decimal_or_none(_first_row_value(row, candidate_columns))


def _int_from_row(row: pd.Series, candidate_columns: list[str]) -> int | None:
    return _int_or_none(_first_row_value(row, candidate_columns))


def _first_row_value(row: pd.Series, candidate_columns: list[str]) -> object | None:
    for candidate_column in candidate_columns:
        if candidate_column in row and pd.notna(row[candidate_column]):
            return row[candidate_column]
    return None


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _datetime_or_none(value: object) -> datetime | None:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    try:
        parsed_timestamp = pd.to_datetime(value, errors="coerce")
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed_timestamp):
        return None
    if isinstance(parsed_timestamp, pd.Timestamp):
        return parsed_timestamp.to_pydatetime()
    return None
