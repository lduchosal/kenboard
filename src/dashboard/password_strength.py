"""Password strength policy (#198).

Single source of truth for "is this password strong enough?" so the
Pydantic models, the admin reset endpoint, and the ``kenboard
set-password`` CLI all enforce the exact same bar.

Policy:

- Minimum length: 8 characters (already enforced by the Pydantic
  ``min_length=8``; included here as defence in depth for direct
  callers that bypass the models).
- ``zxcvbn`` score ≥ 3 on the 0-4 scale ("safely unguessable: moderate
  protection from offline slow-hash scenario"). Score 3 is the NIST
  SP 800-63B-flavoured minimum recommended by the zxcvbn authors for
  user-facing accounts.

``zxcvbn`` evaluates entropy taking into account common passwords,
keyboard patterns, repeated characters, dictionary words, and l33t
substitutions, so a long password made entirely of "password1234"
variants fails while a modest 10-char random string passes.

This module raises :class:`ValueError` with a human-readable message
on failure — callers catch it and translate to the appropriate layer
(HTTP 422 via Pydantic, ``click.echo(..., err=True)`` in the CLI).
"""

from __future__ import annotations

from zxcvbn import zxcvbn

MIN_LENGTH = 8
MIN_SCORE = 3


def validate_password_strength(password: str) -> None:
    """Raise ``ValueError`` if ``password`` does not meet the policy.

    Args:
        password: The candidate password in plain text.

    Raises:
        ValueError: when the password is too short or too weak. The
            message includes actionable guidance from zxcvbn
            (``warning`` + ``suggestions``) so the end-user knows how
            to fix it.
    """
    if len(password) < MIN_LENGTH:
        raise ValueError(f"Password must be at least {MIN_LENGTH} characters long")

    result = zxcvbn(password)
    score = result.get("score", 0)
    if score < MIN_SCORE:
        feedback = result.get("feedback", {}) or {}
        warning = feedback.get("warning") or ""
        suggestions = feedback.get("suggestions") or []
        hint_parts: list[str] = []
        if warning:
            hint_parts.append(warning)
        if suggestions:
            hint_parts.append(" ".join(suggestions))
        hint = f" {' '.join(hint_parts)}" if hint_parts else ""
        raise ValueError(
            f"Password is too weak (strength {score}/4, need {MIN_SCORE}/4).{hint}"
        )
