#!/usr/bin/env python3
"""Blocking malware gate on the runtime dependencies (ken #1241).

pip-audit only knows *published* vulnerabilities. GuardDog (Datadog) looks for
*malicious* packages — typosquatting, compromised maintainer e-mail domain, code
exfiltrating secrets, obfuscated ``exec``, download-and-run, reverse shells… — with
semgrep/yara heuristics over the package source and metadata checks.

Scope: the runtime closure of ``kenboard[prod,oidc]`` (scripts/runtime_deps.py) —
what lands on a production host. Dev tools are out of scope (~155 packages, ~13 min
per cold scan).

Isolation: GuardDog lives in its own venv under ``.cache/guarddog/venv``, upgraded
on every run (no pin, ratchet principle). As a dev dependency its upper-bound pins
(``click<9``, ``pygit2<1.19``…) would hold back kenboard's own runtime deps in the
test venv, and it drags boto3 along.

Cache: a scan costs ~5 s of CPU per package. Raw results are cached per
``(guarddog version, package==version)``; only new versions get scanned. The
allowlist is applied on every run, so editing it never needs a rescan.

Blocking rules: every ``threat-*`` rule plus the metadata detectors (typosquatting,
compromised e-mail domain, …). ``capability-*`` rules only describe what a package
*can* do (network, files, subprocess) and fire on half of any healthy dependency
tree; ``threat-npm-*`` don't apply to PyPI.

False positives: ``[[tool.kenboard.guarddog.allow]]`` in pyproject.toml, one entry
per (package, rule, files) with a mandatory ``reason``. Files are matched exactly: a
hit in another file of the same package blocks again. An entry that no longer
matches anything prints a warning — remove it.

Usage:
    .venv/bin/python scripts/guarddog_gate.py
Exit 1 on any finding not covered by the allowlist, or on a package GuardDog could
not scan.
"""

import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from runtime_deps import PYPROJECT, REPO, canonical, runtime_closure

CACHE = REPO / ".cache" / "guarddog"
VENV = CACHE / "venv"
NON_BLOCKING_PREFIXES = ("capability-", "threat-npm-")
# ``<sha256>: <file name> (<type>)`` lines of the bundled_binary message.
BINARY_LINE = re.compile(r"^[0-9a-f]{64}: (.+?) \(\w+\)$", re.MULTILINE)


@dataclass(frozen=True)
class Finding:
    """One blocking GuardDog hit."""

    package: str
    version: str
    rule: str
    file: str
    location: str
    message: str
    code: str


@dataclass
class Allow:
    """One allowlist entry from pyproject.toml."""

    package: str
    rule: str
    files: frozenset[str]
    reason: str
    used: bool = False

    def covers(self, finding: Finding) -> bool:
        """Tell whether this entry legitimises ``finding``."""
        if finding.package != self.package or finding.rule != self.rule:
            return False
        return not self.files or finding.file in self.files


def load_allowlist(path: Path = PYPROJECT) -> list[Allow]:
    """Read ``[[tool.kenboard.guarddog.allow]]``; every entry needs a reason."""
    conf = tomllib.loads(path.read_text()).get("tool", {}).get("kenboard", {})
    entries = []
    for raw in conf.get("guarddog", {}).get("allow", []):
        if not str(raw.get("reason", "")).strip():
            msg = f"guarddog allow entry without a reason: {raw}"
            raise SystemExit(msg)
        entries.append(
            Allow(
                package=canonical(raw["package"]),
                rule=raw["rule"],
                files=frozenset(raw.get("files", [])),
                reason=raw["reason"],
            )
        )
    return entries


def is_blocking(rule: str) -> bool:
    """Tell whether a rule id belongs to the blocking set."""
    return not rule.startswith(NON_BLOCKING_PREFIXES)


def findings_of(
    package: str, version: str, results: dict[str, object]
) -> list[Finding]:
    """Flatten one package's raw GuardDog ``results`` into blocking findings.

    Source rules give one finding per hit, ``file`` = path inside the package and
    ``code`` = the matched text. ``bundled_binary`` gives one finding per binary
    (``file`` = its name) so that allowlisting known binaries still blocks a new
    one. Other metadata detectors give one finding with an empty ``file``.
    """
    out: list[Finding] = []
    for rule, value in sorted(results.items()):
        if not value or not is_blocking(rule):
            continue
        hits = value if isinstance(value, list) else [value]
        for hit in hits:
            if isinstance(hit, dict):
                location = str(hit.get("location", ""))
                file = location.rsplit(":", 1)[0]
                message = str(hit.get("message", ""))
                code = " ".join(str(hit.get("match", "")).split())
                out.append(
                    Finding(package, version, rule, file, location, message, code)
                )
            elif rule == "bundled_binary":
                out.extend(
                    Finding(package, version, rule, name, name, "bundled binary", "")
                    for name in BINARY_LINE.findall(str(hit))
                )
            else:  # metadata detectors report a plain message
                out.append(Finding(package, version, rule, "", "", str(hit), ""))
    return out


def apply_allowlist(
    findings: list[Finding], allowlist: list[Allow]
) -> tuple[list[Finding], int]:
    """Split findings into (blocking, number allowed); marks used entries."""
    blocking, allowed = [], 0
    for finding in findings:
        entry = next((a for a in allowlist if a.covers(finding)), None)
        if entry is None:
            blocking.append(finding)
        else:
            entry.used = True
            allowed += 1
    return blocking, allowed


def _venv_python() -> Path:
    """Python of the isolated GuardDog venv."""
    return VENV / "bin" / "python"


def ensure_guarddog() -> str:
    """Create/upgrade the isolated GuardDog venv; return the GuardDog version."""
    if not _venv_python().exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    subprocess.run(
        [
            str(_venv_python()),
            "-m",
            "pip",
            "install",
            "--quiet",
            "--disable-pip-version-check",
            "--upgrade",
            "guarddog",
        ],
        check=True,
    )
    proc = subprocess.run(
        [
            str(_venv_python()),
            "-c",
            "import importlib.metadata as m; print(m.version('guarddog'))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _cache_file(gd_version: str, package: str, version: str) -> Path:
    """Path of the cached raw result of one package version."""
    return CACHE / "results" / gd_version / f"{package}=={version}.json"


def scan(pkgs: dict[str, str], gd_version: str) -> list[str]:
    """Scan ``pkgs`` with GuardDog, cache clean results; return scan errors."""
    req = CACHE / "requirements.txt"
    req.write_text("".join(f"{n}=={v}\n" for n, v in pkgs.items()))
    stderr_log = CACHE / "last-stderr.log"
    with stderr_log.open("w") as err:
        proc = subprocess.run(
            [
                str(VENV / "bin" / "guarddog"),
                "pypi",
                "verify",
                str(req),
                "--output-format",
                "json",
            ],
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
            check=False,
        )
    if proc.returncode != 0:
        return [
            f"guarddog exited {proc.returncode} — see {stderr_log.relative_to(REPO)}"
        ]
    errors, seen = [], set()
    for entry in json.loads(proc.stdout or "[]"):
        name = canonical(entry["dependency"])
        seen.add(name)
        result = entry["result"]
        if result.get("errors"):
            errors.append(f"{name}=={pkgs.get(name, '?')}: {result['errors']}")
            continue
        target = _cache_file(gd_version, name, pkgs[name])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result["results"], sort_keys=True))
    errors.extend(
        f"{n}=={pkgs[n]}: not in GuardDog output" for n in pkgs if n not in seen
    )
    if stderr_log.stat().st_size:
        print(
            f"note: guarddog stderr (network lookups) kept in {stderr_log.relative_to(REPO)}"
        )
    return errors


def main() -> int:
    """Run the gate; return the process exit code."""
    CACHE.mkdir(parents=True, exist_ok=True)
    closure = runtime_closure()
    gd_version = ensure_guarddog()
    todo = {
        n: v for n, v in closure.items() if not _cache_file(gd_version, n, v).exists()
    }
    errors = scan(todo, gd_version) if todo else []
    if errors:
        print("✗ GuardDog could not scan every package:")
        for line in errors:
            print(f"    {line}")
        return 1

    findings: list[Finding] = []
    for name, version in closure.items():
        results = json.loads(_cache_file(gd_version, name, version).read_text())
        findings.extend(findings_of(name, version, results))
    allowlist = load_allowlist()
    blocking, allowed = apply_allowlist(findings, allowlist)

    for entry in allowlist:
        if not entry.used:
            print(
                f"warning: stale guarddog allow entry {entry.package} / {entry.rule}"
                " — no longer matches, remove it from pyproject.toml"
            )
    for f in blocking:
        print(f"✗ {f.package}=={f.version} {f.rule} {f.location or '(metadata)'}")
        print(f"    {f.message}")
        if f.code:
            print(f"    {f.code[:120]}")
    print(
        f"GuardDog {gd_version}: {len(blocking)} blocking, {allowed} allowed"
        f" — {len(closure)} packages ({len(todo)} scanned, {len(closure) - len(todo)} cached)"
    )
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
