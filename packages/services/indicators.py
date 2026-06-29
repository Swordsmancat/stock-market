from datetime import date, datetime, time, timezone

import pandas as pd
from sqlalchemy.orm import Session

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.domain.models import DailyBar, Instrument, TechnicalIndicator


def _daily_bars_for_symbol(symbol: str, start: date, end: date, session: Session) -> list[DailyBar]:
    return (
        session.query(DailyBar)
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .filter(Instrument.symbol == symbol)
        .filter(DailyBar.trade_date >= start)
        .filter(DailyBar.trade_date <= end)
        .order_by(DailyBar.trade_date)
        .all()
    )


def _instrument_for_symbol(symbol: str, session: Session) -> Instrument:
    instrument = session.query(Instrument).filter(Instrument.symbol == symbol).one()
    return instrument


def _as_of_datetime(trade_date: date) -> datetime:
    return datetime.combine(trade_date, time.min, tzinfo=timezone.utc)


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _latest_rsi_value(close: pd.Series) -> float:
    rsi_series = calculate_rsi(close)
    rsi_values = rsi_series.dropna()
    if rsi_values.empty:
        return 100.0
    return float(rsi_values.iloc[-1])


def calculate_and_store_daily_indicators(
    symbol: str,
    start: date,
    end: date,
    session: Session,
    ma_window: int = 20,
) -> dict[str, object]:
    bars = _daily_bars_for_symbol(symbol, start, end, session)
    if not bars:
        return {"symbol": symbol, "status": "no_data", "indicator_count": 0}

    instrument = _instrument_for_symbol(symbol, session)
    close = pd.Series([float(bar.close) for bar in bars])
    ma_values = calculate_ma(close, ma_window).dropna()
    if ma_values.empty:
        return {"symbol": symbol, "status": "insufficient_data", "indicator_count": 0}

    latest_bar = bars[-1]
    as_of = _as_of_datetime(latest_bar.trade_date)
    indicator_values = {
        "ma": {"params": {"window": ma_window}, "value": float(ma_values.iloc[-1])},
        "rsi": {"params": {"window": 14}, "value": _latest_rsi_value(close)},
    }

    session.query(TechnicalIndicator).filter(
        TechnicalIndicator.instrument_id == instrument.id,
        TechnicalIndicator.timeframe == "1d",
        TechnicalIndicator.as_of == as_of,
        TechnicalIndicator.indicator_code.in_(indicator_values.keys()),
    ).delete(synchronize_session=False)

    for indicator_code, payload in indicator_values.items():
        session.add(
            TechnicalIndicator(
                instrument_id=instrument.id,
                timeframe="1d",
                as_of=as_of,
                indicator_code=indicator_code,
                params=payload["params"],
                value_json={"value": payload["value"]},
            )
        )
    session.commit()

    return {
        "symbol": symbol,
        "status": "calculated",
        "as_of": as_of.isoformat(),
        "indicator_count": len(indicator_values),
    }


def get_stored_indicators_payload(symbol: str, session: Session) -> dict[str, object]:
    instrument = _instrument_for_symbol(symbol, session)
    latest = (
        session.query(TechnicalIndicator)
        .filter(TechnicalIndicator.instrument_id == instrument.id)
        .filter(TechnicalIndicator.timeframe == "1d")
        .order_by(TechnicalIndicator.as_of.desc())
        .first()
    )
    if latest is None:
        return {"symbol": symbol, "source": "database", "indicators": {}}

    rows = (
        session.query(TechnicalIndicator)
        .filter(TechnicalIndicator.instrument_id == instrument.id)
        .filter(TechnicalIndicator.timeframe == "1d")
        .filter(TechnicalIndicator.as_of == latest.as_of)
        .all()
    )

    return {
        "symbol": symbol,
        "source": "database",
        "as_of": _isoformat_utc(latest.as_of),
        "indicators": {
            row.indicator_code: float(row.value_json["value"])
            for row in rows
            if "value" in row.value_json
        },
    }
