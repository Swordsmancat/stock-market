from datetime import date

from packages.services.market_data import get_bars_payload


def get_demo_portfolio_payload() -> dict[str, object]:
    bars_payload = get_bars_payload("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 1))
    latest_price = bars_payload["items"][-1]["close"]
    quantity = 10
    return {
        "id": "demo",
        "name": "Demo Portfolio",
        "base_currency": "USD",
        "positions": [
            {
                "symbol": "AAPL",
                "market": "US",
                "quantity": quantity,
                "avg_cost": 100.0,
                "latest_price": latest_price,
                "market_value": latest_price * quantity,
            }
        ],
        "recommendation": {
            "status": "simulated",
            "risk_summary": "MVP skeleton only; no live brokerage connection or automatic trading.",
            "actions": [
                {
                    "symbol": "AAPL",
                    "action": "hold",
                    "target_weight": 1.0,
                    "reason": "Mock holding remains within the demo portfolio target allocation.",
                }
            ],
        },
    }
