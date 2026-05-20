"""Tests for auth dependencies."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.auth.deps import (
    _decode_jwt,
    _extract_bearer,
    _from_payload,
    _jwt_secret,
)


class TestExtractBearer:
    def test_valid_bearer(self):
        assert _extract_bearer("Bearer abc123") == "abc123"

    def test_no_bearer_prefix(self):
        assert _extract_bearer("Token abc123") is None

    def test_empty_string(self):
        assert _extract_bearer("") is None

    def test_none(self):
        assert _extract_bearer(None) is None

    def test_bearer_with_extra_spaces(self):
        assert _extract_bearer("Bearer   token_with_spaces  ") == "token_with_spaces"

    def test_case_insensitive_bearer(self):
        assert _extract_bearer("bearer abc") == "abc"
        assert _extract_bearer("BEARER abc") == "abc"


def _make_token(claims: dict | None = None) -> str:
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "role": "citizen",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        **(claims or {}),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


class TestDecodeJWT:
    def test_valid_token(self):
        token = _make_token()
        payload = _decode_jwt(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "citizen"

    def test_expired_token(self):
        token = jwt.encode(
            {
                "sub": "x",
                "exp": datetime.now(UTC) - timedelta(hours=1),
            },
            _jwt_secret(),
            algorithm="HS256",
        )
        with pytest.raises(HTTPException) as exc:
            _decode_jwt(token)
        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()

    def test_invalid_signature(self):
        bad_token = jwt.encode({"sub": "x"}, "wrong-secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc:
            _decode_jwt(bad_token)
        assert exc.value.status_code == 401


class TestFromPayload:
    def test_extracts_fields(self):
        user = _from_payload({"sub": "u1", "email": "e@x.com", "role": "official"})
        assert user.user_id == "u1"
        assert user.email == "e@x.com"
        assert user.role == "official"

    def test_defaults_role_to_citizen(self):
        user = _from_payload({"sub": "u1"})
        assert user.role == "citizen"

    def test_missing_email_is_none(self):
        user = _from_payload({"sub": "u1"})
        assert user.email is None
