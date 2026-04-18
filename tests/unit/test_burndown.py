"""Burndown snapshot CLI and queries (#206)."""

from __future__ import annotations

from datetime import date, timedelta


class TestSnapshotRecording:
    """``burndown_record_snapshot`` upserts correctly."""

    def test_record_and_retrieve(self, db, queries, seed_project):
        """Insert a snapshot and read it back."""
        queries.burndown_record_snapshot(
            db, project_id="test-proj", todo=3, doing=2, review=1, done=5
        )
        rows = list(queries.burndown_get_by_project(db, project_id="test-proj", days=1))
        assert len(rows) == 1
        assert rows[0]["todo"] == 3
        assert rows[0]["doing"] == 2
        assert rows[0]["review"] == 1
        assert rows[0]["done"] == 5

    def test_upsert_overwrites_same_day(self, db, queries, seed_project):
        """Running twice on the same day updates the counters."""
        queries.burndown_record_snapshot(
            db, project_id="test-proj", todo=5, doing=0, review=0, done=0
        )
        queries.burndown_record_snapshot(
            db, project_id="test-proj", todo=3, doing=1, review=1, done=0
        )
        rows = list(queries.burndown_get_by_project(db, project_id="test-proj", days=1))
        assert len(rows) == 1
        assert rows[0]["todo"] == 3
        assert rows[0]["doing"] == 1


class TestCategoryAggregation:
    """``burndown_get_by_category`` sums across projects."""

    def test_aggregates_across_projects(self, db, queries):
        """Two projects in the same category are summed by date."""
        queries.cat_create(db, id="cat-bd", name="BD", color="#ff0000", position=0)
        queries.proj_create(
            db,
            id="proj-x",
            cat_id="cat-bd",
            name="X",
            acronym="X",
            status="active",
            position=0,
            default_who="",
        )
        queries.proj_create(
            db,
            id="proj-y",
            cat_id="cat-bd",
            name="Y",
            acronym="Y",
            status="active",
            position=0,
            default_who="",
        )
        queries.burndown_record_snapshot(
            db, project_id="proj-x", todo=2, doing=1, review=0, done=3
        )
        queries.burndown_record_snapshot(
            db, project_id="proj-y", todo=1, doing=0, review=1, done=4
        )
        rows = list(queries.burndown_get_by_category(db, category_id="cat-bd", days=1))
        assert len(rows) == 1
        assert rows[0]["todo"] == 3
        assert rows[0]["doing"] == 1
        assert rows[0]["review"] == 1
        assert rows[0]["done"] == 7


class TestSnapshotCLI:
    """``kenboard snapshot`` records one row per project."""

    def test_snapshot_via_cli(self, app, db, queries, seed_project):
        """Run the CLI and verify a snapshot was written."""
        from click.testing import CliRunner

        from dashboard.cli import snapshot

        # Seed a task so the counts are non-zero
        queries.task_create(
            db,
            project_id="test-proj",
            title="T1",
            description="",
            status="todo",
            who="",
            due_date=None,
            position=0,
        )
        runner = CliRunner()
        result = runner.invoke(snapshot, catch_exceptions=False)
        assert result.exit_code == 0
        assert "1 project" in result.output

        rows = list(queries.burndown_get_by_project(db, project_id="test-proj", days=1))
        assert len(rows) == 1
        assert rows[0]["todo"] == 1
        assert rows[0]["done"] == 0

    def test_snapshot_idempotent(self, app, db, queries, seed_project):
        """Running twice is safe."""
        from click.testing import CliRunner

        from dashboard.cli import snapshot

        runner = CliRunner()
        runner.invoke(snapshot, catch_exceptions=False)
        result = runner.invoke(snapshot, catch_exceptions=False)
        assert result.exit_code == 0


class TestBurndownSVGTemplate:
    """The burndown template renders SVG or a placeholder."""

    def test_renders_svg_with_enough_data(self, app):
        """With 2+ snapshots, the template emits an SVG element."""
        from flask import render_template_string

        tpl = '{% include "partials/burndown.html" %}'
        snapshots = [
            {
                "snapshot_date": date.today() - timedelta(days=1),
                "todo": 5,
                "doing": 2,
                "review": 1,
                "done": 3,
            },
            {
                "snapshot_date": date.today(),
                "todo": 3,
                "doing": 1,
                "review": 1,
                "done": 6,
            },
        ]
        with app.test_request_context():
            html = render_template_string(tpl, snapshots=snapshots, color="#ff0000")
        assert "<svg" in html
        assert "<polyline" in html
        assert "burndown-svg" in html

    def test_renders_placeholder_with_no_data(self, app):
        """With fewer than 2 snapshots, show a text message."""
        from flask import render_template_string

        tpl = '{% include "partials/burndown.html" %}'
        with app.test_request_context():
            html = render_template_string(tpl, snapshots=[], color="#ff0000")
        assert "<svg" not in html
        assert "Pas encore" in html

    def test_renders_placeholder_with_one_snapshot(self, app):
        """One snapshot is not enough for a trend line."""
        from flask import render_template_string

        tpl = '{% include "partials/burndown.html" %}'
        snapshots = [
            {
                "snapshot_date": date.today(),
                "todo": 5,
                "doing": 2,
                "review": 1,
                "done": 3,
            },
        ]
        with app.test_request_context():
            html = render_template_string(tpl, snapshots=snapshots, color="#ff0000")
        assert "<svg" not in html
