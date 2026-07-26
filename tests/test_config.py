"""Unit tests for settings loading and startup validation."""

import pytest

from mcp_server.config import Settings, load_settings_or_exit


class TestLoadSettingsOrExit:
    def test_exits_with_readable_message_when_key_missing(
        self, monkeypatch, tmp_path
    ) -> None:
        # Run from an empty directory so no .env is picked up
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DIP_API_KEY", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            load_settings_or_exit()

        message = str(exc_info.value)
        assert "DIP_API_KEY" in message
        assert ".env.example" in message

    def test_returns_settings_when_complete(self, monkeypatch) -> None:
        monkeypatch.setenv("DIP_API_KEY", "test-key")
        settings = load_settings_or_exit()
        assert isinstance(settings, Settings)
        assert settings.dip_api_key == "test-key"

    def test_unknown_env_keys_are_ignored(self, monkeypatch) -> None:
        monkeypatch.setenv("DIP_API_KEY", "test-key")
        monkeypatch.setenv("DIP_PAGE_SIZE", "50")  # removed setting
        settings = Settings()
        assert settings.dip_api_key == "test-key"
