"""Generate kenboard screenshots for the README using Playwright.

Spins up a kenboard server against the test database, seeds a small
amount of demo data, then drives Chromium through the main views and
writes the captures to ``doc/images/``. Re-run after a UI change to
refresh the README assets::

    pdm run screenshots

The script never touches the production database — it always points
``dashboard.db.get_connection`` at ``DB_TEST_*`` (cf. ``.env``).
"""

from __future__ import annotations

import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

# The app refuses to boot in non-debug mode without a secret key. We
# only ever talk to the test DB, so a constant placeholder is fine.
os.environ.setdefault("KENBOARD_SECRET_KEY", "screenshot-script-secret-not-prod")
os.environ.setdefault("DEBUG", "true")

import pymysql  # noqa: E402
import pymysql.cursors  # noqa: E402

import dashboard.db as db_module  # noqa: E402
from dashboard.app import create_app  # noqa: E402
from dashboard.config import Config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "doc" / "images"
SERVER_PORT = 5077
# Viewport sized just above the mobile breakpoint (max-width: 768px in
# style.css) so the desktop layout still applies while keeping the
# capture compact and readable when scaled down inside the README.
VIEWPORT = {"width": 800, "height": 900}


def _connect() -> pymysql.connections.Connection:
    """Open a dict-cursor connection to the test database."""
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_TEST_USER,
        password=Config.DB_TEST_PASSWORD,
        database=Config.DB_TEST_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _reset_and_seed() -> tuple[str, str]:
    """Wipe the test DB and insert demo categories / projects / tasks.

    Returns:
        ``(tech_cat_id, kenboard_project_id)`` — the IDs the screenshot
        driver uses to navigate to the kanban view.
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in (
        "api_key_projects",
        "api_keys",
        "tasks",
        "projects",
        "categories",
        "users",
    ):
        cur.execute(f"DELETE FROM {table}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    cur.close()

    queries = db_module.load_queries()

    cats = [
        ("Produit", "var(--pink)"),
        ("Tech", "var(--accent)"),
        ("Ops", "var(--green)"),
    ]
    cat_ids: dict[str, str] = {}
    for i, (name, color) in enumerate(cats):
        cid = str(uuid.uuid4())
        queries.cat_create(conn, id=cid, name=name, color=color, position=i)
        cat_ids[name] = cid

    projects = [
        (cat_ids["Tech"], "Kenboard", "KEN"),
        (cat_ids["Tech"], "API publique", "API"),
        (cat_ids["Produit"], "Refonte UI", "UI"),
        (cat_ids["Ops"], "Monitoring", "OPS"),
    ]
    project_ids: dict[str, str] = {}
    for i, (cat_id, name, acronym) in enumerate(projects):
        pid = str(uuid.uuid4())
        queries.proj_create(
            conn,
            id=pid,
            cat_id=cat_id,
            name=name,
            acronym=acronym,
            status="active",
            position=i,
            default_who="Q",
        )
        project_ids[name] = pid

    kenboard_id = project_ids["Kenboard"]
    tasks = [
        ("Refonte du logo en pixel art", "Q", "todo"),
        ("Migration vers MySQL 8.4", "Q", "todo"),
        ("Auth par cookie session", "Claude", "doing"),
        ("Endpoint /api/v1/keys", "Claude", "doing"),
        ("Documentation OpenAPI", "Q", "review"),
        ("Headers CSP / X-Frame-Options", "Claude", "done"),
        ("Rate limit sur /login", "Claude", "done"),
        ("Refus debug + bind public", "Claude", "done"),
    ]
    for i, (title, who, status) in enumerate(tasks):
        queries.task_create(
            conn,
            project_id=kenboard_id,
            title=title,
            description="",
            status=status,
            who=who,
            due_date=None,
            position=i,
        )

    conn.close()
    return cat_ids["Tech"], kenboard_id


def _start_server() -> str:
    """Start the Flask app in a daemon thread and return its base URL."""
    db_module.get_connection = _connect
    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.config["RATELIMIT_ENABLED"] = False

    threading.Thread(
        target=lambda: app.run(port=SERVER_PORT, use_reloader=False),
        daemon=True,
    ).start()

    base = f"http://localhost:{SERVER_PORT}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base, timeout=1)
            return base
        except urllib.error.URLError:
            time.sleep(0.1)
    raise RuntimeError(f"server never came up on {base}")


def _take_screenshots(base_url: str, cat_id: str) -> None:
    """Drive Playwright through the seeded views and write PNGs."""
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        # Kanban — one category page with tasks across all four columns.
        # This is the screenshot referenced from README.md. full_page=True
        # so the capture grows with the kanban content rather than being
        # cropped to the viewport.
        page.goto(f"{base_url}/cat/{cat_id}.html")
        page.wait_for_selector(".kanban-task")
        page.wait_for_timeout(300)
        out = OUTPUT_DIR / "kanban.png"
        page.screenshot(path=str(out), full_page=True)
        print(f"  wrote {out.relative_to(ROOT)}")

        ctx.close()
        browser.close()


def main() -> int:
    """Reset the test DB, start the server and produce the screenshots."""
    print("[1/3] Reset & seed test DB")
    cat_id, _ = _reset_and_seed()
    print("[2/3] Start kenboard server")
    base = _start_server()
    print(f"      → {base}")
    print("[3/3] Capture screenshots")
    _take_screenshots(base, cat_id)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
