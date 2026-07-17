from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.models import IndustryDailyRanking
from packages.providers.eastmoney_industry_rankings import SOURCE_URL, fetch_eastmoney_industry_history
from packages.services.platform_settings import get_platform_settings


def refresh_industry_rankings(*, session: Session, days: int = 12, fetcher=fetch_eastmoney_industry_history) -> dict[str, object]:
    configured = get_platform_settings()
    records = fetcher(days=days, proxy_url=configured.get("eastmoney_proxy_url", ""), cookie=configured.get("eastmoney_cookie", ""))
    by_date = defaultdict(list)
    for record in records:
        by_date[record.trade_date].append(record)
    ranked = []
    for trade_date, rows in by_date.items():
        for rank, record in enumerate(sorted(rows, key=lambda item: (-item.change_percent, item.industry_code)), 1):
            ranked.append((record, rank))
    identities = [(record.industry_code, record.trade_date) for record, _ in ranked]
    existing = {}
    if identities:
        for item in session.scalars(select(IndustryDailyRanking).where(IndustryDailyRanking.provider == "eastmoney", IndustryDailyRanking.taxonomy == "industry")):
            existing[(item.industry_code, item.trade_date)] = item
    now = datetime.now(timezone.utc)
    inserted = updated = 0
    for record, rank in ranked:
        item = existing.get((record.industry_code, record.trade_date))
        if item is None:
            item = IndustryDailyRanking(provider="eastmoney", taxonomy="industry", industry_code=record.industry_code, trade_date=record.trade_date, created_at=now)
            session.add(item)
            inserted += 1
        else:
            updated += 1
        item.industry_name = record.industry_name
        item.change_percent = record.change_percent
        item.rank = rank
        item.source_url = SOURCE_URL
        item.metadata_json = {"endpoint_family": "push2/push2his", "access": "direct_or_configured_proxy"}
        item.retrieved_at = record.retrieved_at
        item.updated_at = now
    session.commit()
    return {"status": "ok", "fetched": len(records), "dates": len(by_date), "inserted": inserted, "updated": updated}


def get_industry_ranking_payload(*, session: Session, days: int = 12, limit: int = 20) -> dict[str, object]:
    if not 1 <= days <= 20 or not 1 <= limit <= 20:
        raise ValueError("days and limit must be between 1 and 20.")
    dates = list(session.scalars(select(IndustryDailyRanking.trade_date).where(IndustryDailyRanking.provider == "eastmoney", IndustryDailyRanking.taxonomy == "industry").distinct().order_by(IndustryDailyRanking.trade_date.desc()).limit(days)))
    rows = []
    if dates:
        rows = list(session.scalars(select(IndustryDailyRanking).where(IndustryDailyRanking.provider == "eastmoney", IndustryDailyRanking.taxonomy == "industry", IndustryDailyRanking.trade_date.in_(dates), IndustryDailyRanking.rank <= limit).order_by(IndustryDailyRanking.trade_date.desc(), IndustryDailyRanking.rank)))
    return {"status": "ok", "provider": "eastmoney", "taxonomy": "industry", "dates": [day.isoformat() for day in dates], "limit": limit, "items": [{"date": item.trade_date.isoformat(), "rank": item.rank, "code": item.industry_code, "name": item.industry_name, "change_percent": str(item.change_percent.normalize())} for item in rows]}
