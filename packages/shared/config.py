from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://stock:stock@localhost:5432/stock"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "mock"
    llm_api_key: str | None = None
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
