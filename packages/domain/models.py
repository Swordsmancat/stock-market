from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID as PythonUUID
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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
    universe_provider: Mapped[str | None] = mapped_column(String(64), default=None)
    universe_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

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


class InstrumentUniverseSync(Base):
    __tablename__ = "instrument_universe_syncs"

    id: Mapped[PythonUUID] = uuid_pk()
    market: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(512))
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status: Mapped[str] = mapped_column(String(32))
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    reactivated_count: Mapped[int] = mapped_column(Integer, default=0)
    deactivated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    availability_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ResearchEvidenceBackfill(Base):
    __tablename__ = "research_evidence_backfills"

    id: Mapped[PythonUUID] = uuid_pk()
    task_run_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("task_runs.id"),
        unique=True,
        default=None,
    )
    parent_run_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("research_evidence_backfills.id"),
        default=None,
    )
    market: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(64))
    daily_bar_policy: Mapped[str] = mapped_column(String(32), default="strict")
    source_stats_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    run_kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    universe_sync_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("instrument_universe_syncs.id"),
        default=None,
    )
    universe_as_of: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    evidence_kinds_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    scope_symbols_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    batch_size: Mapped[int] = mapped_column(Integer, default=25)
    cohort_size: Mapped[int | None] = mapped_column(Integer, default=None)
    shard_index: Mapped[int | None] = mapped_column(Integer, default=None)
    shard_count: Mapped[int | None] = mapped_column(Integer, default=None)
    phase: Mapped[str] = mapped_column(String(32))
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    phase_total: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    counters_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    retry_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )


class DailyBar(Base):
    __tablename__ = "bars_1d"

    instrument_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("instruments.id"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), default=None)
    provider: Mapped[str] = mapped_column(String(64), default="legacy_unknown")
    source: Mapped[str] = mapped_column(String(128), default="legacy_unknown")
    adjustment: Mapped[str] = mapped_column(String(32), default="legacy_unknown")
    source_priority: Mapped[int] = mapped_column(Integer, default=99)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class MinuteBar(Base):
    __tablename__ = "bars_1m"

    instrument_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("instruments.id"), primary_key=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), default=None)


class IntradayMinuteCacheEntry(Base):
    __tablename__ = "intraday_minute_cache_entries"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "provider",
            "symbol",
            "trade_date",
            "timeframe",
            name="uq_intraday_cache_instrument_provider_symbol_date_timeframe",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"))
    provider: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(64))
    trade_date: Mapped[date] = mapped_column(Date)
    timeframe: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(128), default="provider_verified")
    row_count: Mapped[int] = mapped_column(Integer)
    first_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    instrument: Mapped[Instrument] = relationship("Instrument")


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id: Mapped[PythonUUID] = uuid_pk()
    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"))
    timeframe: Mapped[str] = mapped_column(String(16))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    indicator_code: Mapped[str] = mapped_column(String(64))
    params: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    value_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)


class FundamentalSnapshot(Base):
    __tablename__ = "fundamental_snapshots"
    __table_args__ = (
        UniqueConstraint("symbol", "as_of", name="uq_fundamental_snapshots_symbol_as_of"),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64))
    as_of: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(8))
    pe_ratio: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    revenue_growth: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    net_margin: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    debt_to_assets: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    source: Mapped[str] = mapped_column(String(128), default="database")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class MarketIndicator(Base):
    __tablename__ = "market_indicators"
    __table_args__ = (UniqueConstraint("code", name="uq_market_indicators_code"),)

    id: Mapped[PythonUUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64))
    region: Mapped[str] = mapped_column(String(32))
    unit: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    display_order: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    observations: Mapped[list["MarketIndicatorObservation"]] = relationship(
        "MarketIndicatorObservation",
        back_populates="indicator",
    )


class MarketIndicatorObservation(Base):
    __tablename__ = "market_indicator_observations"
    __table_args__ = (
        UniqueConstraint(
            "indicator_id",
            "as_of",
            name="uq_market_indicator_observations_indicator_as_of",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    indicator_id: Mapped[PythonUUID] = mapped_column(ForeignKey("market_indicators.id"))
    as_of: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    source: Mapped[str] = mapped_column(String(512))
    components_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    indicator: Mapped[MarketIndicator] = relationship(
        "MarketIndicator",
        back_populates="observations",
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[PythonUUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    items: Mapped[list["WatchlistItem"]] = relationship("WatchlistItem", back_populates="watchlist")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", "market", name="uq_watchlist_items_identity"),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    watchlist_id: Mapped[PythonUUID] = mapped_column(ForeignKey("watchlists.id"))
    symbol: Mapped[str] = mapped_column(String(64))
    market: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_rules: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    watchlist: Mapped[Watchlist] = relationship("Watchlist", back_populates="items")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[PythonUUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128))
    base_currency: Mapped[str] = mapped_column(String(8), default="USD")
    risk_profile: Mapped[str | None] = mapped_column(String(64), default=None)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    positions: Mapped[list["PortfolioPosition"]] = relationship(
        "PortfolioPosition",
        back_populates="portfolio",
    )


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "symbol", "market", name="uq_portfolio_positions_identity"
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    portfolio_id: Mapped[PythonUUID] = mapped_column(ForeignKey("portfolios.id"))
    symbol: Mapped[str] = mapped_column(String(64))
    market: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(256))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    portfolio: Mapped[Portfolio] = relationship("Portfolio", back_populates="positions")


NEWS_ARTICLE_SYMBOL_MAX_LENGTH = 64
NEWS_ARTICLE_TITLE_MAX_LENGTH = 512
NEWS_ARTICLE_URL_MAX_LENGTH = 1024
NEWS_ARTICLE_SOURCE_MAX_LENGTH = 128


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(NEWS_ARTICLE_SYMBOL_MAX_LENGTH))
    title: Mapped[str] = mapped_column(String(NEWS_ARTICLE_TITLE_MAX_LENGTH))
    url: Mapped[str] = mapped_column(String(NEWS_ARTICLE_URL_MAX_LENGTH))
    source: Mapped[str] = mapped_column(String(NEWS_ARTICLE_SOURCE_MAX_LENGTH))
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
    task_run_id: Mapped[PythonUUID | None] = mapped_column(ForeignKey("task_runs.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ResearchSourceNote(Base):
    __tablename__ = "research_source_notes"

    id: Mapped[PythonUUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    source_name: Mapped[str] = mapped_column(String(256))
    source_type: Mapped[str] = mapped_column(String(64))
    symbols_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    tags_json: Mapped[list] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    as_of: Mapped[date | None] = mapped_column(Date, default=None)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    excerpt: Mapped[str | None] = mapped_column(Text, default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)
    ai_follow_up: Mapped[str | None] = mapped_column(Text, default=None)
    review_status: Mapped[str] = mapped_column(String(32), default="draft")
    is_citable: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OfficialDisclosure(Base):
    __tablename__ = "official_disclosures"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_document_id",
            name="uq_official_disclosures_source_document",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(64))
    source_document_id: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    company_name: Mapped[str | None] = mapped_column(String(256), default=None)
    title: Mapped[str] = mapped_column(String(1024))
    category: Mapped[str | None] = mapped_column(String(128), default=None)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(2048))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OfficialDisclosureMonitorState(Base):
    __tablename__ = "official_disclosure_monitor_states"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "symbol",
            name="uq_official_disclosure_monitor_source_symbol",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(64), default="cninfo")
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    cursor_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    cursor_source_document_id: Mapped[str | None] = mapped_column(
        String(128), default=None
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    status: Mapped[str] = mapped_column(String(32), default="never")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    last_error_code: Mapped[str | None] = mapped_column(String(128), default=None)
    last_error_message: Mapped[str | None] = mapped_column(Text, default=None)
    last_new_disclosure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_task_run_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("task_runs.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OfficialDisclosureDocument(Base):
    __tablename__ = "official_disclosure_documents"
    __table_args__ = (
        UniqueConstraint(
            "official_disclosure_id",
            "sha256",
            name="uq_official_disclosure_documents_version",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    official_disclosure_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("official_disclosures.id"), index=True
    )
    attachment_url: Mapped[str] = mapped_column(String(2048))
    media_type: Mapped[str] = mapped_column(String(128))
    provider_size: Mapped[int | None] = mapped_column(Integer, default=None)
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(1024))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_modified: Mapped[str | None] = mapped_column(String(128), default=None)
    page_count: Mapped[int | None] = mapped_column(Integer, default=None)
    extraction_status: Mapped[str] = mapped_column(String(32))
    extraction_method: Mapped[str] = mapped_column(String(64), default="pypdf")
    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class OfficialDisclosureSection(Base):
    __tablename__ = "official_disclosure_sections"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "section_index",
            name="uq_official_disclosure_sections_index",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    document_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("official_disclosure_documents.id"), index=True
    )
    section_index: Mapped[int] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer)
    heading: Mapped[str] = mapped_column(String(512))
    topic: Mapped[str] = mapped_column(String(64))
    content_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ResearchBrief(Base):
    __tablename__ = "research_briefs"

    id: Mapped[PythonUUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(512))
    brief_type: Mapped[str] = mapped_column(String(64), default="evidence_center")
    scope_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    content_markdown: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    source_summary_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    model_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    safety_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ResearchShortlistRun(Base):
    __tablename__ = "research_shortlist_runs"
    __table_args__ = (
        UniqueConstraint(
            "generation_key",
            name="uq_research_shortlist_runs_generation_key",
        ),
        Index(
            "ix_research_shortlist_runs_latest",
            "market",
            "profile_id",
            "decision_date",
            "generated_at",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    generation_key: Mapped[str] = mapped_column(String(64))
    generation_task_run_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("task_runs.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="committed")
    decision_date: Mapped[date] = mapped_column(Date)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    market: Mapped[str] = mapped_column(String(32))
    asset_type: Mapped[str] = mapped_column(String(32))
    profile_id: Mapped[str] = mapped_column(String(64))
    rule_set: Mapped[str] = mapped_column(String(64))
    scoring_model: Mapped[str] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(8))
    shortlist_limit: Mapped[int] = mapped_column(Integer)
    default_criteria_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    effective_criteria_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    overrides_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    dimension_weights_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    candidate_scope_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    coverage_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    explanation_markdown: Mapped[str] = mapped_column(Text)
    model_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    citations_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    safety_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    research_signal_only: Mapped[bool] = mapped_column(Boolean, default=True)

    candidates: Mapped[list["ResearchShortlistCandidate"]] = relationship(
        "ResearchShortlistCandidate",
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ResearchShortlistCandidate(Base):
    __tablename__ = "research_shortlist_candidates"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "instrument_id",
            name="uq_research_shortlist_candidates_instrument",
        ),
        UniqueConstraint(
            "run_id",
            "rank",
            name="uq_research_shortlist_candidates_rank",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    run_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("research_shortlist_runs.id", ondelete="CASCADE"),
        index=True,
    )
    instrument_id: Mapped[PythonUUID] = mapped_column(ForeignKey("instruments.id"))
    symbol: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256))
    market: Mapped[str] = mapped_column(String(32))
    asset_type: Mapped[str] = mapped_column(String(32))
    rank: Mapped[int] = mapped_column(Integer)
    total_score: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    minimum_rule_buffer: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    entry_trade_date: Mapped[date] = mapped_column(Date)
    entry_close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    entry_provider: Mapped[str] = mapped_column(String(64))
    entry_source: Mapped[str] = mapped_column(String(128))
    entry_adjustment: Mapped[str] = mapped_column(String(32))
    entry_source_priority: Mapped[int] = mapped_column(Integer)
    entry_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    factor_scores_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    supporting_factors_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    opposing_factors_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    data_gaps_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    invalidation_conditions_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    evidence_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    matched_rules_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    citations_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    safety_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    run: Mapped[ResearchShortlistRun] = relationship(
        "ResearchShortlistRun",
        back_populates="candidates",
    )
    instrument: Mapped[Instrument] = relationship("Instrument")
    outcomes: Mapped[list["ResearchCandidateOutcome"]] = relationship(
        "ResearchCandidateOutcome",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class ResearchCandidateOutcome(Base):
    __tablename__ = "research_candidate_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "horizon_sessions",
            name="uq_research_candidate_outcomes_horizon",
        ),
        CheckConstraint(
            "horizon_sessions IN (5, 20, 60)",
            name="ck_research_candidate_outcomes_horizon_sessions",
        ),
        CheckConstraint(
            "status IN ('evaluated', 'blocked')",
            name="ck_research_candidate_outcomes_status",
        ),
        CheckConstraint(
            "benchmark_status IN ('pending', 'evaluated', 'blocked', 'not_applicable')",
            name="ck_research_candidate_outcomes_benchmark_status",
        ),
        CheckConstraint(
            "available_forward_bars >= horizon_sessions",
            name="ck_research_candidate_outcomes_mature",
        ),
        CheckConstraint(
            "evaluation_as_of >= maturity_trade_date",
            name="ck_research_candidate_outcomes_evaluation_order",
        ),
        CheckConstraint(
            "(status = 'evaluated' AND exit_close IS NOT NULL "
            "AND minimum_forward_low IS NOT NULL "
            "AND minimum_forward_low_trade_date IS NOT NULL "
            "AND return_ratio IS NOT NULL AND drawdown_ratio IS NOT NULL "
            "AND exit_provider IS NOT NULL AND exit_source IS NOT NULL "
            "AND exit_adjustment IS NOT NULL AND exit_source_priority IS NOT NULL "
            "AND exit_ingested_at IS NOT NULL "
            "AND minimum_low_provider IS NOT NULL "
            "AND minimum_low_source IS NOT NULL "
            "AND minimum_low_adjustment IS NOT NULL "
            "AND minimum_low_source_priority IS NOT NULL "
            "AND minimum_low_ingested_at IS NOT NULL "
            "AND benchmark_status != 'not_applicable') OR "
            "(status = 'blocked' AND exit_close IS NULL "
            "AND minimum_forward_low IS NULL "
            "AND minimum_forward_low_trade_date IS NULL "
            "AND return_ratio IS NULL AND drawdown_ratio IS NULL "
            "AND exit_provider IS NULL AND exit_source IS NULL "
            "AND exit_adjustment IS NULL AND exit_source_priority IS NULL "
            "AND exit_ingested_at IS NULL "
            "AND minimum_low_provider IS NULL "
            "AND minimum_low_source IS NULL "
            "AND minimum_low_adjustment IS NULL "
            "AND minimum_low_source_priority IS NULL "
            "AND minimum_low_ingested_at IS NULL "
            "AND benchmark_status = 'not_applicable')",
            name="ck_research_candidate_outcomes_candidate_terminal_values",
        ),
        CheckConstraint(
            "(benchmark_status = 'evaluated' "
            "AND benchmark_instrument_id IS NOT NULL "
            "AND benchmark_entry_trade_date IS NOT NULL "
            "AND benchmark_entry_close IS NOT NULL "
            "AND benchmark_entry_provider IS NOT NULL "
            "AND benchmark_entry_source IS NOT NULL "
            "AND benchmark_entry_adjustment IS NOT NULL "
            "AND benchmark_entry_source_priority IS NOT NULL "
            "AND benchmark_entry_ingested_at IS NOT NULL "
            "AND benchmark_exit_trade_date IS NOT NULL "
            "AND benchmark_exit_close IS NOT NULL "
            "AND benchmark_exit_provider IS NOT NULL "
            "AND benchmark_exit_source IS NOT NULL "
            "AND benchmark_exit_adjustment IS NOT NULL "
            "AND benchmark_exit_source_priority IS NOT NULL "
            "AND benchmark_exit_ingested_at IS NOT NULL "
            "AND benchmark_return_ratio IS NOT NULL "
            "AND excess_return_ratio IS NOT NULL "
            "AND benchmark_completed_at IS NOT NULL) OR "
            "(benchmark_status = 'blocked' "
            "AND benchmark_instrument_id IS NOT NULL "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NOT NULL) OR "
            "(benchmark_status = 'pending' "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NULL) OR "
            "(benchmark_status = 'not_applicable' "
            "AND benchmark_instrument_id IS NULL "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NULL)",
            name="ck_research_candidate_outcomes_benchmark_terminal_values",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    candidate_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey("research_shortlist_candidates.id", ondelete="CASCADE"),
        index=True,
    )
    horizon_sessions: Mapped[int] = mapped_column(Integer)
    methodology_version: Mapped[str] = mapped_column(
        String(64),
        default="research_candidate_outcome_v1",
    )
    status: Mapped[str] = mapped_column(String(32))
    evaluation_as_of: Mapped[date] = mapped_column(Date)
    available_forward_bars: Mapped[int] = mapped_column(Integer)
    evaluation_task_run_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("task_runs.id"),
        default=None,
    )
    maturity_trade_date: Mapped[date] = mapped_column(Date)
    exit_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), default=None)
    minimum_forward_low: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        default=None,
    )
    minimum_forward_low_trade_date: Mapped[date | None] = mapped_column(
        Date,
        default=None,
    )
    return_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), default=None)
    drawdown_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10),
        default=None,
    )
    exit_provider: Mapped[str | None] = mapped_column(String(64), default=None)
    exit_source: Mapped[str | None] = mapped_column(String(128), default=None)
    exit_adjustment: Mapped[str | None] = mapped_column(String(32), default=None)
    exit_source_priority: Mapped[int | None] = mapped_column(Integer, default=None)
    exit_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    minimum_low_provider: Mapped[str | None] = mapped_column(String(64), default=None)
    minimum_low_source: Mapped[str | None] = mapped_column(String(128), default=None)
    minimum_low_adjustment: Mapped[str | None] = mapped_column(String(32), default=None)
    minimum_low_source_priority: Mapped[int | None] = mapped_column(Integer, default=None)
    minimum_low_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    benchmark_code: Mapped[str] = mapped_column(String(64), default="cn_csi_300")
    benchmark_instrument_id: Mapped[PythonUUID | None] = mapped_column(
        ForeignKey("instruments.id"),
        default=None,
    )
    benchmark_status: Mapped[str] = mapped_column(String(32), default="pending")
    benchmark_entry_trade_date: Mapped[date | None] = mapped_column(Date, default=None)
    benchmark_entry_close: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        default=None,
    )
    benchmark_entry_provider: Mapped[str | None] = mapped_column(String(64), default=None)
    benchmark_entry_source: Mapped[str | None] = mapped_column(String(128), default=None)
    benchmark_entry_adjustment: Mapped[str | None] = mapped_column(String(32), default=None)
    benchmark_entry_source_priority: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
    )
    benchmark_entry_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    benchmark_exit_trade_date: Mapped[date | None] = mapped_column(Date, default=None)
    benchmark_exit_close: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        default=None,
    )
    benchmark_exit_provider: Mapped[str | None] = mapped_column(String(64), default=None)
    benchmark_exit_source: Mapped[str | None] = mapped_column(String(128), default=None)
    benchmark_exit_adjustment: Mapped[str | None] = mapped_column(String(32), default=None)
    benchmark_exit_source_priority: Mapped[int | None] = mapped_column(
        Integer,
        default=None,
    )
    benchmark_exit_ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    benchmark_return_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10),
        default=None,
    )
    excess_return_ratio: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 10),
        default=None,
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    benchmark_diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    benchmark_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    candidate: Mapped[ResearchShortlistCandidate] = relationship(
        "ResearchShortlistCandidate",
        back_populates="outcomes",
    )
    benchmark_instrument: Mapped[Instrument | None] = relationship(
        "Instrument",
        foreign_keys=[benchmark_instrument_id],
    )


class MarketDailyEvidenceEvent(Base):
    __tablename__ = "market_daily_evidence_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "event_type",
            "identity",
            "market",
            "trade_date",
            name="uq_market_daily_evidence_event_identity",
        ),
    )

    id: Mapped[PythonUUID] = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(64))
    identity: Mapped[str] = mapped_column(String(256))
    identity_name: Mapped[str | None] = mapped_column(String(512), default=None)
    market: Mapped[str] = mapped_column(String(32))
    trade_date: Mapped[date] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(512))
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status: Mapped[str] = mapped_column(String(32), default="verified")
    is_citable: Mapped[bool] = mapped_column(Boolean, default=True)
    payload_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    availability_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict
    )
    provider_capabilities_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
    )
    diagnostics_json: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AlertTrigger(Base):
    __tablename__ = "alert_triggers"

    id: Mapped[PythonUUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    market: Mapped[str] = mapped_column(String(32))
    rule_key: Mapped[str] = mapped_column(String(64))
    threshold: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), default=None)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
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
    celery_task_id: Mapped[str | None] = mapped_column(String(128), default=None)
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
