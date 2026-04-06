"""Test aiosql queries load correctly and execute against the DB."""


class TestQueriesLoad:
    """Test that all expected queries are loaded."""

    def test_category_queries_exist(self, queries):
        assert hasattr(queries, "cat_get_all")
        assert hasattr(queries, "cat_get_by_id")
        assert hasattr(queries, "cat_create")
        assert hasattr(queries, "cat_update")
        assert hasattr(queries, "cat_delete")
        assert hasattr(queries, "cat_update_position")
        assert hasattr(queries, "cat_max_position")

    def test_project_queries_exist(self, queries):
        assert hasattr(queries, "proj_get_all")
        assert hasattr(queries, "proj_get_by_cat")
        assert hasattr(queries, "proj_get_by_id")
        assert hasattr(queries, "proj_create")
        assert hasattr(queries, "proj_update")
        assert hasattr(queries, "proj_delete")
        assert hasattr(queries, "proj_update_position")
        assert hasattr(queries, "proj_max_position_in_cat")
        assert hasattr(queries, "proj_count_tasks")

    def test_task_queries_exist(self, queries):
        assert hasattr(queries, "task_get_by_project")
        assert hasattr(queries, "task_get_by_id")
        assert hasattr(queries, "task_create")
        assert hasattr(queries, "task_update")
        assert hasattr(queries, "task_update_status")
        assert hasattr(queries, "task_delete")
        assert hasattr(queries, "task_max_position")


class TestCategoryQueries:
    """Test category SQL queries."""

    def test_get_all_empty(self, db, queries):
        rows = list(queries.cat_get_all(db))
        assert rows == []

    def test_create_and_get(self, db, queries):
        queries.cat_create(db, id="cat1", name="Cat 1", color="red", position=0)
        row = queries.cat_get_by_id(db, id="cat1")
        assert row["name"] == "Cat 1"
        assert row["color"] == "red"
        assert row["position"] == 0

    def test_update(self, db, queries, seed_category):
        queries.cat_update(db, id="test-cat", name="Updated", color="blue")
        row = queries.cat_get_by_id(db, id="test-cat")
        assert row["name"] == "Updated"
        assert row["color"] == "blue"

    def test_delete(self, db, queries, seed_category):
        queries.cat_delete(db, id="test-cat")
        row = queries.cat_get_by_id(db, id="test-cat")
        assert row is None

    def test_max_position_empty(self, db, queries):
        result = queries.cat_max_position(db)
        assert result == -1

    def test_max_position(self, db, queries):
        queries.cat_create(db, id="a", name="A", color="r", position=5)
        queries.cat_create(db, id="b", name="B", color="r", position=10)
        assert queries.cat_max_position(db) == 10

    def test_update_position(self, db, queries, seed_category):
        queries.cat_update_position(db, id="test-cat", position=42)
        row = queries.cat_get_by_id(db, id="test-cat")
        assert row["position"] == 42


class TestProjectQueries:
    """Test project SQL queries."""

    def test_create_and_get(self, db, queries, seed_category):
        queries.proj_create(
            db,
            id="p1",
            cat_id="test-cat",
            name="P1",
            acronym="PP",
            status="active",
            position=0,
        )
        row = queries.proj_get_by_id(db, id="p1")
        assert row["name"] == "P1"
        assert row["cat_id"] == "test-cat"

    def test_get_by_cat(self, db, queries, seed_project):
        rows = list(queries.proj_get_by_cat(db, cat_id="test-cat"))
        assert len(rows) == 1
        assert rows[0]["id"] == "test-proj"

    def test_count_tasks_zero(self, db, queries, seed_project):
        count = queries.proj_count_tasks(db, project_id="test-proj")
        assert count == 0

    def test_count_tasks_nonzero(self, db, queries, seed_task):
        count = queries.proj_count_tasks(db, project_id="test-proj")
        assert count == 1

    def test_cascade_delete(self, db, queries, seed_task):
        """Deleting a category cascades to projects and tasks."""
        queries.cat_delete(db, id="test-cat")
        assert queries.proj_get_by_id(db, id="test-proj") is None


class TestTaskQueries:
    """Test task SQL queries."""

    def test_create_and_get(self, db, queries, seed_project):
        queries.task_create(
            db,
            project_id="test-proj",
            title="T1",
            description="",
            status="todo",
            who="Q",
            due_date=None,
            position=0,
        )
        cur = db.cursor()
        cur.execute("SELECT LAST_INSERT_ID()")
        task_id = cur.fetchone()["LAST_INSERT_ID()"]
        assert isinstance(task_id, int)
        assert task_id > 0
        row = queries.task_get_by_id(db, id=task_id)
        assert row["title"] == "T1"

    def test_get_by_project(self, db, queries, seed_task):
        rows = list(queries.task_get_by_project(db, project_id="test-proj"))
        assert len(rows) == 1
        assert rows[0]["title"] == "Test Task"

    def test_update_status(self, db, queries, seed_task):
        task_id = seed_task["id"]
        queries.task_update_status(db, id=task_id, status="doing", position=0)
        row = queries.task_get_by_id(db, id=task_id)
        assert row["status"] == "doing"

    def test_delete(self, db, queries, seed_task):
        task_id = seed_task["id"]
        queries.task_delete(db, id=task_id)
        assert queries.task_get_by_id(db, id=task_id) is None
