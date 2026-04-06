"""Test Flask API routes."""

import json


class TestCategoryAPI:
    """Test category API endpoints."""

    def test_list_empty(self, client, db):
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create(self, client, db):
        resp = client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "Tech", "color": "var(--accent)"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Tech"
        assert data["color"] == "var(--accent)"
        assert data["position"] == 0

    def test_create_and_list(self, client, db):
        client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "A", "color": "red"}),
            content_type="application/json",
        )
        client.post(
            "/api/v1/categories",
            data=json.dumps({"name": "B", "color": "blue"}),
            content_type="application/json",
        )
        resp = client.get("/api/v1/categories")
        data = resp.get_json()
        assert len(data) == 2

    def test_update(self, client, db, queries):
        queries.cat_create(db, id="upd", name="Old", color="red", position=0)
        resp = client.patch(
            "/api/v1/categories/upd",
            data=json.dumps({"name": "New"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "New"

    def test_update_not_found(self, client, db):
        resp = client.patch(
            "/api/v1/categories/nonexistent",
            data=json.dumps({"name": "X"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_delete(self, client, db, queries):
        queries.cat_create(db, id="del", name="Del", color="red", position=0)
        resp = client.delete("/api/v1/categories/del")
        assert resp.status_code == 204

    def test_reorder(self, client, db, queries):
        queries.cat_create(db, id="a", name="A", color="r", position=0)
        queries.cat_create(db, id="b", name="B", color="r", position=1)
        queries.cat_create(db, id="c", name="C", color="r", position=2)
        resp = client.post(
            "/api/v1/categories/reorder",
            data=json.dumps({"from": 0, "to": 2}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        cats = client.get("/api/v1/categories").get_json()
        ids = [c["id"] for c in cats]
        assert ids == ["b", "c", "a"]

    def test_create_invalid_missing_name(self, client, db):
        resp = client.post(
            "/api/v1/categories",
            data=json.dumps({"color": "red"}),
            content_type="application/json",
        )
        assert resp.status_code == 422


class TestProjectAPI:
    """Test project API endpoints."""

    def test_create(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        resp = client.post(
            "/api/v1/projects",
            data=json.dumps({"name": "My Project", "acronym": "PROJ", "cat": "cat"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["acronym"] == "PROJ"
        assert data["status"] == "active"

    def test_list_by_cat(self, client, db, queries):
        queries.cat_create(db, id="cat", name="Cat", color="r", position=0)
        queries.proj_create(
            db,
            id="p1",
            cat_id="cat",
            name="P1",
            acronym="PP",
            status="active",
            position=0,
        )
        resp = client.get("/api/v1/projects?cat=cat")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    def test_delete_with_tasks_fails(self, client, db, queries, seed_task):
        resp = client.delete("/api/v1/projects/test-proj")
        assert resp.status_code == 400

    def test_delete_empty_project(self, client, db, queries, seed_project):
        resp = client.delete("/api/v1/projects/test-proj")
        assert resp.status_code == 204


class TestTaskAPI:
    """Test task API endpoints."""

    def test_list_requires_project(self, client, db):
        resp = client.get("/api/v1/tasks")
        assert resp.status_code == 400

    def test_create(self, client, db, queries, seed_project):
        resp = client.post(
            "/api/v1/tasks",
            data=json.dumps(
                {"project_id": "test-proj", "title": "New Task", "status": "todo"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "New Task"
        assert data["id"] > 0

    def test_update_status(self, client, db, queries, seed_task):
        task_id = seed_task["id"]
        resp = client.patch(
            f"/api/v1/tasks/{task_id}",
            data=json.dumps({"status": "doing", "position": 0}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "doing"

    def test_delete(self, client, db, queries, seed_task):
        task_id = seed_task["id"]
        resp = client.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 204

    def test_list_by_project(self, client, db, queries, seed_task):
        resp = client.get("/api/v1/tasks?project=test-proj")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Task"
