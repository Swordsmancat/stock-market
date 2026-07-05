from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.domain.models import Portfolio, PortfolioPosition
from packages.services.market_data import get_latest_bar_payload

DEFAULT_PORTFOLIO_NAME = "Demo Portfolio"
_DEFAULT_POSITION_NAMES = {
    "AAPL": "Apple Inc.",
    "600519": "Kweichow Moutai",
    "0700": "Tencent Holdings",
}


def _get_or_create_default_portfolio(session: Session) -> Portfolio:
    portfolio = (
        session.query(Portfolio)
        .filter(Portfolio.is_default.is_(True))
        .filter(Portfolio.is_active.is_(True))
        .first()
    )
    if portfolio is None:
        portfolio = Portfolio(
            name=DEFAULT_PORTFOLIO_NAME,
            base_currency="USD",
            risk_profile="balanced",
            is_default=True,
            is_active=True,
        )
        session.add(portfolio)
        session.flush()
    return portfolio


def _seed_default_positions_if_empty(portfolio: Portfolio, session: Session) -> None:
    existing = (
        session.query(PortfolioPosition.id)
        .filter(PortfolioPosition.portfolio_id == portfolio.id)
        .first()
    )
    if existing is not None:
        return

    session.add(
        PortfolioPosition(
            portfolio_id=portfolio.id,
            symbol="AAPL",
            market="US",
            name="Apple Inc.",
            quantity=Decimal("10"),
            avg_cost=Decimal("100"),
            is_active=True,
        )
    )
    session.commit()


def _resolve_portfolio(portfolio_id: str, session: Session) -> Portfolio | None:
    if portfolio_id == "demo":
        return _get_or_create_default_portfolio(session)

    try:
        portfolio_uuid = UUID(portfolio_id)
    except ValueError:
        return None

    portfolio = session.get(Portfolio, portfolio_uuid)
    if portfolio is None or not portfolio.is_active:
        return None
    return portfolio


def _active_positions(portfolio: Portfolio, session: Session) -> list[PortfolioPosition]:
    return (
        session.query(PortfolioPosition)
        .filter(PortfolioPosition.portfolio_id == portfolio.id)
        .filter(PortfolioPosition.is_active.is_(True))
        .order_by(PortfolioPosition.created_at.asc(), PortfolioPosition.symbol.asc())
        .all()
    )


def _serialize_portfolio_summary(portfolio: Portfolio) -> dict[str, object]:
    return {
        "id": "demo" if portfolio.is_default else str(portfolio.id),
        "name": portfolio.name,
        "base_currency": portfolio.base_currency,
        "risk_profile": portfolio.risk_profile,
        "is_default": portfolio.is_default,
    }


def _build_position_payload(position: PortfolioPosition, session: Session) -> dict[str, object]:
    latest_bar = get_latest_bar_payload(position.symbol, session=session)
    latest_item = latest_bar.get("item")
    latest_price = float(latest_item["close"]) if latest_item else float(position.avg_cost)
    quantity = float(position.quantity)
    avg_cost = float(position.avg_cost)
    cost_basis = avg_cost * quantity
    market_value = latest_price * quantity
    unrealized_pnl = market_value - cost_basis
    unrealized_return_pct = unrealized_pnl / cost_basis if cost_basis else 0.0
    return {
        "symbol": position.symbol,
        "market": position.market,
        "name": position.name,
        "quantity": quantity,
        "avg_cost": avg_cost,
        "latest_price": latest_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_return_pct": unrealized_return_pct,
        "source": latest_bar["source"],
    }


def _build_recommendation(positions: list[dict[str, object]]) -> dict[str, object]:
    if not positions:
        return {
            "status": "simulated",
            "risk_summary": "No active positions in this portfolio.",
            "actions": [],
        }

    total_market_value = sum(float(position["market_value"]) for position in positions)
    actions = []
    for position in positions:
        weight = float(position["market_value"]) / total_market_value if total_market_value else 0.0
        position["weight"] = weight
        actions.append(
            {
                "symbol": position["symbol"],
                "action": "hold",
                "target_weight": weight,
                "reason": "Mock holding remains within the simulated portfolio target allocation.",
            }
        )

    return {
        "status": "simulated",
        "risk_summary": "MVP skeleton only; no live brokerage connection or automatic trading.",
        "actions": actions,
    }


def build_portfolio_payload(portfolio: Portfolio, session: Session) -> dict[str, object]:
    positions = [_build_position_payload(position, session) for position in _active_positions(portfolio, session)]
    recommendation = _build_recommendation(positions)
    total_cost = sum(float(position["cost_basis"]) for position in positions)
    total_market_value = sum(float(position["market_value"]) for position in positions)
    unrealized_pnl = total_market_value - total_cost
    unrealized_return_pct = unrealized_pnl / total_cost if total_cost else 0.0
    source = str(positions[0]["source"]) if positions else "database"

    return {
        **_serialize_portfolio_summary(portfolio),
        "source": source,
        "summary": {
            "total_cost": total_cost,
            "total_market_value": total_market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_return_pct": unrealized_return_pct,
        },
        "positions": positions,
        "recommendation": recommendation,
    }


def get_demo_portfolio_payload(session: Session | None = None) -> dict[str, object]:
    if session is None:
        return _legacy_demo_portfolio_payload()
    try:
        portfolio = _get_or_create_default_portfolio(session)
        _seed_default_positions_if_empty(portfolio, session)
        return build_portfolio_payload(portfolio, session=session)
    except SQLAlchemyError:
        session.rollback()
        return _legacy_demo_portfolio_payload()


def _legacy_demo_portfolio_payload() -> dict[str, object]:
    latest_bar = get_latest_bar_payload("AAPL", session=None, provider_name="mock")
    latest_price = float(latest_bar["item"]["close"])
    quantity = 10.0
    avg_cost = 100.0
    cost_basis = avg_cost * quantity
    market_value = latest_price * quantity
    unrealized_pnl = market_value - cost_basis
    unrealized_return_pct = unrealized_pnl / cost_basis if cost_basis else 0.0
    position = {
        "symbol": "AAPL",
        "market": "US",
        "name": "Apple Inc.",
        "quantity": quantity,
        "avg_cost": avg_cost,
        "latest_price": latest_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_return_pct": unrealized_return_pct,
        "weight": 1.0,
        "source": latest_bar["source"],
    }
    return {
        "id": "demo",
        "name": DEFAULT_PORTFOLIO_NAME,
        "base_currency": "USD",
        "risk_profile": "balanced",
        "is_default": True,
        "source": latest_bar["source"],
        "summary": {
            "total_cost": cost_basis,
            "total_market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_return_pct": unrealized_return_pct,
        },
        "positions": [position],
        "recommendation": _build_recommendation([position]),
    }


def list_portfolios_payload(session: Session) -> dict[str, object]:
    try:
        portfolios = (
            session.query(Portfolio)
            .filter(Portfolio.is_active.is_(True))
            .order_by(Portfolio.is_default.desc(), Portfolio.created_at.asc())
            .all()
        )
        return {
            "source": "database",
            "items": [_serialize_portfolio_summary(portfolio) for portfolio in portfolios],
        }
    except SQLAlchemyError:
        session.rollback()
        legacy = _legacy_demo_portfolio_payload()
        return {
            "source": legacy["source"],
            "items": [
                {
                    "id": legacy["id"],
                    "name": legacy["name"],
                    "base_currency": legacy["base_currency"],
                    "is_default": legacy["is_default"],
                }
            ],
        }


def get_portfolio_payload(portfolio_id: str, session: Session) -> dict[str, object] | None:
    portfolio = _resolve_portfolio(portfolio_id, session)
    if portfolio is None:
        return None
    return build_portfolio_payload(portfolio, session=session)


def create_portfolio_payload(
    name: str,
    session: Session,
    base_currency: str = "USD",
    risk_profile: str | None = None,
) -> dict[str, object]:
    portfolio = Portfolio(
        name=name,
        base_currency=base_currency.upper(),
        risk_profile=risk_profile,
        is_default=False,
        is_active=True,
    )
    session.add(portfolio)
    session.commit()
    return build_portfolio_payload(portfolio, session=session)


def update_portfolio_payload(
    portfolio_id: str,
    session: Session,
    name: str | None = None,
    base_currency: str | None = None,
    risk_profile: str | None = None,
) -> dict[str, object] | None:
    portfolio = _resolve_portfolio(portfolio_id, session)
    if portfolio is None or portfolio.is_default:
        return None
    if name is not None:
        portfolio.name = name
    if base_currency is not None:
        portfolio.base_currency = base_currency.upper()
    if risk_profile is not None:
        portfolio.risk_profile = risk_profile
    session.commit()
    return build_portfolio_payload(portfolio, session=session)


def delete_portfolio_payload(portfolio_id: str, session: Session) -> dict[str, object] | None:
    portfolio = _resolve_portfolio(portfolio_id, session)
    if portfolio is None or portfolio.is_default:
        return None
    portfolio.is_active = False
    session.commit()
    return {"source": "database", "status": "deleted", "id": str(portfolio.id)}


def upsert_portfolio_position_payload(
    portfolio_id: str,
    symbol: str,
    market: str,
    quantity: float,
    avg_cost: float,
    session: Session,
    name: str | None = None,
) -> dict[str, object] | None:
    portfolio = _resolve_portfolio(portfolio_id, session)
    if portfolio is None:
        return None

    normalized_symbol = symbol.upper()
    normalized_market = market.upper()
    position = (
        session.query(PortfolioPosition)
        .filter(PortfolioPosition.portfolio_id == portfolio.id)
        .filter(PortfolioPosition.symbol == normalized_symbol)
        .filter(PortfolioPosition.market == normalized_market)
        .first()
    )
    values = {
        "symbol": normalized_symbol,
        "market": normalized_market,
        "name": name or _DEFAULT_POSITION_NAMES.get(normalized_symbol, normalized_symbol),
        "quantity": Decimal(str(quantity)),
        "avg_cost": Decimal(str(avg_cost)),
        "is_active": True,
    }
    if position is None:
        position = PortfolioPosition(portfolio_id=portfolio.id, **values)
        session.add(position)
    else:
        for key, value in values.items():
            setattr(position, key, value)
    session.commit()
    return build_portfolio_payload(portfolio, session=session)


def remove_portfolio_position_payload(
    portfolio_id: str,
    symbol: str,
    market: str,
    session: Session,
) -> dict[str, object] | None:
    portfolio = _resolve_portfolio(portfolio_id, session)
    if portfolio is None:
        return None

    position = (
        session.query(PortfolioPosition)
        .filter(PortfolioPosition.portfolio_id == portfolio.id)
        .filter(PortfolioPosition.symbol == symbol.upper())
        .filter(PortfolioPosition.market == market.upper())
        .first()
    )
    if position is None:
        return {
            "source": "database",
            "status": "not_found",
            "symbol": symbol.upper(),
            "market": market.upper(),
        }

    position.is_active = False
    session.commit()
    return {
        "source": "database",
        "status": "removed",
        "portfolio": build_portfolio_payload(portfolio, session=session),
    }
