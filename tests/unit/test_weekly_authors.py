"""Weekly per-person activity chart unit tests (#492).

Covers the two pure helpers behind the home-page "tasks handled per week"
bar chart:
- ``_resolve_activity_author`` maps a raw ``activities.user_name`` principal
  to a person (session name verbatim, token → owner, else None).
- ``_build_weekly_author_chart`` resolves + re-aggregates rows into stacked
  bar geometry over a trailing ISO-week window.
"""

from __future__ import annotations

from datetime import date

from dashboard.routes.pages import (
    _build_weekly_author_chart,
    _resolve_activity_author,
)


def _yearweek(d: date) -> int:
    """ISO yearweek key matching ``YEARWEEK(d, 3)`` / the chart builder."""
    iso = d.isocalendar()
    return iso[0] * 100 + iso[1]


def test_resolve_author_session_name_passthrough():
    """A session write stores the display name verbatim."""
    assert _resolve_activity_author("Luc", {}) == "Luc"


def test_resolve_author_token_owner():
    """A token principal resolves to the owning user's name."""
    assert _resolve_activity_author("key:abc:user:u1", {"u1": "Luc"}) == "Luc"


def test_resolve_author_unowned_token_is_none():
    """A legacy/unowned key:<id> principal has no attributable person."""
    assert _resolve_activity_author("key:abc", {"u1": "Luc"}) is None


def test_resolve_author_deleted_owner_is_none():
    """An owner id no longer in the users map is unattributable."""
    assert _resolve_activity_author("key:abc:user:gone", {"u1": "Luc"}) is None


def test_resolve_author_empty_is_none():
    """An anonymous (empty) principal yields no person."""
    assert _resolve_activity_author("", {}) is None


def test_weekly_chart_attributes_token_to_owner_and_drops_unowned():
    """Token rows fold into their owner; unowned tokens are dropped."""
    today = date(2026, 5, 28)
    key = _yearweek(today)
    users = [
        {"id": "u1", "name": "Luc", "color": "var(--accent)"},
        {"id": "u2", "name": "Bob", "color": "var(--green)"},
    ]
    rows = [
        {"yearweek": key, "user_name": "key:k1:user:u1", "count": 3},
        {"yearweek": key, "user_name": "Bob", "count": 2},
        {"yearweek": key, "user_name": "key:k2", "count": 9},  # unowned → dropped
    ]
    ctx = _build_weekly_author_chart(rows, users, today=today)
    assert ctx["weekly_total"] == 5
    legend = {row["person"]: row["count"] for row in ctx["weekly_legend"]}
    assert legend == {"Luc": 3, "Bob": 2}
    # Highest total stacked first (bottom) and listed first in the legend.
    assert ctx["weekly_legend"][0]["person"] == "Luc"
    assert len(ctx["weekly_axis"]) == 12
    assert all(b["count"] > 0 for b in ctx["weekly_bars"])


def test_weekly_chart_merges_session_and_token_for_same_person():
    """A user's session writes and token writes count toward one bucket."""
    today = date(2026, 5, 28)
    key = _yearweek(today)
    users = [{"id": "u1", "name": "Luc", "color": "var(--accent)"}]
    rows = [
        {"yearweek": key, "user_name": "Luc", "count": 2},
        {"yearweek": key, "user_name": "key:k1:user:u1", "count": 4},
    ]
    ctx = _build_weekly_author_chart(rows, users, today=today)
    assert ctx["weekly_total"] == 6
    assert ctx["weekly_legend"] == [
        {"person": "Luc", "color": "var(--accent)", "count": 6}
    ]


def test_weekly_chart_empty_without_attributable_activity():
    """No attributable rows → empty geometry, no bars."""
    ctx = _build_weekly_author_chart([], [], today=date(2026, 5, 28))
    assert ctx["weekly_bars"] == []
    assert ctx["weekly_total"] == 0
    assert ctx["weekly_legend"] == []


def test_weekly_chart_ignores_weeks_outside_window():
    """Rows older than the trailing window are not counted."""
    today = date(2026, 5, 28)
    users = [{"id": "u1", "name": "Luc", "color": "var(--accent)"}]
    rows = [{"yearweek": _yearweek(date(2024, 1, 8)), "user_name": "Luc", "count": 5}]
    ctx = _build_weekly_author_chart(rows, users, today=today)
    assert ctx["weekly_total"] == 0
