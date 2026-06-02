"""Tests for internal backend API auth helpers."""

from backend.security import is_internal_api_authorized, is_public_path


def test_public_paths_do_not_require_internal_key():
    assert is_public_path("/health") is True
    assert is_internal_api_authorized("/health", "", "secret") is True


def test_empty_expected_key_disables_internal_auth():
    assert is_internal_api_authorized("/admin/overview", "", "") is True


def test_internal_key_required_for_private_paths():
    assert is_internal_api_authorized("/admin/overview", "bad", "secret") is False
    assert is_internal_api_authorized("/admin/overview", "secret", "secret") is True
