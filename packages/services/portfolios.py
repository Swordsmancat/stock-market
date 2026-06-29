from sqlalchemy.orm import Session

from packages.services.market_data import get_latest_bar_payload


def get_demo_portfolio_payload(session: Session | None = None) -> dict[str, object]:
    latest_bar = get_latest_bar_payload("AAPL", session=session)
    latest_price = latest_bar["item"]["close"]
    quantity = 10
    return {
        "id": "demo",
        "name": "Demo Portfolio",
        "base_currency": "USD",
        "source": latest_bar["source"],
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
