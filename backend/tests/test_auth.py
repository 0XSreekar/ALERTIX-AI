"""Tests for auth dependencies."""

import pytest
from unittest.mock import patch
from app.auth.deps import _decode_supabase_jwt, _extract_bearer


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
