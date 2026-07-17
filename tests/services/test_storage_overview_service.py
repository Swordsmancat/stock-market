from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from packages.services.storage_overview import (
    _build_storage_payload,
    get_storage_overview,
)


def test_build_storage_payload_groups_known_and_unknown_tables():
    payload = _build_storage_payload(
        engine="PostgreSQL",
        row_count_kind="estimated",
        table_rows=[
            {
                "table_name": "bars_1d",
                "estimated_rows": 120,
                "data_bytes": 1000,
                "index_bytes": 200,
                "total_bytes": 1200,
            },
            {
                "table_name": "future_dataset",
                "estimated_rows": 7,
                "data_bytes": 70,
                "index_bytes": 30,
                "total_bytes": 100,
            },
        ],
    )

    assert payload["summary"] == {
        "table_count": 2,
        "estimated_rows": 127,
        "data_bytes": 1070,
        "index_bytes": 230,
        "total_bytes": 1300,
    }
    domains = {domain["code"]: domain for domain in payload["domains"]}
    assert domains["market_prices"]["estimated_rows"] == 120
    assert domains["other"]["tables"][0]["name"] == "future_dataset"
    assert "database_url" not in payload


def test_sqlite_overview_uses_exact_counts_and_truthful_unknown_sizes():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE news_articles (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO news_articles (id) VALUES (1), (2)"))
        connection.execute(text("CREATE TABLE future_dataset (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO future_dataset (id) VALUES (1)"))

    session = sessionmaker(bind=engine)()
    try:
        payload = get_storage_overview(session)
    finally:
        session.close()

    assert payload["engine"] == "SQLite"
    assert payload["row_count_kind"] == "exact"
    assert payload["summary"] == {
        "table_count": 2,
        "estimated_rows": 3,
        "data_bytes": None,
        "index_bytes": None,
        "total_bytes": None,
    }
    domains = {domain["code"]: domain for domain in payload["domains"]}
    assert domains["news_disclosures"]["estimated_rows"] == 2
    assert domains["other"]["estimated_rows"] == 1
