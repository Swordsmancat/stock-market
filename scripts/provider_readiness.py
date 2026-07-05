"""Smoke-check market data providers without writing to the database."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Protocol, TextIO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.providers.akshare_provider import AkShareProvider  # noqa: E402
from packages.providers.base import ProviderBar  # noqa: E402
from packages.providers.base import ProviderInstrument  # noqa: E402
from packages.providers.base import ProviderIntradayBar  # noqa: E402
from packages.providers.base import ProviderMarketDepthSnapshot  # noqa: E402
from packages.providers.mock_provider import MockProvider  # noqa: E402
from packages.providers.yfinance_provider import YFinanceProvider  # noqa: E402


DEFAULT_PROVIDER = "mock"
DEFAULT_MARKET = "US"
DEFAULT_TIMEFRAME = "1d"
DEFAULT_INTRADAY_TIMEFRAME = "1m"
DEFAULT_INTRADAY_LOOKBACK_DAYS = 5
DEFAULT_DEPTH_LEVELS = 5
LOOKBACK_DAYS = 10
NETWORK_OPT_IN_PROVIDERS = {"akshare", "yfinance"}


class ReadinessStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class ProviderReadinessResult:
    status: ReadinessStatus
    name: str
    message: str
    details: list[str]
    suggestions: list[str]


class Provider(Protocol):
    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]: ...

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
    ) -> list[ProviderBar]: ...


class MarketDepthProvider(Provider, Protocol):
    def fetch_market_depth(
        self,
        symbol: str,
        depth_levels: int,
    ) -> ProviderMarketDepthSnapshot: ...


class IntradayProvider(Provider, Protocol):
    def fetch_intraday_bars(
        self,
        symbol: str,
        trade_date: date,
        timeframe: str,
    ) -> list[ProviderIntradayBar]: ...


ProviderFactory = Callable[[], Provider]


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "akshare": AkShareProvider,
    "mock": MockProvider,
    "yfinance": YFinanceProvider,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-check a market data provider without database writes.",
    )
    parser.add_argument(
        "--provider",
        default=DEFAULT_PROVIDER,
        help=f"Provider to check. Defaults to {DEFAULT_PROVIDER!r}.",
    )
    parser.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        help=f"Market used when selecting a default instrument. Defaults to {DEFAULT_MARKET!r}.",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Symbol to fetch. Defaults to the provider's first instrument for the market.",
    )
    parser.add_argument(
        "--real-network",
        action="store_true",
        help="Opt in to real network access for live providers such as yfinance.",
    )
    parser.add_argument(
        "--check-depth",
        action="store_true",
        help="Smoke-check explicit market-depth support instead of daily bars.",
    )
    parser.add_argument(
        "--check-intraday",
        action="store_true",
        help="Smoke-check explicit intraday minute-bar support instead of daily bars.",
    )
    parser.add_argument(
        "--trade-date",
        type=parse_trade_date,
        default=None,
        help="Trade date for --check-intraday in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--intraday-lookback-days",
        type=int,
        default=DEFAULT_INTRADAY_LOOKBACK_DAYS,
        help=(
            "Number of recent weekdays to try for --check-intraday when --trade-date is not "
            f"provided. Defaults to {DEFAULT_INTRADAY_LOOKBACK_DAYS}."
        ),
    )
    parser.add_argument(
        "--depth-levels",
        type=int,
        default=DEFAULT_DEPTH_LEVELS,
        help=f"Order-book depth levels for --check-depth. Defaults to {DEFAULT_DEPTH_LEVELS}.",
    )
    return parser


def check_provider_readiness(
    provider_name: str,
    market: str,
    symbol: str | None,
    real_network: bool,
    check_depth: bool = False,
    check_intraday: bool = False,
    trade_date: date | None = None,
    intraday_lookback_days: int = DEFAULT_INTRADAY_LOOKBACK_DAYS,
    depth_levels: int = DEFAULT_DEPTH_LEVELS,
) -> list[ProviderReadinessResult]:
    normalized_provider_name = provider_name.strip().lower()
    normalized_market = market.strip().upper()
    normalized_symbol = symbol.strip().upper() if symbol is not None and symbol.strip() else None

    if normalized_provider_name not in PROVIDER_FACTORIES:
        supported_providers = ", ".join(sorted(PROVIDER_FACTORIES))
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"unknown provider: {provider_name}",
                details=[f"Supported providers: {supported_providers}."],
                suggestions=[f"Use one of: {supported_providers}."],
            )
        ]

    if normalized_provider_name in NETWORK_OPT_IN_PROVIDERS and not real_network:
        check_label = _readiness_check_label(check_depth=check_depth, check_intraday=check_intraday)
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.WARN,
                name="provider readiness",
                message=f"{normalized_provider_name} {check_label} readiness requires explicit real-network opt-in.",
                details=[
                    f"Skipped live {normalized_provider_name} fetch because --real-network was not provided.",
                    "This smoke check is non-destructive and performs no database writes.",
                ],
                suggestions=[
                    _provider_network_opt_in_suggestion(
                        normalized_provider_name,
                        normalized_market,
                        normalized_symbol,
                        check_depth,
                        check_intraday,
                        trade_date,
                        intraday_lookback_days,
                        depth_levels,
                    )
                ],
            )
        ]

    try:
        provider = PROVIDER_FACTORIES[normalized_provider_name]()
    except Exception as exc:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"failed to create provider {normalized_provider_name}: {exc}",
                details=[type(exc).__name__],
                suggestions=["Check provider dependencies and local environment configuration."],
            )
        ]

    selected_symbol = normalized_symbol
    if selected_symbol is None:
        symbol_result = select_default_symbol(provider, normalized_market, normalized_provider_name)
        if isinstance(symbol_result, ProviderReadinessResult):
            return [symbol_result]
        selected_symbol = symbol_result

    if check_depth:
        return [
            check_market_depth_readiness(
                provider=provider,
                provider_name=normalized_provider_name,
                market=normalized_market,
                symbol=selected_symbol,
                depth_levels=depth_levels,
            )
        ]

    if check_intraday:
        if trade_date is None:
            return [
                check_intraday_readiness_window(
                    provider=provider,
                    provider_name=normalized_provider_name,
                    market=normalized_market,
                    symbol=selected_symbol,
                    lookback_days=intraday_lookback_days,
                )
            ]
        return [
            check_intraday_readiness(
                provider=provider,
                provider_name=normalized_provider_name,
                market=normalized_market,
                symbol=selected_symbol,
                trade_date=trade_date,
            )
        ]

    end_date = date.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)

    try:
        bars = provider.fetch_bars(selected_symbol, DEFAULT_TIMEFRAME, start_date, end_date)
    except Exception as exc:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"{normalized_provider_name} failed to fetch bars for {selected_symbol}: {exc}",
                details=[
                    f"provider={normalized_provider_name}",
                    f"market={normalized_market}",
                    f"symbol={selected_symbol}",
                    f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                    type(exc).__name__,
                ],
                suggestions=["Verify provider credentials, dependencies, and symbol mapping."],
            )
        ]

    if not bars:
        return [
            ProviderReadinessResult(
                status=ReadinessStatus.FAIL,
                name="provider readiness",
                message=f"{normalized_provider_name} returned no bars for {selected_symbol}.",
                details=[
                    f"provider={normalized_provider_name}",
                    f"market={normalized_market}",
                    f"symbol={selected_symbol}",
                    f"timeframe={DEFAULT_TIMEFRAME}",
                    f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                ],
                suggestions=["Try an explicit --symbol or a wider provider-specific smoke later."],
            )
        ]

    return [
        ProviderReadinessResult(
            status=ReadinessStatus.OK,
            name="provider readiness",
            message=f"{normalized_provider_name} returned {len(bars)} bars for {selected_symbol}.",
            details=[
                f"provider={normalized_provider_name}",
                f"market={normalized_market}",
                f"symbol={selected_symbol}",
                f"timeframe={DEFAULT_TIMEFRAME}",
                f"date_range={start_date.isoformat()}..{end_date.isoformat()}",
                "database_writes=none",
            ],
            suggestions=[],
        )
    ]


def check_intraday_readiness_window(
    *,
    provider: Provider,
    provider_name: str,
    market: str,
    symbol: str,
    lookback_days: int,
) -> ProviderReadinessResult:
    fetch_intraday_bars = getattr(provider, "fetch_intraday_bars", None)
    if not callable(fetch_intraday_bars):
        return ProviderReadinessResult(
            status=ReadinessStatus.WARN,
            name="provider intraday readiness",
            message=f"{provider_name} does not expose explicit fetch_intraday_bars support.",
            details=[f"provider={provider_name}", f"market={market}", f"symbol={symbol}"],
            suggestions=["Do not infer intraday minutes from daily bars; add an explicit provider method first."],
        )

    attempted_dates = iter_recent_weekday_dates(lookback_days=lookback_days)
    failures: list[str] = []
    for attempted_trade_date in attempted_dates:
        if is_known_intraday_market_holiday(provider_name, symbol, attempted_trade_date):
            continue

        try:
            bars = fetch_intraday_bars(symbol, attempted_trade_date, DEFAULT_INTRADAY_TIMEFRAME)
        except Exception as exc:
            failures.append(f"{attempted_trade_date.isoformat()}:{type(exc).__name__}")
            continue

        if bars:
            return ProviderReadinessResult(
                status=ReadinessStatus.OK,
                name="provider intraday readiness",
                message=(
                    f"{provider_name} returned {len(bars)} verified intraday bars for "
                    f"{symbol} on {attempted_trade_date.isoformat()}."
                ),
                details=[
                    f"provider={provider_name}",
                    f"market={market}",
                    f"symbol={symbol}",
                    f"trade_date={attempted_trade_date.isoformat()}",
                    f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
                    f"bars={len(bars)}",
                    f"attempted_dates={','.join(date_value.isoformat() for date_value in attempted_dates)}",
                    "database_writes=none",
                ],
                suggestions=[],
            )

    return ProviderReadinessResult(
        status=ReadinessStatus.FAIL,
        name="provider intraday readiness",
        message=f"{provider_name} returned no verified intraday bars for {symbol}.",
        details=[
            f"provider={provider_name}",
            f"market={market}",
            f"symbol={symbol}",
            f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
            f"attempted_dates={','.join(date_value.isoformat() for date_value in attempted_dates)}",
            f"failures={','.join(failures) if failures else 'none'}",
            "database_writes=none",
        ],
        suggestions=["Try an explicit --trade-date, verify retention windows, or run provider-specific diagnostics."],
    )


def check_intraday_readiness(
    *,
    provider: Provider,
    provider_name: str,
    market: str,
    symbol: str,
    trade_date: date,
) -> ProviderReadinessResult:
    fetch_intraday_bars = getattr(provider, "fetch_intraday_bars", None)
    if not callable(fetch_intraday_bars):
        return ProviderReadinessResult(
            status=ReadinessStatus.WARN,
            name="provider intraday readiness",
            message=f"{provider_name} does not expose explicit fetch_intraday_bars support.",
            details=[f"provider={provider_name}", f"market={market}", f"symbol={symbol}"],
            suggestions=["Do not infer intraday minutes from daily bars; add an explicit provider method first."],
        )

    if is_future_trade_date(trade_date):
        return ProviderReadinessResult(
            status=ReadinessStatus.WARN,
            name="provider intraday readiness",
            message=f"{provider_name} intraday readiness skipped future trade date for {symbol}.",
            details=[
                f"provider={provider_name}",
                f"market={market}",
                f"symbol={symbol}",
                f"trade_date={trade_date.isoformat()}",
                f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
                "reason=future_trade_date",
                "database_writes=none",
            ],
            suggestions=["Use a completed trading date or omit --trade-date to try the recent-weekday lookback window."],
        )

    if is_known_intraday_market_holiday(provider_name, symbol, trade_date):
        return ProviderReadinessResult(
            status=ReadinessStatus.WARN,
            name="provider intraday readiness",
            message=f"{provider_name} intraday readiness skipped known market holiday for {symbol}.",
            details=[
                f"provider={provider_name}",
                f"market={market}",
                f"symbol={symbol}",
                f"trade_date={trade_date.isoformat()}",
                f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
                "reason=known_market_holiday",
                "database_writes=none",
            ],
            suggestions=["Use a completed non-holiday trading date or omit --trade-date to try the recent-weekday lookback window."],
        )

    try:
        bars = fetch_intraday_bars(symbol, trade_date, DEFAULT_INTRADAY_TIMEFRAME)
    except Exception as exc:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider intraday readiness",
            message=f"{provider_name} failed to fetch intraday bars for {symbol}: {exc}",
            details=[
                f"provider={provider_name}",
                f"market={market}",
                f"symbol={symbol}",
                f"trade_date={trade_date.isoformat()}",
                f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
                type(exc).__name__,
            ],
            suggestions=["Verify provider dependency, symbol mapping, trade date, market session, and live endpoint schema."],
        )

    if not bars:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider intraday readiness",
            message=f"{provider_name} returned no verified intraday bars for {symbol}.",
            details=[
                f"provider={provider_name}",
                f"market={market}",
                f"symbol={symbol}",
                f"trade_date={trade_date.isoformat()}",
                f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
                "database_writes=none",
            ],
            suggestions=["Try a recent trading day, verify market session support, or run provider-specific diagnostics."],
        )

    return ProviderReadinessResult(
        status=ReadinessStatus.OK,
        name="provider intraday readiness",
        message=f"{provider_name} returned {len(bars)} verified intraday bars for {symbol}.",
        details=[
            f"provider={provider_name}",
            f"market={market}",
            f"symbol={symbol}",
            f"trade_date={trade_date.isoformat()}",
            f"timeframe={DEFAULT_INTRADAY_TIMEFRAME}",
            f"bars={len(bars)}",
            "database_writes=none",
        ],
        suggestions=[],
    )


def check_market_depth_readiness(
    *,
    provider: Provider,
    provider_name: str,
    market: str,
    symbol: str,
    depth_levels: int,
) -> ProviderReadinessResult:
    fetch_market_depth = getattr(provider, "fetch_market_depth", None)
    if not callable(fetch_market_depth):
        return ProviderReadinessResult(
            status=ReadinessStatus.WARN,
            name="provider depth readiness",
            message=f"{provider_name} does not expose explicit fetch_market_depth support.",
            details=[f"provider={provider_name}", f"market={market}", f"symbol={symbol}"],
            suggestions=["Do not infer depth from daily bars or minute bars; add an explicit provider method first."],
        )

    try:
        snapshot = fetch_market_depth(symbol, depth_levels)
    except Exception as exc:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider depth readiness",
            message=f"{provider_name} failed to fetch market depth for {symbol}: {exc}",
            details=[f"provider={provider_name}", f"market={market}", f"symbol={symbol}", type(exc).__name__],
            suggestions=["Verify provider dependency, symbol mapping, entitlement, and live endpoint schema."],
        )

    has_order_book = bool(snapshot.bids or snapshot.asks)
    has_recent_trades = bool(snapshot.recent_trades)
    has_fund_flow = snapshot.fund_flow is not None
    has_any_depth_data = has_order_book or has_recent_trades or has_fund_flow
    availability_reason = snapshot.availability.get("reason") if isinstance(snapshot.availability, dict) else None
    availability_diagnostics = _availability_diagnostic_details(snapshot.availability)

    if not has_any_depth_data:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider depth readiness",
            message=f"{provider_name} returned no verified market-depth sections for {symbol}.",
            details=[
                f"provider={provider_name}",
                f"market={market}",
                f"symbol={symbol}",
                f"depth_levels={depth_levels}",
                f"availability_reason={availability_reason}",
                *availability_diagnostics,
                "database_writes=none",
            ],
            suggestions=["Run again later or verify dependency, live schema, provider permission, and symbol support."],
        )

    return ProviderReadinessResult(
        status=ReadinessStatus.OK,
        name="provider depth readiness",
        message=f"{provider_name} returned verified market-depth sections for {symbol}.",
        details=[
            f"provider={provider_name}",
            f"market={market}",
            f"symbol={symbol}",
            f"depth_levels={depth_levels}",
            f"bids={len(snapshot.bids)}",
            f"asks={len(snapshot.asks)}",
            f"recent_trades={len(snapshot.recent_trades)}",
            f"fund_flow={has_fund_flow}",
            "database_writes=none",
        ],
        suggestions=[],
    )


def _availability_diagnostic_details(availability: object) -> list[str]:
    if not isinstance(availability, dict):
        return []

    diagnostic_details: list[str] = []
    for key in ("exception_type", "raw_shape", "raw_columns", "raw_fields_sample"):
        value = availability.get(key)
        if value is None:
            continue
        diagnostic_details.append(f"availability_{key}={_format_diagnostic_value(value)}")
    return diagnostic_details


def _format_diagnostic_value(value: object) -> str:
    if isinstance(value, Sequence) and not isinstance(value, str):
        return ",".join(str(item) for item in value[:20])
    return str(value)


def _provider_network_opt_in_suggestion(
    provider_name: str,
    market: str,
    symbol: str | None,
    check_depth: bool,
    check_intraday: bool,
    trade_date: date | None,
    intraday_lookback_days: int,
    depth_levels: int,
) -> str:
    command_parts = [
        "python scripts/provider_readiness.py",
        f"--provider {provider_name}",
        f"--market {market}",
    ]
    if symbol is not None:
        command_parts.append(f"--symbol {symbol}")
    if check_depth:
        command_parts.append("--check-depth")
        command_parts.append(f"--depth-levels {depth_levels}")
    if check_intraday:
        command_parts.append("--check-intraday")
        if trade_date is not None:
            command_parts.append(f"--trade-date {trade_date.isoformat()}")
        else:
            command_parts.append(f"--intraday-lookback-days {intraday_lookback_days}")
    command_parts.append("--real-network")
    return " ".join(command_parts)


def _readiness_check_label(*, check_depth: bool, check_intraday: bool) -> str:
    if check_depth:
        return "market-depth"
    if check_intraday:
        return "intraday"
    return "daily-bar"


def parse_trade_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("trade date must use YYYY-MM-DD format") from error


def resolve_default_intraday_trade_date(today: date | None = None) -> date:
    candidate_date = today or date.today()
    while candidate_date.weekday() >= 5:
        candidate_date -= timedelta(days=1)
    return candidate_date


def iter_recent_weekday_dates(
    *,
    lookback_days: int,
    today: date | None = None,
) -> list[date]:
    weekday_dates: list[date] = []
    candidate_date = resolve_default_intraday_trade_date(today)
    required_weekday_count = max(1, lookback_days)
    while len(weekday_dates) < required_weekday_count:
        if candidate_date.weekday() < 5:
            weekday_dates.append(candidate_date)
        candidate_date -= timedelta(days=1)
    return weekday_dates


def is_future_trade_date(trade_date: date, today: date | None = None) -> bool:
    return trade_date > (today or date.today())


def is_known_intraday_market_holiday(provider_name: str, symbol: str, trade_date: date) -> bool:
    if provider_name != "yfinance" or not _symbol_looks_like_us_equity(symbol):
        return False
    return _is_us_equity_fixed_holiday_or_observed(trade_date)


def _symbol_looks_like_us_equity(symbol: str) -> bool:
    normalized_symbol = symbol.strip().upper()
    return 1 <= len(normalized_symbol) <= 5 and normalized_symbol.isalpha()


def _is_us_equity_fixed_holiday_or_observed(trade_date: date) -> bool:
    fixed_us_equity_holidays = (
        (1, 1),
        (6, 19),
        (7, 4),
        (12, 25),
    )
    for holiday_month, holiday_day in fixed_us_equity_holidays:
        holiday_date = date(trade_date.year, holiday_month, holiday_day)
        if trade_date in {holiday_date, _observed_fixed_holiday_date(holiday_date)}:
            return True

    movable_us_equity_holidays = {
        _nth_weekday_of_month(trade_date.year, 1, weekday=0, occurrence=3),
        _nth_weekday_of_month(trade_date.year, 2, weekday=0, occurrence=3),
        _last_weekday_of_month(trade_date.year, 5, weekday=0),
        _nth_weekday_of_month(trade_date.year, 9, weekday=0, occurrence=1),
        _nth_weekday_of_month(trade_date.year, 11, weekday=3, occurrence=4),
        _easter_sunday(trade_date.year) - timedelta(days=2),
    }
    return trade_date in movable_us_equity_holidays


def _observed_fixed_holiday_date(holiday_date: date) -> date:
    if holiday_date.weekday() == 5:
        return holiday_date - timedelta(days=1)
    if holiday_date.weekday() == 6:
        return holiday_date + timedelta(days=1)
    return holiday_date


def _nth_weekday_of_month(year: int, month: int, *, weekday: int, occurrence: int) -> date:
    first_day_of_month = date(year, month, 1)
    days_until_weekday = (weekday - first_day_of_month.weekday()) % 7
    return first_day_of_month + timedelta(days=days_until_weekday + 7 * (occurrence - 1))


def _last_weekday_of_month(year: int, month: int, *, weekday: int) -> date:
    first_day_of_next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    candidate_date = first_day_of_next_month - timedelta(days=1)
    while candidate_date.weekday() != weekday:
        candidate_date -= timedelta(days=1)
    return candidate_date


def _easter_sunday(year: int) -> date:
    golden_year = year % 19
    century = year // 100
    year_in_century = year % 100
    skipped_leap_years = century // 4
    century_remainder = century % 4
    correction = (century + 8) // 25
    moon_correction = (century - correction + 1) // 3
    epact = (19 * golden_year + century - skipped_leap_years - moon_correction + 15) % 30
    year_in_century_leaps = year_in_century // 4
    year_in_century_remainder = year_in_century % 4
    weekday_correction = (32 + 2 * century_remainder + 2 * year_in_century_leaps - epact - year_in_century_remainder) % 7
    month_offset = (golden_year + 11 * epact + 22 * weekday_correction) // 451
    month = (epact + weekday_correction - 7 * month_offset + 114) // 31
    day = ((epact + weekday_correction - 7 * month_offset + 114) % 31) + 1
    return date(year, month, day)


def resolve_default_intraday_trade_date(today: date | None = None) -> date:
    candidate_date = today or date.today()
    while candidate_date.weekday() >= 5:
        candidate_date -= timedelta(days=1)
    return candidate_date


def select_default_symbol(
    provider: Provider,
    market: str,
    provider_name: str,
) -> str | ProviderReadinessResult:
    try:
        instruments = provider.fetch_instruments(market)
    except Exception as exc:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider readiness",
            message=f"{provider_name} failed to fetch instruments for market {market}: {exc}",
            details=[f"provider={provider_name}", f"market={market}", type(exc).__name__],
            suggestions=["Pass --symbol explicitly or verify provider instrument support."],
        )

    if not instruments:
        return ProviderReadinessResult(
            status=ReadinessStatus.FAIL,
            name="provider readiness",
            message=f"{provider_name} has no instruments for market {market}.",
            details=[f"provider={provider_name}", f"market={market}"],
            suggestions=["Pass --symbol explicitly or choose a supported market."],
        )

    return instruments[0].symbol


def render_results(
    results: Sequence[ProviderReadinessResult],
    output: TextIO | None = None,
) -> None:
    output_stream = output if output is not None else sys.stdout
    for result in results:
        print(f"{result.status.value} {result.name}: {result.message}", file=output_stream)
        for detail in result.details:
            print(f"  - {detail}", file=output_stream)
        for suggestion in result.suggestions:
            print(f"  suggestion: {suggestion}", file=output_stream)

    status_counts = {
        ReadinessStatus.OK: 0,
        ReadinessStatus.WARN: 0,
        ReadinessStatus.FAIL: 0,
    }
    for result in results:
        status_counts[result.status] += 1

    print(
        "Summary: "
        f"OK={status_counts[ReadinessStatus.OK]} "
        f"WARN={status_counts[ReadinessStatus.WARN]} "
        f"FAIL={status_counts[ReadinessStatus.FAIL]}",
        file=output_stream,
    )


def has_failures(results: Sequence[ProviderReadinessResult]) -> bool:
    return any(result.status == ReadinessStatus.FAIL for result in results)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = check_provider_readiness(
        provider_name=args.provider,
        market=args.market,
        symbol=args.symbol,
        real_network=args.real_network,
        check_depth=args.check_depth,
        check_intraday=args.check_intraday,
        trade_date=args.trade_date,
        intraday_lookback_days=args.intraday_lookback_days,
        depth_levels=args.depth_levels,
    )
    render_results(results)
    return 1 if has_failures(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
