"""E2E tests for the dashboard page."""

from playwright.sync_api import Page, expect


class TestDashboardLoads:
    """Test that the dashboard renders correctly."""

    def test_title(self, live_server, clean_db, page: Page):
        """Dashboard page has correct title."""
        page.goto(live_server)
        expect(page).to_have_title("Kenboard")

    def test_header_visible(self, live_server, clean_db, page: Page):
        """Header with KENBOARD title is visible."""
        page.goto(live_server)
        expect(page.locator("h1")).to_have_text("KENBOARD")

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

    def test_edit_modal_status_reflects_dragged_position(
        self, live_server, clean_db, page: Page
    ):
        """Regression #11: after a drag&drop without reload, opening the edit modal must
        show the task's current column status, not the stale value baked into the inline
        onclick at render time.

        The previous bug made every edited task silently revert to "A faire".
        """
        self._setup_project(live_server, page)
        self._add_task(page, "Bug11")

        task_id = page.locator(".kanban-task").first.get_attribute("data-task-id")
        project_id = page.locator(".kanban").first.get_attribute("data-project-id")
        page.evaluate(
            """async ({ taskId, projectId }) => {
                const card = document.querySelector(`[data-task-id="${taskId}"]`);
                const target = document.querySelector('.kanban-tasks[data-status="doing"]');
                target.appendChild(card);
                await fetch(`/api/v1/tasks/${taskId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'doing', position: 0, project_id: projectId }),
                });
            }""",
            {"taskId": task_id, "projectId": project_id},
        )
        # No reload — the onclick attribute still has render-time data
        self._open_task_edit_modal(page)
        assert page.eval_on_selector("#task-modal-status", "el => el.value") == "doing"

        # Save without touching status, reload, the task must stay in 'doing'
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(
            page.locator('.kanban-tasks[data-status="doing"] .kanban-task')
        ).to_have_count(1)
        expect(
            page.locator('.kanban-tasks[data-status="todo"] .kanban-task')
        ).to_have_count(0)

    def test_task_description_renders_markdown(self, live_server, clean_db, page: Page):
        """#15: task descriptions are authored in Markdown and rendered as HTML in the
        card body via marked.js.
        """
        self._setup_project(live_server, page)

        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "MD")
        page.fill(
            "#task-modal-desc",
            "**bold** and *italic*\n\n- one\n- two\n\n`code`",
        )
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # marked.js parses the textContent into rich HTML
        html = page.eval_on_selector(".task-desc", "el => el.innerHTML")
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<ul>" in html and "<li>one</li>" in html
        assert "<code>code</code>" in html

        # Editing must round-trip the raw markdown (not the rendered HTML) so
        # the user keeps editing the source.
        self._open_task_edit_modal(page)
        textarea_value = page.eval_on_selector("#task-modal-desc", "el => el.value")
        assert "**bold**" in textarea_value
        assert "- one" in textarea_value

    def test_auto_refresh_skips_when_modal_open(
        self, live_server, clean_db, page: Page
    ):
        """#14: shouldSkipRefresh() must return true while a modal is open so the
        periodic reload does not wipe a half-typed task.
        """
        self._setup_project(live_server, page)

        # No modal open → refresh would proceed
        assert page.evaluate("shouldSkipRefresh()") is False

        # Open the new-task modal → refresh must be skipped
        page.click(".kanban-add-btn")
        page.locator("#task-modal").wait_for(state="visible")
        assert page.evaluate("shouldSkipRefresh()") is True

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


class TestAdminUsers:
    """Test the /admin/users page UI."""

    def test_admin_page_loads(self, live_server, clean_db, page: Page):
        """Admin users page renders with header and empty user table."""
        page.goto(live_server + "/admin/users")
        expect(page).to_have_title("Utilisateurs")
        expect(page.locator("#users-table")).to_be_visible()
        # Empty DB → only the "add" row exists
        expect(page.locator("#users-table tbody tr[data-user-id]")).to_have_count(0)
        expect(page.locator("#users-add-row")).to_be_visible()

    def test_create_user(self, live_server, clean_db, page: Page):
        """Create a user via the add row at the bottom of the table."""
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Dave")
        page.fill("#new-color", "#abcdef")
        page.click("#new-password")
        page.fill("#new-password", "secret123")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()
        rows = page.locator("#users-table tbody tr[data-user-id]")
        expect(rows).to_have_count(1)
        expect(rows.first.locator(".u-name")).to_have_value("Dave")
        expect(rows.first.locator(".u-color")).to_have_value("#abcdef")

    def test_create_user_admin_flag(self, live_server, clean_db, page: Page):
        """Create a user with the admin checkbox checked."""
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Eve")
        page.fill("#new-color", "#112233")
        page.check("#new-admin")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()
        admin_checkbox = page.locator(
            "#users-table tbody tr[data-user-id] .u-admin"
        ).first
        expect(admin_checkbox).to_be_checked()

    def test_edit_user_color(self, live_server, clean_db, page: Page):
        """Edit an existing user's color via the inline form."""
        # Seed via API
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Frank")
        page.fill("#new-color", "#000000")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()

        row = page.locator("#users-table tbody tr[data-user-id]").first
        row.locator(".u-color").fill("#ffffff")
        row.locator(".btn-save-user").click()
        page.wait_for_timeout(500)
        page.reload()

        expect(
            page.locator("#users-table tbody tr[data-user-id]").first.locator(
                ".u-color"
            )
        ).to_have_value("#ffffff")

    def test_toggle_admin_via_edit(self, live_server, clean_db, page: Page):
        """Toggle is_admin from false to true via the edit form."""
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Grace")
        page.fill("#new-color", "#102030")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()

        row = page.locator("#users-table tbody tr[data-user-id]").first
        row.locator(".u-admin").check()
        row.locator(".btn-save-user").click()
        page.wait_for_timeout(500)
        page.reload()

        expect(
            page.locator("#users-table tbody tr[data-user-id]").first.locator(
                ".u-admin"
            )
        ).to_be_checked()

    def test_delete_user(self, live_server, clean_db, page: Page):
        """Delete a user via the confirm dialog."""
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Heidi")
        page.fill("#new-color", "#aabbcc")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()

        expect(page.locator("#users-table tbody tr[data-user-id]")).to_have_count(1)

        page.locator("#users-table tbody tr[data-user-id]").first.locator(
            ".btn-delete-user"
        ).click()
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()

        expect(page.locator("#users-table tbody tr[data-user-id]")).to_have_count(0)

    def test_users_appear_in_task_who_dropdown(self, live_server, clean_db, page: Page):
        """Created users populate the 'who' dropdown of the task modal."""
        # Create two users via the admin page
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Ivan")
        page.fill("#new-color", "#111111")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)
        page.reload()
        page.fill("#new-name", "Judy")
        page.fill("#new-color", "#222222")
        page.click("#users-add-row .btn-edit")
        page.wait_for_timeout(500)

        # Now create a category + project + open the task modal
        page.goto(live_server)
        page.click(".cat-card-add")
        page.fill("#cat-modal-name", "Tech")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")
        page.click(".cat-card-add")
        page.fill("#new-proj-name", "Proj")
        page.fill("#new-proj-acronym", "PROJ")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        page.click(".kanban-add-btn")

        # The dropdown options should match the users we created
        options = page.locator("#task-modal-who option")
        expect(options).to_have_count(2)
        expect(options.nth(0)).to_have_text("Ivan")
        expect(options.nth(1)).to_have_text("Judy")
