"""Test Pydantic models validation."""

import pytest
from pydantic import ValidationError

from dashboard.models.category import Category, CategoryCreate, CategoryUpdate
from dashboard.models.project import Project, ProjectCreate, ProjectUpdate
from dashboard.models.task import Task, TaskCreate, TaskUpdate


class TestCategoryModels:
    """Test Category model validation."""

    def test_create_valid(self):
        data = CategoryCreate(name="Test", color="var(--accent)")
        assert data.name == "Test"
        assert data.color == "var(--accent)"

    def test_create_empty_name_fails(self):
        with pytest.raises(ValidationError):
            CategoryCreate(name="", color="var(--accent)")

    def test_create_missing_name_fails(self):
        with pytest.raises(ValidationError):
            CategoryCreate(color="var(--accent)")

    def test_update_partial(self):
        data = CategoryUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.color is None

    def test_update_with_project_order(self):
        data = CategoryUpdate(project_order=["a", "b", "c"])
        assert data.project_order == ["a", "b", "c"]

    def test_full_model(self):
        cat = Category(id="test", name="Test", color="var(--red)", position=0)
        dump = cat.model_dump()
        assert dump["id"] == "test"
        assert dump["position"] == 0


class TestProjectModels:
    """Test Project model validation."""

    def test_create_valid(self):
        data = ProjectCreate(name="My Project", acronym="PROJ", cat="tech")
        assert data.acronym == "PROJ"
        assert data.status == "active"

    def test_create_archived(self):
        data = ProjectCreate(
            name="Old", acronym="OLD", cat="tech", status="archived"
        )
        assert data.status == "archived"

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="X", acronym="X", cat="c", status="deleted")

    def test_create_acronym_too_long(self):
        with pytest.raises(ValidationError):
            ProjectCreate(name="X", acronym="TOOLONG", cat="c")

    def test_update_partial(self):
        data = ProjectUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.acronym is None

    def test_full_model(self):
        proj = Project(
            id="p", cat_id="c", name="P", acronym="PP", status="active", position=0
        )
        assert proj.cat_id == "c"


class TestTaskModels:
    """Test Task model validation."""

    def test_create_minimal(self):
        data = TaskCreate(project_id="proj", title="Do something")
        assert data.status == "todo"
        assert data.who == ""
        assert data.due_date is None

    def test_create_full(self):
        data = TaskCreate(
            project_id="proj",
            title="Do it",
            description="Details",
            status="doing",
            who="Alice",
            due_date="2026-04-15",
        )
        assert data.status == "doing"
        assert str(data.due_date) == "2026-04-15"

    def test_create_invalid_status(self):
        with pytest.raises(ValidationError):
            TaskCreate(project_id="p", title="X", status="invalid")

    def test_create_empty_title_fails(self):
        with pytest.raises(ValidationError):
            TaskCreate(project_id="p", title="")

    def test_update_partial(self):
        data = TaskUpdate(status="done", position=3)
        assert data.status == "done"
        assert data.position == 3
        assert data.title is None

    def test_full_model(self):
        from datetime import datetime

        task = Task(
            id=1,
            project_id="p",
            title="T",
            description="D",
            status="todo",
            who="Q",
            due_date=None,
            position=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        dump = task.model_dump(mode="json")
        assert dump["id"] == 1
        assert dump["due_date"] is None
