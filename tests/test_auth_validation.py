"""Unit tests for registration validator (no DB needed)."""

import pytest

from app.services.auth import AuthError, validate_registration


def test_valid_registration():
    validate_registration("tester1", "foo@example.com", "longenoughpassword")


@pytest.mark.parametrize(
    "u,e,p,msg",
    [
        ("ab", "a@b.co", "longenoughpw", "Username"),       # too short
        ("ok", "not-an-email", "longenoughpw", "Username"),  # shorter than 3
        ("tester1", "bad-email", "longenoughpw", "email"),
        ("tester1", "a@b.co", "short", "8 characters"),
        ("tester1", "a@b.co", "password", "too common"),
        ("has space", "a@b.co", "longenoughpw", "Username"),
    ],
)
def test_invalid_registration(u, e, p, msg):
    with pytest.raises(AuthError) as exc:
        validate_registration(u, e, p)
    assert msg.lower() in str(exc.value).lower()
