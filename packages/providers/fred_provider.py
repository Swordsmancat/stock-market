from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_FRED_API_BASE_URL = "https://api.stlouisfed.org/fred"
FRED_SERIES_URL_TEMPLATE = "https://fred.stlouisfed.org/series/{series_id}"


class FredProviderError(RuntimeError):
    """Base error for sanitized FRED provider failures."""


class FredProviderConfigurationError(FredProviderError):
    """Raised when required FRED provider configuration is missing."""


@dataclass(frozen=True)
class FredObservation:
    series_id: str
    as_of: date
    value: Decimal
    raw_value: str
    realtime_start: str | None = None
    realtime_end: str | None = None


@dataclass(frozen=True)
class FredSkippedObservation:
    series_id: str
    reason: str
    raw_date: object
    raw_value: object


@dataclass(frozen=True)
class FredSeriesObservations:
    series_id: str
    observations: tuple[FredObservation, ...]
    skipped: tuple[FredSkippedObservation, ...]


HttpGetter = Callable[..., object]


class FredProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        api_base_url: str = DEFAULT_FRED_API_BASE_URL,
        http_getter: HttpGetter | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key.strip() if api_key is not None else ""
        self._api_base_url = api_base_url.rstrip("/")
        self._http_getter = http_getter or _default_http_getter
        self._timeout = timeout

    def fetch_series_observations(
        self,
        series_id: str,
        *,
        observation_start: date,
        observation_end: date,
        frequency: str | None = None,
        units: str | None = None,
    ) -> FredSeriesObservations:
        normalized_series_id = series_id.strip().upper()
        if not self._api_key:
            raise FredProviderConfigurationError("FRED API key is not configured.")

        params: dict[str, object] = {
            "series_id": normalized_series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "observation_start": observation_start.isoformat(),
            "observation_end": observation_end.isoformat(),
            "sort_order": "asc",
        }
        if frequency is not None:
            params["frequency"] = frequency
        if units is not None:
            params["units"] = units

        payload = self._request_observations_payload(normalized_series_id, params)
        raw_observations = payload.get("observations")
        if not isinstance(raw_observations, list):
            raise FredProviderError(
                f"FRED response for series {normalized_series_id} did not include an observations list."
            )

        observations: list[FredObservation] = []
        skipped: list[FredSkippedObservation] = []
        for raw_observation in raw_observations:
            if not isinstance(raw_observation, Mapping):
                skipped.append(
                    FredSkippedObservation(
                        series_id=normalized_series_id,
                        reason="row_not_object",
                        raw_date=None,
                        raw_value=None,
                    )
                )
                continue

            raw_date = raw_observation.get("date")
            raw_value = raw_observation.get("value")
            as_of = _parse_fred_date(raw_date)
            if as_of is None:
                skipped.append(
                    FredSkippedObservation(
                        series_id=normalized_series_id,
                        reason="invalid_date",
                        raw_date=raw_date,
                        raw_value=raw_value,
                    )
                )
                continue

            value = _parse_fred_decimal(raw_value)
            if value is None:
                skipped.append(
                    FredSkippedObservation(
                        series_id=normalized_series_id,
                        reason="missing_or_invalid_value",
                        raw_date=raw_date,
                        raw_value=raw_value,
                    )
                )
                continue

            observations.append(
                FredObservation(
                    series_id=normalized_series_id,
                    as_of=as_of,
                    value=value,
                    raw_value=str(raw_value),
                    realtime_start=_optional_text(raw_observation.get("realtime_start")),
                    realtime_end=_optional_text(raw_observation.get("realtime_end")),
                )
            )

        return FredSeriesObservations(
            series_id=normalized_series_id,
            observations=tuple(observations),
            skipped=tuple(skipped),
        )

    def _request_observations_payload(
        self,
        series_id: str,
        params: Mapping[str, object],
    ) -> Mapping[str, Any]:
        endpoint = f"{self._api_base_url}/series/observations"
        try:
            response = self._http_getter(endpoint, params=params, timeout=self._timeout)
            if isinstance(response, Mapping):
                return response
            raise_for_status = getattr(response, "raise_for_status", None)
            if callable(raise_for_status):
                raise_for_status()
            payload = response.json()
        except FredProviderError:
            raise
        except Exception as error:
            raise FredProviderError(
                f"FRED observations request failed for series {series_id}: {type(error).__name__}."
            ) from error

        if not isinstance(payload, Mapping):
            raise FredProviderError(f"FRED response for series {series_id} was not a JSON object.")
        return payload


def _default_http_getter(url: str, **kwargs: object) -> object:
    import httpx

    return httpx.get(url, **kwargs)


def _parse_fred_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_fred_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value or text_value == ".":
        return None
    try:
        decimal_value = Decimal(text_value)
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
