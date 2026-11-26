"""In-house SQL migration runner (ken #1249, replaces yoyo-migrations).

Applies ``src/dashboard/migrations/NNNN.<name>.sql`` in lexical order over a plain
PyMySQL connection, and records each applied file in ``_yoyo_migration``.

Why not yoyo any more
    yoyo treats a ``.sql`` migration as one block of statements: its own rollback
    lives in a separate ``<id>.rollback.sql`` file, so our in-file ``-- rollback``
    marker was a plain comment and everything below it ran on *forward* apply. That
    is the root cause of the 0008 → 0009, 0010 → 0011 and 0012 → 0013 incidents
    (column added, then dropped by its own "rollback", migration recorded as
    applied). yoyo also had no OpenSSF scorecard nor PyPI attestation, pulled three
    transitive packages, and ``kenboard migrate`` passed the DDL password to the
    ``yoyo`` binary in argv, readable through ``ps`` by any local user.

Contract
    - **Forward only.** A line that is exactly ``-- rollback`` ends the forward
      section; what follows is never executed. A real rollback is a new forward
      migration.
    - **Tracking table compatible with yoyo.** ``_yoyo_migration``
      (``migration_hash`` = sha256 of the id, ``migration_id``, ``applied_at_utc``)
      is kept as is: databases migrated by yoyo replay nothing and the */about*
      page (#1165) keeps reading it. yoyo's other tables (``_yoyo_log``,
      ``_yoyo_version``, ``yoyo_lock``) are left untouched.
    - **Recorded after success.** Statements run in autocommit (MySQL DDL commits
      implicitly anyway); a migration is recorded only once all its statements
      succeeded, so a failure is replayed from the start of that file on the next
      run — hence the idempotency rules of CLAUDE.md.
    - ``-- depends: <id> …`` must name migrations applied before this one.
    - One ``GET_LOCK`` per database prevents two concurrent ``kenboard migrate``.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymysql

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
TRACKING_TABLE = "_yoyo_migration"
LOCK_TIMEOUT_S = 30

_ROLLBACK_MARKER = re.compile(r"^--\s*rollback\s*$", re.MULTILINE)
_DEPENDS = re.compile(r"^--\s*depends:(.*)$", re.MULTILINE)
_QUOTES = "'\"`"


class MigrationError(Exception):
    """A migration file is invalid or could not be applied."""


@dataclass(frozen=True)
class Migration:
    """One parsed migration file."""

    id: str
    depends: tuple[str, ...]
    statements: tuple[str, ...]

    @property
    def hash(self) -> str:
        """Primary key in ``_yoyo_migration`` (sha256 of the id, as yoyo)."""
        return hashlib.sha256(self.id.encode()).hexdigest()


def _skip_comment(sql: str, i: int) -> int:
    """Return the index after the comment starting at ``sql[i]``, or ``i``."""
    if sql.startswith("/*", i):
        end = sql.find("*/", i + 2)
        if end < 0:
            msg = "unterminated /* comment"
            raise MigrationError(msg)
        return end + 2
    line_comment = sql[i] == "#" or (
        sql.startswith("--", i) and (i + 2 == len(sql) or sql[i + 2].isspace())
    )
    if line_comment:
        end = sql.find("\n", i)
        return len(sql) if end < 0 else end
    return i


def _skip_quoted(sql: str, i: int) -> int:
    """Return the index after the quoted literal/identifier opening at ``sql[i]``.

    Handles doubled quotes (``'it''s'``) and backslash escapes (not inside backtick
    identifiers).
    """
    quote, i = sql[i], i + 1
    while i < len(sql):
        if sql[i] == "\\" and quote != "`":
            i += 2
        elif sql[i] == quote:
            if sql.startswith(quote, i + 1):
                i += 2
            else:
                return i + 1
        else:
            i += 1
    msg = f"unterminated {quote} literal"
    raise MigrationError(msg)


def split_statements(sql: str) -> list[str]:
    """Split ``sql`` on top-level ``;``, dropping comments.

    ``;`` inside quoted literals, identifiers and comments does not split. No
    ``DELIMITER`` support (no procedure/trigger in our migrations).
    """
    statements: list[str] = []
    start = i = 0
    chunks: list[str] = []
    while i < len(sql):
        after_comment = _skip_comment(sql, i)
        if after_comment != i:
            chunks.append(sql[start:i] + " ")
            start = i = after_comment
        elif sql[i] in _QUOTES:
            i = _skip_quoted(sql, i)
        elif sql[i] == ";":
            chunks.append(sql[start:i])
            statements.append("".join(chunks))
            chunks, start, i = [], i + 1, i + 1
        else:
            i += 1
    chunks.append(sql[start:])
    statements.append("".join(chunks))
    return [s.strip() for s in statements if s.strip()]


def forward_section(text: str) -> str:
    """Return the part of a migration above its ``-- rollback`` marker line."""
    marker = _ROLLBACK_MARKER.search(text)
    return text if marker is None else text[: marker.start()]


def parse_migration(path: Path) -> Migration:
    """Parse one migration file.

    Raises:
        MigrationError: nothing to run above the ``-- rollback`` marker.
    """
    forward = forward_section(path.read_text(encoding="utf-8"))
    depends = tuple(dep for line in _DEPENDS.findall(forward) for dep in line.split())
    statements = tuple(split_statements(forward))
    if not statements:
        msg = f"{path.name}: no statement above the -- rollback marker"
        raise MigrationError(msg)
    return Migration(path.stem, depends, statements)


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Parse every ``*.sql`` of ``directory`` in lexical order, checking depends.

    Raises:
        MigrationError: a ``-- depends:`` names no earlier migration.
    """
    migrations = [parse_migration(p) for p in sorted(directory.glob("*.sql"))]
    seen: set[str] = set()
    for migration in migrations:
        missing = [dep for dep in migration.depends if dep not in seen]
        if missing:
            msg = f"{migration.id}: depends on {', '.join(missing)}, not an earlier migration"
            raise MigrationError(msg)
        seen.add(migration.id)
    return migrations


def _ensure_tracking_table(cur: pymysql.cursors.Cursor) -> None:
    """Create ``_yoyo_migration`` with yoyo's DDL when missing."""
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} ("
        " migration_hash VARCHAR(64),"
        " migration_id VARCHAR(255),"
        " applied_at_utc TIMESTAMP,"
        " PRIMARY KEY (migration_hash))"
    )


def apply_migrations(
    conn: pymysql.Connection,
    migrations: list[Migration],
    echo: Callable[[str], None] = print,
) -> list[str]:
    """Apply the pending ``migrations`` on ``conn``; return the applied ids.

    Raises:
        MigrationError: the lock is held elsewhere or a statement failed (the
            failing migration is not recorded).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT GET_LOCK(CONCAT('kenboard_migrate.', DATABASE()), %s)",
            (LOCK_TIMEOUT_S,),
        )
        (got_lock,) = cur.fetchone()
        if got_lock != 1:
            msg = "another `kenboard migrate` holds the migration lock"
            raise MigrationError(msg)
        try:
            _ensure_tracking_table(cur)
            cur.execute(f"SELECT migration_hash FROM {TRACKING_TABLE}")
            applied = {row[0] for row in cur.fetchall()}
            done: list[str] = []
            for migration in migrations:
                if migration.hash in applied:
                    continue
                echo(f"applying {migration.id}")
                for number, statement in enumerate(migration.statements, 1):
                    try:
                        cur.execute(statement)
                    except pymysql.Error as exc:
                        msg = f"{migration.id}, statement {number}: {exc}"
                        raise MigrationError(msg) from exc
                cur.execute(
                    f"INSERT INTO {TRACKING_TABLE}"
                    " (migration_hash, migration_id, applied_at_utc)"
                    " VALUES (%s, %s, UTC_TIMESTAMP())",
                    (migration.hash, migration.id),
                )
                done.append(migration.id)
            return done
        finally:
            cur.execute("SELECT RELEASE_LOCK(CONCAT('kenboard_migrate.', DATABASE()))")


def migrate(  # noqa: PLR0913
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    echo: Callable[[str], None] = print,
) -> list[str]:
    """Connect with the DDL account and apply every pending migration."""
    migrations = load_migrations()
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=True,
    )
    try:
        done = apply_migrations(conn, migrations, echo)
    finally:
        conn.close()
    echo(
        f"{database}: {len(done)} migration(s) applied,"
        f" {len(migrations) - len(done)} already up to date"
    )
    return done
