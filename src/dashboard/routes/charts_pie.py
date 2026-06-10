"""Tasks-per-board pie chart geometry (ken #620).

Split out of ``routes/charts.py`` (ken #806) — SVG arc paths for the dashboard pie, one
slice per category.
"""

import math
from typing import Any


def _full_circle_slice(
    counts: list[tuple[dict[str, Any], int]],
    grand_total: int,
    *,
    cx: float,
    cy: float,
    radius: float,
) -> dict[str, Any]:
    """Render the single-category degenerate pie as one full circle.

    Args:
        counts: The single ``(category, count)`` pair.
        grand_total: Total task count (equals the single count).
        cx: SVG x coordinate of the pie centre.
        cy: SVG y coordinate of the pie centre.
        radius: Pie radius in SVG units.

    Returns:
        The full context dict (one slice covering 100 %).
    """
    c, cnt = counts[0]
    path_d = (
        f"M {cx:.2f} {cy - radius:.2f} "
        f"A {radius} {radius} 0 1 1 {cx:.2f} {cy + radius:.2f} "
        f"A {radius} {radius} 0 1 1 {cx:.2f} {cy - radius:.2f} Z"
    )
    slices = [{"cat": c, "count": cnt, "pct": 100.0, "path_d": path_d}]
    return {"tasks_per_board_pie": slices, "tasks_per_board_total": grand_total}


def _build_tasks_per_board_pie(
    categories: list[dict[str, Any]],
    all_projects: list[dict[str, Any]],
    *,
    cx: float = 80.0,
    cy: float = 80.0,
    radius: float = 70.0,
) -> dict[str, Any]:
    """Build pie chart data for tasks per board (category) — replaces #540 (ken #620).

    Sums ``project["total"]`` (already populated by the caller from
    ``task_counts_by_project``) across each category, then computes SVG arc paths
    so the template can render the slices without any JS. Categories with zero
    tasks are dropped; the remaining slices follow ``categories`` order. Arc
    sweep starts at 12 o'clock and runs clockwise.

    Args:
        categories: Visible categories in display order.
        all_projects: All projects (filtered to the visible scope), each with a
            ``total`` key holding the project's task count.
        cx: SVG x coordinate of the pie centre.
        cy: SVG y coordinate of the pie centre.
        radius: Pie radius in SVG units.

    Returns:
        A context dict with ``tasks_per_board_pie`` (list of slices, each with
        ``cat``, ``count``, ``pct``, ``path_d``) and ``tasks_per_board_total``.
    """
    counts: list[tuple[dict[str, Any], int]] = []
    grand_total = 0
    for c in categories:
        cnt = sum(
            int(p.get("total", 0)) for p in all_projects if p["cat_id"] == c["id"]
        )
        if cnt > 0:
            counts.append((c, cnt))
            grand_total += cnt

    if grand_total == 0:
        return {"tasks_per_board_pie": [], "tasks_per_board_total": 0}

    # Single slice would degenerate to a point with the M/L/A/Z form, so draw
    # it as a full circle via two 180° arcs.
    if len(counts) == 1:
        return _full_circle_slice(counts, grand_total, cx=cx, cy=cy, radius=radius)

    slices = _pie_slices(counts, grand_total, cx=cx, cy=cy, radius=radius)
    return {"tasks_per_board_pie": slices, "tasks_per_board_total": grand_total}


def _pie_slices(
    counts: list[tuple[dict[str, Any], int]],
    grand_total: int,
    *,
    cx: float,
    cy: float,
    radius: float,
) -> list[dict[str, Any]]:
    """Compute the SVG arc path of each pie slice, clockwise from 12 o'clock.

    Args:
        counts: ``(category, count)`` pairs in display order (all non-zero).
        grand_total: Sum of all counts.
        cx: SVG x coordinate of the pie centre.
        cy: SVG y coordinate of the pie centre.
        radius: Pie radius in SVG units.

    Returns:
        The slice dicts (``cat``, ``count``, ``pct``, ``path_d``).
    """
    slices: list[dict[str, Any]] = []
    angle = -math.pi / 2  # 12 o'clock
    for c, cnt in counts:
        frac = cnt / grand_total
        sweep = frac * 2 * math.pi
        x1 = cx + radius * math.cos(angle)
        y1 = cy + radius * math.sin(angle)
        end_angle = angle + sweep
        x2 = cx + radius * math.cos(end_angle)
        y2 = cy + radius * math.sin(end_angle)
        large_arc = 1 if sweep > math.pi else 0
        path_d = (
            f"M {cx:.2f} {cy:.2f} "
            f"L {x1:.4f} {y1:.4f} "
            f"A {radius} {radius} 0 {large_arc} 1 {x2:.4f} {y2:.4f} Z"
        )
        slices.append(
            {
                "cat": c,
                "count": cnt,
                "pct": round(100 * frac, 1),
                "path_d": path_d,
            }
        )
        angle = end_angle
    return slices
