from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol


DEFAULT_MARKET_DAILY_DATA_PROVIDER = "akshare"
DEFAULT_MARKET_DAILY_MARKET = "CN"
DEFAULT_STOCK_FUND_FLOW_WINDOW = "today"
SUPPORTED_MARKETS = {"CN"}
SUPPORTED_STOCK_FUND_FLOW_WINDOWS = {"today", "3d", "5d", "10d"}

AKSHARE_STOCK_FUND_FLOW_WINDOWS = {
    "today": "\u4eca\u65e5",
    "3d": "3\u65e5",
    "5d": "5\u65e5",
    "10d": "10\u65e5",
}

CN_CODE = "\u4ee3\u7801"
CN_NAME = "\u540d\u79f0"
CN_LATEST_PRICE = "\u6700\u65b0\u4ef7"
CN_CHANGE_PERCENT = "\u6da8\u8dcc\u5e45"
CN_MAIN_FORCE = "\u4e3b\u529b"
CN_NET_INFLOW = "\u51c0\u6d41\u5165"
CN_AMOUNT = "\u989d"
CN_SUPER_LARGE_ORDER = "\u8d85\u5927\u5355"
CN_LARGE_ORDER = "\u5927\u5355"
CN_MEDIUM_ORDER = "\u4e2d\u5355"
CN_SMALL_ORDER = "\u5c0f\u5355"
CN_REASON = "\u539f\u56e0"
CN_REASON_DETAIL = "\u8be6\u56e0"
CN_THEME = "\u9898\u6750"
CN_INDUSTRY = "\u884c\u4e1a"
CN_SECTOR = "\u6240\u5c5e\u884c\u4e1a"
CN_FIRST_LIMIT_UP_TIME = "\u9996\u6b21\u5c01\u677f\u65f6\u95f4"
CN_LAST_LIMIT_UP_TIME = "\u6700\u540e\u5c01\u677f\u65f6\u95f4"
CN_TURNOVER_RATE = "\u6362\u624b\u7387"
CN_TOTAL_MARKET_CAP = "\u603b\u5e02\u503c"
CN_FREE_MARKET_CAP = "\u6d41\u901a\u5e02\u503c"
CN_LIMIT_UP_STATS = "\u6da8\u505c\u7edf\u8ba1"
CN_CONSECUTIVE_LIMIT_UP = "\u8fde\u677f\u6570"


@dataclass(frozen=True)
class StockFundFlowProviderItem:
    symbol: str | None = None
    name: str | None = None
    latest_price: float | None = None
    change_percent: float | None = None
    net_flow_amount: float | None = None
    main_net_flow_amount: float | None = None
    super_large_net_flow_amount: float | None = None
    large_net_flow_amount: float | None = None
    medium_net_flow_amount: float | None = None
    small_net_flow_amount: float | None = None
    currency: str = "CNY"
    unit: str = "yuan"
    flow_window: str = DEFAULT_STOCK_FUND_FLOW_WINDOW
    provider: str | None = None
    source: str | None = None

    def to_payload(self, rank: int, fallback_provider: str, fallback_source: str) -> dict[str, object]:
        main_net_flow_amount = self.main_net_flow_amount
        return {
            "symbol": self.symbol,
            "name": self.name,
            "rank": rank,
            "latest_price": self.latest_price,
            "change_percent": self.change_percent,
            "net_flow_amount": self.net_flow_amount
            if self.net_flow_amount is not None
            else main_net_flow_amount,
            "main_net_flow_amount": main_net_flow_amount,
            "super_large_net_flow_amount": self.super_large_net_flow_amount,
            "large_net_flow_amount": self.large_net_flow_amount,
            "medium_net_flow_amount": self.medium_net_flow_amount,
            "small_net_flow_amount": self.small_net_flow_amount,
            "currency": self.currency,
            "unit": self.unit,
            "flow_window": self.flow_window,
            "provider": self.provider or fallback_provider,
            "source": self.source or fallback_source,
        }


@dataclass(frozen=True)
class LimitUpReasonProviderItem:
    symbol: str | None = None
    name: str | None = None
    trade_date: str | None = None
    latest_price: float | None = None
    change_percent: float | None = None
    reason: str | None = None
    detail: str | None = None
    sector: str | None = None
    limit_up_count: int | None = None
    consecutive_limit_up_count: int | None = None
    first_limit_up_time: str | None = None
    last_limit_up_time: str | None = None
    turnover_rate: float | None = None
    market_cap: float | None = None
    provider: str | None = None
    source: str | None = None

    def to_payload(self, rank: int, fallback_provider: str, fallback_source: str) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "rank": rank,
            "trade_date": self.trade_date,
            "latest_price": self.latest_price,
            "change_percent": self.change_percent,
            "reason": self.reason,
            "detail": self.detail,
            "sector": self.sector,
            "limit_up_count": self.limit_up_count,
            "consecutive_limit_up_count": self.consecutive_limit_up_count,
            "first_limit_up_time": self.first_limit_up_time,
            "last_limit_up_time": self.last_limit_up_time,
            "turnover_rate": self.turnover_rate,
            "market_cap": self.market_cap,
            "provider": self.provider or fallback_provider,
            "source": self.source or fallback_source,
        }


MarketDailyProviderItem = StockFundFlowProviderItem | LimitUpReasonProviderItem


@dataclass(frozen=True)
class MarketDailyProviderResult:
    status: str
    data_mode: str
    source: str
    provider: str | None
    as_of: str | None
    market: str
    window: str
    message: str
    availability: dict[str, object]
    items: list[MarketDailyProviderItem]
    trade_date: str | None = None
    requested_provider: str | None = None
    effective_provider: str | None = None
    provider_capabilities: dict[str, object] = field(default_factory=dict)


class MarketDailyDataProvider(Protocol):
    provider_name: str

    def fetch_stock_fund_flow(self, *, limit: int, window: str) -> MarketDailyProviderResult:
        ...

    def fetch_limit_up_reasons(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        ...


class AkshareMarketDailyDataProvider:
    provider_name = DEFAULT_MARKET_DAILY_DATA_PROVIDER

    def fetch_stock_fund_flow(self, *, limit: int, window: str) -> MarketDailyProviderResult:
        try:
            import akshare as ak
        except ImportError:
            return _provider_unavailable_result(
                operation="stock_fund_flow",
                message="AkShare is not installed in this environment.",
                window=window,
            )

        stock_frame = ak.stock_individual_fund_flow_rank(
            indicator=AKSHARE_STOCK_FUND_FLOW_WINDOWS[window],
        )
        columns = [str(column) for column in getattr(stock_frame, "columns", [])]
        as_of = _utc_now_isoformat()
        items: list[MarketDailyProviderItem] = []
        for _, row in stock_frame.head(limit).iterrows():
            main_net_flow_amount = _safe_float(
                _row_value_from_candidates(
                    row,
                    columns,
                    [
                        _candidate("main_net_flow_amount"),
                        _candidate("fund_amount"),
                        _candidate(CN_MAIN_FORCE, CN_NET_INFLOW, CN_AMOUNT),
                    ],
                )
            )
            items.append(
                StockFundFlowProviderItem(
                    symbol=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("symbol"), _candidate("code"), _candidate(CN_CODE)],
                        )
                    ),
                    name=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("name"), _candidate(CN_NAME)],
                        )
                    ),
                    latest_price=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("latest_price"), _candidate("new_price"), _candidate(CN_LATEST_PRICE)],
                        )
                    ),
                    change_percent=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("change_percent"),
                                _candidate("change_rate"),
                                _candidate(CN_CHANGE_PERCENT),
                            ],
                        )
                    ),
                    net_flow_amount=main_net_flow_amount,
                    main_net_flow_amount=main_net_flow_amount,
                    super_large_net_flow_amount=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("super_large_net_flow_amount"),
                                _candidate(CN_SUPER_LARGE_ORDER, CN_NET_INFLOW, CN_AMOUNT),
                            ],
                        )
                    ),
                    large_net_flow_amount=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("large_net_flow_amount"),
                                _candidate(
                                    CN_LARGE_ORDER,
                                    CN_NET_INFLOW,
                                    CN_AMOUNT,
                                    excludes=(CN_SUPER_LARGE_ORDER,),
                                ),
                            ],
                        )
                    ),
                    medium_net_flow_amount=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("medium_net_flow_amount"),
                                _candidate(CN_MEDIUM_ORDER, CN_NET_INFLOW, CN_AMOUNT),
                            ],
                        )
                    ),
                    small_net_flow_amount=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("small_net_flow_amount"),
                                _candidate(CN_SMALL_ORDER, CN_NET_INFLOW, CN_AMOUNT),
                            ],
                        )
                    ),
                    flow_window=window,
                    provider=self.provider_name,
                    source="akshare_stock_individual_fund_flow_rank",
                )
            )

        return MarketDailyProviderResult(
            status="ok" if items else "degraded",
            data_mode="delayed" if items else "none",
            source="akshare_stock_individual_fund_flow_rank",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of=as_of if items else None,
            market=DEFAULT_MARKET_DAILY_MARKET,
            window=window,
            message="AkShare/Eastmoney stock fund-flow ranking. Rows are provider-backed research context only.",
            availability={
                "status": "delayed" if items else "no_data",
                "reason": None if items else "AkShare returned no stock fund-flow rows.",
                "ranking": "available" if items else "no_data",
                "fund_flow": "available" if items else "no_data",
                "price": "available" if items else "no_data",
            },
            provider_capabilities={
                "stock_fund_flow": {
                    "status": "delayed" if items else "unavailable",
                    "window": window,
                    "source": "akshare_stock_individual_fund_flow_rank",
                },
                "ranking": {"status": "delayed" if items else "unavailable"},
                "citation": {
                    "status": "not_citable",
                    "reason": "Live provider rows are not stored local evidence in this phase.",
                },
            },
            items=items,
        )

    def fetch_limit_up_reasons(
        self,
        *,
        trade_date: date,
        limit: int,
    ) -> MarketDailyProviderResult:
        try:
            import akshare as ak
        except ImportError:
            return _provider_unavailable_result(
                operation="limit_up_reasons",
                message="AkShare is not installed in this environment.",
                trade_date=trade_date.isoformat(),
            )

        if not hasattr(ak, "stock_zt_pool_em"):
            return _provider_unavailable_result(
                operation="limit_up_reasons",
                message="AkShare does not expose stock_zt_pool_em in this environment.",
                trade_date=trade_date.isoformat(),
            )

        limit_up_frame = ak.stock_zt_pool_em(date=trade_date.strftime("%Y%m%d"))
        columns = [str(column) for column in getattr(limit_up_frame, "columns", [])]
        as_of = _utc_now_isoformat()
        items: list[MarketDailyProviderItem] = []
        for _, row in limit_up_frame.head(limit).iterrows():
            reason = _safe_string(
                _row_value_from_candidates(
                    row,
                    columns,
                    [
                        _candidate("reason"),
                        _candidate("limit_up_reason"),
                        _candidate(CN_REASON),
                        _candidate(CN_THEME),
                    ],
                )
            )
            detail = _safe_string(
                _row_value_from_candidates(
                    row,
                    columns,
                    [_candidate("detail"), _candidate(CN_REASON_DETAIL)],
                )
            )
            items.append(
                LimitUpReasonProviderItem(
                    symbol=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("symbol"), _candidate("code"), _candidate(CN_CODE)],
                        )
                    ),
                    name=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("name"), _candidate(CN_NAME)],
                        )
                    ),
                    trade_date=trade_date.isoformat(),
                    latest_price=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("latest_price"), _candidate("new_price"), _candidate(CN_LATEST_PRICE)],
                        )
                    ),
                    change_percent=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("change_percent"),
                                _candidate("change_rate"),
                                _candidate(CN_CHANGE_PERCENT),
                            ],
                        )
                    ),
                    reason=reason,
                    detail=detail,
                    sector=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("sector"),
                                _candidate("industry"),
                                _candidate(CN_SECTOR),
                                _candidate(CN_INDUSTRY),
                            ],
                        )
                    ),
                    limit_up_count=_safe_int(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("limit_up_count"), _candidate(CN_LIMIT_UP_STATS)],
                        )
                    ),
                    consecutive_limit_up_count=_safe_int(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("consecutive_limit_up_count"), _candidate(CN_CONSECUTIVE_LIMIT_UP)],
                        )
                    ),
                    first_limit_up_time=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("first_limit_up_time"), _candidate(CN_FIRST_LIMIT_UP_TIME)],
                        )
                    ),
                    last_limit_up_time=_safe_string(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("last_limit_up_time"), _candidate(CN_LAST_LIMIT_UP_TIME)],
                        )
                    ),
                    turnover_rate=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [_candidate("turnover_rate"), _candidate(CN_TURNOVER_RATE)],
                        )
                    ),
                    market_cap=_safe_float(
                        _row_value_from_candidates(
                            row,
                            columns,
                            [
                                _candidate("market_cap"),
                                _candidate(CN_TOTAL_MARKET_CAP),
                                _candidate(CN_FREE_MARKET_CAP),
                            ],
                        )
                    ),
                    provider=self.provider_name,
                    source="akshare_stock_zt_pool_em",
                )
            )

        has_reason_fields = any(
            isinstance(item, LimitUpReasonProviderItem) and (item.reason or item.detail)
            for item in items
        )
        reason_message = None
        if items and not has_reason_fields:
            reason_message = (
                "AkShare returned limit-up pool rows but no reason/detail field; "
                "rows are shown as limit-up pool context only."
            )

        return MarketDailyProviderResult(
            status="ok" if items and has_reason_fields else "degraded",
            data_mode="delayed" if items else "none",
            source="akshare_stock_zt_pool_em",
            provider=self.provider_name,
            requested_provider=self.provider_name,
            effective_provider=self.provider_name,
            as_of=as_of if items else None,
            market=DEFAULT_MARKET_DAILY_MARKET,
            window="today",
            trade_date=trade_date.isoformat(),
            message=reason_message
            or "AkShare/Eastmoney limit-up pool rows. Reason fields are provider-dependent.",
            availability={
                "status": "delayed" if items else "no_data",
                "reason": reason_message
                or (None if items else "AkShare returned no limit-up rows for the requested date."),
                "limit_up_pool": "available" if items else "no_data",
                "reason_detail": "available" if has_reason_fields else "unavailable",
            },
            provider_capabilities={
                "limit_up_pool": {
                    "status": "delayed" if items else "unavailable",
                    "source": "akshare_stock_zt_pool_em",
                },
                "limit_up_reasons": {
                    "status": "delayed" if has_reason_fields else "unavailable",
                    "reason": reason_message,
                },
                "citation": {
                    "status": "not_citable",
                    "reason": "Live provider rows are not stored local evidence in this phase.",
                },
            },
            items=items,
        )


def get_stock_fund_flow_payload(
    *,
    market: str = DEFAULT_MARKET_DAILY_MARKET,
    window: str = DEFAULT_STOCK_FUND_FLOW_WINDOW,
    limit: int = 20,
    provider_name: str | None = None,
    provider: MarketDailyDataProvider | None = None,
) -> dict[str, object]:
    normalized_market = _normalize_market(market)
    normalized_window = _normalize_stock_fund_flow_window(window)
    requested_provider = _normalize_requested_provider(provider_name)
    if normalized_market is None:
        return build_unavailable_market_daily_data_payload(
            operation="stock_fund_flow",
            message=f"Market '{market}' is not supported for stock fund-flow ranking.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=str(market or "").strip().upper() or DEFAULT_MARKET_DAILY_MARKET,
            window=normalized_window or DEFAULT_STOCK_FUND_FLOW_WINDOW,
        )
    if normalized_window is None:
        return build_unavailable_market_daily_data_payload(
            operation="stock_fund_flow",
            message=f"Fund-flow window '{window}' is not supported. Use today, 3d, 5d, or 10d.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=normalized_market,
            window=str(window or "").strip().lower() or DEFAULT_STOCK_FUND_FLOW_WINDOW,
        )

    resolved_provider = provider or _resolve_market_daily_data_provider(requested_provider)
    if resolved_provider is None:
        return build_unavailable_market_daily_data_payload(
            operation="stock_fund_flow",
            message=f"Market daily-data provider '{requested_provider}' is not configured or verified.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=normalized_market,
            window=normalized_window,
        )

    try:
        result = resolved_provider.fetch_stock_fund_flow(
            limit=_normalize_limit(limit, default=20, maximum=100),
            window=normalized_window,
        )
    except Exception as error:
        return build_unavailable_market_daily_data_payload(
            operation="stock_fund_flow",
            message=f"Market daily-data provider '{resolved_provider.provider_name}' failed: {error.__class__.__name__}.",
            requested_provider=requested_provider,
            effective_provider=resolved_provider.provider_name,
            source="provider_error",
            market=normalized_market,
            window=normalized_window,
        )

    return _normalize_provider_result(
        operation="stock_fund_flow",
        result=result,
        requested_provider=requested_provider,
        limit=_normalize_limit(limit, default=20, maximum=100),
        market=normalized_market,
        window=normalized_window,
    )


def get_limit_up_reasons_payload(
    *,
    trade_date: str | date | None = None,
    market: str = DEFAULT_MARKET_DAILY_MARKET,
    limit: int = 50,
    provider_name: str | None = None,
    provider: MarketDailyDataProvider | None = None,
) -> dict[str, object]:
    normalized_market = _normalize_market(market)
    parsed_trade_date = _parse_trade_date(trade_date)
    requested_provider = _normalize_requested_provider(provider_name)
    trade_date_label = _trade_date_label(parsed_trade_date, trade_date)
    if normalized_market is None:
        return build_unavailable_market_daily_data_payload(
            operation="limit_up_reasons",
            message=f"Market '{market}' is not supported for limit-up reasons.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=str(market or "").strip().upper() or DEFAULT_MARKET_DAILY_MARKET,
            trade_date=trade_date_label,
        )
    if parsed_trade_date is None:
        return build_unavailable_market_daily_data_payload(
            operation="limit_up_reasons",
            message="Invalid trade date. Use YYYY-MM-DD or YYYYMMDD.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=normalized_market,
            trade_date=trade_date_label,
        )

    resolved_provider = provider or _resolve_market_daily_data_provider(requested_provider)
    if resolved_provider is None:
        return build_unavailable_market_daily_data_payload(
            operation="limit_up_reasons",
            message=f"Market daily-data provider '{requested_provider}' is not configured or verified.",
            requested_provider=requested_provider,
            effective_provider=requested_provider,
            market=normalized_market,
            trade_date=parsed_trade_date.isoformat(),
        )

    try:
        result = resolved_provider.fetch_limit_up_reasons(
            trade_date=parsed_trade_date,
            limit=_normalize_limit(limit, default=50, maximum=100),
        )
    except Exception as error:
        return build_unavailable_market_daily_data_payload(
            operation="limit_up_reasons",
            message=f"Market daily-data provider '{resolved_provider.provider_name}' failed: {error.__class__.__name__}.",
            requested_provider=requested_provider,
            effective_provider=resolved_provider.provider_name,
            source="provider_error",
            market=normalized_market,
            trade_date=parsed_trade_date.isoformat(),
        )

    return _normalize_provider_result(
        operation="limit_up_reasons",
        result=result,
        requested_provider=requested_provider,
        limit=_normalize_limit(limit, default=50, maximum=100),
        market=normalized_market,
        window="today",
        trade_date=parsed_trade_date.isoformat(),
    )


def build_unavailable_market_daily_data_payload(
    *,
    operation: str,
    message: str,
    requested_provider: str | None = None,
    effective_provider: str | None = None,
    source: str = "none",
    market: str = DEFAULT_MARKET_DAILY_MARKET,
    window: str = DEFAULT_STOCK_FUND_FLOW_WINDOW,
    trade_date: str | None = None,
) -> dict[str, object]:
    return {
        "status": "unavailable",
        "data_mode": "none",
        "source": source,
        "provider": effective_provider,
        "requested_provider": requested_provider or DEFAULT_MARKET_DAILY_DATA_PROVIDER,
        "effective_provider": effective_provider or "none",
        "as_of": None,
        "generated_at": _utc_now_isoformat(),
        "market": market,
        "window": window,
        "trade_date": trade_date,
        "availability": {
            "status": "unavailable",
            "reason": message,
        },
        "provider_capabilities": _build_unavailable_provider_capabilities(operation, message),
        "message": message,
        "count": 0,
        "items": [],
    }


def _normalize_provider_result(
    *,
    operation: str,
    result: MarketDailyProviderResult,
    requested_provider: str,
    limit: int,
    market: str,
    window: str,
    trade_date: str | None = None,
) -> dict[str, object]:
    effective_provider = result.effective_provider or result.provider or DEFAULT_MARKET_DAILY_DATA_PROVIDER
    items = result.items[:limit]
    if not items:
        status = "unavailable" if result.status == "unavailable" else "degraded"
        message = result.message or f"No {operation.replace('_', ' ')} rows are available."
        availability_status = "unavailable" if status == "unavailable" else "no_data"
        return {
            "status": status,
            "data_mode": "none",
            "source": result.source,
            "provider": result.provider,
            "requested_provider": requested_provider,
            "effective_provider": effective_provider,
            "as_of": None,
            "generated_at": _utc_now_isoformat(),
            "market": result.market or market,
            "window": result.window or window,
            "trade_date": result.trade_date or trade_date,
            "availability": {
                **result.availability,
                "status": availability_status,
                "reason": message,
            },
            "provider_capabilities": result.provider_capabilities
            or _build_unavailable_provider_capabilities(operation, message),
            "message": message,
            "count": 0,
            "items": [],
        }

    return {
        "status": result.status,
        "data_mode": result.data_mode,
        "source": result.source,
        "provider": result.provider,
        "requested_provider": requested_provider,
        "effective_provider": effective_provider,
        "as_of": result.as_of,
        "generated_at": _utc_now_isoformat(),
        "market": result.market or market,
        "window": result.window or window,
        "trade_date": result.trade_date or trade_date,
        "availability": result.availability,
        "provider_capabilities": result.provider_capabilities
        or _build_available_provider_capabilities(operation, result),
        "message": result.message,
        "count": len(items),
        "items": [
            item.to_payload(
                rank=index + 1,
                fallback_provider=effective_provider,
                fallback_source=result.source,
            )
            for index, item in enumerate(items)
        ],
    }


def _provider_unavailable_result(
    *,
    operation: str,
    message: str,
    window: str = DEFAULT_STOCK_FUND_FLOW_WINDOW,
    trade_date: str | None = None,
) -> MarketDailyProviderResult:
    return MarketDailyProviderResult(
        status="unavailable",
        data_mode="none",
        source="none",
        provider=DEFAULT_MARKET_DAILY_DATA_PROVIDER,
        requested_provider=DEFAULT_MARKET_DAILY_DATA_PROVIDER,
        effective_provider=DEFAULT_MARKET_DAILY_DATA_PROVIDER,
        as_of=None,
        market=DEFAULT_MARKET_DAILY_MARKET,
        window=window,
        trade_date=trade_date,
        message=message,
        availability={"status": "unavailable", "reason": message},
        provider_capabilities=_build_unavailable_provider_capabilities(operation, message),
        items=[],
    )


def _resolve_market_daily_data_provider(provider_name: str) -> MarketDailyDataProvider | None:
    if provider_name == DEFAULT_MARKET_DAILY_DATA_PROVIDER:
        return AkshareMarketDailyDataProvider()
    return None


def _normalize_requested_provider(provider_name: str | None) -> str:
    normalized_provider = (provider_name or DEFAULT_MARKET_DAILY_DATA_PROVIDER).strip().lower()
    return normalized_provider or DEFAULT_MARKET_DAILY_DATA_PROVIDER


def _normalize_market(market: str | None) -> str | None:
    normalized_market = (market or DEFAULT_MARKET_DAILY_MARKET).strip().upper()
    if normalized_market in SUPPORTED_MARKETS:
        return normalized_market
    return None


def _normalize_stock_fund_flow_window(window: str | None) -> str | None:
    normalized_window = (window or DEFAULT_STOCK_FUND_FLOW_WINDOW).strip().lower()
    if normalized_window in SUPPORTED_STOCK_FUND_FLOW_WINDOWS:
        return normalized_window
    return None


def _normalize_limit(limit: int, *, default: int, maximum: int) -> int:
    try:
        parsed_limit = int(limit)
    except (TypeError, ValueError):
        return default
    return min(max(parsed_limit, 1), maximum)


def _parse_trade_date(value: str | date | None) -> date | None:
    if isinstance(value, date):
        return value
    if value is None or str(value).strip() == "":
        return date.today()

    raw_value = str(value).strip()
    formats = ("%Y-%m-%d", "%Y%m%d")
    for date_format in formats:
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue
    return None


def _trade_date_label(parsed_trade_date: date | None, raw_value: str | date | None) -> str | None:
    if parsed_trade_date is not None:
        return parsed_trade_date.isoformat()
    if raw_value is None:
        return None
    return str(raw_value)


def _candidate(
    *substrings: str,
    excludes: tuple[str, ...] = (),
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return tuple(substrings), excludes


def _row_value_from_candidates(
    row: object,
    columns: list[str],
    candidates: list[tuple[tuple[str, ...], tuple[str, ...]]],
) -> object | None:
    for substrings, excludes in candidates:
        value = _row_value(row, columns, *substrings, excludes=excludes)
        if value is not None:
            return value
    return None


def _row_value(
    row: object,
    columns: list[str],
    *substrings: str,
    excludes: tuple[str, ...] = (),
) -> object | None:
    column = _find_column(columns, *substrings, excludes=excludes)
    if column is None:
        return None
    try:
        return row[column]
    except Exception:
        return None


def _find_column(
    columns: list[str],
    *substrings: str,
    excludes: tuple[str, ...] = (),
) -> str | None:
    for column in columns:
        normalized_column = column.lower()
        if all(substring.lower() in normalized_column for substring in substrings) and not any(
            excluded.lower() in normalized_column for excluded in excludes
        ):
            return column
    return None


def _safe_string(value: object) -> str | None:
    if value is None:
        return None
    normalized_value = str(value).strip()
    if normalized_value in {"", "-", "nan", "None"}:
        return None
    return normalized_value


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        parsed_value = float(value)
    except (TypeError, ValueError):
        return None
    if parsed_value != parsed_value:
        return None
    return parsed_value


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and "/" in value:
        value = value.split("/", 1)[0]
    try:
        parsed_value = int(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed_value


def _build_unavailable_provider_capabilities(operation: str, reason: str) -> dict[str, object]:
    if operation == "stock_fund_flow":
        return {
            "stock_fund_flow": {"status": "unavailable", "reason": reason},
            "ranking": {"status": "unavailable", "reason": reason},
            "citation": {"status": "not_citable", "reason": "No stored evidence is emitted."},
        }
    return {
        "limit_up_pool": {"status": "unavailable", "reason": reason},
        "limit_up_reasons": {"status": "unavailable", "reason": reason},
        "citation": {"status": "not_citable", "reason": "No stored evidence is emitted."},
    }


def _build_available_provider_capabilities(
    operation: str,
    result: MarketDailyProviderResult,
) -> dict[str, object]:
    capability_status = "delayed" if result.data_mode == "delayed" else result.status
    if operation == "stock_fund_flow":
        return {
            "stock_fund_flow": {"status": capability_status, "source": result.source},
            "ranking": {"status": capability_status},
            "citation": {
                "status": "not_citable",
                "reason": "Live provider rows are not stored local evidence in this phase.",
            },
        }
    return {
        "limit_up_pool": {"status": capability_status, "source": result.source},
        "limit_up_reasons": {"status": capability_status},
        "citation": {
            "status": "not_citable",
            "reason": "Live provider rows are not stored local evidence in this phase.",
        },
    }


def _utc_now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()
