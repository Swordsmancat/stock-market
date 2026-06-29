from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID as PythonUUID
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.database import Base


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[PythonUUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(8))
    trading_calendar_code: Mapped[str | None] = mapped_column(String(64), default=None)


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[PythonUUID] = uuid_pk()
    market_id: Mapped[PythonUUID] = mapped_column(ForeignKey("markets.id"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))

    market: Mapped[Market] = relationship("Market")


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("market_id", "symbol", name="uq_instruments_market_symbol"),)

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256))
    market_id: Mapped[PythonUUID | None] = mapped_column(ForeignKey("markets.id"), default=None)
    exchange_id: Mapped[PythonUUID | None] = mapped_column(ForeignKey("exchanges.id"), default=None)
    asset_type: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    market: Mapped[Market | None] = relationship("Market")
    exchange: Mapped[Exchange | None] = relationship("Exchange")


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[PythonUUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True)
    type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column(default=100)
    license_scope: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DailyBar(Base):
    __tablename__ = "bars_1d"

    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), default=None)


class MinuteBar(Base):
    __tablename__ = "bars_1m"

    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), default=None)


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id: Mapped[PythonUUID] = uuid_pk()
    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"))
    timeframe: Mapped[str] = mapped_column(String(16))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    indicator_code: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    value_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    source: Mapped[str] = mapped_column(String(128))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    dedupe_hash: Mapped[str] = mapped_column(String(64), unique=True)


class SentimentSignal(Base):
    __tablename__ = "sentiment_signals"

    id: Mapped[PythonUUID] = uuid_pk()
    article_id: Mapped[PythonUUID] = mapped_column(ForeignKey("news_articles.id"))
    symbol: Mapped[str] = mapped_column(String(64))
    sentiment: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    article: Mapped[NewsArticle] = relationship("NewsArticle")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64))
    report_type: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[date] = mapped_column(Date)
    content_markdown: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    source_summary: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[PythonUUID] = uuid_pk()
    task_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    input_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    result_json: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=None,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
