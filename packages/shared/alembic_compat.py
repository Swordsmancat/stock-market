"""Compatibility guards for Alembic metadata used by existing databases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

ALEMBIC_VERSION_LENGTH = 128


def ensure_alembic_version_capacity(connection: Connection) -> bool:
    """Create or widen PostgreSQL's revision column for descriptive identifiers."""
    if connection.dialect.name != "postgresql":
        return False

    inspector = inspect(connection)
    if not inspector.has_table("alembic_version"):
        connection.execute(
            text(
                "CREATE TABLE alembic_version ("
                f"version_num VARCHAR({ALEMBIC_VERSION_LENGTH}) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            )
        )
        return True

    version_column = next(
        (
            column
            for column in inspector.get_columns("alembic_version")
            if column["name"] == "version_num"
        ),
        None,
    )
    current_length = getattr(version_column.get("type"), "length", None) if version_column else None
    if current_length is not None and current_length >= ALEMBIC_VERSION_LENGTH:
        return False

    connection.execute(
        text(
            "ALTER TABLE alembic_version "
            f"ALTER COLUMN version_num TYPE VARCHAR({ALEMBIC_VERSION_LENGTH})"
        )
    )
    return True
