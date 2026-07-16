from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import time

from packages.providers.base import ProviderBar


STRICT_POLICY = "strict"
CN_RESILIENT_POLICY = "cn_resilient"
SUPPORTED_DAILY_BAR_POLICIES = {STRICT_POLICY, CN_RESILIENT_POLICY}

DailyBarFetcher = Callable[[str, str, date, date], list[ProviderBar]]


def resolve_daily_bar_adjustment(
    source: object,
    adjustment: object,
) -> tuple[str | None, bool]:
    normalized_source = str(source or "").strip().lower()
    normalized_adjustment = str(adjustment or "").strip().lower()
    if normalized_source == "tushare.pro.daily":
        return "raw", normalized_adjustment != "raw"
    if normalized_adjustment in {"none", "unadjusted", "no_adjust"}:
        return "raw", False
    if normalized_adjustment in {"qfq", "hfq", "raw"}:
        return normalized_adjustment, False
    return None, False


@dataclass(frozen=True)
class DailyBarSource:
    provider: str
    source: str
    adjustment: str
    priority: int
    fetch: DailyBarFetcher
    configured: bool = True
    min_interval_seconds: float = 0.0


@dataclass(frozen=True)
class DailyBarFetchResult:
    status: str
    requested_provider: str
    policy: str
    bars: list[ProviderBar] = field(default_factory=list)
    effective_provider: str | None = None
    source: str | None = None
    adjustment: str | None = None
    source_priority: int | None = None
    fallback_used: bool = False
    attempts: list[dict[str, object]] = field(default_factory=list)


class DailyBarValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DailyBarFetchCoordinator:
    def __init__(
        self,
        sources: list[DailyBarSource],
        *,
        circuit_failure_threshold: int = 3,
        monotonic_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if not sources:
            raise ValueError("At least one daily-bar source is required.")
        self._sources = sorted(sources, key=lambda item: item.priority)
        self._circuit_failure_threshold = max(1, int(circuit_failure_threshold))
        self._monotonic_fn = monotonic_fn
        self._sleep_fn = sleep_fn
        self._failure_counts: dict[str, int] = {}
        self._last_call_at: dict[str, float] = {}
        self._stats: dict[str, dict[str, int]] = {}

    def fetch(
        self,
        symbol: str,
        timeframe: str,
        start: date,
        end: date,
        *,
        policy: str = STRICT_POLICY,
        required_coverage: tuple[date, date] | None = None,
        minimum_row_count: int | None = None,
    ) -> DailyBarFetchResult:
        normalized_policy = policy.strip().lower()
        if normalized_policy not in SUPPORTED_DAILY_BAR_POLICIES:
            raise ValueError(f"Unsupported daily-bar policy: {policy}")
        if start > end:
            raise ValueError("Daily-bar start date must not be after end date.")

        sources = self._sources[:1] if normalized_policy == STRICT_POLICY else self._sources
        attempts: list[dict[str, object]] = []
        had_failure = False
        for source in sources:
            if not source.configured:
                self._increment(source.source, "skipped_unconfigured")
                attempts.append(self._attempt(source, "skipped_unconfigured"))
                continue
            if self._circuit_is_open(source.source):
                self._increment(source.source, "skipped_circuit_open")
                attempts.append(self._attempt(source, "skipped_circuit_open"))
                had_failure = True
                continue

            self._pace(source)
            self._increment(source.source, "attempted")
            try:
                bars = source.fetch(symbol, timeframe, start, end)
            except Exception as exc:
                self._record_failure(source.source)
                self._increment(source.source, "failed")
                had_failure = True
                attempts.append(
                    {
                        **self._attempt(source, "failed"),
                        "exception_type": type(exc).__name__,
                    }
                )
                if normalized_policy == STRICT_POLICY:
                    raise
                continue

            if not bars:
                self._failure_counts[source.source] = 0
                self._increment(source.source, "no_data")
                attempts.append(self._attempt(source, "no_data", row_count=0))
                continue

            try:
                _validate_bars(bars, symbol=symbol, start=start, end=end)
            except DailyBarValidationError as exc:
                self._record_failure(source.source)
                self._increment(source.source, "invalid")
                had_failure = True
                attempts.append(
                    {
                        **self._attempt(source, "invalid"),
                        "code": exc.code,
                    }
                )
                if normalized_policy == STRICT_POLICY:
                    raise
                continue

            bars = sorted(
                bars,
                key=lambda bar: (
                    bar.timestamp.date()
                    if hasattr(bar.timestamp, "date")
                    else bar.timestamp
                ),
            )
            coverage_is_insufficient = False
            if required_coverage is not None:
                required_start, required_end = required_coverage
                first_date = _bar_trade_date(bars[0])
                last_date = _bar_trade_date(bars[-1])
                coverage_is_insufficient = (
                    first_date > required_start
                    or last_date < required_end
                )
            if minimum_row_count is not None and len(bars) < minimum_row_count:
                coverage_is_insufficient = True
            if coverage_is_insufficient:
                self._failure_counts[source.source] = 0
                self._increment(source.source, "insufficient_coverage")
                had_failure = True
                attempts.append(
                    self._attempt(
                        source,
                        "insufficient_coverage",
                        row_count=len(bars),
                    )
                )
                continue
            self._failure_counts[source.source] = 0
            self._increment(source.source, "selected")
            attempts.append(self._attempt(source, "selected", row_count=len(bars)))
            return DailyBarFetchResult(
                status="ok",
                requested_provider=self._sources[0].provider,
                policy=normalized_policy,
                bars=bars,
                effective_provider=source.provider,
                source=source.source,
                adjustment=source.adjustment,
                source_priority=source.priority,
                fallback_used=source.priority > self._sources[0].priority,
                attempts=attempts,
            )

        return DailyBarFetchResult(
            status="failed" if had_failure else "no_data",
            requested_provider=self._sources[0].provider,
            policy=normalized_policy,
            attempts=attempts,
        )

    def stats(self) -> dict[str, dict[str, int]]:
        return {source: dict(counts) for source, counts in self._stats.items()}

    def _pace(self, source: DailyBarSource) -> None:
        now = self._monotonic_fn()
        previous = self._last_call_at.get(source.source)
        if previous is not None:
            remaining = max(0.0, source.min_interval_seconds - (now - previous))
            if remaining:
                self._sleep_fn(remaining)
                now = self._monotonic_fn()
        self._last_call_at[source.source] = now

    def _circuit_is_open(self, source: str) -> bool:
        return self._failure_counts.get(source, 0) >= self._circuit_failure_threshold

    def _record_failure(self, source: str) -> None:
        self._failure_counts[source] = self._failure_counts.get(source, 0) + 1

    def _increment(self, source: str, key: str) -> None:
        counts = self._stats.setdefault(source, {})
        counts[key] = counts.get(key, 0) + 1

    @staticmethod
    def _attempt(
        source: DailyBarSource,
        status: str,
        *,
        row_count: int | None = None,
    ) -> dict[str, object]:
        attempt: dict[str, object] = {
            "provider": source.provider,
            "source": source.source,
            "status": status,
        }
        if row_count is not None:
            attempt["row_count"] = row_count
        return attempt


def _bar_trade_date(bar: ProviderBar) -> date:
    return bar.timestamp.date() if isinstance(bar.timestamp, datetime) else bar.timestamp


def _validate_bars(
    bars: list[ProviderBar],
    *,
    symbol: str,
    start: date,
    end: date,
) -> None:
    seen_dates: set[date] = set()
    normalized_symbol = symbol.strip().upper()
    for bar in bars:
        if not isinstance(bar, ProviderBar):
            raise DailyBarValidationError(
                "MALFORMED_BAR",
                "A daily-bar source returned an unsupported row structure.",
            )
        numeric_values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if (
            not isinstance(bar.symbol, str)
            or not isinstance(bar.timestamp, date)
            or any(not isinstance(value, Decimal) for value in numeric_values)
            or (bar.amount is not None and not isinstance(bar.amount, Decimal))
        ):
            raise DailyBarValidationError(
                "MALFORMED_BAR",
                "A daily-bar source returned malformed field values.",
            )
        trade_date = (
            bar.timestamp.date() if isinstance(bar.timestamp, datetime) else bar.timestamp
        )
        if not isinstance(trade_date, date) or trade_date < start or trade_date > end:
            raise DailyBarValidationError("DATE_OUT_OF_RANGE", "A bar date is outside the request.")
        if trade_date in seen_dates:
            raise DailyBarValidationError("DUPLICATE_DATE", "Duplicate daily-bar date.")
        seen_dates.add(trade_date)
        if bar.symbol.strip().upper() != normalized_symbol:
            raise DailyBarValidationError("SYMBOL_MISMATCH", "A provider bar has another symbol.")
        values = (
            (*numeric_values, bar.amount)
            if bar.amount is not None
            else numeric_values
        )
        if any(not value.is_finite() for value in values):
            raise DailyBarValidationError("NON_FINITE_VALUE", "A daily-bar value is not finite.")
        if bar.high < max(bar.open, bar.low, bar.close) or bar.low > min(
            bar.open, bar.high, bar.close
        ):
            raise DailyBarValidationError("INVALID_OHLC", "Daily-bar OHLC values are inconsistent.")
        if bar.volume < 0:
            raise DailyBarValidationError("NEGATIVE_VOLUME", "Daily-bar volume is negative.")
