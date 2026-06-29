from datetime import date

from sqlalchemy.orm import Session

from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.base import ProviderAdapter
from packages.services.market_data import get_market_snapshot, get_provider


MARKET_META = {
    "CN": {"name": "China A Share", "timezone": "Asia/Shanghai", "currency": "CNY"},
    "HK": {"name": "Hong Kong Stock", "timezone": "Asia/Hong_Kong", "currency": "HKD"},
    "US": {"name": "US Stock", "timezone": "America/New_York", "currency": "USD"},
}


def _get_or_create_market(session: Session, code: str) -> Market:
    market = session.query(Market).filter(Market.code == code).one_or_none()
    if market is not None:
        return market
    meta = MARKET_META.get(code, {"name": code, "timezone": "UTC", "currency": "USD"})
    market = Market(
        code=code,
        name=meta["name"],
        timezone=meta["timezone"],
        currency=meta["currency"],
    )
    session.add(market)
    session.flush()
    return market


def _get_or_create_instrument(
    session: Session,
    market: Market,
    symbol: str,
    name: str,
    asset_type: str,
    currency: str,
) -> Instrument:
    instrument = (
        session.query(Instrument)
        .filter(Instrument.market_id == market.id)
        .filter(Instrument.symbol == symbol)
        .one_or_none()
    )
    if instrument is not None:
        return instrument
    instrument = Instrument(
        symbol=symbol,
        name=name,
        market=market,
        asset_type=asset_type,
        currency=currency,
    )
    session.add(instrument)
    session.flush()
    return instrument


def _write_snapshot_to_database(
    market_code: str,
    start: date,
    end: date,
    session: Session,
    provider: ProviderAdapter,
) -> int:
    market = _get_or_create_market(session, market_code)
    bar_count = 0
    for provider_instrument in provider.fetch_instruments(market_code):
        instrument = _get_or_create_instrument(
            session=session,
            market=market,
            symbol=provider_instrument.symbol,
            name=provider_instrument.name,
            asset_type=provider_instrument.asset_type,
            currency=provider_instrument.currency,
        )
        for provider_bar in provider.fetch_bars(provider_instrument.symbol, "1d", start, end):
            trade_date = (
                provider_bar.timestamp
                if isinstance(provider_bar.timestamp, date)
                else provider_bar.timestamp.date()
            )
            daily_bar = session.get(DailyBar, (instrument.id, trade_date))
            if daily_bar is None:
                daily_bar = DailyBar(instrument_id=instrument.id, trade_date=trade_date)
                session.add(daily_bar)
            daily_bar.open = provider_bar.open
            daily_bar.high = provider_bar.high
            daily_bar.low = provider_bar.low
            daily_bar.close = provider_bar.close
            daily_bar.volume = provider_bar.volume
            daily_bar.amount = provider_bar.amount
            bar_count += 1
    session.commit()
    return bar_count


def ingest_mock_market_snapshot(
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    return ingest_market_snapshot(
        market=market,
        start=start,
        end=end,
        session=session,
        provider_name=provider_name,
    )


def ingest_market_snapshot(
    market: str,
    start: date,
    end: date,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    provider_name = provider_name.lower()
    provider = get_provider(provider_name)
    snapshot = get_market_snapshot(market, start, end, provider_name=provider_name)
    bar_count = (
        _write_snapshot_to_database(market, start, end, session, provider)
        if session is not None
        else sum(len(instrument["bars"]) for instrument in snapshot["instruments"])
    )
    return {
        **snapshot,
        "bar_count": bar_count,
        "status": "ingested",
    }
