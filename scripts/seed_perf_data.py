#!/usr/bin/env python3
"""Seed a kenboard with large volumes via the REST API for performance testing.

Every POST goes through the perf monitoring middleware, so both write
performance and threshold violations are observed and reported.

Usage:
    python scripts/seed_perf_data.py --config .ken3 [--cats 120] [--projects 25] [--tasks 110]

Defaults: 120 categories, 25 projects/category, 110 tasks/project
(= 330 000 tasks total).
"""

import argparse
import concurrent.futures
import json
import random
import time
import urllib.request

STATUSES = ["todo", "doing", "review", "done"]
STATUS_WEIGHTS = [15, 10, 5, 70]
WHOS = ["Claude", "Q", "Alice", "Bob", "Charlie"]
COLORS = [
    "var(--accent)",
    "var(--green)",
    "var(--purple)",
    "var(--cyan)",
    "var(--orange)",
    "var(--red)",
    "var(--todo)",
    "var(--yellow)",
]
DESC = (
    "## Contexte\n\n"
    "Tache de test generee pour valider les performances du kenboard avec un "
    "volume important de donnees.\n\n"
    "## Etapes\n\n"
    "1. Premiere etape de la tache\n"
    "2. Deuxieme etape avec plus de detail\n"
    "3. Troisieme etape finale\n\n"
    "## Notes\n\n"
    "- Point important a retenir\n"
    "- Autre point technique\n"
    "- Reference vers une documentation"
)


def _read_ken(path: str) -> dict[str, str]:
    """Parse a .ken config file."""
    data: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip()
    return data


def api(base: str, token: str, method: str, path: str, body: dict | None = None):
    """Send an API request and return parsed JSON."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{base}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        if r.status == 204:
            return None
        return json.loads(r.read())


def main() -> None:
    """Seed the board via API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to .ken config file")
    parser.add_argument("--cats", type=int, default=120, help="Number of categories")
    parser.add_argument("--projects", type=int, default=25, help="Projects per category")
    parser.add_argument("--tasks", type=int, default=110, help="Tasks per project")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent workers")
    args = parser.parse_args()

    cfg = _read_ken(args.config)
    base = cfg["base_url"].rstrip("/")
    token = cfg["api_token"]

    total_projects = args.cats * args.projects
    total_tasks = total_projects * args.tasks
    print(
        f"Plan: {args.cats} categories, {total_projects} projects, "
        f"{total_tasks} tasks ({args.workers} workers)"
    )

    # --- Categories (sequential — fast enough) ---
    print(f"\nCreating {args.cats} categories...")
    t0 = time.time()
    cat_ids = []
    for i in range(args.cats):
        c = api(base, token, "POST", "/api/v1/categories", {
            "name": f"Cat {i + 1:03d}",
            "color": COLORS[i % len(COLORS)],
        })
        cat_ids.append(c["id"])
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{args.cats} categories...")
    print(f"  {len(cat_ids)} categories in {time.time() - t0:.1f}s")

    # --- Projects (concurrent) ---
    print(f"\nCreating {total_projects} projects...")
    t0 = time.time()
    project_jobs = []
    for ci, cid in enumerate(cat_ids):
        for j in range(args.projects):
            acr = f"P{ci + 1:02d}{j + 1:02d}"[:4].upper()
            project_jobs.append({
                "cat": cid,
                "name": f"Project {ci + 1:03d}-{j + 1:02d}",
                "acronym": acr,
            })

    proj_ids = []  # (project_id, cat_id)
    proj_errors = 0

    def create_project(job):
        try:
            p = api(base, token, "POST", "/api/v1/projects", job)
            return p["id"], job["cat"]
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(create_project, j) for j in project_jobs]
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            result = f.result()
            if result:
                proj_ids.append(result)
            else:
                proj_errors += 1
            if (i + 1) % 500 == 0:
                print(f"  {i + 1}/{total_projects} projects...")
    print(
        f"  {len(proj_ids)} projects in {time.time() - t0:.1f}s "
        f"({proj_errors} errors)"
    )

    # --- Tasks (concurrent) ---
    print(f"\nCreating {total_tasks} tasks...")
    t0 = time.time()
    task_count = 0
    task_errors = 0

    def create_task(pid, k):
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        who = random.choice(WHOS)
        try:
            api(base, token, "POST", "/api/v1/tasks", {
                "project_id": pid,
                "title": f"Task {k + 1:03d}",
                "description": DESC,
                "status": status,
                "who": who,
            })
            return True
        except Exception:
            return False

    # Process in batches per project to avoid overwhelming the thread pool
    for batch_start in range(0, len(proj_ids), 50):
        batch_projs = proj_ids[batch_start:batch_start + 50]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = []
            for pid, _cid in batch_projs:
                for k in range(args.tasks):
                    futures.append(pool.submit(create_task, pid, k))
            for f in concurrent.futures.as_completed(futures):
                if f.result():
                    task_count += 1
                else:
                    task_errors += 1
        done = batch_start + len(batch_projs)
        print(
            f"  {done}/{len(proj_ids)} projects seeded "
            f"({task_count} tasks, {task_errors} errors, "
            f"{time.time() - t0:.0f}s)"
        )

    elapsed = time.time() - t0
    print(
        f"\nDone: {len(cat_ids)} categories, {len(proj_ids)} projects, "
        f"{task_count} tasks in {elapsed:.0f}s ({task_errors} errors)"
    )


if __name__ == "__main__":
    main()
