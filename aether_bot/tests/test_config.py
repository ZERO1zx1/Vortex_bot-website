from __future__ import annotations

import pytest

import config


def test_defaults() -> None:
    settings = config.load_settings({})
    assert settings.guild_id == 0
    assert settings.rate_limit_per_second == 45
    assert settings.log_level == "INFO"
    assert settings.default_prefix == "a!"
    assert settings.db_path == config.BASE_DIR / "data" / "aether.db"


def test_empty_db_path_falls_back_to_default() -> None:
    settings = config.load_settings({"AETHER_DB_PATH": "   "})
    assert settings.db_path == config.BASE_DIR / "data" / "aether.db"


def test_relative_db_path_is_anchored_to_base_dir() -> None:
    settings = config.load_settings({"AETHER_DB_PATH": "data/test.db"})
    assert settings.db_path == config.BASE_DIR / "data" / "test.db"


def test_invalid_guild_id_has_clear_error() -> None:
    with pytest.raises(config.ConfigError, match="GUILD_ID"):
        config.load_settings({"GUILD_ID": "abc"})


def test_zero_rate_limit_is_rejected() -> None:
    with pytest.raises(config.ConfigError, match="RATE_LIMIT_PER_SECOND"):
        config.load_settings({"RATE_LIMIT_PER_SECOND": "0"})


def test_rate_limit_is_clamped_to_discord_safe_max() -> None:
    settings = config.load_settings({"RATE_LIMIT_PER_SECOND": "500"})
    assert settings.rate_limit_per_second == 45


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(config.ConfigError, match="LOG_LEVEL"):
        config.load_settings({"LOG_LEVEL": "verbose"})


def test_prefix_must_be_short() -> None:
    with pytest.raises(config.ConfigError, match="DEFAULT_PREFIX"):
        config.load_settings({"DEFAULT_PREFIX": "toolong"})
    assert config.load_settings({"DEFAULT_PREFIX": "?"}).default_prefix == "?"


def test_token_is_optional_at_import_but_trimmed() -> None:
    assert config.load_settings({"DISCORD_TOKEN": "  token  "}).discord_token == "token"
