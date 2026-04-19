"""Tests for src package structure."""

import pytest


def test_src_package_importable():
    """Test that src is importable as a package."""
    # This test should pass once src/__init__.py exists
    import src
    assert src is not None


def test_src_has_docstring():
    """Test that src package has a docstring."""
    import src
    assert src.__doc__ is not None
    assert "X Bookmarked Posts" in src.__doc__ or "bookmarked" in src.__doc__.lower()