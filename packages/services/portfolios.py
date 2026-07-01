from sqlalchemy.orm import Session

from packages.services.market_data import get_latest_bar_payload


def get_demo_portfolio_payload(session: Session | None = None) -> dict[str, object]:
    latest_bar = get_latest_bar_payload("AAPL", session=session)
    latest_price = latest_bar["item"]["close"]
    quantity = 10
    avg_cost = 100.0
    cost_basis = avg_cost * quantity
    market_value = latest_price * quantity
    unrealized_pnl = market_value - cost_basis
    unrealized_return_pct = unrealized_pnl / cost_basis if cost_basis else 0.0
    return {
        "id": "demo",
        "name": "Demo Portfolio",
        "base_currency": "USD",
        "source": latest_bar["source"],
        "summary": {
            "total_cost": cost_basis,
            "total_market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_return_pct": unrealized_return_pct,
        },
        "positions": [
            {
                "symbol": "AAPL",
                "market": "US",
                "quantity": quantity,
                "avg_cost": avg_cost,
                "latest_price": latest_price,
                "market_value": market_value,
                "cost_basis": cost_basis,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_return_pct": unrealized_return_pct,
                "weight": 1.0,
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
