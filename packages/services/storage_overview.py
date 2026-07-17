from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


DOMAIN_TABLES: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "reference_data",
        frozenset(
            {
                "markets",
                "exchanges",
                "instruments",
                "data_sources",
            }
        ),
    ),
    (
        "market_prices",
        frozenset(
            {
                "bars_1d",
                "bars_1m",
                "intraday_minute_cache_entries",
            }
        ),
    ),
    (
        "technical_analysis",
        frozenset({"technical_indicators", "sentiment_signals"}),
    ),
    ("fundamentals", frozenset({"fundamental_snapshots"})),
    (
        "macro_economy",
        frozenset(
            {
                "market_indicators",
                "market_indicator_observations",
                "economic_calendar_events",
            }
        ),
    ),
    (
        "market_structure",
        frozenset(
            {
                "industry_daily_rankings",
                "market_daily_evidence_events",
            }
        ),
    ),
    (
        "news_disclosures",
        frozenset(
            {
                "news_articles",
                "official_disclosures",
                "official_disclosure_documents",
                "official_disclosure_sections",
            }
        ),
    ),
    (
        "research_outputs",
        frozenset(
            {
                "generated_reports",
                "research_source_notes",
                "research_briefs",
                "research_shortlist_runs",
                "research_shortlist_candidates",
                "research_candidate_outcomes",
            }
        ),
    ),
    (
        "personal_operations",
        frozenset(
            {
                "watchlists",
                "watchlist_items",
                "portfolios",
                "portfolio_positions",
                "alert_triggers",
                "task_runs",
                "instrument_universe_syncs",
                "research_evidence_backfills",
                "official_disclosure_monitor_states",
            }
        ),
    ),
    ("other", frozenset()),
)

_TABLE_DOMAIN = {
    table_name: domain_code
    for domain_code, table_names in DOMAIN_TABLES
    for table_name in table_names
}

_POSTGRES_TABLE_STATS = text(
    """
    SELECT
        c.relname AS table_name,
        GREATEST(COALESCE(s.n_live_tup, c.reltuples, 0), 0)::bigint
            AS estimated_rows,
        pg_catalog.pg_table_size(c.oid)::bigint AS data_bytes,
        pg_catalog.pg_indexes_size(c.oid)::bigint AS index_bytes,
        pg_catalog.pg_total_relation_size(c.oid)::bigint AS total_bytes
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    LEFT JOIN pg_catalog.pg_stat_user_tables AS s ON s.relid = c.oid
    WHERE n.nspname = current_schema()
      AND c.relkind IN ('r', 'p')
      AND c.relname <> 'alembic_version'
    ORDER BY c.relname
    """
)


class StorageOverviewUnavailable(RuntimeError):
    """Raised when database storage metadata cannot be read safely."""


def _optional_sum(rows: list[dict[str, Any]], field: str) -> int | None:
    values = [row[field] for row in rows if row.get(field) is not None]
    return sum(int(value) for value in values) if values else None


def _normalize_table_row(row: dict[str, Any]) -> dict[str, int | str | None]:
    return {
        "name": str(row["table_name"]),
        "estimated_rows": max(int(row.get("estimated_rows") or 0), 0),
        "data_bytes": (
            int(row["data_bytes"]) if row.get("data_bytes") is not None else None
        ),
        "index_bytes": (
            int(row["index_bytes"])
            if row.get("index_bytes") is not None
            else None
        ),
        "total_bytes": (
            int(row["total_bytes"])
            if row.get("total_bytes") is not None
            else None
        ),
    }


def _load_postgresql_table_stats(session: Session) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(_POSTGRES_TABLE_STATS).mappings()]


def _load_sqlite_table_stats(session: Session) -> list[dict[str, Any]]:
    bind = session.get_bind()
    table_names = sorted(
        table_name
        for table_name in inspect(bind).get_table_names()
        if table_name != "alembic_version" and not table_name.startswith("sqlite_")
    )
    rows: list[dict[str, Any]] = []
    for table_name in table_names:
        table = Table(table_name, MetaData(), autoload_with=bind)
        row_count = session.execute(select(func.count()).select_from(table)).scalar_one()
        rows.append(
            {
                "table_name": table_name,
                "estimated_rows": int(row_count),
                "data_bytes": None,
                "index_bytes": None,
                "total_bytes": None,
            }
        )
    return rows


def _build_storage_payload(
    *,
    engine: str,
    row_count_kind: str,
    table_rows: list[dict[str, Any]],
) -> dict[str, object]:
    normalized = [_normalize_table_row(row) for row in table_rows]
    domains: list[dict[str, object]] = []

    for domain_code, _ in DOMAIN_TABLES:
        tables = [
            row
            for row in normalized
            if _TABLE_DOMAIN.get(str(row["name"]), "other") == domain_code
        ]
        if not tables:
            continue
        domains.append(
            {
                "code": domain_code,
                "table_count": len(tables),
                "estimated_rows": sum(int(row["estimated_rows"]) for row in tables),
                "data_bytes": _optional_sum(tables, "data_bytes"),
                "index_bytes": _optional_sum(tables, "index_bytes"),
                "total_bytes": _optional_sum(tables, "total_bytes"),
                "tables": tables,
            }
        )

    return {
        "status": "ok",
        "engine": engine,
        "row_count_kind": row_count_kind,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "table_count": len(normalized),
            "estimated_rows": sum(
                int(row["estimated_rows"]) for row in normalized
            ),
            "data_bytes": _optional_sum(normalized, "data_bytes"),
            "index_bytes": _optional_sum(normalized, "index_bytes"),
            "total_bytes": _optional_sum(normalized, "total_bytes"),
        },
        "domains": domains,
    }


def get_storage_overview(session: Session) -> dict[str, object]:
    dialect = session.get_bind().dialect.name
    try:
        if dialect == "postgresql":
            rows = _load_postgresql_table_stats(session)
            return _build_storage_payload(
                engine="PostgreSQL",
                row_count_kind="estimated",
                table_rows=rows,
            )
        if dialect == "sqlite":
            rows = _load_sqlite_table_stats(session)
            return _build_storage_payload(
                engine="SQLite",
                row_count_kind="exact",
                table_rows=rows,
            )
        raise StorageOverviewUnavailable("Unsupported database engine")
    except StorageOverviewUnavailable:
        raise
    except SQLAlchemyError as error:
        session.rollback()
        raise StorageOverviewUnavailable("Storage statistics unavailable") from error
