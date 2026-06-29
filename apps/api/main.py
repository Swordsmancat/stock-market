from fastapi import FastAPI

from apps.api.routers.health import router as health_router
from apps.api.routers.indicators import router as indicators_router
from apps.api.routers.ingestion import router as ingestion_router
from apps.api.routers.instruments import router as instruments_router
from apps.api.routers.market_data import router as market_data_router
from apps.api.routers.news import router as news_router
from apps.api.routers.portfolios import router as portfolios_router
from apps.api.routers.reports import router as reports_router

app = FastAPI(title="Stock Analysis Platform")
app.include_router(health_router)
app.include_router(indicators_router)
app.include_router(ingestion_router)
app.include_router(instruments_router)
app.include_router(market_data_router)
app.include_router(news_router)
app.include_router(portfolios_router)
app.include_router(reports_router)
