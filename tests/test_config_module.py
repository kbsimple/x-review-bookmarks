"""Tests for src.config module."""

import pytest


def test_config_module_importable():
    """Test that src.config is importable as a module."""
    from src import config
    assert config is not None


def test_settings_class_exported():
    """Test that Settings class is exported from src.config."""
    from src.config import Settings
    assert Settings is not None
    assert Settings.__name__ == "Settings"


def test_settings_class_in_all():
    """Test that Settings is in __all__."""
    from src.config import __all__
    assert "Settings" in __all__