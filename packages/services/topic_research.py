from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.orm import Session

from packages.domain.models import (
    FundamentalSnapshot,
    IndustryDailyRanking,
    Instrument,
    Market,
    NewsArticle,
)


TopicId = Literal["agriculture", "consumption", "real_estate", "nonferrous"]
TopicWindow = Literal["30d", "90d", "180d"]

TOPIC_TAXONOMY_VERSION = "focused-topic-v1"
WINDOW_DAYS: dict[str, int] = {"30d": 30, "90d": 90, "180d": 180}
NEWS_LIMIT = 12
RANKING_LIMIT = 40
COMPANY_LIMIT = 12
TEXT_LIMIT = 420


@dataclass(frozen=True)
class TopicDefinition:
    id: TopicId
    keywords: tuple[str, ...]


TOPIC_DEFINITIONS: tuple[TopicDefinition, ...] = (
    TopicDefinition(
        id="agriculture",
        keywords=("农业", "农产品", "农林牧渔", "种业", "粮食", "养殖", "agriculture"),
    ),
    TopicDefinition(
        id="consumption",
        keywords=("消费", "白酒", "家电", "旅游", "食品饮料", "consumer"),
    ),
    TopicDefinition(
        id="real_estate",
        keywords=("房地产", "地产", "楼市", "物业", "房屋", "建筑材料", "real estate", "property"),
    ),
    TopicDefinition(
        id="nonferrous",
        keywords=("有色", "铜", "铝", "锂", "稀土", "黄金", "金属", "nonferrous", "copper", "aluminum", "lithium"),
    ),
)
TOPIC_BY_ID = {definition.id: definition for definition in TOPIC_DEFINITIONS}


def get_topic_research_payload(
    *,
    session: Session,
    topic: str = "agriculture",
    window: str = "90d",
    as_of: date | None = None,
) -> dict[str, object]:
    definition = TOPIC_BY_ID.get(topic)
    if definition is None:
        raise ValueError("Unsupported topic.")
    window_days = WINDOW_DAYS.get(window)
    if window_days is None:
        raise ValueError("Unsupported topic window.")

    anchor_date = as_of or _shanghai_today()
    start_date = anchor_date - timedelta(days=window_days - 1)
    news = _news_section(session, definition, start_date, anchor_date)
    rankings = _ranking_section(session, definition, start_date, anchor_date)
    companies = _company_section(session, definition, anchor_date)
    sections = {"news": news, "industry_rankings": rankings, "companies": companies}
    evidence_count = sum(int(section["total"]) for section in sections.values())
    latest_dates = [
        str(section["latest_date"])
        for section in sections.values()
        if section.get("latest_date")
    ]

    return {
        "status": "ready" if evidence_count else "empty",
        "source": "database",
        "taxonomy_version": TOPIC_TAXONOMY_VERSION,
        "topic": definition.id,
        "topics": [item.id for item in TOPIC_DEFINITIONS],
        "window": window,
        "period": {"start": start_date.isoformat(), "end": anchor_date.isoformat()},
        "evidence_count": evidence_count,
        "latest_evidence_date": max(latest_dates) if latest_dates else None,
        "sections": sections,
        "safety": {"research_only": True, "trading_enabled": False},
    }


def _news_section(
    session: Session,
    definition: TopicDefinition,
    start_date: date,
    anchor_date: date,
) -> dict[str, object]:
    text_filter = _text_filter((NewsArticle.title, NewsArticle.summary), definition.keywords)
    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(anchor_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    base = session.query(NewsArticle).filter(
        NewsArticle.published_at >= start_at,
        NewsArticle.published_at < end_at,
        text_filter,
    )
    total = base.count()
    rows = base.order_by(NewsArticle.published_at.desc(), NewsArticle.title.asc()).limit(NEWS_LIMIT).all()
    items = []
    for row in rows:
        match = _first_field_match(
            (("title", row.title), ("summary", row.summary)),
            definition.keywords,
        )
        if match is None:
            continue
        items.append(
            {
                "id": str(row.id),
                "symbol": row.symbol,
                "title": row.title,
                "url": row.url,
                "source": row.source,
                "published_at": _iso_datetime(row.published_at),
                "summary": _clip(row.summary),
                "matched_on": match,
            }
        )
    return _section(total=total, items=items, latest_date=_latest_news_date(rows))


def _ranking_section(
    session: Session,
    definition: TopicDefinition,
    start_date: date,
    anchor_date: date,
) -> dict[str, object]:
    text_filter = _text_filter((IndustryDailyRanking.industry_name,), definition.keywords)
    base = session.query(IndustryDailyRanking).filter(
        IndustryDailyRanking.trade_date >= start_date,
        IndustryDailyRanking.trade_date <= anchor_date,
        text_filter,
    )
    total = base.count()
    rows = (
        base.order_by(
            IndustryDailyRanking.trade_date.desc(),
            IndustryDailyRanking.rank.asc(),
            IndustryDailyRanking.industry_code.asc(),
        )
        .limit(RANKING_LIMIT)
        .all()
    )
    items = []
    for row in rows:
        match = _first_field_match((("industry_name", row.industry_name),), definition.keywords)
        if match is None:
            continue
        items.append(
            {
                "date": row.trade_date.isoformat(),
                "rank": row.rank,
                "code": row.industry_code,
                "name": row.industry_name,
                "change_percent": float(row.change_percent),
                "provider": row.provider,
                "source_url": row.source_url,
                "matched_on": match,
            }
        )
    latest = rows[0].trade_date.isoformat() if rows else None
    return _section(total=total, items=items, latest_date=latest)


def _company_section(
    session: Session,
    definition: TopicDefinition,
    anchor_date: date,
) -> dict[str, object]:
    snapshots = (
        session.query(FundamentalSnapshot)
        .filter(FundamentalSnapshot.as_of <= anchor_date)
        .order_by(FundamentalSnapshot.symbol.asc(), FundamentalSnapshot.as_of.desc())
        .all()
    )
    rows: list[FundamentalSnapshot] = []
    selected_symbols: set[str] = set()
    for snapshot in snapshots:
        if snapshot.symbol in selected_symbols:
            continue
        if not isinstance(snapshot.company_json, dict) or not snapshot.company_json:
            continue
        rows.append(snapshot)
        selected_symbols.add(snapshot.symbol)
    matched_rows: list[tuple[FundamentalSnapshot, dict[str, str]]] = []
    for row in rows:
        company = row.company_json if isinstance(row.company_json, dict) else {}
        match = _first_field_match(
            (
                ("industry", company.get("industry")),
                ("business_scope", company.get("business_scope")),
                ("profile", company.get("profile")),
                ("name", company.get("name")),
            ),
            definition.keywords,
        )
        if match is None:
            continue
        matched_rows.append((row, match))

    selected_rows = matched_rows[:COMPANY_LIMIT]
    identities = _instrument_identities(session, [row.symbol for row, _match in selected_rows])
    items = []
    for row, match in selected_rows:
        company = row.company_json if isinstance(row.company_json, dict) else {}
        identity = identities.get(row.symbol)
        items.append(
            {
                "symbol": row.symbol,
                "name": _clean(company.get("name")) or (identity or {}).get("name") or row.symbol,
                "industry": _clean(company.get("industry")),
                "business_scope": _clip(company.get("business_scope")),
                "profile": _clip(company.get("profile")),
                "as_of": row.as_of.isoformat(),
                "market": (identity or {}).get("market"),
                "instrument_name": (identity or {}).get("name"),
                "matched_on": match,
            }
        )
    latest_date = max((row.as_of for row, _match in selected_rows), default=None)
    return _section(
        total=len(matched_rows),
        items=items,
        latest_date=latest_date.isoformat() if latest_date else None,
    )


def _instrument_identities(session: Session, symbols: list[str]) -> dict[str, dict[str, str]]:
    if not symbols:
        return {}
    rows = (
        session.query(Instrument, Market)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Instrument.symbol.in_(symbols), Instrument.is_active.is_(True))
        .order_by(Instrument.symbol.asc(), Market.code.asc())
        .all()
    )
    identities: dict[str, dict[str, str]] = {}
    for instrument, market in rows:
        identities.setdefault(
            instrument.symbol,
            {"name": instrument.name, "market": market.code},
        )
    return identities


def _text_filter(fields: tuple[object, ...], keywords: tuple[str, ...]):
    return or_(*(field.ilike(f"%{keyword}%") for field in fields for keyword in keywords))


def _first_field_match(
    fields: tuple[tuple[str, object], ...],
    keywords: tuple[str, ...],
) -> dict[str, str] | None:
    for field_name, raw_value in fields:
        value = _clean(raw_value)
        if not value:
            continue
        folded = value.casefold()
        for keyword in keywords:
            if keyword.casefold() in folded:
                return {"field": field_name, "keyword": keyword}
    return None


def _section(*, total: int, items: list[dict[str, object]], latest_date: str | None) -> dict[str, object]:
    return {
        "status": "ready" if items else "empty",
        "total": total,
        "returned": len(items),
        "latest_date": latest_date,
        "items": items,
    }


def _latest_news_date(rows: list[NewsArticle]) -> str | None:
    if not rows:
        return None
    return rows[0].published_at.date().isoformat()


def _iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _shanghai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _clean(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clip(value: object, limit: int = TEXT_LIMIT) -> str | None:
    cleaned = _clean(value)
    if cleaned is None or len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip()
