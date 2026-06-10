"""Server-side chart geometry builders for the HTML pages.

Pure functions (no Flask context): they turn SQL aggregates into the SVG geometry dicts
the Jinja2 templates render without any JS — grouped bars for the per-day taskers chart
(#507), per-project wiki mini-cards (#572) and the tasks-per-board pie (ken #620).
"""

from datetime import date, timedelta
from typing import Any

# Trailing window (days) for the per-day taskers chart (#507).
TASKERS_WINDOW_DAYS = 7

_FR_WEEKDAYS = ("lun", "mar", "mer", "jeu", "ven", "sam", "dim")


def _resolve_activity_author(raw: str, users_by_id: dict[str, str]) -> str | None:
    """Map a raw ``activities.user_name`` principal to a person's display name.

    Session writes already store the display name verbatim; token writes store
    the ``key:<id>:user:<owner>`` principal from the auth middleware, which we
    resolve back to the owning user's name (#492 — the token owner *is* the
    author). Returns ``None`` when no human can be attributed (anonymous
    writes, unowned/legacy ``key:<id>`` tokens, or a since-deleted owner) so
    the caller drops the row from the per-person chart.

    Args:
        raw: The stored ``user_name`` value.
        users_by_id: Map of user id to display name.

    Returns:
        The resolved display name, or ``None`` when unattributable.
    """
    if not raw:
        return None
    if raw.startswith("key:"):
        marker = ":user:"
        idx = raw.find(marker)
        if idx == -1:
            return None
        return users_by_id.get(raw[idx + len(marker) :])
    return raw


def _bucket_activity_by_person(
    rows: list[dict[str, Any]],
    users_by_id: dict[str, str],
    day_keys: list[str],
) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """Bucket raw activity rows per (day, person) within the window.

    Args:
        rows: Per-(day, principal) activity counts.
        users_by_id: Map of user id to display name.
        day_keys: ISO dates of the rendered window, oldest first.

    Returns:
        ``(per_day, totals_by_person)`` — counts keyed by day then person, and
        window totals per person.
    """
    per_day: dict[str, dict[str, int]] = {k: {} for k in day_keys}
    totals_by_person: dict[str, int] = {}
    for r in rows:
        key = str(r["day"])
        if key not in per_day:
            continue
        person = _resolve_activity_author(str(r["user_name"]), users_by_id)
        if person is None:
            continue
        cnt = int(r["count"])
        per_day[key][person] = per_day[key].get(person, 0) + cnt
        totals_by_person[person] = totals_by_person.get(person, 0) + cnt
    return per_day, totals_by_person


def _bar_grid(
    w: float, h: float, day_count: int, person_count: int
) -> tuple[float, float, float, float, float, float]:
    """Grid geometry: ``(band, group_w, slot_w, bar_w, plot_h, pad_bottom)``."""
    pad_top, pad_bottom = 8.0, 4.0
    plot_h = h - pad_top - pad_bottom
    band = w / day_count
    group_w = band * 0.82
    slot_w = group_w / person_count
    bar_w = slot_w * 0.85
    return band, group_w, slot_w, bar_w, plot_h, pad_bottom


def _layout_taskers_bars(  # noqa: PLR0913 — géométrie : données + dimensions explicites
    per_day: dict[str, dict[str, int]],
    day_keys: list[str],
    persons: list[str],
    color_by_name: dict[str, str],
    *,
    w: float,
    h: float,
) -> list[dict[str, Any]]:
    """Lay out one SVG rect per (day, person) with a non-zero count.

    Args:
        per_day: Counts keyed by day then person.
        day_keys: ISO dates of the rendered window, oldest first.
        persons: Stable person order (most active first).
        color_by_name: Map of display name to CSS color.
        w: SVG viewBox width.
        h: SVG viewBox height.

    Returns:
        The list of bar dicts (``x``/``y``/``w``/``h``/``color``/…).
    """
    default_color = "var(--dimmed)"
    band, group_w, slot_w, bar_w, plot_h, pad_bottom = _bar_grid(
        w, h, len(day_keys), len(persons)
    )
    max_count = max(max(d.values()) for d in per_day.values() if d)

    bars: list[dict[str, Any]] = []
    for di, key in enumerate(day_keys):
        for pj, person in enumerate(persons):
            cnt = per_day[key].get(person, 0)
            if cnt == 0:
                continue
            bar_h = (cnt / max_count) * plot_h
            x = di * band + (band - group_w) / 2 + pj * slot_w + (slot_w - bar_w) / 2
            bars.append(
                {
                    "x": round(x, 1),
                    "y": round(h - pad_bottom - bar_h, 1),
                    "w": round(bar_w, 1),
                    "h": round(bar_h, 1),
                    "color": color_by_name.get(person, default_color),
                    "person": person,
                    "day": key,
                    "count": cnt,
                }
            )
    return bars


def _taskers_axis_legend(
    day_seq: list[date],
    persons: list[str],
    totals_by_person: dict[str, int],
    color_by_name: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the day-axis labels and the per-person legend of the taskers chart."""
    default_color = "var(--dimmed)"
    axis = [{"label": "%s %d" % (_FR_WEEKDAYS[d.weekday()], d.day)} for d in day_seq]
    legend = [
        {
            "person": p,
            "color": color_by_name.get(p, default_color),
            "count": totals_by_person[p],
        }
        for p in persons
    ]
    return axis, legend


def _empty_taskers_ctx(w: float, h: float) -> dict[str, Any]:
    """Context of an empty taskers chart (no attributable activity)."""
    return {
        "taskers_bars": [],
        "taskers_axis": [],
        "taskers_legend": [],
        "taskers_total": 0,
        "taskers_vb_w": w,
        "taskers_vb_h": h,
    }


def _build_taskers_daily_chart(
    rows: list[dict[str, Any]],
    users: list[dict[str, Any]],
    *,
    today: date,
    days: int = TASKERS_WINDOW_DAYS,
) -> dict[str, Any]:
    """Build grouped-bar geometry for the per-day taskers chart (#507).

    ``rows`` are ``{day, user_name, count}`` aggregates from
    ``activity_daily_by_user``. Each raw principal is resolved to a person
    (token writes fold into the owner, #492), counts are bucketed per
    (day, person), and within each of the last ``days`` days one bar per
    active person is laid out side by side — a per-day comparison of who did
    the most. The SVG rects are precomputed here; day labels and the person
    legend live in HTML since the SVG is stretched with
    ``preserveAspectRatio=none`` and text would distort. ``today`` anchors the
    trailing window (injected for testing). Returns the template context
    (``taskers_bars``/``axis``/``legend``/``total`` + viewBox dimensions).
    """
    w, h = 760.0, 150.0
    users_by_id = {u["id"]: u["name"] for u in users}
    color_by_name = {u["name"]: u["color"] for u in users}

    day_seq = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    day_keys = [d.isoformat() for d in day_seq]

    per_day, totals_by_person = _bucket_activity_by_person(rows, users_by_id, day_keys)
    if not totals_by_person:
        return _empty_taskers_ctx(w, h)

    # Stable person order (most active first) shared across every day so a
    # person keeps the same slot + colour across the week.
    persons = sorted(totals_by_person, key=lambda p: (-totals_by_person[p], p))
    bars = _layout_taskers_bars(per_day, day_keys, persons, color_by_name, w=w, h=h)

    axis, legend = _taskers_axis_legend(
        day_seq, persons, totals_by_person, color_by_name
    )
    ctx = _empty_taskers_ctx(w, h)
    ctx.update(
        taskers_bars=bars,
        taskers_axis=axis,
        taskers_legend=legend,
        taskers_total=sum(totals_by_person.values()),
        taskers_window_days=days,
    )
    return ctx


def _project_card(
    project: dict[str, Any], proj_rows: list[tuple[str, int]], top_n: int
) -> dict[str, Any] | None:
    """One mini-card (top sections + total) — ``None`` if nothing classified."""
    if not proj_rows:
        return None
    max_count = proj_rows[0][1]
    sections = [
        {
            "section": name,
            "count": cnt,
            "pct": round(100 * cnt / max_count, 1) if max_count else 0,
        }
        for name, cnt in proj_rows[:top_n]
    ]
    return {
        "project": project,
        "sections": sections,
        "total": sum(cnt for _, cnt in proj_rows),
    }


def _build_wiki_sections_per_project_chart(
    rows: list[dict[str, Any]],
    projects: list[dict[str, Any]],
    *,
    top_n: int = 8,
) -> dict[str, Any]:
    """Build per-project mini-chart data for the category page (#572).

    Replaces the per-category aggregate (#533) that still mixed métiers — a finance
    board and a server board under the same cat have nothing in common, so each
    project gets its own bars.

    ``rows`` are ``{project_id, section_path, count}`` from
    ``wiki_section_counts_by_category_per_project`` (already ordered by project,
    then count desc). ``projects`` is the category's project list in display order;
    projects with no classifications are dropped. Bars within a card scale to that
    project's busiest section so they stay comparable inside the card.

    Args:
        rows: Per-(project, section) classification counts for one category.
        projects: Visible projects of the category in display order.
        top_n: Maximum number of section rows per mini-card.

    Returns:
        A context dict with ``wiki_by_project`` (list of cards, each with ``project``,
        ``sections``, ``total``) and ``wiki_by_project_total``.
    """
    by_proj: dict[str, list[tuple[str, int]]] = {}
    for r in rows:
        pid = str(r["project_id"])
        by_proj.setdefault(pid, []).append((str(r["section_path"]), int(r["count"])))

    cards = [
        card
        for p in projects
        if (card := _project_card(p, by_proj.get(p["id"], []), top_n)) is not None
    ]
    return {
        "wiki_by_project": cards,
        "wiki_by_project_total": sum(c["total"] for c in cards),
    }
