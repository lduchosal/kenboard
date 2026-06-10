"""Unit tests for the tasks-per-board pie geometry (ken #620 / #806)."""

from dashboard.routes.charts_pie import _build_tasks_per_board_pie

CATS = [
    {"id": "c1", "name": "Infra"},
    {"id": "c2", "name": "Dev"},
]


def _proj(pid: str, cat: str, total: int) -> dict:
    return {"id": pid, "cat_id": cat, "total": total}


class TestTasksPerBoardPie:
    """SVG arc paths for the dashboard pie, one slice per category."""

    def test_empty_when_no_tasks(self):
        ctx = _build_tasks_per_board_pie(CATS, [_proj("p1", "c1", 0)])
        assert ctx == {"tasks_per_board_pie": [], "tasks_per_board_total": 0}

    def test_single_category_renders_full_circle(self):
        ctx = _build_tasks_per_board_pie(CATS, [_proj("p1", "c1", 7)])
        slices = ctx["tasks_per_board_pie"]
        assert len(slices) == 1
        assert slices[0]["pct"] == 100.0
        assert slices[0]["count"] == 7
        # Full circle = two 180° arcs, no line-to-centre segment.
        assert slices[0]["path_d"].count("A ") == 2
        assert "L " not in slices[0]["path_d"]

    def test_two_categories_split_proportionally(self):
        projects = [_proj("p1", "c1", 3), _proj("p2", "c2", 1)]
        ctx = _build_tasks_per_board_pie(CATS, projects)
        slices = ctx["tasks_per_board_pie"]
        assert ctx["tasks_per_board_total"] == 4
        assert [s["pct"] for s in slices] == [75.0, 25.0]
        # The 75 % slice spans more than half the circle → large-arc flag set.
        assert " 1 1 " in slices[0]["path_d"]
        assert " 0 1 " in slices[1]["path_d"]

    def test_zero_count_category_is_dropped(self):
        projects = [_proj("p1", "c1", 5), _proj("p2", "c2", 0)]
        ctx = _build_tasks_per_board_pie(CATS, projects)
        assert len(ctx["tasks_per_board_pie"]) == 1
        assert ctx["tasks_per_board_pie"][0]["cat"]["id"] == "c1"
