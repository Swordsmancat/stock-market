from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_LLM_API_BASE = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://stock:stock@localhost:5432/stock"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "mock"
    llm_api_key: str | None = None
    llm_api_base: str = DEFAULT_LLM_API_BASE
    llm_model: str = DEFAULT_LLM_MODEL
    daily_report_watchlist: str = "AAPL:US"
    daily_report_symbol: str = "AAPL"
    daily_report_market: str = "US"
    daily_report_start: str = "2026-01-01"
    daily_report_end: str = "2026-01-20"
    daily_report_ma_window: int = 3
    daily_report_cron_hour: int = 21
    daily_report_cron_minute: int = 30
    market_data_provider: str = "yfinance"
    task_run_stale_minutes: int = 30
    a_share_backfill_request_delay_ms: int = 250
    a_share_backfill_max_transient_attempts: int = 3
    a_share_backfill_retry_base_seconds: float = 1.0
    daily_research_loop_enabled: bool = True
    daily_research_loop_cron_hour: int = 21
    daily_research_loop_cron_minute: int = 30
    daily_research_loop_outcome_run_limit: int = 25
    disclosure_batch_request_delay_ms: int = 1000
    disclosure_monitor_enabled: bool = True
    disclosure_monitor_interval_minutes: int = 60
    disclosure_monitor_lookback_days: int = 30
    disclosure_monitor_overlap_days: int = 3
    disclosure_monitor_max_documents: int = 20
    disclosure_monitor_freshness_hours: int = 24
    disclosure_monitor_retry_base_minutes: int = 60
    disclosure_monitor_retry_max_minutes: int = 1440
    eastmoney_automation_enabled: bool = True
    eastmoney_calendar_cron_hour: int = 5
    eastmoney_calendar_cron_minute: int = 30
    eastmoney_industry_cron_hour: int = 16
    eastmoney_industry_cron_minute: int = 30
    eastmoney_news_interval_minutes: int = 60
    eastmoney_fundamentals_cron_hour: int = 19
    eastmoney_fundamentals_cron_minute: int = 30
    eastmoney_research_batch_size: int = 20
    eastmoney_request_delay_ms: int = 1000
    eastmoney_max_transient_attempts: int = 2
    eastmoney_retry_base_seconds: float = 2.0
    fred_api_key: str | None = None
    fred_api_base_url: str = "https://api.stlouisfed.org/fred"
    world_bank_api_base_url: str = "https://api.worldbank.org/v2"
    disclosure_document_storage_dir: str = "data/official_disclosures"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
