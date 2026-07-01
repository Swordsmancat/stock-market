from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from packages.domain.models import AlertTrigger


def record_triggered_alerts(
    symbol: str,
    market: str,
    alert_status: dict[str, object] | None,
    session: Session,
) -> None:
    if not alert_status or not alert_status.get("triggered"):
        return

    now = datetime.now(timezone.utc)
    dedupe_since = now - timedelta(hours=1)
    for rule in alert_status.get("rules") or []:
        if not rule.get("triggered"):
            continue
        rule_key = str(rule["key"])
        existing = (
            session.query(AlertTrigger.id)
            .filter(AlertTrigger.symbol == symbol.upper())
            .filter(AlertTrigger.rule_key == rule_key)
            .filter(AlertTrigger.triggered_at >= dedupe_since)
            .first()
        )
        if existing is not None:
            continue
        observed = rule.get("value")
        session.add(
            AlertTrigger(
                symbol=symbol.upper(),
                market=market.upper(),
                rule_key=rule_key,
                threshold=Decimal(str(rule["threshold"])),
                observed_value=Decimal(str(observed)) if observed is not None else None,
                triggered_at=now,
            )
        )
    session.commit()


def list_recent_alert_triggers_payload(session: Session, limit: int = 20) -> dict[str, object]:
    rows = (
        session.query(AlertTrigger)
        .order_by(AlertTrigger.triggered_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "source": "database",
        "items": [
            {
                "id": str(row.id),
                "symbol": row.symbol,
                "market": row.market,
                "rule_key": row.rule_key,
                "threshold": float(row.threshold),
                "observed_value": float(row.observed_value) if row.observed_value is not None else None,
                "triggered_at": row.triggered_at.isoformat(),
            }
            for row in rows
        ],
    }
