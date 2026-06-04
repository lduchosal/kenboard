---
id: 57
title: "CI / Warning dans les tests"
status: done
who: "Claude"
due_date: 
classified_at: 2026-05-24T14:29:18
classified_by: "key:038c1b37-7879-43bc-82aa-b83f61f6da8a:user:049c2571-0e1a-4e95-b0ad-3943f0f80a7e"
section: quality
section_title: "Code quality & CI"
---

# #57 — CI / Warning dans les tests

→ Running: pdm run test-quick
.................................................................. [ 32%]
.................................................................. [ 64%]
.................................................................. [ 96%]
.......                                                            [100%]
============================ warnings summary ============================
tests/unit/test_admin_only.py: 15 warnings
tests/unit/test_auth_user.py: 11 warnings
tests/unit/test_csrf.py: 7 warnings
tests/unit/test_logout_invalidates.py: 9 warnings
  /Users/q/Projects/2113.ch/dashboard/.venv/lib/python3.13/site-packages/flask_login/login_manager.py:488: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expires = datetime.utcnow() + duration

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
205 passed, 42 warnings in 5.08s
✓ Unit Tests completed successfully
---

[← retour à quality](index.md) · [voir log](../log/2026-05-24.md)
