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


class TestTaskCRUD:
    """Test task operations."""

    def _setup_project(self, live_server, page: Page) -> None:
        """Create a category and project."""
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
        page.fill("#new-proj-name", "Projet")
        page.fill("#new-proj-acronym", "PROJ")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

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
