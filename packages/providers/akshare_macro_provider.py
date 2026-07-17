from __future__ import annotations

import calendar
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


AKSHARE_MACRO_SOURCE_URLS = {
    "lpr": "https://data.eastmoney.com/cjsj/globalRateLPR.html",
    "shibor": "https://datacenter.jin10.com/reportType/dc_shibor",
    "repo_rates": "https://www.chinamoney.com.cn/chinese/bkfrr/",
    "bond_yields": "https://data.eastmoney.com/cjsj/zmgzsyl.html",
    "cpi": "https://data.eastmoney.com/cjsj/cpi.html",
    "ppi": "https://data.eastmoney.com/cjsj/ppi.html",
    "retail": "https://data.eastmoney.com/cjsj/xfp.html",
    "pmi": "https://data.eastmoney.com/cjsj/pmi.html",
    "gdp": "https://data.eastmoney.com/cjsj/gdp.html",
    "money": "https://data.eastmoney.com/cjsj/hbgyl.html",
    "trade": "https://data.eastmoney.com/cjsj/hgjck.html",
    "fiscal": "https://data.eastmoney.com/cjsj/qgsssr.html",
}


@dataclass(frozen=True)
class AkShareMacroTarget:
    code: str
    value_column: str
    methodology: str


@dataclass(frozen=True)
class AkShareMacroFamily:
    id: str
    provider_function: str
    date_column: str
    targets: tuple[AkShareMacroTarget, ...]


@dataclass(frozen=True)
class AkShareMacroObservation:
    code: str
    as_of: date
    value: Decimal
    source: str
    components: dict[str, Any]


@dataclass(frozen=True)
class AkShareMacroFamilyResult:
    family: str
    status: str
    fetched: int
    skipped: int
    observations: tuple[AkShareMacroObservation, ...]
    diagnostics: tuple[str, ...]


AKSHARE_MACRO_FAMILIES: tuple[AkShareMacroFamily, ...] = (
    AkShareMacroFamily(
        id="lpr",
        provider_function="macro_china_lpr",
        date_column="TRADE_DATE",
        targets=(
            AkShareMacroTarget("cn_lpr_1y", "LPR1Y", "China one-year loan prime rate."),
            AkShareMacroTarget("cn_lpr_5y", "LPR5Y", "China five-year loan prime rate."),
        ),
    ),
    AkShareMacroFamily(
        id="shibor",
        provider_function="macro_china_shibor_all",
        date_column="日期",
        targets=(
            AkShareMacroTarget(
                "cn_shibor_overnight",
                "O/N-定价",
                "Shanghai interbank offered rate, overnight fixing.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="repo_rates",
        provider_function="repo_rate_hist",
        date_column="date",
        targets=(
            AkShareMacroTarget(
                "cn_fr007",
                "FR007",
                "Seven-day repo fixing rate published by ChinaMoney.",
            ),
            AkShareMacroTarget(
                "cn_fdr007",
                "FDR007",
                "Seven-day depository-institutions repo fixing rate published by ChinaMoney.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="bond_yields",
        provider_function="bond_zh_us_rate",
        date_column="日期",
        targets=(
            AkShareMacroTarget(
                "cn_10y_yield",
                "中国国债收益率10年",
                "China 10-year government bond yield.",
            ),
            AkShareMacroTarget(
                "us_10y_yield",
                "美国国债收益率10年",
                "US 10-year Treasury yield from the China/US yield comparison feed.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="cpi",
        provider_function="macro_china_cpi",
        date_column="月份",
        targets=(
            AkShareMacroTarget("cn_cpi_yoy", "全国-同比增长", "China national CPI YoY."),
        ),
    ),
    AkShareMacroFamily(
        id="ppi",
        provider_function="macro_china_ppi",
        date_column="月份",
        targets=(
            AkShareMacroTarget("cn_ppi_yoy", "当月同比增长", "China PPI YoY."),
        ),
    ),
    AkShareMacroFamily(
        id="retail",
        provider_function="macro_china_consumer_goods_retail",
        date_column="月份",
        targets=(
            AkShareMacroTarget(
                "cn_retail_sales_yoy",
                "同比增长",
                "China total retail sales of consumer goods YoY.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="pmi",
        provider_function="macro_china_pmi",
        date_column="月份",
        targets=(
            AkShareMacroTarget(
                "cn_manufacturing_pmi",
                "制造业-指数",
                "China official manufacturing purchasing managers index.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="gdp",
        provider_function="macro_china_gdp",
        date_column="季度",
        targets=(
            AkShareMacroTarget(
                "cn_gdp_yoy",
                "国内生产总值-同比增长",
                "China cumulative GDP YoY for the reported quarter.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="money",
        provider_function="macro_china_money_supply",
        date_column="月份",
        targets=(
            AkShareMacroTarget(
                "cn_m2_yoy",
                "货币和准货币(M2)-同比增长",
                "China M2 money supply YoY.",
            ),
            AkShareMacroTarget(
                "cn_m1_yoy",
                "货币(M1)-同比增长",
                "China M1 money supply YoY.",
            ),
            AkShareMacroTarget(
                "cn_m0_yoy",
                "流通中的现金(M0)-同比增长",
                "China M0 money supply YoY.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="trade",
        provider_function="macro_china_hgjck",
        date_column="月份",
        targets=(
            AkShareMacroTarget(
                "cn_exports_yoy",
                "当月出口额-同比增长",
                "China monthly exports YoY from customs statistics.",
            ),
            AkShareMacroTarget(
                "cn_imports_yoy",
                "当月进口额-同比增长",
                "China monthly imports YoY from customs statistics.",
            ),
        ),
    ),
    AkShareMacroFamily(
        id="fiscal",
        provider_function="macro_china_national_tax_receipts",
        date_column="季度",
        targets=(
            AkShareMacroTarget(
                "cn_tax_revenue_yoy",
                "较上年同期",
                "China cumulative national tax revenue YoY.",
            ),
        ),
    ),
)


_MONTH_PATTERN = re.compile(r"(?P<year>\d{4})年(?P<month>\d{1,2})月")
_QUARTER_PATTERN = re.compile(r"(?P<year>\d{4})年第1(?:-(?P<quarter>[1-4]))?季度")


def _parse_period(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass

    month_match = _MONTH_PATTERN.search(text)
    if month_match:
        year = int(month_match.group("year"))
        month = int(month_match.group("month"))
        return date(year, month, calendar.monthrange(year, month)[1])

    quarter_match = _QUARTER_PATTERN.search(text)
    if quarter_match:
        year = int(quarter_match.group("year"))
        quarter = int(quarter_match.group("quarter") or 1)
        month = quarter * 3
        return date(year, month, calendar.monthrange(year, month)[1])
    return None


def _parse_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not parsed.is_finite() or not math.isfinite(float(parsed)):
        return None
    return parsed


class AkShareMacroProvider:
    def __init__(
        self,
        fetchers: Mapping[str, Callable[[], Any]] | None = None,
    ) -> None:
        self._fetchers = dict(fetchers or {})

    def _default_fetcher(self, family: AkShareMacroFamily) -> Callable[[], Any]:
        import akshare as ak  # type: ignore[import-untyped]

        provider_function = getattr(ak, family.provider_function)
        if family.id == "bond_yields":
            start_date = (date.today() - timedelta(days=180)).strftime("%Y%m%d")
            return lambda: provider_function(start_date=start_date)
        if family.id == "repo_rates":
            import pandas as pd

            today = date.today()
            previous_month_end = today.replace(day=1) - timedelta(days=1)
            previous_month_start = previous_month_end.replace(day=1)

            def fetch_repo_rates() -> Any:
                frames = (
                    provider_function(
                        start_date=previous_month_start.strftime("%Y%m%d"),
                        end_date=previous_month_end.strftime("%Y%m%d"),
                    ),
                    provider_function(
                        start_date=today.replace(day=1).strftime("%Y%m%d"),
                        end_date=today.strftime("%Y%m%d"),
                    ),
                )
                return pd.concat(frames, ignore_index=True)

            return fetch_repo_rates
        return provider_function

    def fetch_family(
        self,
        family: AkShareMacroFamily,
        *,
        history_limit: int = 24,
        retrieved_at: datetime | None = None,
    ) -> AkShareMacroFamilyResult:
        fetcher = self._fetchers.get(family.id) or self._default_fetcher(family)
        try:
            frame = fetcher()
        except Exception as error:  # provider libraries expose heterogeneous errors
            return AkShareMacroFamilyResult(
                family=family.id,
                status="error",
                fetched=0,
                skipped=0,
                observations=(),
                diagnostics=(f"{family.id}: provider_error:{type(error).__name__}",),
            )

        columns = set(getattr(frame, "columns", ()))
        required_columns = {family.date_column, *(target.value_column for target in family.targets)}
        if not required_columns.issubset(columns):
            return AkShareMacroFamilyResult(
                family=family.id,
                status="error",
                fetched=len(frame) if hasattr(frame, "__len__") else 0,
                skipped=0,
                observations=(),
                diagnostics=(f"{family.id}: schema_mismatch",),
            )

        now = retrieved_at or datetime.now(timezone.utc)
        source_url = AKSHARE_MACRO_SOURCE_URLS[family.id]
        parsed_by_code: dict[str, list[AkShareMacroObservation]] = {
            target.code: [] for target in family.targets
        }
        skipped = 0
        for row in frame.to_dict(orient="records"):
            as_of = _parse_period(row.get(family.date_column))
            if as_of is None:
                skipped += len(family.targets)
                continue
            for target in family.targets:
                value = _parse_decimal(row.get(target.value_column))
                if value is None:
                    skipped += 1
                    continue
                parsed_by_code[target.code].append(
                    AkShareMacroObservation(
                        code=target.code,
                        as_of=as_of,
                        value=value,
                        source=f"AkShare {family.provider_function}",
                        components={
                            "provider": "akshare",
                            "provider_function": family.provider_function,
                            "source_name": "AkShare public macro adapter",
                            "source_url": source_url,
                            "source_date_field": family.date_column,
                            "source_value_field": target.value_column,
                            "retrieved_at": now.isoformat(),
                            "methodology": target.methodology,
                        },
                    )
                )

        observations: list[AkShareMacroObservation] = []
        for target in family.targets:
            deduplicated = {
                observation.as_of: observation for observation in parsed_by_code[target.code]
            }
            ordered = sorted(deduplicated.values(), key=lambda item: item.as_of)
            observations.extend(ordered[-history_limit:])

        status = "ok" if observations else "no_data"
        diagnostics = () if observations else (f"{family.id}: no_valid_observations",)
        return AkShareMacroFamilyResult(
            family=family.id,
            status=status,
            fetched=len(frame),
            skipped=skipped,
            observations=tuple(observations),
            diagnostics=diagnostics,
        )

    def fetch(
        self,
        *,
        family: str = "all",
        history_limit: int = 24,
        retrieved_at: datetime | None = None,
    ) -> tuple[AkShareMacroFamilyResult, ...]:
        normalized_family = family.strip().lower()
        selected = (
            AKSHARE_MACRO_FAMILIES
            if normalized_family == "all"
            else tuple(item for item in AKSHARE_MACRO_FAMILIES if item.id == normalized_family)
        )
        if not selected:
            supported = ", ".join(item.id for item in AKSHARE_MACRO_FAMILIES)
            raise ValueError(
                f"Unsupported AkShare macro family '{family}'. Expected all or one of: {supported}."
            )
        return tuple(
            self.fetch_family(
                item,
                history_limit=history_limit,
                retrieved_at=retrieved_at,
            )
            for item in selected
        )
