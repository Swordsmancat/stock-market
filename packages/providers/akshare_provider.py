from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import pandas as pd

from packages.providers.base import ProviderBar
from packages.providers.base import ProviderCorporateActionSnapshot
from packages.providers.base import ProviderFundFlow
from packages.providers.base import ProviderInstrument
from packages.providers.base import ProviderInstrumentUniverseSnapshot
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.base import ProviderRecentTrade

DailyBarsDownloader = Callable[[str, date, date], pd.DataFrame]
MarketDepthDownloader = Callable[[str, int], dict[str, object]]
InstrumentUniverseDownloader = Callable[[], pd.DataFrame]
DividendBonusDownloader = Callable[[str], pd.DataFrame]
RightsAllotmentDownloader = Callable[[str, str, str], pd.DataFrame]


class AkShareProvider:
    """AkShare data provider for Chinese markets (CN stocks, indices, futures)."""

    def __init__(
        self,
        downloader: DailyBarsDownloader | None = None,
        market_depth_downloader: MarketDepthDownloader | None = None,
        instrument_universe_downloader: InstrumentUniverseDownloader | None = None,
        dividend_bonus_downloader: DividendBonusDownloader | None = None,
        rights_allotment_downloader: RightsAllotmentDownloader | None = None,
    ) -> None:
        self._downloader = downloader or self._download
        self._market_depth_downloader = market_depth_downloader or self._download_market_depth
        self._instrument_universe_downloader = (
            instrument_universe_downloader or self._download_instrument_universe
        )
        self._dividend_bonus_downloader = dividend_bonus_downloader or self._download_dividend_bonus
        self._rights_allotment_downloader = (
            rights_allotment_downloader or self._download_rights_allotment
        )

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

    def fetch_instrument_universe(self, market: str) -> ProviderInstrumentUniverseSnapshot:
        normalized_market = market.strip().upper()
        source = "akshare.stock_info_a_code_name"
        if normalized_market != "CN":
            return ProviderInstrumentUniverseSnapshot(
                provider="akshare",
                source=source,
                as_of=datetime.now(timezone.utc),
                status="unavailable",
                availability={
                    "status": "unavailable",
                    "reason": f"AkShare A-share universe does not support market {normalized_market or '<empty>'}.",
                },
                diagnostics=[
                    {
                        "code": "INSTRUMENT_UNIVERSE_MARKET_UNSUPPORTED",
                        "message": "Only the CN A-share universe is supported by this provider path.",
                    }
                ],
            )

        frame = self._instrument_universe_downloader()
        return _normalize_a_share_universe_frame(frame, source=source)

    def fetch_corporate_actions(
        self,
        event_type: str,
        report_period: date,
        symbols: list[str],
    ) -> ProviderCorporateActionSnapshot:
        normalized_event_type = event_type.strip().lower()
        normalized_symbols = sorted(
            {symbol.strip().upper() for symbol in symbols if symbol.strip()}
        )
        if normalized_event_type == "dividend_bonus":
            source = "akshare.stock_fhps_em"
            frame = self._dividend_bonus_downloader(report_period.strftime("%Y%m%d"))
            return _normalize_dividend_bonus_frame(
                frame,
                report_period=report_period,
                symbols=normalized_symbols,
                source=source,
            )
        if normalized_event_type == "rights_allotment":
            return self._fetch_rights_allotment_actions(report_period, normalized_symbols)
        raise ValueError(f"Unsupported AkShare corporate action event type: {event_type}")

    def _fetch_rights_allotment_actions(
        self,
        report_period: date,
        symbols: list[str],
    ) -> ProviderCorporateActionSnapshot:
        source = "akshare.stock_allotment_cninfo"
        items: list[dict[str, object]] = []
        diagnostics: list[dict[str, object]] = []
        start_date = date(report_period.year, 1, 1).strftime("%Y%m%d")
        end_date = date(report_period.year, 12, 31).strftime("%Y%m%d")
        for symbol in symbols:
            try:
                frame = self._rights_allotment_downloader(symbol, start_date, end_date)
                items.extend(
                    _normalize_rights_allotment_frame(
                        frame,
                        report_period=report_period,
                        symbol=symbol,
                        source=source,
                    )
                )
            except Exception as exc:
                diagnostics.append(
                    {
                        "code": "RIGHTS_ALLOTMENT_SYMBOL_FAILED",
                        "message": "A symbol-level rights-allotment provider request failed.",
                        "details": {"symbol": symbol, "exception_type": type(exc).__name__},
                    }
                )
        status = "ok" if not diagnostics else ("degraded" if items else "unavailable")
        return ProviderCorporateActionSnapshot(
            provider="akshare",
            source=source,
            event_type="rights_allotment",
            report_period=report_period,
            as_of=datetime.now(timezone.utc),
            status=status,
            items=items,
            availability={
                "status": status,
                "row_count": len(items),
                "requested_symbol_count": len(symbols),
            },
            diagnostics=diagnostics,
        )

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
        except ImportError as exc:
            raise RuntimeError("AkShare dependency is unavailable.") from exc

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

    @staticmethod
    def _download_instrument_universe() -> pd.DataFrame:
        import akshare as ak

        frame = ak.stock_info_a_code_name()
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _download_dividend_bonus(report_period: str) -> pd.DataFrame:
        import akshare as ak

        frame = ak.stock_fhps_em(date=report_period)
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    def _download_rights_allotment(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        import akshare as ak

        frame = ak.stock_allotment_cninfo(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        return frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()


def _normalize_a_share_universe_frame(
    frame: pd.DataFrame | None,
    *,
    source: str,
) -> ProviderInstrumentUniverseSnapshot:
    now = datetime.now(timezone.utc)
    if frame is None or frame.empty:
        return ProviderInstrumentUniverseSnapshot(
            provider="akshare",
            source=source,
            as_of=now,
            status="unavailable",
            availability={
                "status": "unavailable",
                "reason": "AkShare returned an empty A-share universe payload.",
            },
            diagnostics=[
                {
                    "code": "INSTRUMENT_UNIVERSE_EMPTY",
                    "message": "The provider returned no A-share instrument rows.",
                }
            ],
        )

    instruments_by_symbol: dict[str, ProviderInstrument] = {}
    skipped_count = 0
    duplicate_count = 0
    for _, row in frame.iterrows():
        raw_symbol = _first_row_value(
            row,
            ["code", "symbol", "证券代码", "股票代码", "品种代码"],
        )
        raw_name = _first_row_value(
            row,
            ["name", "证券简称", "股票简称", "品种名称"],
        )
        symbol = str(raw_symbol).strip().zfill(6) if raw_symbol is not None else ""
        name = str(raw_name).strip() if raw_name is not None else ""
        exchange = _a_share_exchange(symbol)
        if len(symbol) != 6 or not symbol.isdigit() or not name or exchange is None:
            skipped_count += 1
            continue
        if symbol in instruments_by_symbol:
            duplicate_count += 1
        instruments_by_symbol[symbol] = ProviderInstrument(
            symbol=symbol,
            name=name,
            market="CN",
            exchange=exchange,
            asset_type="stock",
            currency="CNY",
        )

    items = [instruments_by_symbol[symbol] for symbol in sorted(instruments_by_symbol)]
    if not items:
        return ProviderInstrumentUniverseSnapshot(
            provider="akshare",
            source=source,
            as_of=now,
            status="unavailable",
            availability={
                "status": "unavailable",
                "reason": "AkShare A-share rows could not be normalized.",
            },
            diagnostics=[
                {
                    "code": "INSTRUMENT_UNIVERSE_SCHEMA_UNSUPPORTED",
                    "message": "No provider rows contained a supported symbol, name, and exchange identity.",
                }
            ],
        )

    diagnostics: list[dict[str, object]] = []
    if skipped_count:
        diagnostics.append(
            {
                "code": "INSTRUMENT_UNIVERSE_ROWS_SKIPPED",
                "message": "Some A-share universe rows were skipped because required identity fields were invalid.",
                "details": {"skipped_count": skipped_count},
            }
        )
    if duplicate_count:
        diagnostics.append(
            {
                "code": "INSTRUMENT_UNIVERSE_DUPLICATES_DEDUPED",
                "message": "Duplicate provider symbols were deterministically de-duplicated.",
                "details": {"duplicate_count": duplicate_count},
            }
        )

    is_complete = skipped_count == 0
    return ProviderInstrumentUniverseSnapshot(
        provider="akshare",
        source=source,
        as_of=now,
        status="ok" if is_complete else "degraded",
        items=items,
        is_complete=is_complete,
        availability={
            "status": "ok" if is_complete else "degraded",
            "reason": None if is_complete else "Some provider rows were skipped during normalization.",
            "row_count": len(items),
        },
        diagnostics=diagnostics,
    )


def _a_share_exchange(symbol: str) -> str | None:
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        return None
    if symbol.startswith("6"):
        return "SSE"
    if symbol.startswith(("0", "3")):
        return "SZSE"
    if symbol.startswith(("4", "8", "92")):
        return "BSE"
    return None


def _normalize_dividend_bonus_frame(
    frame: pd.DataFrame | None,
    *,
    report_period: date,
    symbols: list[str],
    source: str,
) -> ProviderCorporateActionSnapshot:
    requested_symbols = set(symbols)
    items: list[dict[str, object]] = []
    skipped_count = 0
    if frame is not None and not frame.empty:
        for _, row in frame.iterrows():
            symbol = _normalize_stock_symbol(
                _first_row_value(row, ["code", "symbol", "代码", "证券代码", "股票代码"])
            )
            if not symbol or (requested_symbols and symbol not in requested_symbols):
                continue
            name = _text_or_none(_first_row_value(row, ["name", "名称", "证券简称", "股票简称"]))
            if not name:
                skipped_count += 1
                continue
            announcement_date = _date_text(
                _first_row_value(row, ["announcement_date", "预案公告日", "最新公告日期", "公告日期"])
            )
            record_date = _date_text(
                _first_row_value(row, ["record_date", "股权登记日", "权益登记日"])
            )
            ex_date = _date_text(
                _first_row_value(row, ["ex_date", "除权除息日", "除权日", "除息日"])
            )
            items.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "market": "CN",
                    "report_period": report_period.isoformat(),
                    "trade_date": ex_date or announcement_date or report_period.isoformat(),
                    "announcement_date": announcement_date,
                    "record_date": record_date,
                    "ex_date": ex_date,
                    "cash_dividend_per_10": _float_from_row(
                        row,
                        ["cash_dividend_per_10", "现金分红-现金分红比例", "派息比例", "派息"],
                    ),
                    "bonus_shares_per_10": _float_from_row(
                        row,
                        ["bonus_shares_per_10", "送转股份-送股比例", "送股比例", "送股"],
                    ),
                    "transfer_shares_per_10": _float_from_row(
                        row,
                        ["transfer_shares_per_10", "送转股份-转股比例", "转股比例", "转增"],
                    ),
                    "action_status": _text_or_none(
                        _first_row_value(row, ["action_status", "方案进度", "实施进度"])
                    ),
                    "provider": "akshare",
                    "source": source,
                }
            )
    diagnostics = []
    if skipped_count:
        diagnostics.append(
            {
                "code": "DIVIDEND_BONUS_ROWS_SKIPPED",
                "message": "Dividend/bonus rows with incomplete instrument identity were skipped.",
                "details": {"skipped_count": skipped_count},
            }
        )
    status = "degraded" if skipped_count else "ok"
    return ProviderCorporateActionSnapshot(
        provider="akshare",
        source=source,
        event_type="dividend_bonus",
        report_period=report_period,
        as_of=datetime.now(timezone.utc),
        status=status,
        items=items,
        availability={
            "status": status if items else "no_data",
            "row_count": len(items),
            "requested_symbol_count": len(symbols),
        },
        diagnostics=diagnostics,
    )


def _normalize_rights_allotment_frame(
    frame: pd.DataFrame | None,
    *,
    report_period: date,
    symbol: str,
    source: str,
) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return []
    items: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        row_symbol = _normalize_stock_symbol(
            _first_row_value(row, ["symbol", "code", "证券代码", "股票代码"])
        ) or symbol
        announcement_date = _date_text(
            _first_row_value(row, ["announcement_date", "公告日期", "最新公告日"])
        )
        payment_start_date = _date_text(
            _first_row_value(row, ["payment_start_date", "配股缴款起始日", "缴款起始日"])
        )
        payment_end_date = _date_text(
            _first_row_value(row, ["payment_end_date", "配股缴款截止日", "缴款截止日"])
        )
        items.append(
            {
                "symbol": row_symbol,
                "name": _text_or_none(
                    _first_row_value(row, ["name", "证券简称", "股票简称", "配股简称"])
                ) or row_symbol,
                "market": "CN",
                "report_period": report_period.isoformat(),
                "trade_date": announcement_date or payment_start_date or report_period.isoformat(),
                "announcement_date": announcement_date,
                "payment_start_date": payment_start_date,
                "payment_end_date": payment_end_date,
                "rights_code": _text_or_none(
                    _first_row_value(row, ["rights_code", "配股代码"])
                ),
                "rights_name": _text_or_none(
                    _first_row_value(row, ["rights_name", "配股简称"])
                ),
                "rights_ratio": _float_from_row(
                    row,
                    ["rights_ratio", "配股比例", "实际配股比例"],
                ),
                "rights_price": _float_from_row(row, ["rights_price", "配股价格"]),
                "actual_allotment_shares": _float_from_row(
                    row,
                    ["actual_allotment_shares", "实际配股数量"],
                ),
                "provider": "akshare",
                "source": source,
            }
        )
    return items


def _normalize_stock_symbol(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    symbol = text.zfill(6)
    return symbol if len(symbol) == 6 and symbol.isdigit() else None


def _text_or_none(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _date_text(value: object) -> str | None:
    parsed = _datetime_or_none(value)
    return parsed.date().isoformat() if parsed is not None else None


def _float_from_row(row: pd.Series, candidate_columns: list[str]) -> float | None:
    value = _decimal_from_row(row, candidate_columns)
    return float(value) if value is not None else None


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
