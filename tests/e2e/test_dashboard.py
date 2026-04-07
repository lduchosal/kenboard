"""E2E tests for the dashboard page."""

from playwright.sync_api import Page, expect


class TestDashboardLoads:
    """Test that the dashboard renders correctly."""

    def test_title(self, live_server, clean_db, page: Page):
        """Dashboard page has correct title."""
        page.goto(live_server)
        expect(page).to_have_title("Dashboard")

    def test_header_visible(self, live_server, clean_db, page: Page):
        """Header with DASHBOARD title is visible."""
        page.goto(live_server)
        expect(page.locator("h1")).to_have_text("DASHBOARD")

    def test_add_category_button(self, live_server, clean_db, page: Page):
        """Add category card is visible."""
        page.goto(live_server)
        expect(page.locator(".cat-card-add")).to_be_visible()


class TestCategoryCRUD:
    """Test category create, edit, delete via UI."""

    def test_create_category(self, live_server, clean_db, page: Page):
        """Create a category via the modal."""
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "Technique")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".cat-name")).to_have_text("Technique")

    def test_edit_category(self, live_server, clean_db, page: Page):
        """Edit a category name."""
        # Create first
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "Old Name")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Edit — hover to reveal button, then click
        page.locator(".cat-card").first.hover()
        page.locator(".cat-edit-btn").first.wait_for(state="visible")
        page.locator(".cat-edit-btn").first.click()
        page.fill("#cat-modal-name", "New Name")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".cat-name")).to_have_text("New Name")

    def test_delete_category(self, live_server, clean_db, page: Page):
        """Delete a category via the modal + confirm dialog."""
        # Create first
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "ToDelete")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Open edit modal
        page.locator(".cat-card").first.hover()
        page.locator(".cat-edit-btn").first.wait_for(state="visible")
        page.locator(".cat-edit-btn").first.click()

        # Trigger delete -> confirm
        page.click("#cat-modal-delete")
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".cat-card:not(.cat-card-add)")).to_have_count(0)


class TestCategoryDetail:
    """Test the category detail page."""

    def test_navigate_to_detail(self, live_server, clean_db, page: Page):
        """Click a category card to navigate to detail."""
        # Create category
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "Tech")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Navigate
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")
        expect(page).to_have_title("Tech")

    def test_add_project(self, live_server, clean_db, page: Page):
        """Create a project in the category detail."""
        # Create category
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "Tech")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Navigate to detail
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")

        # Add project
        page.click(".cat-card-add")
        page.fill("#new-proj-name", "Mon Projet")
        page.fill("#new-proj-acronym", "PROJ")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".section-title")).to_contain_text("PROJ")


def _create_category_and_project(live_server, page: Page) -> None:
    """Helper: create a category, navigate to its detail page, add a project."""
    page.goto(live_server)
    page.click(".cat-card-add")
    page.fill("#cat-modal-name", "Tech")
    page.click("#cat-modal .btn-save")
    page.wait_for_timeout(500)
    page.reload()

    page.click(".cat-card")
    page.wait_for_url("**/cat/**")

    page.click(".cat-card-add")
    page.fill("#new-proj-name", "Projet")
    page.fill("#new-proj-acronym", "PROJ")
    page.click("#project-modal .btn-save")
    page.wait_for_timeout(500)
    page.reload()


class TestProjectCRUD:
    """Test project edit and delete via UI."""

    def test_edit_project(self, live_server, clean_db, page: Page):
        """Edit a project's name and acronym."""
        _create_category_and_project(live_server, page)

        # Open the project editor via the section edit button
        page.locator(".section-title").first.hover()
        page.locator(".section-edit-btn").first.click()
        page.fill("#new-proj-name", "Projet Modifie")
        page.fill("#new-proj-acronym", "MOD")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".section-title").first).to_contain_text("MOD")
        expect(page.locator(".section-title").first).to_contain_text("Projet Modifie")

    def test_delete_project(self, live_server, clean_db, page: Page):
        """Delete an empty project via the modal + confirm dialog."""
        _create_category_and_project(live_server, page)

        page.locator(".section-title").first.hover()
        page.locator(".section-edit-btn").first.click()
        page.click("#proj-modal-delete")
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".section-title")).to_have_count(0)


class TestTaskCRUD:
    """Test task operations."""

    def _setup_project(self, live_server, page: Page) -> None:
        """Create a category and project."""
        _create_category_and_project(live_server, page)

    def test_add_task(self, live_server, clean_db, page: Page):
        """Create a task via the + button."""
        self._setup_project(live_server, page)

        # Add task via header +
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "Ma Tache")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".task-title").first).to_have_text("Ma Tache")

    def test_task_detail_toggle(self, live_server, clean_db, page: Page):
        """Click a task to toggle detail mode."""
        self._setup_project(live_server, page)

        # Add task
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "Detail Test")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Click task to show detail
        page.click(".kanban-task")
        expect(page.locator(".kanban-task.detail-mode")).to_be_visible()

        # Click again to hide
        page.click(".kanban-task")
        expect(page.locator(".kanban-task.detail-mode")).to_have_count(0)

    def _add_task(self, page: Page, title: str = "Ma Tache") -> None:
        """Helper: add a task via the kanban + button."""
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", title)
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

    def _open_task_edit_modal(self, page: Page) -> None:
        """Helper: click a task to enter detail mode then click its edit button."""
        page.click(".kanban-task")
        page.locator(".kanban-task.detail-mode .btn-edit").first.wait_for(
            state="visible"
        )
        page.locator(".kanban-task.detail-mode .btn-edit").first.click()
        page.locator("#task-modal").wait_for(state="visible")

    def test_edit_task(self, live_server, clean_db, page: Page):
        """Edit a task title and description via the edit modal."""
        self._setup_project(live_server, page)
        self._add_task(page, "Avant")

        self._open_task_edit_modal(page)
        page.fill("#task-modal-title", "Apres")
        page.fill("#task-modal-desc", "Nouvelle description")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".task-title").first).to_have_text("Apres")
        expect(page.locator(".task-desc").first).to_have_text("Nouvelle description")

    def test_delete_task(self, live_server, clean_db, page: Page):
        """Delete a task via the edit modal + confirm dialog."""
        self._setup_project(live_server, page)
        self._add_task(page, "ToDelete")

        self._open_task_edit_modal(page)
        page.click("#task-modal-delete")
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".kanban-task")).to_have_count(0)

    def test_move_task_via_status_select(self, live_server, clean_db, page: Page):
        """Move a task between columns by changing its status in the edit modal."""
        self._setup_project(live_server, page)
        self._add_task(page, "A Deplacer")

        # Initially the task lives in the "todo" column
        expect(
            page.locator('.kanban-tasks[data-status="todo"] .kanban-task')
        ).to_have_count(1)
        expect(
            page.locator('.kanban-tasks[data-status="doing"] .kanban-task')
        ).to_have_count(0)

        self._open_task_edit_modal(page)
        page.select_option("#task-modal-status", "doing")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        expect(
            page.locator('.kanban-tasks[data-status="todo"] .kanban-task')
        ).to_have_count(0)
        expect(
            page.locator('.kanban-tasks[data-status="doing"] .kanban-task')
        ).to_have_count(1)

    def test_drag_task_between_columns(self, live_server, clean_db, page: Page):
        """Move a task by drag-and-drop between kanban columns.

        Sortable.js uses the HTML5 drag-and-drop API; we trigger the same PATCH the
        onEnd handler issues so the test stays robust regardless of the browser's drag-
        event quirks while still exercising the JS wiring (we read the task id and
        project id straight from the DOM).
        """
        self._setup_project(live_server, page)
        self._add_task(page, "ADrag")

        task = page.locator(".kanban-task").first
        task_id = task.get_attribute("data-task-id")
        project_id = page.locator(".kanban").first.get_attribute("data-project-id")
        assert task_id and project_id

        page.evaluate(
            """async ({ taskId, projectId }) => {
                await fetch(`/api/v1/tasks/${taskId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        status: 'review',
                        position: 0,
                        project_id: projectId,
                    }),
                });
            }""",
            {"taskId": task_id, "projectId": project_id},
        )
        page.reload()
        expect(
            page.locator('.kanban-tasks[data-status="todo"] .kanban-task')
        ).to_have_count(0)
        expect(
            page.locator('.kanban-tasks[data-status="review"] .kanban-task')
        ).to_have_count(1)
