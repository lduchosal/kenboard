"""Author leaderboard unit tests (#492).

Covers the two pure helpers behind the home-page "biggest ken tasker"
leaderboard:
- ``_resolve_activity_author`` maps a raw ``activities.user_name`` principal
  to a person (session name verbatim, token → owner, else None).
- ``_build_author_leaderboard`` resolves + sums per person and lays out one
  ranked bar per person.
"""

from __future__ import annotations

from dashboard.routes.pages import (
    _build_author_leaderboard,
    _resolve_activity_author,
)

USERS = [
    {"id": "u1", "name": "Luc", "color": "var(--accent)"},
    {"id": "u2", "name": "Bob", "color": "var(--green)"},
]


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


def test_leaderboard_one_bar_per_person_ranked_desc():
    """One bar per attributable person, tallest (most active) first."""
    rows = [
        {"user_name": "Bob", "count": 2},
        {"user_name": "key:k1:user:u1", "count": 5},
        {"user_name": "key:k2", "count": 9},  # unowned → dropped
    ]
    ctx = _build_author_leaderboard(rows, USERS)
    assert ctx["leaderboard_total"] == 7
    assert [b["person"] for b in ctx["leaderboard_bars"]] == ["Luc", "Bob"]
    assert [b["count"] for b in ctx["leaderboard_bars"]] == [5, 2]
    # leader's bar is the tallest
    assert ctx["leaderboard_bars"][0]["h"] >= ctx["leaderboard_bars"][1]["h"]


def test_leaderboard_merges_session_and_token_for_same_person():
    """A user's session writes and token writes count toward one bar."""
    rows = [
        {"user_name": "Luc", "count": 2},
        {"user_name": "key:k1:user:u1", "count": 4},
    ]
    ctx = _build_author_leaderboard(rows, USERS)
    assert len(ctx["leaderboard_bars"]) == 1
    bar = ctx["leaderboard_bars"][0]
    assert bar["person"] == "Luc"
    assert bar["count"] == 6
    assert bar["color"] == "var(--accent)"
    assert ctx["leaderboard_total"] == 6


def test_leaderboard_empty_without_attributable_activity():
    """No attributable rows → no bars."""
    ctx = _build_author_leaderboard([], [])
    assert ctx["leaderboard_bars"] == []
    assert ctx["leaderboard_total"] == 0
