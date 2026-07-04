from fastapi import FastAPI

from apps.api.routers.alerts import router as alerts_router
from apps.api.routers.analysis import router as analysis_router
from apps.api.routers.assistant import router as assistant_router
from apps.api.routers.dashboard import router as dashboard_router
from apps.api.routers.fundamentals import router as fundamentals_router
from apps.api.routers.health import router as health_router
from apps.api.routers.indicators import router as indicators_router
from apps.api.routers.ingestion import router as ingestion_router
from apps.api.routers.instruments import router as instruments_router
from apps.api.routers.market_data import router as market_data_router
from apps.api.routers.news import router as news_router
from apps.api.routers.portfolios import router as portfolios_router
from apps.api.routers.recommendations import router as recommendations_router
from apps.api.routers.reports import router as reports_router
from apps.api.routers.sectors import router as sectors_router
from apps.api.routers.settings import router as settings_router
from apps.api.routers.task_runs import router as task_runs_router
from apps.api.routers.watchlists import router as watchlists_router

app = FastAPI(title="Stock Analysis Platform")
app.include_router(alerts_router)
app.include_router(analysis_router)
app.include_router(assistant_router)
app.include_router(dashboard_router)
app.include_router(fundamentals_router)
app.include_router(health_router)
app.include_router(indicators_router)
app.include_router(ingestion_router)
app.include_router(instruments_router)
app.include_router(market_data_router)
app.include_router(news_router)
app.include_router(portfolios_router)
app.include_router(recommendations_router)
app.include_router(reports_router)
app.include_router(sectors_router)
app.include_router(settings_router)
app.include_router(task_runs_router)
app.include_router(watchlists_router)
