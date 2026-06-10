"""Per-day taskers chart unit tests (#507).

Covers the two pure helpers behind the home-page taskers chart:
- ``_resolve_activity_author`` maps a raw ``activities.user_name`` principal
  to a person (session name verbatim, token → owner, else None).
- ``_build_taskers_daily_chart`` resolves + buckets per (day, person) and
  lays out grouped bars over the trailing window.
"""

from __future__ import annotations

from datetime import date

from dashboard.routes.charts import (
    _build_taskers_daily_chart,
    _resolve_activity_author,
)

USERS = [
    {"id": "u1", "name": "Luc", "color": "var(--accent)"},
    {"id": "u2", "name": "Bob", "color": "var(--green)"},
]
TODAY = date(2026, 5, 29)


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


def test_taskers_daily_grouped_bars():
    """One bar per active person per day; token folds into owner, unowned dropped."""
    rows = [
        {"day": "2026-05-29", "user_name": "Luc", "count": 3},
        {"day": "2026-05-29", "user_name": "key:k:user:u2", "count": 1},  # Bob
        {"day": "2026-05-28", "user_name": "Luc", "count": 2},
        {"day": "2026-05-28", "user_name": "key:x", "count": 9},  # unowned → drop
    ]
    ctx = _build_taskers_daily_chart(rows, USERS, today=TODAY)
    assert ctx["taskers_total"] == 6
    assert len(ctx["taskers_axis"]) == 7
    assert ctx["taskers_axis"][-1]["label"].endswith("29")
    assert ctx["taskers_axis"][0]["label"].endswith("23")
    # Luc (5) ranks before Bob (1) in the shared legend / slot order.
    assert [row["person"] for row in ctx["taskers_legend"]] == ["Luc", "Bob"]
    # 3 bars: Luc+Bob on the 29th, Luc on the 28th.
    assert len(ctx["taskers_bars"]) == 3
    assert {b["day"] for b in ctx["taskers_bars"]} == {"2026-05-29", "2026-05-28"}
    assert all(b["count"] > 0 for b in ctx["taskers_bars"])


def test_taskers_merges_session_and_token_same_person_per_day():
    """A person's session + token writes count toward one bar that day."""
    rows = [
        {"day": "2026-05-29", "user_name": "Luc", "count": 2},
        {"day": "2026-05-29", "user_name": "key:k:user:u1", "count": 4},
    ]
    ctx = _build_taskers_daily_chart(rows, USERS, today=TODAY)
    assert ctx["taskers_total"] == 6
    bars = [b for b in ctx["taskers_bars"] if b["day"] == "2026-05-29"]
    assert len(bars) == 1
    assert bars[0]["person"] == "Luc"
    assert bars[0]["count"] == 6


def test_taskers_ignores_days_outside_window():
    """Activity older than the window is not counted."""
    rows = [{"day": "2026-05-01", "user_name": "Luc", "count": 5}]
    ctx = _build_taskers_daily_chart(rows, USERS, today=TODAY)
    assert ctx["taskers_total"] == 0
    assert ctx["taskers_bars"] == []


def test_taskers_empty_without_attributable_activity():
    """No attributable rows → no bars."""
    ctx = _build_taskers_daily_chart([], [], today=TODAY)
    assert ctx["taskers_bars"] == []
    assert ctx["taskers_total"] == 0
