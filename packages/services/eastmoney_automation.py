from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
import time
from typing import TypeVar
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from packages.domain.models import (
    FundamentalSnapshot,
    ResearchShortlistCandidate,
    ResearchShortlistRun,
    WatchlistItem,
)
from packages.providers.eastmoney_economic_calendar import EastmoneyEconomicCalendarError
from packages.providers.eastmoney_industry_rankings import EastmoneyIndustryRankingError
from packages.providers.eastmoney_public_fundamentals import (
    EastmoneyPublicFundamentalsProviderError,
    EastmoneyPublicFundamentalsSnapshot,
    fetch_eastmoney_public_fundamentals,
)
from packages.services.economic_calendar import refresh_economic_calendar
from packages.services.industry_rankings import refresh_industry_rankings
from packages.services.news import ingest_akshare_news


EASTMONEY_CALENDAR_TASK_NAME = "ingestion.refresh_eastmoney_economic_calendar"
EASTMONEY_INDUSTRY_TASK_NAME = "ingestion.refresh_eastmoney_industry_rankings"
EASTMONEY_NEWS_TASK_NAME = "ingestion.refresh_eastmoney_research_news"
EASTMONEY_FUNDAMENTALS_TASK_NAME = "ingestion.refresh_eastmoney_research_fundamentals"
EASTMONEY_TASK_NAMES = (
    EASTMONEY_CALENDAR_TASK_NAME,
    EASTMONEY_INDUSTRY_TASK_NAME,
    EASTMONEY_NEWS_TASK_NAME,
    EASTMONEY_FUNDAMENTALS_TASK_NAME,
)

ProgressCallback = Callable[[str, int, int, str], None]
Sleep = Callable[[float], None]
T = TypeVar("T")
MAX_RESEARCH_SYMBOLS = 100


class EastmoneyAutomationError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def resolve_eastmoney_research_symbols(
    session: Session,
    *,
    limit: int,
) -> tuple[str, ...]:
    bounded_limit = max(1, min(limit, MAX_RESEARCH_SYMBOLS))
    watchlist_symbols = {
        str(symbol).strip()
        for (symbol,) in session.query(WatchlistItem.symbol)
        .filter(WatchlistItem.is_active.is_(True))
        .filter(WatchlistItem.market == "CN")
        .all()
        if _is_cn_symbol(symbol)
    }
    latest_run = (
        session.query(ResearchShortlistRun)
        .filter(ResearchShortlistRun.market == "CN")
        .filter(ResearchShortlistRun.status == "committed")
        .order_by(
            ResearchShortlistRun.decision_date.desc(),
            ResearchShortlistRun.generated_at.desc(),
        )
        .first()
    )
    shortlist_symbols: list[str] = []
    if latest_run is not None:
        shortlist_symbols = [
            str(symbol).strip()
            for (symbol,) in session.query(ResearchShortlistCandidate.symbol)
            .filter(ResearchShortlistCandidate.run_id == latest_run.id)
            .order_by(ResearchShortlistCandidate.rank.asc())
            .all()
            if _is_cn_symbol(symbol)
        ]
    ordered = shortlist_symbols + sorted(watchlist_symbols)
    return tuple(dict.fromkeys(ordered))[:bounded_limit]


def refresh_eastmoney_calendar_batch(
    *,
    session: Session,
    today: date | None = None,
    progress_callback: ProgressCallback | None = None,
    max_attempts: int = 1,
    retry_base_seconds: float = 0,
    sleeper: Sleep = time.sleep,
) -> dict[str, object]:
    effective_today = today or _shanghai_today()
    start = effective_today - timedelta(days=7)
    end = effective_today + timedelta(days=54)
    _progress(progress_callback, "preparing", 0, 1, "Preparing calendar refresh.")
    try:
        result = _with_transient_retry(
            lambda: refresh_economic_calendar(session=session, start=start, end=end),
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
            sleeper=sleeper,
        )
    except EastmoneyEconomicCalendarError as error:
        raise EastmoneyAutomationError(error.code) from error
    _progress(progress_callback, "persisted", 1, 1, "Calendar refresh persisted.")
    return {
        "status": "ok",
        "provider": "eastmoney_public",
        "pipeline": "economic_calendar",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "stored_count": result.inserted + result.updated,
    }


def refresh_eastmoney_industry_batch(
    *,
    session: Session,
    days: int = 20,
    progress_callback: ProgressCallback | None = None,
    max_attempts: int = 1,
    retry_base_seconds: float = 0,
    sleeper: Sleep = time.sleep,
) -> dict[str, object]:
    bounded_days = max(1, min(days, 20))
    _progress(progress_callback, "preparing", 0, 1, "Preparing industry refresh.")
    try:
        result = _with_transient_retry(
            lambda: refresh_industry_rankings(session=session, days=bounded_days),
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
            sleeper=sleeper,
        )
    except EastmoneyIndustryRankingError as error:
        raise EastmoneyAutomationError(error.code) from error
    _progress(progress_callback, "persisted", 1, 1, "Industry refresh persisted.")
    return {
        "status": "ok",
        "provider": "eastmoney_public",
        "pipeline": "industry_rankings",
        "days": bounded_days,
        "stored_count": int(result.get("inserted") or 0) + int(result.get("updated") or 0),
    }


def refresh_eastmoney_news_batch(
    *,
    session: Session,
    limit: int,
    request_delay_seconds: float,
    progress_callback: ProgressCallback | None = None,
    sleeper: Sleep = time.sleep,
) -> dict[str, object]:
    symbols = resolve_eastmoney_research_symbols(session, limit=limit)
    counts = {"ingested": 0, "empty": 0, "skipped": 0, "provider_error": 0}
    total = len(symbols)
    _progress(progress_callback, "preparing", 0, total, "Research universe resolved.")
    for index, symbol in enumerate(symbols, start=1):
        result = ingest_akshare_news(symbol, session=session)
        status = str(result.get("status") or "provider_error")
        counts[status if status in counts else "provider_error"] += 1
        _progress(progress_callback, "news", index, total, "News symbol processed.")
        if index < total and request_delay_seconds > 0:
            sleeper(request_delay_seconds)
    if total and counts["provider_error"] == total:
        raise EastmoneyAutomationError("EASTMONEY_NEWS_PROVIDER_WIDE_FAILURE")
    return {
        "status": "ok" if counts["provider_error"] == 0 else "degraded",
        "provider": "eastmoney_public",
        "pipeline": "research_news",
        "symbol_count": total,
        "counts": counts,
    }


def refresh_eastmoney_fundamentals_batch(
    *,
    session: Session,
    limit: int,
    as_of: date | None = None,
    request_delay_seconds: float,
    progress_callback: ProgressCallback | None = None,
    sleeper: Sleep = time.sleep,
    fetcher=fetch_eastmoney_public_fundamentals,
    max_attempts: int = 1,
    retry_base_seconds: float = 0,
) -> dict[str, object]:
    symbols = resolve_eastmoney_research_symbols(session, limit=limit)
    effective_as_of = as_of or _shanghai_today()
    counts = {"ingested": 0, "empty": 0, "provider_error": 0}
    total = len(symbols)
    _progress(progress_callback, "preparing", 0, total, "Research universe resolved.")
    for index, symbol in enumerate(symbols, start=1):
        try:
            snapshot = _with_transient_retry(
                lambda: fetcher(symbol, as_of=effective_as_of),
                max_attempts=max_attempts,
                retry_base_seconds=retry_base_seconds,
                sleeper=sleeper,
            )
        except EastmoneyPublicFundamentalsProviderError:
            counts["provider_error"] += 1
        else:
            if snapshot is None:
                counts["empty"] += 1
            else:
                _persist_eastmoney_fundamental(snapshot, session=session)
                counts["ingested"] += 1
        _progress(progress_callback, "fundamentals", index, total, "Fundamental symbol processed.")
        if index < total and request_delay_seconds > 0:
            sleeper(request_delay_seconds)
    if total and counts["provider_error"] == total:
        raise EastmoneyAutomationError("EASTMONEY_FUNDAMENTALS_PROVIDER_WIDE_FAILURE")
    return {
        "status": "ok" if counts["provider_error"] == 0 else "degraded",
        "provider": "eastmoney_public",
        "pipeline": "research_fundamentals",
        "as_of": effective_as_of.isoformat(),
        "symbol_count": total,
        "counts": counts,
    }


def _persist_eastmoney_fundamental(
    snapshot: EastmoneyPublicFundamentalsSnapshot,
    *,
    session: Session,
) -> None:
    row = (
        session.query(FundamentalSnapshot)
        .filter(FundamentalSnapshot.symbol == snapshot.symbol)
        .filter(FundamentalSnapshot.as_of == snapshot.as_of)
        .first()
    )
    company = snapshot.company
    company_json = (
        {
            "name": company.name,
            "industry": company.industry,
            "business_scope": company.business_scope,
            "profile": company.profile,
        }
        if company is not None
        else {}
    )
    values = {
        "currency": snapshot.currency,
        "pe_ratio": None,
        "revenue_growth": _decimal(snapshot.revenue_growth),
        "net_margin": _decimal(snapshot.net_margin),
        "debt_to_assets": _decimal(snapshot.debt_to_assets),
        "source": "eastmoney_public",
        "company_json": company_json,
    }
    if row is None:
        session.add(
            FundamentalSnapshot(symbol=snapshot.symbol, as_of=snapshot.as_of, **values)
        )
    elif row.source == "eastmoney_public" or _metric_count(row) < _snapshot_metric_count(snapshot):
        for key, value in values.items():
            setattr(row, key, value)
    elif company_json:
        row.company_json = company_json
    session.commit()


def _is_cn_symbol(value: object) -> bool:
    return isinstance(value, str) and len(value.strip()) == 6 and value.strip().isdigit()


def _shanghai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _metric_count(row: FundamentalSnapshot) -> int:
    return sum(
        value is not None
        for value in (
            row.pe_ratio,
            row.revenue_growth,
            row.net_margin,
            row.debt_to_assets,
        )
    )


def _snapshot_metric_count(snapshot: EastmoneyPublicFundamentalsSnapshot) -> int:
    return sum(
        value is not None
        for value in (
            snapshot.pe_ratio,
            snapshot.revenue_growth,
            snapshot.net_margin,
            snapshot.debt_to_assets,
        )
    )


def _progress(
    callback: ProgressCallback | None,
    phase: str,
    current: int,
    total: int,
    message: str,
) -> None:
    if callback is not None:
        callback(phase, current, total, message)


def _with_transient_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int,
    retry_base_seconds: float,
    sleeper: Sleep,
) -> T:
    attempts = max(1, min(max_attempts, 3))
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except (
            EastmoneyEconomicCalendarError,
            EastmoneyIndustryRankingError,
            EastmoneyPublicFundamentalsProviderError,
        ) as error:
            if not _is_transient_code(error.code) or attempt == attempts:
                raise
            sleeper(max(0, retry_base_seconds) * (2 ** (attempt - 1)))
    raise RuntimeError("unreachable")


def _is_transient_code(code: str) -> bool:
    return any(
        token in code
        for token in ("TIMEOUT", "REQUEST_FAILED", "HTTP_STATUS", "RATE_LIMIT")
    )
