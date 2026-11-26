#!/usr/bin/env python3
"""OpenSSF Scorecard of the runtime dependencies, tracked over time (ken #1242).

Non-blocking companion of the dependency gates: a low score is not a defect of
kenboard, but its evolution is a supply-chain signal the operator must hear about.

For every package of the runtime closure (scripts/runtime_deps.py) the script asks
deps.dev (https://docs.deps.dev/api/v3/) for the source repository and whether the
release carries a PyPI publish attestation (Trusted Publishing), then the repository's
OpenSSF Scorecard (overall score + per-check scores) from the OpenSSF API
(api.securityscorecards.dev, refreshed weekly). deps.dev's own copy of the scorecard
lags by months (2026-08 data in 2026-11): it is only a fallback for repositories
the OpenSSF weekly scan doesn't cover; ``scorecard_source`` records which one answered.

State, both versioned:
- ``doc/dep-scorecard.csv`` — history: one full snapshot (one row per package) each
  time the observed state changes. Scorecard refresh dates alone don't count.
- ``doc/dep-scorecard.md`` — scoreboard: latest snapshot + divergences between the
  last two snapshots. Generated from the CSV only, never edit by hand.

Divergences are computed against the last snapshot **committed** to git (``git show
HEAD:doc/dep-scorecard.csv``), and the working CSV is rebuilt as committed history +
at most one pending snapshot. Repeated quality runs therefore neither bloat the
history nor hide a divergence: it is reported on every run until the release commit
records it. Each divergence prints as a ``warning:`` line, which publish.sh surfaces
as ⚠ for the operator.

deps.dev unreachable: a warning, the state files are left untouched, exit 0.

Usage:
    .venv/bin/python scripts/dep_scorecard.py
"""

import csv
import datetime
import io
import statistics
import subprocess
import sys
import urllib.error
import urllib.parse
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

from runtime_deps import REPO, get_json, runtime_closure

HISTORY = REPO / "doc" / "dep-scorecard.csv"
BOARD = REPO / "doc" / "dep-scorecard.md"
DEPS_DEV = "https://api.deps.dev/v3"
OPENSSF = "https://api.securityscorecards.dev/projects"
ATTESTATION = "PYPI_PUBLISH_ATTESTATION"

CHECKS = (
    "Maintained",
    "Code-Review",
    "Dangerous-Workflow",
    "Signed-Releases",
    "Branch-Protection",
    "Token-Permissions",
    "Pinned-Dependencies",
    "Vulnerabilities",
    "Security-Policy",
    "Packaging",
    "Binary-Artifacts",
    "Fuzzing",
    "SAST",
    "CI-Tests",
    "CII-Best-Practices",
    "Contributors",
    "Dependency-Update-Tool",
    "License",
)
# A check of these falling to 0 is a divergence on its own (abandoned project,
# exploitable CI workflow, unreviewed pushes).
CRITICAL = ("Maintained", "Dangerous-Workflow", "Code-Review")
SCORE_DROP = 1.0
LOW_SCORE = 5.0
STALE_DAYS = 90
HTTP_NOT_FOUND = 404

FIELDS = (
    "snapshot",
    "package",
    "version",
    "repo",
    "attested",
    "score",
    "scorecard_date",
    "scorecard_source",
    *CHECKS,
)
# What makes a new snapshot worth recording (scorecard_date refreshes weekly alone).
COMPARED = tuple(f for f in FIELDS if f not in {"snapshot", "scorecard_date"})

Row = dict[str, str]


class FetchError(Exception):
    """deps.dev could not be queried (network, 5xx, rate limit)."""


def _get(url: str) -> dict[str, object] | None:
    """GET a JSON resource; ``None`` on 404."""
    try:
        data = get_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            return None
        msg = f"{url}: HTTP {exc.code}"
        raise FetchError(msg) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        msg = f"{url}: {exc}"
        raise FetchError(msg) from exc
    return data if isinstance(data, dict) else None


def _scorecard(repo: str) -> tuple[dict[str, object] | None, str]:
    """Scorecard of ``repo``: OpenSSF API first, deps.dev's stale copy as fallback."""
    fresh = _get(f"{OPENSSF}/{repo}")
    if fresh and "score" in fresh:
        return {
            "overallScore": fresh["score"],
            "date": fresh.get("date"),
            "checks": fresh.get("checks", []),
        }, "openssf"
    project = _get(f"{DEPS_DEV}/projects/{urllib.parse.quote(repo, safe='')}")
    card = (project or {}).get("scorecard")
    return (card, "deps.dev") if isinstance(card, dict) else (None, "")


def _source_repo(version_info: dict[str, object]) -> tuple[str, bool]:
    """Pick the source repo of a release and tell whether it is attested."""
    repo, attested = "", False
    related = version_info.get("relatedProjects") or []
    assert isinstance(related, list)
    for rel in related:
        if rel.get("relationType") != "SOURCE_REPO":
            continue
        if rel.get("relationProvenance") == ATTESTATION:
            return rel["projectKey"]["id"], True
        repo = repo or rel["projectKey"]["id"]
    return repo, attested or bool(version_info.get("attestations"))


def fetch(package: str, version: str) -> Row:
    """Build the scorecard row of one ``package==version``."""
    row: Row = dict.fromkeys(FIELDS, "")
    row |= {"package": package, "version": version, "attested": "no"}
    q = urllib.parse.quote
    info = _get(f"{DEPS_DEV}/systems/pypi/packages/{q(package)}/versions/{q(version)}")
    if info is None:
        return row
    repo, attested = _source_repo(info)
    row |= {"repo": repo, "attested": "yes" if attested else "no"}
    card, source = _scorecard(repo) if repo else (None, "")
    if card is not None:
        row["score"] = f"{float(card.get('overallScore', 0)):.1f}"  # type: ignore[arg-type]
        row["scorecard_date"] = str(card.get("date", ""))[:10]
        row["scorecard_source"] = source
        checks = card.get("checks", [])
        assert isinstance(checks, list)
        for check in checks:
            if check.get("name") in CHECKS:
                row[check["name"]] = str(check.get("score", ""))
    return row


def live_state(closure: dict[str, str]) -> list[Row]:
    """Fetch every package of the closure (8 parallel lookups)."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda kv: fetch(*kv), closure.items()))


def parse_history(text: str) -> list[tuple[str, list[Row]]]:
    """Split the history CSV into ``[(snapshot id, rows)]`` in file order."""
    snapshots: dict[str, list[Row]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        snapshots.setdefault(row["snapshot"], []).append(row)
    return list(snapshots.items())


def same_state(a: Iterable[Row], b: Iterable[Row]) -> bool:
    """Tell whether two snapshots differ on any compared field."""

    def key(rows: Iterable[Row]) -> dict[str, tuple[str, ...]]:
        return {r["package"]: tuple(r.get(f, "") for f in COMPARED) for r in rows}

    return key(a) == key(b)


def _num(value: str) -> float | None:
    """Parse a score cell (empty = no data)."""
    try:
        return float(value)
    except ValueError:
        return None


def _describe(row: Row) -> str:
    """Short description of a package for a divergence line."""
    score = row["score"] or "no scorecard"
    repo = row["repo"] or "no source repo"
    return f"{row['package']}=={row['version']} — score {score} ({repo}, attested: {row['attested']})"


def _compare(old: Row, new: Row) -> list[str]:
    """Divergences of one package present in both snapshots."""
    pkg, out = new["package"], []
    if old["repo"] != new["repo"]:
        out.append(
            f"{pkg}: source repo changed {old['repo'] or '∅'} → {new['repo'] or '∅'}"
        )
    if old["attested"] == "yes" and new["attested"] != "yes":
        out.append(f"{pkg}: release {new['version']} lost its PyPI publish attestation")
    before, after = _num(old["score"]), _num(new["score"])
    if before is not None and after is None:
        out.append(f"{pkg}: scorecard no longer available (was {old['score']})")
    elif before is not None and after is not None and before - after >= SCORE_DROP:
        out.append(f"{pkg}: score dropped {old['score']} → {new['score']}")
    out.extend(
        f"{pkg}: {check} fell to 0 (was {old[check]})"
        for check in CRITICAL
        if (_num(old.get(check, "")) or 0) > 0 and _num(new.get(check, "")) == 0
    )
    return out


def divergences(old: list[Row], new: list[Row]) -> tuple[list[str], list[str]]:
    """Return ``(warnings, notes)`` between two snapshots."""
    before = {r["package"]: r for r in old}
    after = {r["package"]: r for r in new}
    warnings: list[str] = []
    for pkg, row in after.items():
        if pkg not in before:
            warnings.append(f"new runtime dependency {_describe(row)}")
        else:
            warnings.extend(_compare(before[pkg], row))
    notes = [f"{pkg} left the runtime closure" for pkg in before if pkg not in after]
    return warnings, notes


def _committed_history() -> str:
    """History CSV as of git HEAD; empty when not committed yet."""
    proc = subprocess.run(
        ["git", "show", f"HEAD:{HISTORY.relative_to(REPO)}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def render_history(committed: str, pending: list[Row] | None) -> str:
    """Committed history text plus the optional pending snapshot."""
    buf = io.StringIO()
    if committed:
        buf.write(committed if committed.endswith("\n") else committed + "\n")
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    if not committed:
        writer.writeheader()
    for row in pending or []:
        writer.writerow(row)
    return buf.getvalue()


def _sort_key(row: Row) -> tuple[float, str]:
    """Order the scoreboard by ascending score, unscored first."""
    score = _num(row["score"])
    return (-1.0 if score is None else score, row["package"])


def _stale(row: Row, today: datetime.date) -> bool:
    """Tell whether a scorecard is older than ``STALE_DAYS``."""
    try:
        date = datetime.date.fromisoformat(row["scorecard_date"])
    except ValueError:
        return False
    return (today - date).days > STALE_DAYS


def render_board(history: list[tuple[str, list[Row]]], today: datetime.date) -> str:
    """Markdown scoreboard: latest snapshot + divergences vs the previous one."""
    snap_id, rows = history[-1]
    scores = [s for s in (_num(r["score"]) for r in rows) if s is not None]
    lines = [
        "# Scorecard des dépendances runtime",
        "",
        (
            "<!-- Généré par scripts/dep_scorecard.py depuis doc/dep-scorecard.csv"
            " — ne pas éditer (ken #1242). -->"
        ),
        "",
        (
            f"Snapshot **{snap_id}** — {len(rows)} paquets de `kenboard[prod,oidc]`,"
            f" score médian **{statistics.median(scores):.1f}**"
            f", {sum(s < LOW_SCORE for s in scores)} sous {LOW_SCORE:.0f}"
            f", {len(rows) - len(scores)} sans scorecard"
            f", {sum(r['attested'] == 'yes' for r in rows)} avec attestation PyPI."
            if scores
            else f"Snapshot **{snap_id}** — aucun scorecard disponible."
        ),
        "",
        "## Divergences",
        "",
    ]
    if len(history) == 1:
        lines.append("Premier snapshot : pas de point de comparaison.")
    else:
        prev_id, prev_rows = history[-2]
        warnings, notes = divergences(prev_rows, rows)
        lines.append(f"Snapshot {snap_id} vs {prev_id} :")
        lines.append("")
        lines.extend(f"- ⚠ {w}" for w in warnings)
        lines.extend(f"- {n}" for n in notes)
        if not warnings and not notes:
            lines.append("- aucune (versions mises à jour seulement)")
    lines += [
        "",
        "## État",
        "",
        (
            "| Paquet | Version | Score | Maintained | Code-Review | Dangerous-Workflow"
            " | Signed-Releases | Attestation | Scorecard du | Repo |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=_sort_key):
        date = r["scorecard_date"] + (" (ancien)" if _stale(r, today) else "")
        lines.append(
            f"| {r['package']} | {r['version']} | {r['score'] or '—'} | {r['Maintained']}"
            f" | {r['Code-Review']} | {r['Dangerous-Workflow']} | {r['Signed-Releases']}"
            f" | {r['attested']} | {date} | {r['repo'] or '—'} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    """Refresh the scoreboard; always exit 0 unless the script itself breaks."""
    now = datetime.datetime.now(datetime.UTC)
    try:
        live = live_state(runtime_closure())
    except FetchError as exc:
        print(f"warning: deps.dev unreachable ({exc}) — scoreboard not updated")
        return 0
    committed = _committed_history()
    snapshots = parse_history(committed)
    snap_id = now.strftime("%Y-%m-%dT%H:%MZ")

    if snapshots and same_state(snapshots[-1][1], live):
        text, status = committed, f"unchanged since {snapshots[-1][0]}"
        warnings: list[str] = []
        notes: list[str] = []
    else:
        for row in live:
            row["snapshot"] = snap_id
        text = render_history(committed, live)
        if snapshots:
            warnings, notes = divergences(snapshots[-1][1], live)
            status = f"snapshot {snap_id} pending (vs committed {snapshots[-1][0]})"
        else:
            warnings, notes = [], [
                "no committed snapshot yet: this run is the baseline"
            ]
            status = f"baseline snapshot {snap_id} pending"

    HISTORY.write_text(text)
    BOARD.write_text(render_board(parse_history(text), now.date()))
    for line in notes:
        print(f"note: {line}")
    for line in warnings:
        print(f"warning: {line}")
    scores = [s for s in (_num(r["score"]) for r in live) if s is not None]
    median = f"{statistics.median(scores):.1f}" if scores else "n/a"
    print(
        f"Scorecard: {len(warnings)} divergence(s), median {median}, {len(live)} packages"
        f" — {status} — see {BOARD.relative_to(REPO)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
