#!/usr/bin/env python3
"""Check the Sonarcloud quality gate for the latest analysis.

Polls the Sonarcloud API until the analysis for the current commit is
available, then checks the quality gate status. Exits 0 if the gate
passes, 1 if it fails (with issue details printed to stderr).

Usage:
    python scripts/sonar_gate.py [--timeout 300] [--interval 15] [--max-wait 3600]

``--timeout`` borne l'attente aveugle ; au-delà, l'attente ne continue (jusqu'au
cap dur ``--max-wait``) que si le pipeline montre un signe de vie : run GitHub
Actions queued/in_progress pour le commit, ou tâche compute-engine Sonarcloud
PENDING/IN_PROGRESS (fenêtres de maintenance, backlog — ken #995).

Requires SONAR_TOKEN in the environment (or .env file).
"""

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_KEY = "lduchosal_kenboard"
SONAR_BASE = "https://sonarcloud.io/api"


def _ssl_context() -> ssl.SSLContext | None:
    """Build an SSL context using certifi's CA bundle if available."""
    try:
        import certifi  # noqa: PLC0415 — dépendance optionnelle, import au besoin

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


_SSL_CTX = _ssl_context()


def _get_token() -> str:
    """Resolve the Sonar token from env or .env file."""
    token = os.environ.get("SONAR_TOKEN", "")
    if token:
        return token
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.is_file():
        with env_path.open() as f:
            for line in f:
                line = line.strip()
                if line.startswith("SONAR_TOKEN="):
                    return line.split("=", 1)[1].strip()
    return ""


def _api(path: str, token: str, params: dict | None = None) -> dict:
    """Call the Sonarcloud API and return parsed JSON."""
    url = f"{SONAR_BASE}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        return json.loads(resp.read())


def _current_commit() -> str:
    """Return the current git HEAD commit SHA."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()


def _ce_queue_busy(token: str) -> bool:
    """Return True when a Sonarcloud compute-engine task is pending or running.

    Couvre la file côté serveur (maintenance planifiée, backlog) : le rapport a
    été soumis mais l'analyse n'est pas encore indexée — publish 0.2.4 du
    26.07.2026, ~70 min de file (ken #995). Toute erreur API renvoie False :
    l'appelant retombe alors sur le timeout simple.
    """
    try:
        data = _api("/ce/component", token, {"component": PROJECT_KEY})
    except Exception:  # noqa: BLE001 — fail-open : retomber sur le timeout simple
        return False
    if data.get("queue"):
        return True
    return (data.get("current") or {}).get("status") in ("PENDING", "IN_PROGRESS")


def _ci_running(commit: str) -> bool:
    """Return True when a GitHub Actions run for ``commit`` is queued or running.

    Sonde best-effort via le CLI ``gh`` : couvre le délai de scheduling GitHub
    (14 min observées le 26.07.2026 avant que la CI ne tourne, ken #995). Si
    ``gh`` est absent, non authentifié ou en erreur, renvoie False — l'appelant
    retombe sur le timeout simple.
    """
    try:
        out = subprocess.check_output(
            ["gh", "run", "list", "--limit", "15", "--json", "headSha,status"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        runs = json.loads(out)
    except Exception:  # noqa: BLE001 — fail-open : gh absent/non authentifié = timeout simple
        return False
    active = {"queued", "in_progress", "requested", "waiting", "pending"}
    return any(
        r.get("headSha") == commit and r.get("status") in active for r in runs
    )


def _wait_for_analysis(
    token: str, commit: str, timeout: int, interval: int, max_wait: int
) -> str | None:
    """Poll until the analysis for the given commit is available.

    ``timeout`` borne l'attente *aveugle* : passé ce délai, on n'abandonne que
    si rien n'est en cours ni côté Sonarcloud (tâche compute-engine, cf.
    :func:`_ce_queue_busy`) ni côté GitHub Actions (cf. :func:`_ci_running`).
    Tant qu'un des deux est actif, l'attente continue jusqu'au cap dur
    ``max_wait``. Après drain de la file, deux polls de grâce couvrent le
    délai d'indexation de l'analyse.

    Returns the analysis key or None on timeout.
    """
    start = time.time()
    soft_deadline = start + timeout
    hard_deadline = start + max(max_wait, timeout)
    grace = 0
    print(f"Waiting for Sonarcloud analysis of commit {commit[:8]}...")
    while True:
        try:
            data = _api("/project_analyses/search", token, {
                "project": PROJECT_KEY,
                "ps": "5",
            })
            for analysis in data.get("analyses", []):
                revision = analysis.get("revision", "")
                if revision == commit:
                    print(f"  Analysis found: {analysis['key']}")
                    return analysis["key"]
        except Exception as e:  # noqa: BLE001 — erreur API transitoire : on retente
            print(f"  API error: {e}", file=sys.stderr)
        now = time.time()
        if now >= hard_deadline:
            print("  Cap --max-wait atteint.", file=sys.stderr)
            return None
        if now >= soft_deadline:
            cap = int(hard_deadline - now)
            if _ce_queue_busy(token):
                grace = 2
                print(f"  Rapport en file côté Sonarcloud — attente prolongée (cap {cap}s)...")
            elif _ci_running(commit):
                grace = 2
                print(f"  Run GitHub Actions en cours pour ce commit — attente prolongée (cap {cap}s)...")
            elif grace > 0:
                grace -= 1
                print(f"  File vide — poll de grâce pour l'indexation ({grace + 1} restant)...")
            else:
                return None
        else:
            remaining = int(soft_deadline - now)
            print(f"  Not ready yet, retrying in {interval}s ({remaining}s remaining)...")
        time.sleep(interval)


def _check_gate(token: str, analysis_key: str) -> tuple[bool, list[dict]]:
    """Check the LIVE quality gate status of the main branch.

    ``analysis_key`` n'est plus passé à l'API : le statut figé par analysisId
    ignore le triage d'issues postérieur à l'analyse (faux positif marqué dans
    l'UI → la branche repasse OK mais l'analyse resterait FAILED à jamais).
    L'appelant a déjà attendu l'analyse du commit courant, ce qui garantit que
    le statut live couvre bien ce code. Returns (passed, conditions).
    """
    del analysis_key  # fraîcheur déjà garantie par _wait_for_analysis
    data = _api("/qualitygates/project_status", token, {
        "projectKey": PROJECT_KEY,
        "branch": "main",
    })
    status = data.get("projectStatus", {})
    passed = status.get("status") == "OK"
    conditions = status.get("conditions", [])
    return passed, conditions


def _fetch_issues(token: str) -> list[dict]:
    """Fetch open issues for the project."""
    data = _api("/issues/search", token, {
        "componentKeys": PROJECT_KEY,
        "resolved": "false",
        "ps": "50",
    })
    return data.get("issues", [])


def main() -> None:
    """Run the Sonarcloud quality gate check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Max seconds to wait for analysis (default 300)",
    )
    parser.add_argument(
        "--interval", type=int, default=15,
        help="Poll interval in seconds (default 15)",
    )
    parser.add_argument(
        "--max-wait", type=int, default=3600,
        help="Hard cap in seconds when CI/Sonar queue is still busy (default 3600)",
    )
    args = parser.parse_args()

    token = _get_token()
    if not token:
        print("Error: SONAR_TOKEN not found in env or .env", file=sys.stderr)
        sys.exit(1)

    commit = _current_commit()

    analysis_key = _wait_for_analysis(
        token, commit, args.timeout, args.interval, args.max_wait
    )
    if not analysis_key:
        print(
            f"Timeout: no analysis found for {commit[:8]} "
            f"(timeout {args.timeout}s, max-wait {args.max_wait}s)",
            file=sys.stderr,
        )
        sys.exit(1)

    passed, conditions = _check_gate(token, analysis_key)

    if passed:
        print("\n✓ Sonarcloud quality gate: PASSED")
        sys.exit(0)

    print("\n✗ Sonarcloud quality gate: FAILED", file=sys.stderr)
    for c in conditions:
        if c.get("status") != "OK":
            print(
                f"  - {c.get('metricKey')}: {c.get('actualValue')} "
                f"(threshold: {c.get('errorThreshold', 'n/a')})",
                file=sys.stderr,
            )

    print("\nOpen issues:", file=sys.stderr)
    issues = _fetch_issues(token)
    for issue in issues:
        component = issue.get("component", "").replace(f"{PROJECT_KEY}:", "")
        line = issue.get("line", "?")
        severity = issue.get("severity", "?")
        msg = issue.get("message", "")
        print(f"  [{severity}] {component}:{line} — {msg}", file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
