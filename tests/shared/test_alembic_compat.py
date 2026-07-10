import ast
from pathlib import Path
from unittest.mock import Mock

from packages.shared.alembic_compat import ALEMBIC_VERSION_LENGTH, ensure_alembic_version_capacity


class FakeConnection:
    def __init__(self, dialect_name: str) -> None:
        self.dialect = Mock(name=dialect_name)
        self.dialect.name = dialect_name
        self.executed = []

    def execute(self, statement) -> None:
        self.executed.append(statement)


def test_postgresql_legacy_alembic_version_column_is_widened(monkeypatch) -> None:
    connection = FakeConnection("postgresql")
    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": Mock(length=32)}]
    monkeypatch.setattr("packages.shared.alembic_compat.inspect", lambda _connection: inspector)

    changed = ensure_alembic_version_capacity(connection)

    assert changed is True
    assert len(connection.executed) == 1
    assert "ALTER COLUMN version_num TYPE VARCHAR(128)" in str(connection.executed[0])


def test_current_or_non_postgresql_version_columns_are_unchanged(monkeypatch) -> None:
    inspector = Mock()
    inspector.has_table.return_value = True
    inspector.get_columns.return_value = [{"name": "version_num", "type": Mock(length=128)}]
    monkeypatch.setattr("packages.shared.alembic_compat.inspect", lambda _connection: inspector)

    current_postgres = FakeConnection("postgresql")
    sqlite = FakeConnection("sqlite")

    assert ensure_alembic_version_capacity(current_postgres) is False
    assert ensure_alembic_version_capacity(sqlite) is False
    assert current_postgres.executed == []
    assert sqlite.executed == []


def test_all_migration_revision_ids_fit_the_compatibility_capacity() -> None:
    revision_ids: list[str] = []
    for migration_path in Path("alembic/versions").glob("*.py"):
        tree = ast.parse(migration_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if any(isinstance(target, ast.Name) and target.id == "revision" for target in node.targets):
                value = ast.literal_eval(node.value)
                if isinstance(value, str):
                    revision_ids.append(value)

    assert revision_ids
    assert max(map(len, revision_ids)) <= ALEMBIC_VERSION_LENGTH
    assert any(len(revision_id) > 32 for revision_id in revision_ids)
