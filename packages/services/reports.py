from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from packages.ai.report_builder import ReportContext, build_stock_report
from packages.domain.models import GeneratedReport
from packages.services.fundamentals import get_fundamental_payload
from packages.services.indicators import get_stored_indicators_payload
from packages.services.market_data import get_bars_payload
from packages.services.news import get_news_sentiment_payload


def _serialize_generated_report(report: GeneratedReport) -> dict[str, object]:
    return {
        "id": str(report.id),
        "symbol": report.symbol,
        "report_type": report.report_type,
        "as_of": report.as_of.isoformat(),
        "content_markdown": report.content_markdown,
        "citations": report.citations,
        "source_summary": report.source_summary,
        "task_run_id": str(report.task_run_id) if report.task_run_id else None,
        "created_at": report.created_at.isoformat(),
    }


class ReportDataUnavailableError(RuntimeError):
    category = "no_market_data"
    http_status_code = 422

    def __init__(
        self,
        *,
        symbol: str,
        start: date,
        end: date,
        source: str,
        provider: str | None,
        requested_provider: str | None,
        effective_provider: str | None,
        no_data_reason: str | None,
    ) -> None:
        self.symbol = symbol
        self.start = start
        self.end = end
        self.source = source
        self.provider = provider
        self.requested_provider = requested_provider
        self.effective_provider = effective_provider
        self.no_data_reason = no_data_reason or "No market data is available for report generation."
        self.category = self.__class__.category
        self.http_status_code = self.__class__.http_status_code
        super().__init__(
            f"Market data is unavailable for report generation: {symbol} {start.isoformat()}..{end.isoformat()}."
        )

    def to_http_detail(self) -> dict[str, object]:
        return {
            "message": str(self),
            "category": self.category,
            "symbol": self.symbol,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "source": self.source,
            "provider": self.provider,
            "requested_provider": self.requested_provider,
            "effective_provider": self.effective_provider,
            "no_data_reason": self.no_data_reason,
        }


def list_reports_payload(
    session: Session,
    symbol: str | None = None,
    report_type: str | None = None,
    query: str | None = None,
    as_of_start: date | None = None,
    as_of_end: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    report_query = session.query(GeneratedReport)
    if symbol:
        report_query = report_query.filter(GeneratedReport.symbol == symbol.upper())
    if report_type:
        report_query = report_query.filter(GeneratedReport.report_type == report_type)
    if as_of_start:
        report_query = report_query.filter(GeneratedReport.as_of >= as_of_start)
    if as_of_end:
        report_query = report_query.filter(GeneratedReport.as_of <= as_of_end)
    if query:
        like_query = f"%{query.strip()}%"
        report_query = report_query.filter(
            (GeneratedReport.symbol.ilike(like_query))
            | (GeneratedReport.content_markdown.ilike(like_query))
        )

    total = report_query.count()
    reports = (
        report_query.order_by(GeneratedReport.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "source": "database",
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize_generated_report(report) for report in reports],
    }


def get_report_payload(report_id: str, session: Session) -> dict[str, object] | None:
    try:
        report_uuid = UUID(report_id)
    except ValueError:
        return None
    report = session.get(GeneratedReport, report_uuid)
    if report is None:
        return None
    return _serialize_generated_report(report)


def _format_indicator_number(value: object) -> str:
    return f"{float(value):.2f}"


def _indicator_summary_and_citation(symbol: str, session: Session | None) -> tuple[str, str | None]:
    if session is None:
        return "No stored technical indicators are available in the MVP skeleton.", None

    indicator_payload = get_stored_indicators_payload(symbol, session=session)
    indicators = indicator_payload["indicators"]
    if not indicators:
        return "No stored technical indicators are available yet.", None

    ma = indicators.get("ma")
    rsi = indicators.get("rsi")
    bollinger = indicators.get("bollinger")
    atr = indicators.get("atr")
    parts = []
    if ma is not None:
        parts.append(f"MA {_format_indicator_number(ma)}")
    if rsi is not None:
        parts.append(f"RSI {_format_indicator_number(rsi)}")
    if isinstance(bollinger, dict):
        parts.append(
            "BOLL "
            f"upper {_format_indicator_number(bollinger['upper'])}, "
            f"middle {_format_indicator_number(bollinger['middle'])}, "
            f"lower {_format_indicator_number(bollinger['lower'])}"
        )
    if atr is not None:
        parts.append(f"ATR {_format_indicator_number(atr)}")
    citation = f"technical_indicators:{symbol}:{indicator_payload['as_of']}"
    return ", ".join(parts), citation


def _news_summary_and_citation(symbol: str, session: Session | None) -> tuple[str, str | None]:
    if session is None:
        return "No external news source is connected in the MVP skeleton.", None

    news_payload = get_news_sentiment_payload(symbol, session=session)
    items = news_payload["items"]
    if not items:
        return "No stored news sentiment is available yet.", None

    latest_news = items[0]
    summary = (
        f"{latest_news['title']}，情绪 {latest_news['sentiment']}，"
        f"置信度 {latest_news['confidence']:.2f}"
    )
    citation = f"news_articles:{symbol}:{latest_news['url']}"
    return summary, citation


def _fundamental_summary_and_citation(
    symbol: str,
    as_of: date,
    session: Session | None,
) -> tuple[str, str | None]:
    fundamental_payload = get_fundamental_payload(symbol, as_of=as_of, session=session)
    item = fundamental_payload["item"]
    if item is None:
        return "No stored fundamental metrics are available yet.", None

    return str(item["summary"]), str(fundamental_payload["citation"])


def _combined_analysis_summary(
    price_summary: str,
    indicator_summary: str,
    fundamental_summary: str,
    news_summary: str,
) -> str:
    return (
        f"综合来看，行情表现为 {price_summary}；技术面关注 {indicator_summary}；"
        f"基本面显示 {fundamental_summary}；消息面为 {news_summary}。"
    )


def generate_stock_report_payload(
    symbol: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    bars_payload = get_bars_payload(
        symbol,
        "1d",
        start,
        end,
        session=session,
        provider_name=provider_name,
    )
    items = bars_payload["items"]
    if not items:
        raise ReportDataUnavailableError(
            symbol=symbol,
            start=start,
            end=end,
            source=str(bars_payload.get("source", "unknown")),
            provider=str(bars_payload.get("provider")) if bars_payload.get("provider") is not None else None,
            requested_provider=str(bars_payload.get("requested_provider"))
            if bars_payload.get("requested_provider") is not None
            else None,
            effective_provider=str(bars_payload.get("effective_provider"))
            if bars_payload.get("effective_provider") is not None
            else None,
            no_data_reason=str(bars_payload.get("no_data_reason"))
            if bars_payload.get("no_data_reason") is not None
            else None,
        )
    first_bar = items[0]
    latest_bar = items[-1]
    change_pct = ((latest_bar["close"] - first_bar["close"]) / first_bar["close"]) * 100
    citations = [f"bars_1d:{symbol}:{latest_bar['timestamp']}"]
    indicator_summary, indicator_citation = _indicator_summary_and_citation(symbol, session)
    if indicator_citation is not None:
        citations.append(indicator_citation)
    news_summary, news_citation = _news_summary_and_citation(symbol, session)
    if news_citation is not None:
        citations.append(news_citation)
    fundamental_summary, fundamental_citation = _fundamental_summary_and_citation(symbol, end, session)
    if fundamental_citation is not None:
        citations.append(fundamental_citation)
    price_summary = f"Close {latest_bar['close']:.2f}, period change {change_pct:.2f}%"
    context = ReportContext(
        symbol=symbol,
        as_of=str(latest_bar["timestamp"]),
        price_summary=price_summary,
        indicator_summary=indicator_summary,
        fundamental_summary=fundamental_summary,
        news_summary=news_summary,
        citations=citations,
        combined_summary=_combined_analysis_summary(
            price_summary,
            indicator_summary,
            fundamental_summary,
            news_summary,
        ),
    )
    return {
        "symbol": symbol,
        "report_type": "stock_daily",
        "as_of": context.as_of,
        "source": bars_payload["source"],
        "provider": provider_name,
        "content_markdown": build_stock_report(context),
        "citations": context.citations,
    }


def _build_report_source_summary(
    payload: dict[str, object],
    provider_name: str,
    task_run_id: UUID | None,
) -> dict[str, object]:
    price_source = str(payload["source"])

    return {
        "source": price_source,
        "price_source": price_source,
        "provider": provider_name,
        "requested_provider": provider_name,
        "task_run_id": str(task_run_id) if task_run_id else None,
        "citations": list(payload["citations"]),
    }


def generate_and_store_daily_report(
    symbol: str,
    start: date,
    end: date,
    session: Session,
    task_run_id: UUID | str | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    payload = generate_stock_report_payload(
        symbol,
        start,
        end,
        session=session,
        provider_name=provider_name,
    )
    parsed_task_run_id: UUID | None = None
    if task_run_id is not None:
        parsed_task_run_id = task_run_id if isinstance(task_run_id, UUID) else UUID(str(task_run_id))
    source_summary = _build_report_source_summary(payload, provider_name, parsed_task_run_id)
    report = GeneratedReport(
        symbol=symbol,
        report_type=str(payload["report_type"]),
        as_of=end,
        content_markdown=str(payload["content_markdown"]),
        citations=list(payload["citations"]),
        source_summary=source_summary,
        task_run_id=parsed_task_run_id,
    )
    session.add(report)
    session.commit()

    return {
        "id": str(report.id),
        "symbol": symbol,
        "report_type": payload["report_type"],
        "as_of": end.isoformat(),
        "status": "stored",
        "task_run_id": str(report.task_run_id) if report.task_run_id else None,
        "source_summary": report.source_summary,
        "content_markdown": payload["content_markdown"],
        "citations": payload["citations"],
    }


def get_latest_daily_report_payload(symbol: str, session: Session) -> dict[str, object]:
    report = (
        session.query(GeneratedReport)
        .filter(GeneratedReport.symbol == symbol)
        .filter(GeneratedReport.report_type == "stock_daily")
        .order_by(GeneratedReport.as_of.desc(), GeneratedReport.created_at.desc())
        .first()
    )
    if report is None:
        return {
            "symbol": symbol,
            "report_type": "stock_daily",
            "source": "database",
            "items": [],
        }

    return {
        "symbol": report.symbol,
        "report_type": report.report_type,
        "as_of": report.as_of.isoformat(),
        "source": "database",
        "content_markdown": report.content_markdown,
        "citations": report.citations,
        "source_summary": report.source_summary,
        "task_run_id": str(report.task_run_id) if report.task_run_id else None,
    }


def get_daily_report_history_payload(
    symbol: str,
    session: Session,
    limit: int = 10,
) -> dict[str, object]:
    reports = (
        session.query(GeneratedReport)
        .filter(GeneratedReport.symbol == symbol)
        .filter(GeneratedReport.report_type == "stock_daily")
        .order_by(GeneratedReport.as_of.desc(), GeneratedReport.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "symbol": symbol,
        "source": "database",
        "items": [
            {
                "symbol": report.symbol,
                "report_type": report.report_type,
                "as_of": report.as_of.isoformat(),
                "content_markdown": report.content_markdown,
                "citations": report.citations,
                "source_summary": report.source_summary,
                "task_run_id": str(report.task_run_id) if report.task_run_id else None,
            }
            for report in reports
        ],
    }
