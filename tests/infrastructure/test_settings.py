"""
Unit tests for Settings model_config migration (Pydantic v2 SettingsConfigDict).

These tests verify:
- Settings uses model_config (not inner class Config)
- SettingsConfigDict is used for configuration
- Comma-separated trusted_hosts env var is parsed into a list
- Environment detection properties work correctly
"""

import pytest
from pydantic_settings import SettingsConfigDict

from src.infrastructure.config.settings import Settings


class TestSettingsModelConfig:
    """Verify that Settings uses model_config instead of inner class Config."""

    def test_has_model_config(self):
        """Settings must expose model_config attribute (not inner class Config)."""
        assert hasattr(Settings, "model_config")
        assert isinstance(Settings.model_config, dict)

    def test_no_inner_config_class(self):
        """Settings must NOT have an inner Config class."""
        # After migration, there should be no nested 'Config' class attribute
        assert not (hasattr(Settings, "Config") and isinstance(getattr(Settings, "Config"), type))

    def test_model_config_is_settings_config_dict(self):
        """model_config should be a SettingsConfigDict instance (which is a dict subclass)."""
        # SettingsConfigDict returns a plain dict-like mapping; just verify the keys it should set
        config = Settings.model_config
        assert "extra" in config
        assert config["extra"] == "ignore"

    def test_trusted_hosts_comma_parse(self, monkeypatch):
        """TRUSTED_HOSTS env var with comma-separated values is parsed into a list."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.setenv("TRUSTED_HOSTS", "a.com,b.com")
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings()
        assert settings.trusted_hosts == ["a.com", "b.com"]

    def test_trusted_hosts_default(self, monkeypatch):
        """When TRUSTED_HOSTS is not set, trusted_hosts defaults to ['*']."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.delenv("TRUSTED_HOSTS", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings()
        assert settings.trusted_hosts == ["*"]

    def test_trusted_hosts_single_value(self, monkeypatch):
        """Single-value TRUSTED_HOSTS without comma is parsed as a one-element list."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.setenv("TRUSTED_HOSTS", "example.com")
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings()
        assert settings.trusted_hosts == ["example.com"]

    def test_is_development(self, monkeypatch):
        """is_development property returns True when ENVIRONMENT=development."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.setenv("ENVIRONMENT", "development")
        settings = Settings()
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False

    def test_is_production(self, monkeypatch):
        """is_production property returns True when ENVIRONMENT=production."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.setenv("ENVIRONMENT", "production")
        settings = Settings()
        assert settings.is_production is True
        assert settings.is_development is False
        assert settings.is_testing is False

    def test_is_testing(self, monkeypatch):
        """is_testing property returns True when ENVIRONMENT=testing."""
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-settings-test")
        monkeypatch.setenv("ENVIRONMENT", "testing")
        settings = Settings()
        assert settings.is_testing is True
        assert settings.is_development is False
        assert settings.is_production is False
