"""Compatibility guards for Alembic metadata used by existing databases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

ALEMBIC_VERSION_LENGTH = 128


def ensure_alembic_version_capacity(connection: Connection) -> bool:
    """Widen PostgreSQL's legacy 32-character revision column when needed."""
    if connection.dialect.name != "postgresql":
        return False

    inspector = inspect(connection)
    if not inspector.has_table("alembic_version"):
        return False

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
