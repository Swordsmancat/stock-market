# 股票分析平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个面向团队内部研究使用的股票分析平台 MVP，打通多市场行情采集、指标计算、新闻舆情、AI 报告、模拟组合和 Web Dashboard 的主链路。

**Architecture:** 第一阶段采用模块化单体，后端 API、异步任务、领域模型、数据源适配、分析模块和 AI 模块共享一个代码库并通过目录边界隔离职责。耗时任务由 Celery/Redis 执行，PostgreSQL + TimescaleDB 保存业务数据和时序行情，Next.js 提供 Dashboard。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Celery, Redis, PostgreSQL, TimescaleDB, pandas, pandas-ta 或 TA-Lib, Next.js, React, TypeScript, Tailwind CSS, pytest, Vitest。

---

## 0. 参考文档

- 术语表：`CONTEXT.md`
- 详细设计：`docs/superpowers/specs/2026-06-29-stock-analysis-platform-design.md`
- 架构决策：`docs/adr/0001-modular-monolith-first.md`

当前目录不是 Git 仓库。若要按任务提交，请在执行代码实现前先将目录放入 Git 仓库；否则每个任务末尾的“提交”动作改为记录任务完成状态。

## 1. 目标文件结构

```text
apps/
  api/
    main.py
    routers/
      health.py
      instruments.py
      market_data.py
      reports.py
      portfolios.py
  worker/
    celery_app.py
    tasks/
      ingestion.py
      indicators.py
      news.py
      reports.py
  web/
    app/
      page.tsx
      instruments/[id]/page.tsx
      reports/page.tsx
      portfolios/page.tsx
packages/
  domain/
    models.py
    schemas.py
  providers/
    base.py
    mock_provider.py
  analytics/
    indicators.py
    fundamentals.py
    sentiment.py
    portfolio.py
  ai/
    provider.py
    report_builder.py
    prompts.py
  shared/
    config.py
    database.py
    logging.py
alembic/
  versions/
tests/
  domain/
  providers/
  analytics/
  api/
docker-compose.yml
pyproject.toml
package.json
.env.example
```

## Task 1: 基础工程骨架

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `apps/api/main.py`
- Create: `apps/api/routers/health.py`
- Create: `apps/worker/celery_app.py`
- Create: `packages/shared/config.py`
- Create: `packages/shared/database.py`
- Create: `packages/shared/logging.py`
- Test: `tests/api/test_health.py`

- [ ] **Step 1: 写健康检查测试**

```python
# tests/api/test_health.py
from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 创建 Python 依赖配置**

```toml
# pyproject.toml
[project]
name = "stock-analysis-platform"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic-settings",
  "sqlalchemy",
  "psycopg[binary]",
  "alembic",
  "celery",
  "redis",
  "pandas",
  "httpx",
  "python-dotenv"
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff", "mypy"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 3: 创建环境变量样例**

```dotenv
# .env.example
APP_ENV=local
DATABASE_URL=postgresql+psycopg://stock:stock@localhost:5432/stock
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=mock
LLM_API_KEY=
```

- [ ] **Step 4: 创建本地依赖服务**

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: stock
      POSTGRES_PASSWORD: stock
      POSTGRES_DB: stock
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 5: 创建共享配置**

```python
# packages/shared/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "mock"
    llm_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 6: 创建数据库连接工具**

```python
# packages/shared/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from packages.shared.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 7: 创建 API 和健康检查路由**

```python
# apps/api/routers/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}
```

```python
# apps/api/main.py
from fastapi import FastAPI

from apps.api.routers.health import router as health_router

app = FastAPI(title="Stock Analysis Platform")
app.include_router(health_router)
```

- [ ] **Step 8: 创建 Celery 入口**

```python
# apps/worker/celery_app.py
from celery import Celery

from packages.shared.config import settings

celery_app = Celery(
    "stock_analysis_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(["apps.worker.tasks"])
```

- [ ] **Step 9: 运行测试**

Run: `pytest tests/api/test_health.py -v`

Expected: `1 passed`。

## Task 2: 数据库模型和迁移

**Files:**
- Create: `packages/domain/models.py`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_core_schema.py`
- Test: `tests/domain/test_models.py`

- [ ] **Step 1: 写模型约束测试**

```python
# tests/domain/test_models.py
from packages.domain.models import Instrument, Market


def test_instrument_has_market_identity():
    market = Market(code="US", name="US Stock", timezone="America/New_York", currency="USD")
    instrument = Instrument(symbol="AAPL", name="Apple Inc.", asset_type="stock", currency="USD")
    instrument.market = market
    assert instrument.market.code == "US"
    assert instrument.symbol == "AAPL"
```

- [ ] **Step 2: 定义核心 SQLAlchemy 模型**

```python
# packages/domain/models.py
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.database import Base


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    timezone: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(8))
    trading_calendar_code: Mapped[str | None] = mapped_column(String(64))


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[UUID] = uuid_pk()
    market_id: Mapped[UUID] = mapped_column(ForeignKey("markets.id"))
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))


class Instrument(Base):
    __tablename__ = "instruments"
    __table_args__ = (UniqueConstraint("market_id", "symbol", name="uq_instruments_market_symbol"),)

    id: Mapped[UUID] = uuid_pk()
    symbol: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(256))
    market_id: Mapped[UUID | None] = mapped_column(ForeignKey("markets.id"))
    exchange_id: Mapped[UUID | None] = mapped_column(ForeignKey("exchanges.id"))
    asset_type: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    market: Mapped[Market | None] = relationship("Market")


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True)
    type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[int] = mapped_column(default=100)
    license_scope: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 3: 创建迁移脚本**

```python
# alembic/versions/0001_core_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "markets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("trading_calendar_code", sa.String(64)),
    )
    op.create_table(
        "exchanges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
    )
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("exchanges.id")),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("market_id", "symbol", name="uq_instruments_market_symbol"),
    )
    op.create_table(
        "bars_1d",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "trade_date"),
    )
    op.create_table(
        "bars_1m",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "ts"),
    )
    op.execute("SELECT create_hypertable('bars_1m', 'ts', if_not_exists => TRUE)")


def downgrade():
    op.drop_table("bars_1m")
    op.drop_table("bars_1d")
    op.drop_table("instruments")
    op.drop_table("exchanges")
    op.drop_table("markets")
```

- [ ] **Step 4: 运行模型测试**

Run: `pytest tests/domain/test_models.py -v`

Expected: `1 passed`。

## Task 3: 数据源适配器和 Mock Provider

**Files:**
- Create: `packages/providers/base.py`
- Create: `packages/providers/mock_provider.py`
- Test: `tests/providers/test_mock_provider.py`

- [ ] **Step 1: 写 Provider 合约测试**

```python
# tests/providers/test_mock_provider.py
from datetime import date

from packages.providers.mock_provider import MockProvider


def test_mock_provider_returns_bars_for_symbol():
    provider = MockProvider()
    bars = provider.fetch_bars("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))
    assert len(bars) == 3
    assert bars[0].symbol == "AAPL"
    assert bars[0].close > 0
```

- [ ] **Step 2: 定义 Provider 数据结构和抽象类**

```python
# packages/providers/base.py
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ProviderInstrument:
    symbol: str
    name: str
    market: str
    exchange: str
    asset_type: str
    currency: str


@dataclass(frozen=True)
class ProviderBar:
    symbol: str
    timestamp: datetime | date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None = None


class ProviderAdapter(Protocol):
    def fetch_instruments(self, market: str, exchange: str | None = None) -> list[ProviderInstrument]:
        ...

    def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
        ...
```

- [ ] **Step 3: 实现 Mock Provider**

```python
# packages/providers/mock_provider.py
from datetime import date, timedelta
from decimal import Decimal

from packages.providers.base import ProviderBar, ProviderInstrument


class MockProvider:
    def fetch_instruments(self, market: str, exchange: str | None = None) -> list[ProviderInstrument]:
        fixtures = {
            "CN": [ProviderInstrument("600519", "Kweichow Moutai", "CN", "SSE", "stock", "CNY")],
            "HK": [ProviderInstrument("0700", "Tencent Holdings", "HK", "HKEX", "stock", "HKD")],
            "US": [ProviderInstrument("AAPL", "Apple Inc.", "US", "NASDAQ", "stock", "USD")],
        }
        return fixtures.get(market, [])

    def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
        bars: list[ProviderBar] = []
        current = start
        price = Decimal("100.00")
        while current <= end:
            bars.append(
                ProviderBar(
                    symbol=symbol,
                    timestamp=current,
                    open=price,
                    high=price + Decimal("2.00"),
                    low=price - Decimal("1.00"),
                    close=price + Decimal("1.00"),
                    volume=Decimal("1000000"),
                    amount=Decimal("101000000"),
                )
            )
            current += timedelta(days=1)
            price += Decimal("1.00")
        return bars
```

- [ ] **Step 4: 运行 Provider 测试**

Run: `pytest tests/providers/test_mock_provider.py -v`

Expected: `1 passed`。

## Task 4: 技术指标计算

**Files:**
- Create: `packages/analytics/indicators.py`
- Test: `tests/analytics/test_indicators.py`

- [ ] **Step 1: 写指标测试**

```python
# tests/analytics/test_indicators.py
import pandas as pd

from packages.analytics.indicators import calculate_ma, calculate_rsi


def test_calculate_ma_returns_rolling_average():
    series = pd.Series([1, 2, 3, 4, 5])
    result = calculate_ma(series, window=3)
    assert result.iloc[-1] == 4


def test_calculate_rsi_bounds_between_zero_and_one_hundred():
    series = pd.Series([1, 2, 3, 2, 4, 5, 4, 6, 7, 8, 7, 9, 10, 11, 12])
    result = calculate_rsi(series, window=14)
    assert 0 <= result.dropna().iloc[-1] <= 100
```

- [ ] **Step 2: 实现指标函数**

```python
# packages/analytics/indicators.py
import pandas as pd


def calculate_ma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window=window, min_periods=window).mean()


def calculate_ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    fast_ema = calculate_ema(close, fast)
    slow_ema = calculate_ema(close, slow)
    macd = fast_ema - slow_ema
    signal_line = calculate_ema(macd, signal)
    return pd.DataFrame({"macd": macd, "signal": signal_line, "histogram": macd - signal_line})


def calculate_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window, min_periods=window).mean()
    loss = -delta.clip(upper=0).rolling(window=window, min_periods=window).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))
```

- [ ] **Step 3: 运行指标测试**

Run: `pytest tests/analytics/test_indicators.py -v`

Expected: `2 passed`。

## Task 5: 新闻舆情基础能力

**Files:**
- Create: `packages/analytics/sentiment.py`
- Test: `tests/analytics/test_sentiment.py`

- [ ] **Step 1: 写舆情测试**

```python
# tests/analytics/test_sentiment.py
from packages.analytics.sentiment import classify_sentiment, make_dedupe_hash


def test_make_dedupe_hash_is_stable():
    assert make_dedupe_hash("Title", "https://example.com/a") == make_dedupe_hash("Title", "https://example.com/a")


def test_classify_sentiment_detects_positive_news():
    result = classify_sentiment("Company reports strong growth and record profit")
    assert result.sentiment == "positive"
```

- [ ] **Step 2: 实现基础舆情规则**

```python
# packages/analytics/sentiment.py
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class SentimentResult:
    sentiment: str
    confidence: float


def make_dedupe_hash(title: str, url: str) -> str:
    normalized = f"{title.strip().lower()}|{url.strip().lower()}"
    return sha256(normalized.encode("utf-8")).hexdigest()


def classify_sentiment(text: str) -> SentimentResult:
    lowered = text.lower()
    positive_words = {"growth", "profit", "record", "beat", "upgrade", "strong"}
    negative_words = {"loss", "fraud", "miss", "downgrade", "weak", "lawsuit"}
    positive_score = sum(word in lowered for word in positive_words)
    negative_score = sum(word in lowered for word in negative_words)
    if positive_score > negative_score:
        return SentimentResult("positive", 0.6)
    if negative_score > positive_score:
        return SentimentResult("negative", 0.6)
    return SentimentResult("neutral", 0.5)
```

- [ ] **Step 3: 运行舆情测试**

Run: `pytest tests/analytics/test_sentiment.py -v`

Expected: `2 passed`。

## Task 6: AI 报告生成骨架

**Files:**
- Create: `packages/ai/provider.py`
- Create: `packages/ai/report_builder.py`
- Test: `tests/ai/test_report_builder.py`

- [ ] **Step 1: 写报告生成测试**

```python
# tests/ai/test_report_builder.py
from packages.ai.report_builder import ReportContext, build_stock_report


def test_build_stock_report_includes_citations_and_cutoff():
    context = ReportContext(
        symbol="AAPL",
        as_of="2026-06-29",
        price_summary="Close 101.00, up 1.0%",
        indicator_summary="MA20 above MA60",
        news_summary="Positive earnings news",
        citations=["news_articles:1", "bars_1d:AAPL:2026-06-29"],
    )
    report = build_stock_report(context)
    assert "AAPL" in report
    assert "2026-06-29" in report
    assert "news_articles:1" in report
```

- [ ] **Step 2: 实现 Mock LLM Provider 和报告构造**

```python
# packages/ai/provider.py
from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class MockLLMProvider:
    def generate(self, prompt: str) -> str:
        return prompt
```

```python
# packages/ai/report_builder.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ReportContext:
    symbol: str
    as_of: str
    price_summary: str
    indicator_summary: str
    news_summary: str
    citations: list[str]


def build_stock_report(context: ReportContext) -> str:
    citations = "\n".join(f"- {citation}" for citation in context.citations)
    return f"""# {context.symbol} AI 个股报告

数据截止时间：{context.as_of}

## 行情摘要

{context.price_summary}

## 技术指标

{context.indicator_summary}

## 新闻舆情

{context.news_summary}

## 风险提示

本报告仅基于平台内可验证数据生成，用于研究辅助，不构成收益承诺或自动交易指令。

## 引用

{citations}
"""
```

- [ ] **Step 3: 运行 AI 报告测试**

Run: `pytest tests/ai/test_report_builder.py -v`

Expected: `1 passed`。

## Task 7: API 查询接口

**Files:**
- Create: `apps/api/routers/instruments.py`
- Create: `apps/api/routers/reports.py`
- Modify: `apps/api/main.py`
- Test: `tests/api/test_instruments_api.py`

- [ ] **Step 1: 写 API 测试**

```python
# tests/api/test_instruments_api.py
from fastapi.testclient import TestClient

from apps.api.main import app


def test_list_instruments_returns_seed_scope():
    client = TestClient(app)
    response = client.get("/instruments")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["symbol"] in {"600519", "0700", "AAPL"}
```

- [ ] **Step 2: 实现标的接口**

```python
# apps/api/routers/instruments.py
from fastapi import APIRouter

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("")
def list_instruments():
    return {
        "items": [
            {"symbol": "600519", "name": "Kweichow Moutai", "market": "CN"},
            {"symbol": "0700", "name": "Tencent Holdings", "market": "HK"},
            {"symbol": "AAPL", "name": "Apple Inc.", "market": "US"},
        ]
    }
```

- [ ] **Step 3: 实现报告接口**

```python
# apps/api/routers/reports.py
from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports():
    return {"items": []}
```

- [ ] **Step 4: 注册路由**

```python
# apps/api/main.py
from fastapi import FastAPI

from apps.api.routers.health import router as health_router
from apps.api.routers.instruments import router as instruments_router
from apps.api.routers.reports import router as reports_router

app = FastAPI(title="Stock Analysis Platform")
app.include_router(health_router)
app.include_router(instruments_router)
app.include_router(reports_router)
```

- [ ] **Step 5: 运行 API 测试**

Run: `pytest tests/api -v`

Expected: 所有 API 测试通过。

## Task 8: Web Dashboard MVP

**Files:**
- Create: `package.json`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/app/reports/page.tsx`
- Create: `apps/web/app/portfolios/page.tsx`
- Test: `apps/web/app/page.test.tsx`

- [ ] **Step 1: 创建前端依赖配置**

```json
{
  "scripts": {
    "dev:web": "next dev apps/web",
    "test:web": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "next": "latest",
    "react": "latest",
    "react-dom": "latest",
    "typescript": "latest"
  },
  "devDependencies": {
    "vitest": "latest",
    "@testing-library/react": "latest",
    "@testing-library/jest-dom": "latest",
    "jsdom": "latest"
  }
}
```

- [ ] **Step 2: 创建首页**

```tsx
// apps/web/app/page.tsx
const instruments = [
  { symbol: "600519", name: "Kweichow Moutai", market: "A股" },
  { symbol: "0700", name: "Tencent Holdings", market: "港股" },
  { symbol: "AAPL", name: "Apple Inc.", market: "美股" },
];

export default function HomePage() {
  return (
    <main>
      <h1>股票分析平台</h1>
      <section>
        <h2>市场概览</h2>
        <ul>
          {instruments.map((item) => (
            <li key={item.symbol}>{item.market} - {item.symbol} - {item.name}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

- [ ] **Step 3: 创建报告页和组合页占位内容**

```tsx
// apps/web/app/reports/page.tsx
export default function ReportsPage() {
  return <main><h1>报告中心</h1><p>展示市场、个股和模拟组合报告。</p></main>;
}
```

```tsx
// apps/web/app/portfolios/page.tsx
export default function PortfoliosPage() {
  return <main><h1>模拟组合</h1><p>展示持仓、收益、风险暴露和 AI 调仓建议。</p></main>;
}
```

- [ ] **Step 4: 写首页测试**

```tsx
// apps/web/app/page.test.tsx
import { render, screen } from "@testing-library/react";
import HomePage from "./page";

it("renders stock analysis dashboard title", () => {
  render(<HomePage />);
  expect(screen.getByText("股票分析平台")).toBeInTheDocument();
});
```

- [ ] **Step 5: 运行前端测试**

Run: `npm run test:web`

Expected: 首页渲染测试通过。

## Task 9: 后台任务和任务审计

**Files:**
- Create: `apps/worker/tasks/ingestion.py`
- Create: `apps/worker/tasks/indicators.py`
- Create: `apps/worker/tasks/reports.py`
- Test: `tests/worker/test_tasks.py`

- [ ] **Step 1: 写任务测试**

```python
# tests/worker/test_tasks.py
from apps.worker.tasks.ingestion import ingest_mock_market_data


def test_ingest_mock_market_data_returns_summary():
    result = ingest_mock_market_data("US")
    assert result["market"] == "US"
    assert result["instrument_count"] >= 1
```

- [ ] **Step 2: 实现采集任务函数**

```python
# apps/worker/tasks/ingestion.py
from apps.worker.celery_app import celery_app
from packages.providers.mock_provider import MockProvider


@celery_app.task(name="ingestion.ingest_mock_market_data")
def ingest_mock_market_data(market: str) -> dict:
    provider = MockProvider()
    instruments = provider.fetch_instruments(market)
    return {"market": market, "instrument_count": len(instruments)}
```

- [ ] **Step 3: 创建指标和报告任务骨架**

```python
# apps/worker/tasks/indicators.py
from apps.worker.celery_app import celery_app


@celery_app.task(name="indicators.calculate_daily_indicators")
def calculate_daily_indicators(market: str) -> dict:
    return {"market": market, "status": "scheduled"}
```

```python
# apps/worker/tasks/reports.py
from apps.worker.celery_app import celery_app


@celery_app.task(name="reports.generate_daily_reports")
def generate_daily_reports(scope: str) -> dict:
    return {"scope": scope, "status": "scheduled"}
```

- [ ] **Step 4: 运行任务测试**

Run: `pytest tests/worker/test_tasks.py -v`

Expected: `1 passed`。

## Task 10: MVP 端到端验收

**Files:**
- Create: `docs/runbooks/local-development.md`
- Create: `docs/runbooks/mvp-acceptance.md`

- [ ] **Step 1: 编写本地开发手册**

```markdown
# 本地开发手册

## 启动依赖

```bash
docker compose up -d db redis
```

## 后端测试

```bash
pytest -v
```

## 后端 API

```bash
uvicorn apps.api.main:app --reload
```

## 前端

```bash
npm install
npm run dev:web
```
```

- [ ] **Step 2: 编写 MVP 验收手册**

```markdown
# MVP 验收手册

## 验收项

1. `/health` 返回 `{ "status": "ok" }`。
2. `/instruments` 返回 A股、港股、美股样例标的。
3. 技术指标测试覆盖 MA、RSI。
4. 新闻舆情测试覆盖去重和情绪分类。
5. AI 报告测试确认报告包含数据截止时间和引用。
6. Web 首页展示“股票分析平台”和三类市场样例标的。
7. 后台任务可以调度 mock 行情采集、指标计算和报告生成。
```

- [ ] **Step 3: 运行全部测试**

Run: `pytest -v && npm run test:web`

Expected: 后端与前端测试全部通过。

## 执行策略

推荐执行顺序：Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9 -> Task 10。

每完成一个任务后做一次小范围验证，避免把数据模型、异步任务、前端页面和 AI 报告问题堆到最后一起排查。

## 范围控制

本实施计划只覆盖 MVP 骨架和主链路。以下内容不在第一轮实现范围内：

- 实盘券商交易。
- 自动下单。
- 高频实时行情。
- 多租户 SaaS 计费。
- 全市场全量股票覆盖。
- 复杂回测系统。

这些能力应在 MVP 主链路稳定、数据授权明确、用户价值被验证后再独立设计。
