import re
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.providers.fred_provider import FredProviderConfigurationError, FredProviderError
from packages.providers.world_bank_provider import WorldBankProviderError
from packages.services.market_indicators import (
    FredMacroRefreshResult,
    AkShareCnMacroRefreshResult,
    MarketIndicatorSeedImportError,
    MarketIndicatorSeedOverwriteRequiredError,
    WorldBankMacroRefreshResult,
    get_official_macro_source_status_payload,
    get_macro_dashboard_payload,
    import_market_indicator_observation_seed_content,
    preview_market_indicator_observation_seed_content,
    refresh_fred_macro_indicators,
    refresh_akshare_cn_macro_indicators,
    refresh_world_bank_macro_indicators,
)
from packages.shared.cache import clear_market_overview_cache
from packages.shared.config import settings
from packages.shared.database import get_session

router = APIRouter(prefix="/market-indicators", tags=["market-indicators"])


class MarketIndicatorSeedContentInput(BaseModel):
    content: str = Field(min_length=1)
    format: str = "auto"
    filename: str | None = None
    overwrite_acknowledged: bool = False


class FredOfficialRefreshInput(BaseModel):
    series: str = Field(default="all", min_length=1)
    start: date | None = None
    end: date | None = None
    latest_only: bool = True
    dry_run: bool = True


class WorldBankOfficialRefreshInput(BaseModel):
    target: str = Field(default="all", min_length=1)
    start_year: int | None = Field(default=None, ge=1, le=9999)
    end_year: int | None = Field(default=None, ge=1, le=9999)
    latest_only: bool = True
    dry_run: bool = True


class AkShareCnMacroRefreshInput(BaseModel):
    family: str = Field(default="all", min_length=1)
    history_limit: int = Field(default=24, ge=2, le=24)
    dry_run: bool = False


def _cache_payload(*, should_clear: bool) -> dict[str, int]:
    if not should_clear:
        return {"market_overview_cleared": 0}
    return {"market_overview_cleared": clear_market_overview_cache()}


def _macro_refresh_response(
    *,
    provider: Literal["fred", "world_bank"],
    result: FredMacroRefreshResult | WorldBankMacroRefreshResult,
    cache: dict[str, int],
) -> dict[str, object]:
    return {
        "status": "ok",
        "provider": provider,
        "dry_run": result.dry_run,
        "observations": result.observations,
        "fetched": result.fetched,
        "skipped": result.skipped,
        "codes": list(result.codes),
        "latest_as_of": result.latest_as_of,
        "diagnostics": list(result.diagnostics),
        "cache": cache,
    }


def _akshare_macro_refresh_response(
    result: AkShareCnMacroRefreshResult,
    cache: dict[str, int],
) -> dict[str, object]:
    degraded = any(item["status"] != "ok" for item in result.families)
    return {
        "status": "degraded" if degraded else "ok",
        "provider": "akshare",
        "dry_run": result.dry_run,
        "observations": result.observations,
        "fetched": result.fetched,
        "skipped": result.skipped,
        "codes": list(result.codes),
        "latest_as_of": result.latest_as_of,
        "families": list(result.families),
        "diagnostics": list(result.diagnostics),
        "cache": cache,
    }


def _sanitize_provider_message(message: str) -> str:
    sanitized = re.sub(r"(?i)(api[_-]?key=)[^&\s]+", r"\1[redacted]", message)
    if settings.fred_api_key:
        sanitized = sanitized.replace(settings.fred_api_key, "[redacted]")
    return sanitized


def _provider_error_detail(provider: str, message: str) -> dict[str, str]:
    return {
        "status": "error",
        "provider": provider,
        "message": _sanitize_provider_message(message),
    }


@router.post("/seeds/preview")
def preview_market_indicator_seeds(
    payload: MarketIndicatorSeedContentInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return preview_market_indicator_observation_seed_content(
        payload.content,
        session=session,
        format_hint=payload.format,
        filename=payload.filename,
    )


@router.post("/seeds/import")
def import_market_indicator_seeds(
    payload: MarketIndicatorSeedContentInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    preview = preview_market_indicator_observation_seed_content(
        payload.content,
        session=session,
        format_hint=payload.format,
        filename=payload.filename,
    )
    if not preview["can_import"]:
        raise HTTPException(status_code=422, detail=preview)

    summary = preview["summary"] if isinstance(preview["summary"], dict) else {}
    if int(summary.get("updates") or 0) > 0 and not payload.overwrite_acknowledged:
        raise HTTPException(status_code=409, detail=preview)

    try:
        result = import_market_indicator_observation_seed_content(
            payload.content,
            session=session,
            format_hint=payload.format,
            filename=payload.filename,
            overwrite_acknowledged=payload.overwrite_acknowledged,
        )
    except MarketIndicatorSeedOverwriteRequiredError as error:
        raise HTTPException(status_code=409, detail=error.preview) from error
    except MarketIndicatorSeedImportError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error

    result["cache"] = {"market_overview_cleared": clear_market_overview_cache()}
    return result


@router.post("/official-refresh/fred")
def refresh_fred_official_macro_indicators(
    payload: FredOfficialRefreshInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        result = refresh_fred_macro_indicators(
            session=session,
            series_group=payload.series,
            start=payload.start,
            end=payload.end,
            latest_only=payload.latest_only,
            dry_run=payload.dry_run,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except MarketIndicatorSeedImportError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error
    except FredProviderConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail=_provider_error_detail("fred", str(error)),
        ) from error
    except FredProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=_provider_error_detail("fred", str(error)),
        ) from error

    return _macro_refresh_response(
        provider="fred",
        result=result,
        cache=_cache_payload(should_clear=not result.dry_run and result.observations > 0),
    )


@router.get("/official-sources/status")
def get_official_macro_source_status(
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_official_macro_source_status_payload(session=session)


@router.get("/dashboard")
def get_macro_dashboard(
    history_limit: int = Query(default=12, ge=2, le=24),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_macro_dashboard_payload(
        session=session,
        history_limit=history_limit,
    )


@router.post("/official-refresh/akshare-cn")
def refresh_akshare_cn_macro(
    payload: AkShareCnMacroRefreshInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        result = refresh_akshare_cn_macro_indicators(
            session=session,
            family=payload.family,
            history_limit=payload.history_limit,
            dry_run=payload.dry_run,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return _akshare_macro_refresh_response(
        result,
        cache=_cache_payload(
            should_clear=not result.dry_run and result.observations > 0,
        ),
    )


@router.post("/official-refresh/world-bank")
def refresh_world_bank_official_macro_indicators(
    payload: WorldBankOfficialRefreshInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        result = refresh_world_bank_macro_indicators(
            session=session,
            target_group=payload.target,
            start_year=payload.start_year,
            end_year=payload.end_year,
            latest_only=payload.latest_only,
            dry_run=payload.dry_run,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except MarketIndicatorSeedImportError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error
    except WorldBankProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=_provider_error_detail("world_bank", str(error)),
        ) from error

    return _macro_refresh_response(
        provider="world_bank",
        result=result,
        cache=_cache_payload(should_clear=not result.dry_run and result.observations > 0),
    )
