"""E2E tests for the dashboard page."""

import re
import shutil
import tempfile

from playwright.sync_api import Page, Playwright, expect


class TestDashboardLoads:
    """Test that the dashboard renders correctly."""

    def test_title(self, live_server, clean_db, page: Page):
        """Dashboard page has correct title."""
        page.goto(live_server)
        expect(page).to_have_title("KEN")

    def test_header_visible(self, live_server, clean_db, page: Page):
        """Header with KENBOARD title is visible."""
        page.goto(live_server)
        expect(page.locator("h1")).to_have_text("KENBOARD")

    def test_header_shows_version(self, live_server, clean_db, page: Page):
        """#22: the kenboard version is rendered next to the title."""
        from dashboard import __version__

        page.goto(live_server)
        badge = page.locator(".header-version")
        expect(badge).to_be_visible()
        expect(badge).to_have_text(f"v{__version__}")

    def test_add_category_via_admin(self, live_server, clean_db, page: Page):
        """#162: categories are managed via /admin/board."""
        page.goto(live_server + "/admin/board")
        expect(page.locator(".section-onboard-btn")).to_be_visible()


class TestCategoryCRUD:
    """Test category create, edit, delete via /admin/board (#162)."""

    def test_create_category(self, live_server, clean_db, page: Page):
        """Create a category via admin board."""
        page.goto(live_server + "/admin/board")
        page.locator(".section-title .section-onboard-btn").click()
        page.locator("#cat-modal").wait_for(state="visible")
        page.fill("#cat-modal-name", "Technique")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".board-cat-name")).to_contain_text("Technique")

    def test_edit_category(self, live_server, clean_db, page: Page):
        """Edit a category name via admin board."""
        page.goto(live_server + "/admin/board")
        page.locator(".section-title .section-onboard-btn").click()
        page.locator("#cat-modal").wait_for(state="visible")
        page.fill("#cat-modal-name", "Old Name")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        page.locator(".board-cat-header .btn-edit:not(.section-onboard-btn)").first.click()
        page.locator("#cat-modal").wait_for(state="visible")
        page.fill("#cat-modal-name", "New Name")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".board-cat-name")).to_contain_text("New Name")

    def test_delete_category(self, live_server, clean_db, page: Page):
        """Delete a category via admin board."""
        page.goto(live_server + "/admin/board")
        page.locator(".section-title .section-onboard-btn").click()
        page.locator("#cat-modal").wait_for(state="visible")
        page.fill("#cat-modal-name", "ToDelete")
        page.click("#cat-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        page.locator(".board-cat-header .btn-edit:not(.section-onboard-btn)").first.click()
        page.locator("#cat-modal").wait_for(state="visible")
        page.click("#cat-modal-delete")
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()
        expect(page.locator(".board-cat")).to_have_count(0)


class TestCategoryDetail:
    """Test the category detail page."""

    def test_navigate_to_detail(self, live_server, clean_db, page: Page):
        """Click a category card to navigate to detail."""
        _create_category_via_admin(live_server, page)
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")
        expect(page).to_have_title("KEN / Tech")

    def test_add_project(self, live_server, clean_db, page: Page):
        """Create a project via admin board, verify on category page."""
        _create_category_and_project(live_server, page)
        expect(page.locator(".section-title")).to_contain_text("PROJ")


def _create_category_via_admin(live_server, page: Page) -> None:
    """Helper: create a category via /admin/board."""
    page.goto(live_server + "/admin/board")
    page.locator(".section-title .section-onboard-btn").click()
    page.fill("#cat-modal-name", "Tech")
    page.click("#cat-modal .btn-save")
    page.wait_for_timeout(500)


def _create_category_and_project(live_server, page: Page) -> None:
    """Helper: create a category + project via /admin/board, then navigate to the category page."""
    # Create category via admin board
    page.goto(live_server + "/admin/board")
    page.click(".section-onboard-btn")  # "+ Catégorie"
    page.fill("#cat-modal-name", "Tech")
    page.click("#cat-modal .btn-save")
    page.wait_for_timeout(500)
    page.reload()

    # Create project via admin board
    page.locator(".board-cat-header .section-onboard-btn").first.click()  # "+ Projet"
    page.fill("#new-proj-name", "Projet")
    page.fill("#new-proj-acronym", "PROJ")
    page.click("#project-modal .btn-save")
    page.wait_for_timeout(500)

    # Navigate to the category detail page
    page.goto(live_server)
    page.click(".cat-card")
    page.wait_for_url("**/cat/**")


class TestProjectCRUD:
    """Test project edit and delete via UI."""

    def test_edit_project(self, live_server, clean_db, page: Page):
        """Edit a project's name and acronym via admin board."""
        _create_category_and_project(live_server, page)

        # Open the project editor via admin board
        page.goto(live_server + "/admin/board")
        page.locator(".board-project .btn-edit").first.click()
        page.fill("#new-proj-name", "Projet Modifie")
        page.fill("#new-proj-acronym", "MOD")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)

        # Verify on category page
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")
        expect(page.locator(".section-title").first).to_contain_text("MOD")
        expect(page.locator(".section-title").first).to_contain_text("Projet Modifie")

    def test_delete_project(self, live_server, clean_db, page: Page):
        """Delete an empty project via admin board."""
        _create_category_and_project(live_server, page)

        page.goto(live_server + "/admin/board")
        page.locator(".board-project .btn-edit").first.click()
        page.click("#proj-modal-delete")
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)

        # Verify on category page
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")
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

    def test_task_id_visible(self, live_server, clean_db, page: Page):
        """#21: the task id is shown on every card (#N), dimmed and right-aligned, in
        both normal and detail mode.

        In normal mode the id sits next to the title (`.task-title-row .task-id`). In
        detail mode it moves into the right column above the avatar (`.task-id-detail`).
        """
        self._setup_project(live_server, page)

        # Add a task and capture its id
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "WithID")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        card = page.locator(".kanban-task").first
        task_id = card.get_attribute("data-task-id")
        inline_id = card.locator(".task-title-row .task-id")
        right_id = card.locator(".task-id-detail")

        # Normal mode: inline id visible, right-column id hidden
        expect(inline_id).to_be_visible()
        expect(inline_id).to_have_text(f"#{task_id}")
        expect(right_id).not_to_be_visible()

        # Detail mode: inline id hidden, right-column id visible
        card.click()
        expect(card).to_have_class(re.compile(r"\bdetail-mode\b"))
        expect(inline_id).not_to_be_visible()
        expect(right_id).to_be_visible()
        expect(right_id).to_have_text(f"#{task_id}")

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

    def test_task_detail_url_hash_sync(self, live_server, clean_db, page: Page):
        """#109: detail mode is mirrored in the URL fragment as ``#ID-<id>``.

        Opening a card writes the fragment, closing clears it, and a reload with the
        fragment still present restores detail mode automatically — which makes the deep
        links from the index "En cours" overview work and survives the 60s auto-refresh.
        """
        self._setup_project(live_server, page)

        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "Deep Link")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        card = page.locator(".kanban-task").first
        task_id = card.get_attribute("data-task-id")
        cat_url = page.url.split("#")[0]

        # Click → URL fragment is set to ``#ID-<id>``.
        card.click()
        expect(card).to_have_class(re.compile(r"\bdetail-mode\b"))
        assert page.evaluate("() => window.location.hash") == f"#ID-{task_id}"

        # Reload with the fragment present → detail mode is restored.
        page.reload()
        expect(page.locator(".kanban-task.detail-mode")).to_be_visible()
        assert page.evaluate("() => window.location.hash") == f"#ID-{task_id}"

        # Click again → fragment is cleared and detail mode collapses.
        page.locator(".kanban-task").first.click()
        expect(page.locator(".kanban-task.detail-mode")).to_have_count(0)
        assert page.evaluate("() => window.location.hash") == ""

        # Direct deep link from outside (e.g. the index "En cours" card).
        page.goto(f"{cat_url}#ID-{task_id}")
        expect(page.locator(".kanban-task.detail-mode")).to_be_visible()

    def _add_task(self, page: Page, title: str = "Ma Tache") -> None:
        """Helper: add a task via the kanban + button."""
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", title)
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

    def _open_task_edit_modal(self, page: Page) -> None:
        """Helper: click a task to enter detail mode then click its edit button.

        The selector explicitly excludes ``.btn-fullscreen`` (#155) which
        also has ``.btn-edit`` for visual styling but opens the fullscreen
        modal instead of the edit modal.
        """
        page.click(".kanban-task")
        page.locator(
            ".kanban-task.detail-mode .btn-edit:not(.btn-fullscreen)"
        ).first.wait_for(state="visible")
        page.locator(
            ".kanban-task.detail-mode .btn-edit:not(.btn-fullscreen)"
        ).first.click()
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

    def test_duplicate_task(self, live_server, clean_db, page: Page):
        """#17: the Dupliquer button creates a copy with ' - copy' suffix."""
        self._setup_project(live_server, page)
        self._add_task(page, "Original")

        self._open_task_edit_modal(page)
        # Duplicate button visible only in edit mode
        expect(page.locator("#task-modal-duplicate")).to_be_visible()
        page.click("#task-modal-duplicate")
        # Modal stays open, heading switches to "(copie)"
        expect(page.locator("#task-modal")).to_be_visible()
        expect(page.locator("#task-modal-heading")).to_contain_text("copie")
        # Title input now shows the new title with " - copy"
        expect(page.locator("#task-modal-title")).to_have_value("Original - copy")
        # Reload — both tasks must be in the DB
        page.reload()
        titles = sorted(t.inner_text() for t in page.locator(".task-title").all())
        assert titles == ["Original", "Original - copy"]

    def test_duplicate_button_hidden_on_create(self, live_server, clean_db, page: Page):
        """The Dupliquer button is only visible when editing an existing task, not when
        creating a new one.
        """
        self._setup_project(live_server, page)
        page.click(".kanban-add-btn")
        expect(page.locator("#task-modal")).to_be_visible()
        expect(page.locator("#task-modal-duplicate")).not_to_be_visible()

    def test_project_default_who_prefills_edit_modal_when_who_empty(
        self, live_server, clean_db, page: Page
    ):
        """#33: when editing a task whose `who` is empty, the project's default_who is
        used as fallback (instead of leaving the select on an arbitrary first option).

        When `who` is set, it is preserved.
        """
        # Seed two users
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Alice")
        page.fill("#new-color", "#8250df")
        page.click("#users-create-btn")
        page.wait_for_timeout(400)
        page.fill("#new-name", "Bob")
        page.fill("#new-color", "#bf8700")
        page.click("#users-create-btn")
        page.wait_for_timeout(400)

        _create_category_and_project(live_server, page)

        # Set default_who = Bob on the project via admin board
        page.goto(live_server + "/admin/board")
        page.locator(".board-project .btn-edit").first.click()
        page.locator("#project-modal").wait_for(state="visible")
        page.select_option("#new-proj-default-who", "Bob")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)

        # Go back to the category page
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")

        # Create a task WITHOUT a who (clear the dropdown)
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "NoWho")
        # Force empty who via JS (simulates an old task with no assignee)
        page.evaluate(
            "document.getElementById('task-modal-who').innerHTML = "
            "'<option value=\"\"></option>' + document.getElementById('task-modal-who').innerHTML"
        )
        page.select_option("#task-modal-who", "")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Open it for editing — `who` is empty, default_who=Bob should kick in
        self._open_task_edit_modal(page)
        expect(page.locator("#task-modal-who")).to_have_value("Bob")

    def test_edit_modal_keeps_existing_who(self, live_server, clean_db, page: Page):
        """#33 corollary: a task that already has a `who` set keeps it on edit, even if
        the project has a different default_who.
        """
        page.goto(live_server + "/admin/users")
        for name, color in [("Alice", "#8250df"), ("Bob", "#bf8700")]:
            page.fill("#new-name", name)
            page.fill("#new-color", color)
            page.click("#users-create-btn")
            page.wait_for_timeout(400)

        _create_category_and_project(live_server, page)
        page.goto(live_server + "/admin/board")
        page.locator(".board-project .btn-edit").first.click()
        page.locator("#project-modal").wait_for(state="visible")
        page.select_option("#new-proj-default-who", "Bob")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)

        # Go back to the category page
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")

        # Create a task explicitly assigned to Alice
        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "AliceTask")
        page.select_option("#task-modal-who", "Alice")
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # Open it: who must stay Alice, NOT switch to Bob (the project default)
        self._open_task_edit_modal(page)
        expect(page.locator("#task-modal-who")).to_have_value("Alice")

    def test_project_default_who_prefills_task_modal(
        self, live_server, clean_db, page: Page
    ):
        """#29: setting a default user on a project pre-fills the `who` select when
        creating a new task in that project.
        """
        # Seed users so the dropdown has options
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Alice")
        page.fill("#new-color", "#8250df")
        page.click("#users-create-btn")
        page.wait_for_timeout(400)
        page.fill("#new-name", "Bob")
        page.fill("#new-color", "#bf8700")
        page.click("#users-create-btn")
        page.wait_for_timeout(400)

        # Setup project
        _create_category_and_project(live_server, page)

        # Edit the project, set default_who = Bob via admin board
        page.goto(live_server + "/admin/board")
        page.locator(".board-project .btn-edit").first.click()
        page.locator("#project-modal").wait_for(state="visible")
        page.select_option("#new-proj-default-who", "Bob")
        page.click("#project-modal .btn-save")
        page.wait_for_timeout(500)

        # Go back to the category page
        page.goto(live_server)
        page.click(".cat-card")
        page.wait_for_url("**/cat/**")

        # Open the new task modal — `who` should be pre-filled to Bob
        page.click(".kanban-add-btn")
        expect(page.locator("#task-modal-who")).to_have_value("Bob")

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

    def test_task_description_xss_is_sanitized(self, live_server, clean_db, page: Page):
        """#52: marked.parse() output is run through DOMPurify before going into
        innerHTML, so a description containing inline event handlers or <script> tags is
        rendered as inert text/HTML, never executed.
        """
        self._setup_project(live_server, page)

        # Trip an alert dialog if any handler fires; the page.expect_dialog
        # context would catch it. Instead we install an unconditional
        # listener that fails the test if any dialog appears.
        dialogs: list[str] = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

        page.click(".kanban-add-btn")
        page.fill("#task-modal-title", "XSS")
        page.fill(
            "#task-modal-desc",
            "<img src=x onerror=alert('pwned-img')>"
            "<script>alert('pwned-script')</script>"
            "[link](javascript:alert('pwned-href'))",
        )
        page.click("#task-modal .btn-save")
        page.wait_for_timeout(500)
        page.reload()

        # ``renderMarkdown`` runs on load and writes into ``.task-desc``
        # regardless of whether the card is expanded. The element is
        # ``display:none`` until the card flips to detail-mode, so wait for
        # it to be attached to the DOM, not visible.
        page.wait_for_selector(".task-desc", state="attached")

        # Inspect the actual DOM, not the HTML source. Marked escapes inline
        # HTML so the substring ``onerror`` may legitimately appear as text
        # inside ``&lt;img onerror=...&gt;`` — that's safe, the browser
        # never executes it. What's NOT safe is an actual element carrying
        # the attribute, or a real <script>, or an anchor whose href is
        # ``javascript:``. Those are the conditions we assert against.
        has_onerror = page.eval_on_selector(
            ".task-desc",
            "el => !!el.querySelector('[onerror], [onload], [onclick]')",
        )
        has_script = page.eval_on_selector(
            ".task-desc", "el => !!el.querySelector('script')"
        )
        has_js_url = page.eval_on_selector(
            ".task-desc",
            "el => Array.from(el.querySelectorAll('a, img'))"
            ".some(n => (n.getAttribute('href') || n.getAttribute('src') || '')"
            ".toLowerCase().startsWith('javascript:'))",
        )
        assert not has_onerror, "an element carries an inline event handler"
        assert not has_script, "a <script> element survived sanitisation"
        assert not has_js_url, "a javascript: URL survived sanitisation"

        # No dialog ever fired
        assert dialogs == [], f"unexpected JS dialogs: {dialogs}"

        # Round-trip: the original markdown is still in the textarea on edit
        self._open_task_edit_modal(page)
        textarea_value = page.eval_on_selector("#task-modal-desc", "el => el.value")
        assert "onerror" in textarea_value  # raw source preserved

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
        expect(page).to_have_title("KEN / Utilisateurs")
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
        page.click("#users-create-btn")
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
        page.click("#users-create-btn")
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
        page.click("#users-create-btn")
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
        page.click("#users-create-btn")
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
        page.click("#users-create-btn")
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

    def test_create_user_does_not_modify_existing_users(
        self, live_server, clean_db, page: Page
    ):
        """Regression #19: creating a new user via the admin page must not touch any
        existing user (no name, color, or admin flag change).
        """
        page.goto(live_server + "/admin/users")
        # Seed several users including an admin Q (mirroring live state)
        for name, color, is_admin in [
            ("Alice", "#8250df", False),
            ("Bob", "#bf8700", False),
            ("Q", "#0969da", True),
        ]:
            page.fill("#new-name", name)
            page.fill("#new-color", color)
            if is_admin:
                page.check("#new-admin")
            page.click("#users-create-btn")
            page.wait_for_timeout(400)
            page.reload()

        # Snapshot all users before
        snap_before = sorted(
            page.eval_on_selector_all(
                "#users-table tbody tr[data-user-id]",
                """rows => rows.map(r => ({
                    id: r.dataset.userId,
                    name: r.querySelector('.u-name').value,
                    color: r.querySelector('.u-color').value,
                    is_admin: r.querySelector('.u-admin').checked,
                }))""",
            ),
            key=lambda r: r["name"],
        )
        assert len(snap_before) == 3

        # Create a new user
        page.fill("#new-name", "Newbie")
        page.fill("#new-color", "#abcdef")
        page.click("#users-create-btn")
        page.wait_for_timeout(500)
        page.reload()

        # All previously existing users must be unchanged
        snap_after = page.eval_on_selector_all(
            "#users-table tbody tr[data-user-id]",
            """rows => rows.map(r => ({
                id: r.dataset.userId,
                name: r.querySelector('.u-name').value,
                color: r.querySelector('.u-color').value,
                is_admin: r.querySelector('.u-admin').checked,
            }))""",
        )
        snap_after_by_id = {r["id"]: r for r in snap_after}
        for orig in snap_before:
            after = snap_after_by_id.get(orig["id"])
            assert after is not None, f"User {orig['name']} disappeared"
            assert after == orig, f"User {orig['name']} was modified: {orig} -> {after}"
        # And the new user is there
        assert any(r["name"] == "Newbie" for r in snap_after)

    def test_create_button_visually_distinct(self, live_server, clean_db, page: Page):
        """The create button uses .btn-save styling to be visually distinct from the
        per-row Enregistrer/Supprimer buttons (.btn-edit).

        Reduces the risk a user clicks the wrong button (#19 root-cause hypothesis).
        """
        page.goto(live_server + "/admin/users")
        btn = page.locator("#users-create-btn")
        expect(btn).to_have_class(re.compile(r"\bbtn-save\b"))

    def test_firefox_create_user_no_autofill_leak(
        self, live_server, clean_db, playwright: Playwright
    ):
        """Regression #19 (Firefox-specific): Firefox's form history would autofill the
        just-typed new-user values into the .u-name / .u-color inputs of pre-existing
        user rows after the page reloaded, making it look like Q (last user
        alphabetically) had been overwritten. The DB was always intact — the visual
        artifact came from form history.

        Fix: autocomplete="off" on .u-name / .u-color and #new-name / #new-color.

        This test launches a real Firefox with a persistent profile (so form
        history is enabled the same way it is for end users) and asserts that
        after creating a new user, every existing row's input still shows the
        server-rendered value, not the freshly-typed one.
        """
        profile_dir = tempfile.mkdtemp(prefix="pw_ff_bug19_")
        try:
            ctx = playwright.firefox.launch_persistent_context(
                profile_dir, headless=True
            )
            try:
                page = ctx.new_page()
                page.goto(live_server + "/admin/users")
                page.wait_for_selector("#users-create-btn")

                # Seed Alice + Q (admin), reloading after each
                expected = 0
                for name, color, is_admin in [
                    ("Alice", "#8250df", False),
                    ("Q", "#0969da", True),
                ]:
                    page.fill("#new-name", name)
                    page.fill("#new-color", color)
                    if is_admin:
                        page.check("#new-admin")
                    page.click("#users-create-btn")
                    expected += 1
                    expect(
                        page.locator("#users-table tbody tr[data-user-id]")
                    ).to_have_count(expected)

                snap_before = page.eval_on_selector_all(
                    "#users-table tbody tr[data-user-id]",
                    """rows => rows.map(r => ({
                        id: r.dataset.userId,
                        name: r.querySelector('.u-name').value,
                        color: r.querySelector('.u-color').value,
                    }))""",
                )
                assert len(snap_before) == 2

                # Now create a new user — Firefox MUST NOT autofill the
                # existing rows with these typed values after reload.
                page.fill("#new-name", "AutofillBait")
                page.fill("#new-color", "#deadbe")
                page.click("#users-create-btn")
                expect(
                    page.locator("#users-table tbody tr[data-user-id]")
                ).to_have_count(3)

                snap_after = page.eval_on_selector_all(
                    "#users-table tbody tr[data-user-id]",
                    """rows => rows.map(r => ({
                        id: r.dataset.userId,
                        name: r.querySelector('.u-name').value,
                        color: r.querySelector('.u-color').value,
                    }))""",
                )
            finally:
                ctx.close()
        finally:
            shutil.rmtree(profile_dir, ignore_errors=True)

        snap_after_by_id = {r["id"]: r for r in snap_after}
        for orig in snap_before:
            after = snap_after_by_id.get(orig["id"])
            assert after is not None, f"User {orig['name']} disappeared"
            assert after["name"] == orig["name"], (
                f"Firefox autofilled {orig['name']}'s name input: "
                f"expected {orig['name']!r}, got {after['name']!r}"
            )
            assert after["color"] == orig["color"], (
                f"Firefox autofilled {orig['name']}'s color input: "
                f"expected {orig['color']!r}, got {after['color']!r}"
            )
        assert any(r["name"] == "AutofillBait" for r in snap_after)

    def test_users_appear_in_task_who_dropdown(self, live_server, clean_db, page: Page):
        """Created users populate the 'who' dropdown of the task modal."""
        # Create two users via the admin page
        page.goto(live_server + "/admin/users")
        page.fill("#new-name", "Ivan")
        page.fill("#new-color", "#111111")
        page.click("#users-create-btn")
        page.wait_for_timeout(500)
        page.reload()
        page.fill("#new-name", "Judy")
        page.fill("#new-color", "#222222")
        page.click("#users-create-btn")
        page.wait_for_timeout(500)

        # Now create a category + project via admin board
        _create_category_and_project(live_server, page)
        page.click(".kanban-add-btn")

        # The dropdown options should match the users we created
        options = page.locator("#task-modal-who option")
        expect(options).to_have_count(2)
        expect(options.nth(0)).to_have_text("Ivan")
        expect(options.nth(1)).to_have_text("Judy")
