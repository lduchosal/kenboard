"""Unit tests for the in-house migration runner (ken #1249).

No database.
"""

import hashlib
from pathlib import Path
from typing import Self

import pymysql
import pytest

from dashboard import migrate as m

# -- split_statements ---------------------------------------------------------


def test_split_on_top_level_semicolons_and_drop_comments() -> None:
    sql = (
        "-- header; not a statement\n"
        "CREATE TABLE a (id INT); # trailing; comment\n"
        "/* block; comment */ SELECT 1;\n"
        "SELECT 2"
    )
    assert m.split_statements(sql) == [
        "CREATE TABLE a (id INT)",
        "SELECT 1",
        "SELECT 2",
    ]


def test_semicolons_inside_literals_do_not_split() -> None:
    sql = (
        "SET @s := 'ALTER TABLE t ADD c CHAR(1) NOT NULL DEFAULT '''';';\n"
        "SELECT \"a;b\", `we;ird`, 'back\\'slash;';"
    )
    assert m.split_statements(sql) == [
        "SET @s := 'ALTER TABLE t ADD c CHAR(1) NOT NULL DEFAULT '''';'",
        "SELECT \"a;b\", `we;ird`, 'back\\'slash;'",
    ]


def test_double_dash_without_space_is_not_a_comment() -> None:
    assert m.split_statements("SELECT 5--3;") == ["SELECT 5--3"]


@pytest.mark.parametrize("sql", ["SELECT 'open;", "SELECT 1 /* open"])
def test_unterminated_literal_or_comment_is_an_error(sql: str) -> None:
    with pytest.raises(m.MigrationError, match="unterminated"):
        m.split_statements(sql)


# -- forward_section / parse --------------------------------------------------


def test_rollback_block_is_never_part_of_the_forward_section() -> None:
    text = (
        "-- rollback between dev runs (prose, not the marker)\n"
        "ALTER TABLE users ADD COLUMN email VARCHAR(255);\n"
        "-- rollback\n"
        "ALTER TABLE users DROP COLUMN email;\n"
    )
    assert m.split_statements(m.forward_section(text)) == [
        "ALTER TABLE users ADD COLUMN email VARCHAR(255)"
    ]


def test_parse_migration_reads_depends(tmp_path: Path) -> None:
    path = tmp_path / "0002.b.sql"
    path.write_text("-- depends: 0001.a 0000.z\nSELECT 1;\n-- rollback\nSELECT 2;\n")
    migration = m.parse_migration(path)
    assert migration.id == "0002.b"
    assert migration.depends == ("0001.a", "0000.z")
    assert migration.statements == ("SELECT 1",)
    assert migration.hash == hashlib.sha256(b"0002.b").hexdigest()


def test_empty_forward_section_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "0001.a.sql"
    path.write_text("-- nothing\n-- rollback\nSELECT 1;\n")
    with pytest.raises(m.MigrationError, match="no statement"):
        m.parse_migration(path)


def test_depends_must_name_an_earlier_migration(tmp_path: Path) -> None:
    (tmp_path / "0001.a.sql").write_text("-- depends: 0002.b\nSELECT 1;\n")
    (tmp_path / "0002.b.sql").write_text("SELECT 2;\n")
    with pytest.raises(m.MigrationError, match=r"0001\.a: depends on 0002\.b"):
        m.load_migrations(tmp_path)


def test_shipped_migrations_parse_and_skip_their_rollback() -> None:
    """The real files: linear chain, and 0008/0010/0012 lose their DROP."""
    migrations = m.load_migrations()
    assert [mig.id[:4] for mig in migrations] == [f"{n:04d}" for n in range(1, 23)]
    by_id = {mig.id[:4]: mig for mig in migrations}
    for key in ("0008", "0010", "0012"):
        assert not any("DROP" in s for s in by_id[key].statements), key


# -- apply_migrations ---------------------------------------------------------


class FakeCursor:
    """Records executed SQL; answers GET_LOCK and the tracking SELECT."""

    def __init__(self, applied: set[str], *, lock: int = 1, fail_on: str = "") -> None:
        self.applied = applied
        self.lock = lock
        self.fail_on = fail_on
        self.executed: list[str] = []
        self._result: list[tuple[object, ...]] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, args: tuple[object, ...] | None = None) -> None:
        self.executed.append(sql)
        if self.fail_on and self.fail_on in sql:
            raise pymysql.err.OperationalError(1054, "Unknown column")
        if "GET_LOCK" in sql:
            self._result = [(self.lock,)]
        elif sql.startswith("SELECT migration_hash"):
            self._result = [(h,) for h in self.applied]
        elif sql.startswith(f"INSERT INTO {m.TRACKING_TABLE}"):
            assert args is not None
            self.applied.add(str(args[0]))

    def fetchone(self) -> tuple[object, ...]:
        return self._result[0]

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._result


class FakeConn:
    """Hands out one shared FakeCursor."""

    def __init__(self, cursor: FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor

    def close(self) -> None:
        self.closed = True


def _migs() -> list[m.Migration]:
    return [
        m.Migration("0001.a", (), ("CREATE TABLE a (id INT)",)),
        m.Migration("0002.b", ("0001.a",), ("ALTER TABLE a ADD b INT", "SELECT 2")),
    ]


def test_applies_only_pending_and_records_them() -> None:
    first, second = _migs()
    cur = FakeCursor({first.hash})
    done = m.apply_migrations(FakeConn(cur), [first, second], echo=lambda _: None)  # type: ignore[arg-type]
    assert done == ["0002.b"]
    assert second.hash in cur.applied
    assert "CREATE TABLE a (id INT)" not in cur.executed
    assert cur.executed[-1].startswith("SELECT RELEASE_LOCK")


def test_failed_statement_is_not_recorded_and_releases_the_lock() -> None:
    cur = FakeCursor(set(), fail_on="ADD b")
    with pytest.raises(m.MigrationError, match=r"0002\.b, statement 1"):
        m.apply_migrations(FakeConn(cur), _migs(), echo=lambda _: None)  # type: ignore[arg-type]
    assert len(cur.applied) == 1  # 0001.a only
    assert cur.executed[-1].startswith("SELECT RELEASE_LOCK")


def test_lock_held_elsewhere_aborts_before_any_ddl() -> None:
    cur = FakeCursor(set(), lock=0)
    with pytest.raises(m.MigrationError, match="holds the migration lock"):
        m.apply_migrations(FakeConn(cur), _migs(), echo=lambda _: None)  # type: ignore[arg-type]
    assert len(cur.executed) == 1


def test_migrate_connects_in_autocommit_applies_and_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = FakeConn(FakeCursor(set()))
    seen: dict[str, object] = {}

    def fake_connect(**kwargs: object) -> FakeConn:
        seen.update(kwargs)
        return conn

    monkeypatch.setattr(m.pymysql, "connect", fake_connect)
    lines: list[str] = []
    done = m.migrate(
        host="h", port=1, user="u", password="p", database="d", echo=lines.append
    )
    assert len(done) == len(m.load_migrations())
    assert seen["autocommit"] is True
    assert seen["database"] == "d"
    assert conn.closed
    assert lines[-1] == f"d: {len(done)} migration(s) applied, 0 already up to date"
