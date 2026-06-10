"""Unit tests for the quality-metrics blocking gate (ken #788).

Covers the pure gate logic of scripts/quality_metrics.py: absolute ceilings/floors, the
best-ever ratchet against the recorded history and the skip behaviour when coverage data
is missing.
"""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "quality_metrics",
    Path(__file__).resolve().parents[2] / "scripts" / "quality_metrics.py",
)
assert _SPEC is not None and _SPEC.loader is not None
qm = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qm)


BEST = {
    "files_over_500": 2,
    "funcs_over_50": 25,
    "c901_over_10": 3,
    "ruff_debt": 255,
    "test_cov": 89.54,
}


def _metrics(**overrides: object) -> dict[str, object]:
    """Build a debt-free snapshot (strict targets met), overridable per test."""
    base: dict[str, object] = {
        "max_file_lines": 400,
        "max_func_lines": 45,
        "mypy_errors": 0,
        "vulture": 0,
        "refurb": 0,
        "docstring_cov": 100.0,
        "test_cov": 89.54,
        "min_file_cov": 45.0,
        "files_over_500": 0,
        "funcs_over_50": 20,
        "c901_over_10": 0,
        "ruff_debt": 0,
    }
    base.update(overrides)
    return base


def test_gate_passes_when_debt_free() -> None:
    """A snapshot meeting every strict target passes the gate."""
    failures, skipped = qm.evaluate_gate(_metrics(), BEST)
    assert failures == []
    assert skipped == []


def test_palier_targets_block_existing_debt() -> None:
    """Debt beyond the active palier (c901, ruff_debt) is blocking."""
    failures, _ = qm.evaluate_gate(_metrics(c901_over_10=3, ruff_debt=255), BEST)
    assert any("c901_over_10" in failure for failure in failures)
    assert any("ruff_debt" in failure for failure in failures)


def test_absolute_ceiling_blocks_monster_file() -> None:
    """A file beyond the absolute ceiling fails the gate."""
    failures, _ = qm.evaluate_gate(_metrics(max_file_lines=1200), BEST)
    assert any("max_file_lines" in failure for failure in failures)


def test_absolute_ceiling_blocks_monster_function() -> None:
    """A function beyond the absolute ceiling fails the gate."""
    failures, _ = qm.evaluate_gate(_metrics(max_func_lines=200), BEST)
    assert any("max_func_lines" in failure for failure in failures)


def test_absolute_floor_blocks_untested_file() -> None:
    """A file below the per-file coverage floor fails the gate."""
    failures, _ = qm.evaluate_gate(_metrics(min_file_cov=10.0), BEST)
    assert any("min_file_cov" in failure for failure in failures)


def test_ratchet_blocks_count_regression() -> None:
    """Any ratcheted count above its best-ever value fails the gate."""
    failures, _ = qm.evaluate_gate(_metrics(funcs_over_50=26), BEST)
    assert any("funcs_over_50" in failure for failure in failures)


def test_ratchet_coverage_slack() -> None:
    """Coverage may dip within the slack but not beyond it."""
    within, _ = qm.evaluate_gate(_metrics(test_cov=89.2), BEST)
    assert within == []
    beyond, _ = qm.evaluate_gate(_metrics(test_cov=88.9), BEST)
    assert any("test_cov" in failure for failure in beyond)


def test_missing_coverage_skips_rules() -> None:
    """Without coverage data the coverage rules are skipped, not failed."""
    failures, skipped = qm.evaluate_gate(
        _metrics(test_cov=None, min_file_cov=None), BEST
    )
    assert failures == []
    assert "test_cov" in skipped
    assert "min_file_cov" in skipped


def test_history_best_takes_extremes_and_ignores_blanks(tmp_path: Path) -> None:
    """Best-ever is the min of counts / max of coverage, blanks ignored."""
    history = tmp_path / "history.csv"
    history.write_text(
        "date,funcs_over_50,ruff_debt,test_cov\n"
        "2026-06-01,30,300,88.0\n"
        "2026-06-02,25,310,\n"
        "2026-06-03,27,255,89.54\n"
    )
    best = qm._history_best(history)
    assert best["funcs_over_50"] == 25
    assert best["ruff_debt"] == 255
    assert best["test_cov"] == 89.54


def test_history_best_empty_without_file(tmp_path: Path) -> None:
    """No history file means no ratchet constraints."""
    assert qm._history_best(tmp_path / "missing.csv") == {}


def test_gate_details_lists_offenders() -> None:
    """A red rule yields an actionable offender list, not just a count."""
    every_file = qm.gate_details("files_over_500")
    assert all("src" in line for line in every_file)
    assert qm._offending_functions(100000) == []
    assert qm._offending_files(1)  # every src file offends a 1-line limit
    assert qm.gate_details("mypy_errors") == ["détail : pdm run typecheck"]
