"""Shared password strength policy (#198)."""

from __future__ import annotations

import pytest

from dashboard.password_strength import (
    MIN_LENGTH,
    MIN_SCORE,
    validate_password_strength,
)


class TestMinLength:
    """Passwords shorter than ``MIN_LENGTH`` are rejected before zxcvbn runs."""

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="at least"):
            validate_password_strength("")

    def test_too_short_rejected(self):
        with pytest.raises(ValueError, match=f"at least {MIN_LENGTH}"):
            validate_password_strength("1234567")

    def test_min_length_alone_not_enough(self):
        """Meeting ``MIN_LENGTH`` is necessary but not sufficient.

        zxcvbn also has to say the password is strong enough. This is the whole reason
        for using zxcvbn on top of a length check — an 8-char password made of mixed
        symbols alone is often still score ≤ 2.
        """
        # 8-char symbol-heavy string that passes the length gate but is
        # too short to reach score 3.
        with pytest.raises(ValueError, match="weak|strength"):
            validate_password_strength("X7k!mQ9$")


class TestZxcvbn:
    """Zxcvbn rejects common, dictionary, and pattern-based passwords."""

    @pytest.mark.parametrize(
        "weak",
        [
            "password",
            "password1",
            "Password123",
            "12345678",
            "qwerty12",
            "abcdefgh",
            "letmein!",
            "adminadmin",
        ],
    )
    def test_common_weak_passwords_rejected(self, weak):
        with pytest.raises(ValueError, match="weak|strength"):
            validate_password_strength(weak)

    def test_error_message_includes_score(self):
        """Message exposes the score so users know how far they are."""
        with pytest.raises(ValueError) as exc:
            validate_password_strength("password")
        msg = str(exc.value)
        assert f"need {MIN_SCORE}/4" in msg

    def test_error_message_includes_zxcvbn_feedback(self):
        """Zxcvbn's guidance ("This is a top-10 common password.") flows through."""
        with pytest.raises(ValueError) as exc:
            validate_password_strength("password")
        msg = str(exc.value)
        # zxcvbn always flags `password` as a common password warning
        assert "common password" in msg.lower() or "top" in msg.lower()

    @pytest.mark.parametrize(
        "strong",
        [
            "X7k!mQvL2pYwR3tN",
            "Np4rW!x8qZmB2kLt",
            "correct horse battery staple",
            "Tr0ub4dor&3-Captain!",
        ],
    )
    def test_strong_passwords_accepted(self, strong):
        # Does not raise
        validate_password_strength(strong)
