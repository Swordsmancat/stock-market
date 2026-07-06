import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from packages.domain.models import MarketIndicator, MarketIndicatorObservation
from packages.providers.fred_provider import FRED_SERIES_URL_TEMPLATE, FredProvider
from packages.providers.fred_provider import FredSeriesObservations
from packages.shared.config import settings


BUFFETT_INDICATOR_REGIONS = ("CN", "HK", "US")
MACRO_INDICATOR_CODES = (
    "buffett_indicator_cn",
    "buffett_indicator_hk",
    "buffett_indicator_us",
    "us_10y_yield",
    "us_2y_yield",
    "us_10y_2y_spread",
    "us_cpi_yoy",
    "us_m2_yoy",
    "cn_m2_yoy",
)


@dataclass(frozen=True)
class MarketIndicatorDefinition:
    code: str
    name: str
    category: str
    region: str
    unit: str
    description: str
    display_order: int
    is_active: bool = True


@dataclass(frozen=True)
class MarketIndicatorObservationSeed:
    code: str
    as_of: date
    value: Decimal
    source: str
    components: dict[str, Any]


@dataclass(frozen=True)
class MarketIndicatorSeedImportResult:
    observations: int
    path: str
    codes: tuple[str, ...]
    latest_as_of: str | None


@dataclass(frozen=True)
class FredMacroSeriesTarget:
    series_id: str
    target_code: str
    group: str
    handling: str
    methodology: str


@dataclass(frozen=True)
class FredMacroRefreshResult:
    observations: int
    fetched: int
    skipped: int
    dry_run: bool
    codes: tuple[str, ...]
    latest_as_of: str | None
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class _ParsedMarketIndicatorObservationSeed:
    row_label: str
    seed: MarketIndicatorObservationSeed


class MarketIndicatorSeedImportError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        joined_errors = "; ".join(errors)
        super().__init__(f"Market indicator seed import failed: {joined_errors}")


AUDIT_SOURCE_COMPONENT_KEYS = frozenset(
    {
        "source_document",
        "source_name",
        "source_series_id",
        "source_url",
    }
)
AUDIT_METHOD_COMPONENT_KEYS = frozenset(
    {
        "calculation",
        "methodology",
        "notes",
        "review_note",
    }
)


DEFAULT_MARKET_INDICATOR_DEFINITIONS: tuple[MarketIndicatorDefinition, ...] = (
    MarketIndicatorDefinition(
        code="buffett_indicator_cn",
        name="Buffett Indicator - China",
        category="valuation",
        region="CN",
        unit="percent",
        description="Total listed-market capitalization divided by GDP for China.",
        display_order=10,
    ),
    MarketIndicatorDefinition(
        code="buffett_indicator_hk",
        name="Buffett Indicator - Hong Kong",
        category="valuation",
        region="HK",
        unit="percent",
        description="Hong Kong listed-market capitalization divided by GDP.",
        display_order=20,
    ),
    MarketIndicatorDefinition(
        code="buffett_indicator_us",
        name="Buffett Indicator - United States",
        category="valuation",
        region="US",
        unit="percent",
        description="Total listed-market capitalization divided by GDP for the United States.",
        display_order=30,
    ),
    MarketIndicatorDefinition(
        code="us_10y_yield",
        name="US 10Y Treasury Yield",
        category="rates",
        region="US",
        unit="percent",
        description="Daily 10-year Treasury constant maturity rate.",
        display_order=40,
    ),
    MarketIndicatorDefinition(
        code="us_2y_yield",
        name="US 2Y Treasury Yield",
        category="rates",
        region="US",
        unit="percent",
        description="Daily 2-year Treasury constant maturity rate.",
        display_order=50,
    ),
    MarketIndicatorDefinition(
        code="us_10y_2y_spread",
        name="US 10Y-2Y Yield Spread",
        category="rates",
        region="US",
        unit="percent",
        description="10-year Treasury yield minus 2-year Treasury yield.",
        display_order=60,
    ),
    MarketIndicatorDefinition(
        code="us_cpi_yoy",
        name="US CPI YoY",
        category="inflation",
        region="US",
        unit="percent",
        description="Year-over-year change in the US consumer price index.",
        display_order=70,
    ),
    MarketIndicatorDefinition(
        code="us_m2_yoy",
        name="US M2 Money Supply YoY",
        category="liquidity",
        region="US",
        unit="percent",
        description="Year-over-year change in US M2 money supply.",
        display_order=80,
    ),
    MarketIndicatorDefinition(
        code="cn_m2_yoy",
        name="China M2 Money Supply YoY",
        category="liquidity",
        region="CN",
        unit="percent",
        description="Year-over-year change in China M2 money supply.",
        display_order=90,
    ),
)

# Real observations should be added only when source and component values are auditable.
# Keeping this empty is intentional: the dashboard returns explicit no-data until a
# verified seed file or operator-provided seed is loaded.
DEFAULT_MARKET_INDICATOR_OBSERVATIONS: tuple[MarketIndicatorObservationSeed, ...] = ()

FRED_DIRECT_HANDLING = "direct"
FRED_YOY_HANDLING = "yoy"
FRED_MACRO_SERIES: tuple[FredMacroSeriesTarget, ...] = (
    FredMacroSeriesTarget(
        series_id="DGS10",
        target_code="us_10y_yield",
        group="rates",
        handling=FRED_DIRECT_HANDLING,
        methodology="Daily 10-year Treasury constant maturity rate from FRED DGS10.",
    ),
    FredMacroSeriesTarget(
        series_id="DGS2",
        target_code="us_2y_yield",
        group="rates",
        handling=FRED_DIRECT_HANDLING,
        methodology="Daily 2-year Treasury constant maturity rate from FRED DGS2.",
    ),
    FredMacroSeriesTarget(
        series_id="T10Y2Y",
        target_code="us_10y_2y_spread",
        group="rates",
        handling=FRED_DIRECT_HANDLING,
        methodology="Daily 10-year minus 2-year Treasury yield spread from FRED T10Y2Y.",
    ),
    FredMacroSeriesTarget(
        series_id="CPIAUCSL",
        target_code="us_cpi_yoy",
        group="inflation",
        handling=FRED_YOY_HANDLING,
        methodology="Year-over-year percent change derived from FRED CPIAUCSL index values.",
    ),
    FredMacroSeriesTarget(
        series_id="M2SL",
        target_code="us_m2_yoy",
        group="liquidity",
        handling=FRED_YOY_HANDLING,
        methodology="Year-over-year percent change derived from FRED M2SL money stock values.",
    ),
)


def parse_market_indicator_observation_seed_file(
    path: str | Path,
) -> list[MarketIndicatorObservationSeed]:
    return [parsed.seed for parsed in _parse_market_indicator_observation_seed_file(path)]


def import_market_indicator_observation_seed_file(
    path: str | Path,
    session: Session,
) -> MarketIndicatorSeedImportResult:
    parsed_seeds = _parse_market_indicator_observation_seed_file(path)
    seed_path = Path(path)

    try:
        seed_market_indicators(session=session, observations=(), commit=False)
        _validate_seed_indicator_codes(parsed_seeds, session=session)
        for parsed_seed in parsed_seeds:
            upsert_market_indicator_observation(
                parsed_seed.seed,
                session=session,
                commit=False,
            )
        session.commit()
    except Exception:
        session.rollback()
        raise

    as_of_values = [parsed_seed.seed.as_of for parsed_seed in parsed_seeds]
    return MarketIndicatorSeedImportResult(
        observations=len(parsed_seeds),
        path=str(seed_path),
        codes=tuple(sorted({parsed_seed.seed.code for parsed_seed in parsed_seeds})),
        latest_as_of=max(as_of_values).isoformat() if as_of_values else None,
    )


def refresh_fred_macro_indicators(
    *,
    session: Session,
    series_group: str = "all",
    start: date | None = None,
    end: date | None = None,
    latest_only: bool = False,
    dry_run: bool = False,
    provider: FredProvider | None = None,
    retrieved_at: datetime | None = None,
) -> FredMacroRefreshResult:
    end_date = end or date.today()
    start_date = start or (end_date - timedelta(days=400) if latest_only else end_date)
    targets = _select_fred_macro_targets(series_group)
    fred_provider = provider or FredProvider(
        api_key=settings.fred_api_key,
        api_base_url=settings.fred_api_base_url,
    )
    retrieved_at_value = retrieved_at or datetime.now(timezone.utc)

    series_payloads: dict[str, FredSeriesObservations] = {}
    diagnostics: list[str] = []
    fetched_count = 0
    skipped_count = 0
    for target in targets:
        fetch_start = _fred_fetch_start(target=target, start=start_date)
        series_payload = fred_provider.fetch_series_observations(
            target.series_id,
            observation_start=fetch_start,
            observation_end=end_date,
        )
        series_payloads[target.series_id] = series_payload
        fetched_count += len(series_payload.observations)
        skipped_count += len(series_payload.skipped)
        if series_payload.skipped:
            diagnostics.append(
                f"FRED {target.series_id} skipped {len(series_payload.skipped)} missing or invalid observations."
            )

    seeds = _build_fred_observation_seeds(
        targets=targets,
        series_payloads=series_payloads,
        start=start_date,
        end=end_date,
        latest_only=latest_only,
        retrieved_at=retrieved_at_value,
    )

    try:
        seed_market_indicators(session=session, observations=(), commit=False)
        _validate_fred_observation_seeds(seeds, session=session)
        if dry_run:
            session.rollback()
        else:
            for seed in seeds:
                upsert_market_indicator_observation(seed, session=session, commit=False)
            session.commit()
    except Exception:
        session.rollback()
        raise

    as_of_values = [seed.as_of for seed in seeds]
    return FredMacroRefreshResult(
        observations=len(seeds),
        fetched=fetched_count,
        skipped=skipped_count,
        dry_run=dry_run,
        codes=tuple(sorted({seed.code for seed in seeds})),
        latest_as_of=max(as_of_values).isoformat() if as_of_values else None,
        diagnostics=tuple(diagnostics),
    )


def _select_fred_macro_targets(series_group: str) -> tuple[FredMacroSeriesTarget, ...]:
    normalized_group = series_group.strip().lower()
    if normalized_group == "all":
        return FRED_MACRO_SERIES

    targets = tuple(target for target in FRED_MACRO_SERIES if target.group == normalized_group)
    if targets:
        return targets

    by_series = tuple(
        target
        for target in FRED_MACRO_SERIES
        if target.series_id.lower() == normalized_group
        or target.target_code.lower() == normalized_group
    )
    if by_series:
        return by_series

    supported = sorted(
        {"all", *(target.group for target in FRED_MACRO_SERIES), *(target.series_id.lower() for target in FRED_MACRO_SERIES)}
    )
    msg = f"Unsupported FRED macro series group {series_group!r}; use one of: {', '.join(supported)}"
    raise ValueError(msg)


def _fred_fetch_start(*, target: FredMacroSeriesTarget, start: date) -> date:
    if target.handling == FRED_YOY_HANDLING:
        return start - timedelta(days=370)
    return start


def _build_fred_observation_seeds(
    *,
    targets: tuple[FredMacroSeriesTarget, ...],
    series_payloads: Mapping[str, FredSeriesObservations],
    start: date,
    end: date,
    latest_only: bool,
    retrieved_at: datetime,
) -> list[MarketIndicatorObservationSeed]:
    seeds: list[MarketIndicatorObservationSeed] = []
    for target in targets:
        series_payload = series_payloads[target.series_id]
        if target.handling == FRED_DIRECT_HANDLING:
            seeds.extend(
                _build_direct_fred_seeds(
                    target=target,
                    series_payload=series_payload,
                    start=start,
                    end=end,
                    latest_only=latest_only,
                    retrieved_at=retrieved_at,
                )
            )
        elif target.handling == FRED_YOY_HANDLING:
            seeds.extend(
                _build_yoy_fred_seeds(
                    target=target,
                    series_payload=series_payload,
                    start=start,
                    end=end,
                    latest_only=latest_only,
                    retrieved_at=retrieved_at,
                )
            )
    return seeds


def _build_direct_fred_seeds(
    *,
    target: FredMacroSeriesTarget,
    series_payload: FredSeriesObservations,
    start: date,
    end: date,
    latest_only: bool,
    retrieved_at: datetime,
) -> list[MarketIndicatorObservationSeed]:
    observations = [
        observation
        for observation in series_payload.observations
        if start <= observation.as_of <= end
    ]
    if latest_only and observations:
        observations = [max(observations, key=lambda observation: observation.as_of)]

    return [
        MarketIndicatorObservationSeed(
            code=target.target_code,
            as_of=observation.as_of,
            value=observation.value,
            source=f"FRED {target.series_id}",
            components={
                "provider": "fred",
                "source_series_id": target.series_id,
                "source_url": FRED_SERIES_URL_TEMPLATE.format(series_id=target.series_id),
                "retrieved_at": retrieved_at.isoformat(),
                "methodology": target.methodology,
                "raw_value": observation.raw_value,
                "realtime_start": observation.realtime_start,
                "realtime_end": observation.realtime_end,
            },
        )
        for observation in observations
    ]


def _build_yoy_fred_seeds(
    *,
    target: FredMacroSeriesTarget,
    series_payload: FredSeriesObservations,
    start: date,
    end: date,
    latest_only: bool,
    retrieved_at: datetime,
) -> list[MarketIndicatorObservationSeed]:
    observations_by_date = {
        observation.as_of: observation for observation in series_payload.observations
    }
    candidate_observations = [
        observation
        for observation in series_payload.observations
        if start <= observation.as_of <= end
    ]
    if latest_only:
        candidate_observations = sorted(
            candidate_observations,
            key=lambda observation: observation.as_of,
            reverse=True,
        )

    seeds: list[MarketIndicatorObservationSeed] = []
    for observation in candidate_observations:
        prior_date = _same_day_previous_year(observation.as_of)
        prior_observation = observations_by_date.get(prior_date)
        if prior_observation is None or prior_observation.value == 0:
            continue

        value = ((observation.value / prior_observation.value) - Decimal("1")) * Decimal("100")
        seed = MarketIndicatorObservationSeed(
            code=target.target_code,
            as_of=observation.as_of,
            value=value.quantize(Decimal("0.000001")),
            source=f"FRED {target.series_id} derived YoY",
            components={
                "provider": "fred",
                "source_series_id": target.series_id,
                "source_url": FRED_SERIES_URL_TEMPLATE.format(series_id=target.series_id),
                "retrieved_at": retrieved_at.isoformat(),
                "calculation": "((current_value / prior_year_value) - 1) * 100",
                "methodology": target.methodology,
                "current_value": str(observation.value),
                "prior_year_value": str(prior_observation.value),
                "source_observation_dates": {
                    "current": observation.as_of.isoformat(),
                    "prior_year": prior_observation.as_of.isoformat(),
                },
                "raw_series_id": target.series_id,
            },
        )
        seeds.append(seed)
        if latest_only:
            break

    return seeds


def _same_day_previous_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _validate_fred_observation_seeds(
    seeds: list[MarketIndicatorObservationSeed],
    *,
    session: Session,
) -> None:
    errors: list[str] = []
    parsed_seeds: list[_ParsedMarketIndicatorObservationSeed] = []
    for index, seed in enumerate(seeds, start=1):
        row_label = f"FRED observation {index}"
        _validate_audit_components(seed.components, row_label=row_label, errors=errors)
        parsed_seeds.append(
            _ParsedMarketIndicatorObservationSeed(row_label=row_label, seed=seed)
        )

    if errors:
        raise MarketIndicatorSeedImportError(errors)
    if parsed_seeds:
        _validate_seed_indicator_codes(parsed_seeds, session=session)


def _parse_market_indicator_observation_seed_file(
    path: str | Path,
) -> list[_ParsedMarketIndicatorObservationSeed]:
    seed_path = Path(path)
    suffix = seed_path.suffix.lower()

    if suffix == ".json":
        row_items = _read_json_seed_rows(seed_path)
    elif suffix == ".csv":
        row_items = _read_csv_seed_rows(seed_path)
    else:
        raise MarketIndicatorSeedImportError(
            [f"unsupported seed file extension {suffix!r}; expected .json or .csv"]
        )

    errors: list[str] = []
    parsed_seeds: list[_ParsedMarketIndicatorObservationSeed] = []
    for row_label, row in row_items:
        parsed_seed = _parse_seed_row(row_label=row_label, row=row, errors=errors)
        if parsed_seed is not None:
            parsed_seeds.append(parsed_seed)

    if not row_items:
        errors.append("seed file contains no observations")
    if errors:
        raise MarketIndicatorSeedImportError(errors)
    return parsed_seeds


def _read_json_seed_rows(seed_path: Path) -> list[tuple[str, object]]:
    try:
        raw_payload = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MarketIndicatorSeedImportError(
            [f"JSON seed file is invalid: {error.msg}"]
        ) from error
    except OSError as error:
        raise MarketIndicatorSeedImportError(
            [f"seed file could not be read: {error}"]
        ) from error

    if isinstance(raw_payload, dict):
        raw_rows = raw_payload.get("observations")
    else:
        raw_rows = raw_payload

    if not isinstance(raw_rows, list):
        raise MarketIndicatorSeedImportError(
            ["JSON seed file must be an array or an object with an observations array"]
        )
    return [(f"row {index}", row) for index, row in enumerate(raw_rows, start=1)]


def _read_csv_seed_rows(seed_path: Path) -> list[tuple[str, object]]:
    try:
        with seed_path.open(encoding="utf-8-sig", newline="") as file_handle:
            reader = csv.DictReader(file_handle)
            if reader.fieldnames is None:
                raise MarketIndicatorSeedImportError(["CSV seed file must include a header row"])
            return [
                (f"row {line_number}", row)
                for line_number, row in enumerate(reader, start=2)
            ]
    except OSError as error:
        raise MarketIndicatorSeedImportError(
            [f"seed file could not be read: {error}"]
        ) from error


def _parse_seed_row(
    *,
    row_label: str,
    row: object,
    errors: list[str],
) -> _ParsedMarketIndicatorObservationSeed | None:
    if not isinstance(row, Mapping):
        errors.append(f"{row_label}: row must be a JSON object or CSV record")
        return None

    row_errors: list[str] = []
    code = _parse_required_text(row, "code", row_label, row_errors)
    as_of = _parse_seed_date(row, row_label, row_errors)
    value = _parse_seed_decimal(row, row_label, row_errors)
    source = _parse_required_text(row, "source", row_label, row_errors)
    components = _parse_components(row, row_label, row_errors)

    if row_errors:
        errors.extend(row_errors)
        return None

    if code is None or as_of is None or value is None or source is None or components is None:
        return None

    return _ParsedMarketIndicatorObservationSeed(
        row_label=row_label,
        seed=MarketIndicatorObservationSeed(
            code=code,
            as_of=as_of,
            value=value,
            source=source,
            components=components,
        ),
    )


def _parse_required_text(
    row: Mapping[str, object],
    field_name: str,
    row_label: str,
    errors: list[str],
) -> str | None:
    raw_value = row.get(field_name)
    value = "" if raw_value is None else str(raw_value).strip()
    if not value:
        errors.append(f"{row_label}: {field_name} is required")
        return None
    return value


def _parse_seed_date(
    row: Mapping[str, object],
    row_label: str,
    errors: list[str],
) -> date | None:
    raw_value = _parse_required_text(row, "as_of", row_label, errors)
    if raw_value is None:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        errors.append(f"{row_label}: as_of must use YYYY-MM-DD format")
        return None


def _parse_seed_decimal(
    row: Mapping[str, object],
    row_label: str,
    errors: list[str],
) -> Decimal | None:
    raw_value = _parse_required_text(row, "value", row_label, errors)
    if raw_value is None:
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, ValueError):
        errors.append(f"{row_label}: value must be a decimal number")
        return None


def _parse_components(
    row: Mapping[str, object],
    row_label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    raw_components = row.get("components")
    if raw_components is None:
        raw_components = row.get("components_json")

    if isinstance(raw_components, str):
        if not raw_components.strip():
            errors.append(f"{row_label}: components is required")
            return None
        try:
            decoded_components = json.loads(raw_components)
        except json.JSONDecodeError as error:
            errors.append(f"{row_label}: components_json must be valid JSON: {error.msg}")
            return None
    else:
        decoded_components = raw_components

    if not isinstance(decoded_components, Mapping):
        errors.append(f"{row_label}: components must be a JSON object")
        return None

    components = dict(decoded_components)
    _validate_audit_components(components, row_label=row_label, errors=errors)
    return components


def _validate_audit_components(
    components: Mapping[str, object],
    *,
    row_label: str,
    errors: list[str],
) -> None:
    if not _has_non_empty_component(components, AUDIT_SOURCE_COMPONENT_KEYS):
        errors.append(
            f"{row_label}: components must include one of "
            f"{', '.join(sorted(AUDIT_SOURCE_COMPONENT_KEYS))}"
        )
    if not _has_non_empty_component(components, AUDIT_METHOD_COMPONENT_KEYS):
        errors.append(
            f"{row_label}: components must include one of "
            f"{', '.join(sorted(AUDIT_METHOD_COMPONENT_KEYS))}"
        )


def _has_non_empty_component(
    components: Mapping[str, object],
    candidate_keys: frozenset[str],
) -> bool:
    for key in candidate_keys:
        value = components.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _validate_seed_indicator_codes(
    parsed_seeds: list[_ParsedMarketIndicatorObservationSeed],
    *,
    session: Session,
) -> None:
    requested_codes = {parsed_seed.seed.code for parsed_seed in parsed_seeds}
    existing_codes = {
        code
        for (code,) in session.query(MarketIndicator.code)
        .filter(MarketIndicator.code.in_(requested_codes))
        .all()
    }
    errors = [
        f"{parsed_seed.row_label}: code {parsed_seed.seed.code!r} is not a known market indicator"
        for parsed_seed in parsed_seeds
        if parsed_seed.seed.code not in existing_codes
    ]
    if errors:
        raise MarketIndicatorSeedImportError(errors)


def _decimal_to_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def upsert_market_indicator_definition(
    definition: MarketIndicatorDefinition,
    session: Session,
    commit: bool = True,
) -> MarketIndicator:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == definition.code)
        .first()
    )
    if indicator is None:
        indicator = MarketIndicator(code=definition.code)
        session.add(indicator)

    indicator.name = definition.name
    indicator.category = definition.category
    indicator.region = definition.region
    indicator.unit = definition.unit
    indicator.description = definition.description
    indicator.display_order = definition.display_order
    indicator.is_active = definition.is_active
    session.flush()

    if commit:
        session.commit()
    return indicator


def upsert_market_indicator_observation(
    seed: MarketIndicatorObservationSeed,
    session: Session,
    commit: bool = True,
) -> MarketIndicatorObservation:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == seed.code)
        .first()
    )
    if indicator is None:
        msg = f"Market indicator definition does not exist: {seed.code}"
        raise ValueError(msg)

    observation = (
        session.query(MarketIndicatorObservation)
        .filter(MarketIndicatorObservation.indicator_id == indicator.id)
        .filter(MarketIndicatorObservation.as_of == seed.as_of)
        .first()
    )
    if observation is None:
        observation = MarketIndicatorObservation(
            indicator_id=indicator.id,
            as_of=seed.as_of,
        )
        session.add(observation)

    observation.value = seed.value
    observation.source = seed.source
    observation.components_json = seed.components
    session.flush()

    if commit:
        session.commit()
    return observation


def seed_market_indicators(
    session: Session,
    definitions: tuple[MarketIndicatorDefinition, ...] = DEFAULT_MARKET_INDICATOR_DEFINITIONS,
    observations: tuple[MarketIndicatorObservationSeed, ...] = DEFAULT_MARKET_INDICATOR_OBSERVATIONS,
    commit: bool = True,
) -> dict[str, int]:
    for definition in definitions:
        upsert_market_indicator_definition(definition, session=session, commit=False)
    for observation in observations:
        upsert_market_indicator_observation(observation, session=session, commit=False)
    if commit:
        session.commit()
    return {
        "definitions": len(definitions),
        "observations": len(observations),
    }


def get_latest_market_indicator_payload(code: str, session: Session) -> dict[str, object]:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == code)
        .filter(MarketIndicator.is_active.is_(True))
        .first()
    )
    if indicator is None:
        return {
            "code": code,
            "name": code,
            "region": None,
            "category": None,
            "status": "no_data",
            "value": None,
            "unit": None,
            "as_of": None,
            "source": None,
            "components": {},
            "no_data_reason": "Indicator definition is not available.",
        }

    observation = (
        session.query(MarketIndicatorObservation)
        .filter(MarketIndicatorObservation.indicator_id == indicator.id)
        .order_by(MarketIndicatorObservation.as_of.desc())
        .first()
    )
    if observation is None:
        return {
            "code": indicator.code,
            "name": indicator.name,
            "region": indicator.region,
            "category": indicator.category,
            "status": "no_data",
            "value": None,
            "unit": indicator.unit,
            "as_of": None,
            "source": None,
            "components": {},
            "no_data_reason": "No audited observation has been seeded for this indicator yet.",
        }

    return {
        "code": indicator.code,
        "name": indicator.name,
        "region": indicator.region,
        "category": indicator.category,
        "status": "ok",
        "value": _decimal_to_float(observation.value),
        "unit": indicator.unit,
        "as_of": observation.as_of.isoformat(),
        "source": observation.source,
        "components": observation.components_json,
        "no_data_reason": None,
    }


def get_buffett_indicator_payloads(session: Session) -> list[dict[str, object]]:
    seed_market_indicators(session=session)
    codes = [f"buffett_indicator_{region.lower()}" for region in BUFFETT_INDICATOR_REGIONS]
    return [get_latest_market_indicator_payload(code, session=session) for code in codes]


def get_macro_indicator_payloads(session: Session) -> list[dict[str, object]]:
    seed_market_indicators(session=session)
    return [get_latest_market_indicator_payload(code, session=session) for code in MACRO_INDICATOR_CODES]
