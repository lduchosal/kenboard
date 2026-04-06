"""Vulture whitelist for false positives.

Pytest fixtures are injected by name, not called directly.
Vulture reports them as unused variables in test function signatures.
"""

# Pytest fixtures used for side-effects (seeding test data)
seed_category  # noqa
seed_project  # noqa
seed_task  # noqa
setup_test_db  # noqa
