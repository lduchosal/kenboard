"""Vulture whitelist for false positives.

Pytest fixtures are injected by name, not called directly.
Vulture reports them as unused variables in test function signatures.
"""

# Pytest fixtures used for side-effects (seeding test data)
seed_category  # noqa
seed_project  # noqa
seed_task  # noqa
setup_test_db  # noqa
clean_db  # noqa
live_server  # noqa
_setup_test_db  # noqa
admin_user  # noqa
normal_user  # noqa
seeded_admin  # noqa
seeded_normal  # noqa
auth_server  # noqa
patch_db_connection  # noqa
disable_auth_enforcement  # noqa
logged_in_user  # noqa
seed_two_categories  # noqa
user_with_email  # noqa
