#!/usr/bin/env python3
"""Measure local code-quality metrics for src/dashboard.

Computes a snapshot of the trackable quality criteria defined in
doc/code-quality.md: size/structure stats (via AST), cyclomatic
complexity (ruff C901), lint debt (curated ruff rule set), mypy /
vulture / refurb findings, docstring coverage (interrogate) and test
coverage (read from the last `coverage` run, if any).

Usage:
    .venv/bin/python scripts/quality_metrics.py [--json] [--record]

--record appends a CSV row to doc/quality-history.csv so the evolution
of each criterion stays visible over time.
"""

import argparse
import ast
import csv
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "dashboard"
HISTORY = REPO / "doc" / "quality-history.csv"
VENV_BIN = Path(sys.executable).parent

# Lint debt: curated rules NOT yet enforced by the ruff gate. Style-only
# rules that fight black (COM, D4xx, ISC) and the S-rules (false positives
# on variable names, audited 2026-06) are deliberately excluded.
DEBT_SELECT = "PLC0415,PLR,DTZ,EM,TRY,PERF,PTH,FBT,ARG,BLE,SLF,G,ANN401,RUF"

LONG_FUNC_LINES = 50
BIG_FILE_LINES = 500


def _run(tool: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a venv tool from the repo root and capture its output."""
    return subprocess.run(
        [str(VENV_BIN / tool), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def _ast_stats() -> dict[str, int]:
    """Walk src/dashboard and compute size/structure metrics via AST."""
    files = sorted(SRC.rglob("*.py"))
    loc = 0
    max_file = 0
    big_files = 0
    func_lengths: list[int] = []
    for path in files:
        text = path.read_text()
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        loc += lines
        max_file = max(max_file, lines)
        if lines > BIG_FILE_LINES:
            big_files += 1
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lengths.append((node.end_lineno or node.lineno) - node.lineno + 1)
    return {
        "py_files": len(files),
        "loc_src": loc,
        "max_file_lines": max_file,
        "files_over_500": big_files,
        "functions": len(func_lengths),
        "max_func_lines": max(func_lengths),
        "funcs_over_50": sum(1 for length in func_lengths if length > LONG_FUNC_LINES),
    }


def _ruff_count(select: str) -> int:
    """Count ruff findings in src for the given rule selection."""
    proc = _run("ruff", "check", "src", "--select", select, "--output-format", "json")
    return len(json.loads(proc.stdout or "[]"))


def _mypy_errors() -> int:
    """Count mypy errors in src."""
    proc = _run("mypy", "src")
    match = re.search(r"Found (\d+) error", proc.stdout)
    return int(match.group(1)) if match else 0


def _vulture_findings() -> int:
    """Count vulture dead-code findings at the gate's confidence level."""
    proc = _run("vulture", "src", "tests", "vulture_whitelist.py")
    return len([line for line in proc.stdout.splitlines() if ": " in line])


def _refurb_findings() -> int:
    """Count refurb findings in src."""
    proc = _run("refurb", "src")
    return len([line for line in proc.stdout.splitlines() if "[FURB" in line])


def _docstring_coverage() -> float:
    """Read the interrogate docstring-coverage percentage for src."""
    proc = _run("interrogate", "src", "-c", "pyproject.toml", "--no-color")
    match = re.search(r"actual: ([\d.]+)%", proc.stdout + proc.stderr)
    return float(match.group(1)) if match else 0.0


def _test_coverage() -> float | None:
    """Read total test coverage from the last coverage run, if available."""
    if not (REPO / ".coverage").exists():
        return None
    proc = _run("coverage", "report", "--format=total", "--precision=2")
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def _version() -> str:
    """Read the package version from src/dashboard/__init__.py."""
    text = (SRC / "__init__.py").read_text()
    match = re.search(r'__version__ = "([^"]+)"', text)
    return match.group(1) if match else "?"


def collect() -> dict[str, object]:
    """Collect the full metrics snapshot."""
    metrics: dict[str, object] = {
        "date": datetime.date.today().isoformat(),
        "version": _version(),
    }
    metrics.update(_ast_stats())
    metrics["c901_over_10"] = _ruff_count("C901")
    metrics["ruff_debt"] = _ruff_count(DEBT_SELECT)
    metrics["mypy_errors"] = _mypy_errors()
    metrics["vulture"] = _vulture_findings()
    metrics["refurb"] = _refurb_findings()
    metrics["docstring_cov"] = _docstring_coverage()
    metrics["test_cov"] = _test_coverage()
    return metrics


def record(metrics: dict[str, object]) -> None:
    """Append the snapshot as a CSV row to doc/quality-history.csv."""
    fresh = not HISTORY.exists()
    with HISTORY.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics))
        if fresh:
            writer.writeheader()
        writer.writerow(metrics)


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="output as JSON")
    parser.add_argument(
        "--record", action="store_true", help="append to doc/quality-history.csv"
    )
    args = parser.parse_args()

    metrics = collect()
    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        width = max(len(key) for key in metrics)
        for key, value in metrics.items():
            shown = "n/a (run pdm run test-cov first)" if value is None else value
            print(f"{key:<{width}}  {shown}")
    if args.record:
        record(metrics)
        print(f"\nrecorded -> {HISTORY.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
