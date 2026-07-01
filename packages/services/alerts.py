from typing import Any


def evaluate_alert_rules(
    alert_rules: dict[str, Any] | None,
    price: float | None,
    rsi: float | None,
) -> dict[str, object]:
    rules_config = alert_rules or {}
    evaluated_rules: list[dict[str, object]] = []
    triggered = False

    price_above = rules_config.get("price_above")
    if price_above is not None:
        is_triggered = price is not None and float(price) > float(price_above)
        evaluated_rules.append(
            {
                "key": "price_above",
                "threshold": float(price_above),
                "value": float(price) if price is not None else None,
                "triggered": is_triggered,
            }
        )
        triggered = triggered or is_triggered

    rsi_below = rules_config.get("rsi_below")
    if rsi_below is not None:
        is_triggered = rsi is not None and float(rsi) < float(rsi_below)
        evaluated_rules.append(
            {
                "key": "rsi_below",
                "threshold": float(rsi_below),
                "value": float(rsi) if rsi is not None else None,
                "triggered": is_triggered,
            }
        )
        triggered = triggered or is_triggered

    return {
        "triggered": triggered,
        "rules": evaluated_rules,
    }
