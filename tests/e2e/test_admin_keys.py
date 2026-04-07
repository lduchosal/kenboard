"""E2E tests for the /admin/keys page."""

from playwright.sync_api import Page, expect


class TestAdminKeysPage:
    """Sanity tests for the /admin/keys management page."""

    def test_page_loads_empty(self, live_server, clean_db, page: Page):
        page.goto(live_server + "/admin/keys")
        expect(page).to_have_title("Cles API")
        expect(page.locator("#keys-table")).to_be_visible()
        expect(page.locator("#keys-table tbody tr[data-key-id]")).to_have_count(0)
        expect(page.locator("#keys-add-row")).to_be_visible()

    def test_create_key_shows_plaintext_modal(self, live_server, clean_db, page: Page):
        page.goto(live_server + "/admin/keys")
        page.fill("#new-key-label", "ci-key")
        page.click("#keys-create-btn")
        modal = page.locator("#key-shown-modal")
        expect(modal).to_be_visible()
        key_value = page.locator("#key-shown-text").input_value()
        assert key_value.startswith("kb_")
        assert len(key_value) > 10

    def test_create_then_list(self, live_server, clean_db, page: Page):
        page.goto(live_server + "/admin/keys")
        page.fill("#new-key-label", "first")
        page.click("#keys-create-btn")
        page.locator("#key-shown-modal").wait_for(state="visible")
        page.click("#key-shown-modal .btn-save")  # closes & reloads
        # After reload, the row exists with the right label
        expect(page.locator("#keys-table tbody tr[data-key-id]")).to_have_count(1)
        expect(
            page.locator("#keys-table tbody tr[data-key-id] .k-label").first
        ).to_have_value("first")

    def test_revoke_key(self, live_server, clean_db, page: Page):
        page.goto(live_server + "/admin/keys")
        page.fill("#new-key-label", "to-revoke")
        page.click("#keys-create-btn")
        page.locator("#key-shown-modal").wait_for(state="visible")
        page.click("#key-shown-modal .btn-save")
        # Revoke
        page.locator("#keys-table tbody tr[data-key-id] .btn-delete-key").first.click()
        page.locator("#confirm-modal").wait_for(state="visible")
        page.click("#confirm-modal-ok")
        page.wait_for_timeout(500)
        page.reload()
        # Key still listed but with revoked badge
        expect(page.locator("#keys-table tbody tr[data-key-id]")).to_have_count(1)
        expect(page.locator("#keys-table tbody tr[data-key-id]").first).to_contain_text(
            "révoquée"
        )
