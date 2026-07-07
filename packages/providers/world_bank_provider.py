from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_WORLD_BANK_API_BASE_URL = "https://api.worldbank.org/v2"
WORLD_BANK_INDICATOR_PAGE_URL_TEMPLATE = (
    "https://data.worldbank.org/indicator/{indicator_id}?locations={country_code}"
)


class WorldBankProviderError(RuntimeError):
    """Base error for sanitized World Bank provider failures."""


@dataclass(frozen=True)
class WorldBankObservation:
    country_code: str
    indicator_id: str
    as_of: date
    value: Decimal
    raw_value: str
    country_name: str | None = None
    indicator_name: str | None = None


@dataclass(frozen=True)
class WorldBankSkippedObservation:
    country_code: str
    indicator_id: str
    reason: str
    raw_date: object
    raw_value: object


@dataclass(frozen=True)
class WorldBankIndicatorObservations:
    country_code: str
    indicator_id: str
    observations: tuple[WorldBankObservation, ...]
    skipped: tuple[WorldBankSkippedObservation, ...]


HttpGetter = Callable[..., object]


class WorldBankProvider:
    def __init__(
        self,
        *,
        api_base_url: str = DEFAULT_WORLD_BANK_API_BASE_URL,
        http_getter: HttpGetter | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_base_url = api_base_url.rstrip("/")
        self._http_getter = http_getter or _default_http_getter
        self._timeout = timeout

    def fetch_country_indicator_observations(
        self,
        country_code: str,
        indicator_id: str,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        most_recent_values: int | None = None,
        per_page: int = 100,
    ) -> WorldBankIndicatorObservations:
        normalized_country_code = country_code.strip().upper()
        normalized_indicator_id = indicator_id.strip().upper()
        if not normalized_country_code:
            raise ValueError("World Bank country code is required.")
        if not normalized_indicator_id:
            raise ValueError("World Bank indicator ID is required.")

        params: dict[str, object] = {
            "format": "json",
            "per_page": per_page,
        }
        if start_year is not None or end_year is not None:
            start = start_year if start_year is not None else end_year
            end = end_year if end_year is not None else start_year
            params["date"] = f"{start}:{end}"
        if most_recent_values is not None:
            params["mrnev"] = most_recent_values

        observations: list[WorldBankObservation] = []
        skipped: list[WorldBankSkippedObservation] = []
        page = 1
        pages = 1
        while page <= pages:
            page_params = {**params, "page": page}
            payload = self._request_indicator_payload(
                country_code=normalized_country_code,
                indicator_id=normalized_indicator_id,
                params=page_params,
            )
            metadata, rows = _parse_world_bank_payload(
                payload,
                country_code=normalized_country_code,
                indicator_id=normalized_indicator_id,
            )
            pages = _parse_page_count(metadata)

            parsed_rows = _parse_world_bank_rows(
                rows,
                country_code=normalized_country_code,
                indicator_id=normalized_indicator_id,
            )
            observations.extend(parsed_rows.observations)
            skipped.extend(parsed_rows.skipped)
            page += 1

        observations.sort(key=lambda observation: observation.as_of)
        return WorldBankIndicatorObservations(
            country_code=normalized_country_code,
            indicator_id=normalized_indicator_id,
            observations=tuple(observations),
            skipped=tuple(skipped),
        )

    def _request_indicator_payload(
        self,
        *,
        country_code: str,
        indicator_id: str,
        params: Mapping[str, object],
    ) -> object:
        endpoint = f"{self._api_base_url}/country/{country_code}/indicator/{indicator_id}"
        try:
            response = self._http_getter(endpoint, params=params, timeout=self._timeout)
            if isinstance(response, (list, Mapping)):
                return response
            raise_for_status = getattr(response, "raise_for_status", None)
            if callable(raise_for_status):
                raise_for_status()
            payload = response.json()
        except WorldBankProviderError:
            raise
        except Exception as error:
            raise WorldBankProviderError(
                (
                    "World Bank request failed for "
                    f"{country_code}/{indicator_id}: {type(error).__name__}."
                )
            ) from error

        return payload


@dataclass(frozen=True)
class _ParsedWorldBankRows:
    observations: tuple[WorldBankObservation, ...]
    skipped: tuple[WorldBankSkippedObservation, ...]


def _default_http_getter(url: str, **kwargs: object) -> object:
    import httpx

    return httpx.get(url, **kwargs)


def _parse_world_bank_payload(
    payload: object,
    *,
    country_code: str,
    indicator_id: str,
) -> tuple[Mapping[str, Any], list[object]]:
    if (
        not isinstance(payload, list)
        or len(payload) < 2
        or not isinstance(payload[0], Mapping)
        or not isinstance(payload[1], list)
    ):
        raise WorldBankProviderError(
            f"World Bank response for {country_code}/{indicator_id} was not a metadata/data list."
        )
    return payload[0], payload[1]


def _parse_world_bank_rows(
    rows: list[object],
    *,
    country_code: str,
    indicator_id: str,
) -> _ParsedWorldBankRows:
    observations: list[WorldBankObservation] = []
    skipped: list[WorldBankSkippedObservation] = []
    for row in rows:
        if not isinstance(row, Mapping):
            skipped.append(
                WorldBankSkippedObservation(
                    country_code=country_code,
                    indicator_id=indicator_id,
                    reason="row_not_object",
                    raw_date=None,
                    raw_value=None,
                )
            )
            continue

        raw_date = row.get("date")
        raw_value = row.get("value")
        as_of = _parse_world_bank_annual_date(raw_date)
        if as_of is None:
            skipped.append(
                WorldBankSkippedObservation(
                    country_code=country_code,
                    indicator_id=indicator_id,
                    reason="invalid_date",
                    raw_date=raw_date,
                    raw_value=raw_value,
                )
            )
            continue

        value = _parse_world_bank_decimal(raw_value)
        if value is None:
            skipped.append(
                WorldBankSkippedObservation(
                    country_code=country_code,
                    indicator_id=indicator_id,
                    reason="missing_or_invalid_value",
                    raw_date=raw_date,
                    raw_value=raw_value,
                )
            )
            continue

        observations.append(
            WorldBankObservation(
                country_code=country_code,
                indicator_id=indicator_id,
                as_of=as_of,
                value=value,
                raw_value=str(raw_value),
                country_name=_nested_text(row.get("country"), "value"),
                indicator_name=_nested_text(row.get("indicator"), "value"),
            )
        )

    return _ParsedWorldBankRows(
        observations=tuple(observations),
        skipped=tuple(skipped),
    )


def _parse_page_count(metadata: Mapping[str, Any]) -> int:
    raw_pages = metadata.get("pages")
    try:
        pages = int(raw_pages)
    except (TypeError, ValueError):
        return 1
    return max(pages, 1)


def _parse_world_bank_annual_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        year = int(value)
    except ValueError:
        return None
    if year < 1 or year > 9999:
        return None
    return date(year, 12, 31)


def _parse_world_bank_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        decimal_value = Decimal(text_value)
    except (InvalidOperation, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _nested_text(value: object, key: str) -> str | None:
    if not isinstance(value, Mapping):
        return None
    raw_text = value.get(key)
    if raw_text is None:
        return None
    text = str(raw_text).strip()
    return text or None
