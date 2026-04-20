#!/usr/bin/env python3
"""Delete seeded perf-test categories via the REST API.

Deletes all categories whose name starts with "Cat " (the pattern used
by seed_perf_data.py). CASCADE on the DB side removes associated
projects and tasks. Each DELETE goes through the perf monitoring
middleware so write performance is measured.

Usage:
    python scripts/cleanup_perf_data.py --config .ken3
"""

import argparse
import concurrent.futures
import json
import time
import urllib.request


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


def api(base: str, token: str, method: str, path: str) -> object:
    """Send an API request and return parsed JSON (or None on 204)."""
    req = urllib.request.Request(f"{base}{path}", method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        if r.status == 204:
            return None
        return json.loads(r.read())


def main() -> None:
    """Delete seeded categories via the API."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to .ken config file")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    parser.add_argument(
        "--prefix", default="Cat ", help="Category name prefix to match"
    )
    args = parser.parse_args()

    cfg = _read_ken(args.config)
    base = cfg["base_url"].rstrip("/")
    token = cfg["api_token"]

    cats = api(base, token, "GET", "/api/v1/categories")
    to_delete = [c for c in cats if c["name"].startswith(args.prefix)]
    print(f"{len(to_delete)} categories to delete (out of {len(cats)} total)")

    if not to_delete:
        print("Nothing to delete")
        return

    deleted = 0
    errors: list[str] = []
    start = time.time()

    def delete_cat(cat: dict) -> bool | str:
        try:
            api(base, token, "DELETE", f"/api/v1/categories/{cat['id']}")
            return True
        except Exception as e:
            return str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(delete_cat, c): c for c in to_delete}
        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            if result is True:
                deleted += 1
            else:
                errors.append(result)
            if deleted % 20 == 0 and deleted > 0:
                print(f"  {deleted}/{len(to_delete)} deleted...")

    elapsed = time.time() - start
    print(f"Done: {deleted} categories deleted in {elapsed:.1f}s ({len(errors)} errors)")
    if errors:
        print(f"Errors: {errors[:5]}")


if __name__ == "__main__":
    main()
