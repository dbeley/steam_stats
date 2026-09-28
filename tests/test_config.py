"""Tests for steam_stats.config.SteamConfig."""

import textwrap

import pytest

from steam_stats.config import SteamConfig


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text(
        textwrap.dedent(
            """\
            [steam]
            user_id=76561198000000000
            api_key=file_steam_key
            [itad]
            api_key=file_itad_key
            """
        )
    )
    return path


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    for var in ("STEAM_API_KEY", "STEAM_USER_ID", "STEAM_CONFIG_PATH", "ITAD_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_api_key_from_config_file(config_file):
    config = SteamConfig(config_path=str(config_file))
    assert config.get_api_key() == "file_steam_key"


def test_api_key_env_overrides_file(config_file, monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "env_steam_key")
    config = SteamConfig(config_path=str(config_file))
    assert config.get_api_key() == "env_steam_key"


def test_user_id_from_config_file(config_file):
    config = SteamConfig(config_path=str(config_file))
    assert config.get_user_id() == "76561198000000000"


def test_user_id_override_wins(config_file, monkeypatch):
    monkeypatch.setenv("STEAM_USER_ID", "env_user")
    config = SteamConfig(config_path=str(config_file))
    assert config.get_user_id(override="cli_user") == "cli_user"


def test_user_id_env_overrides_file(config_file, monkeypatch):
    monkeypatch.setenv("STEAM_USER_ID", "env_user")
    config = SteamConfig(config_path=str(config_file))
    assert config.get_user_id() == "env_user"


def test_itad_api_key_from_config_file(config_file):
    config = SteamConfig(config_path=str(config_file))
    assert config.get_itad_api_key() == "file_itad_key"


def test_itad_api_key_env_overrides_file(config_file, monkeypatch):
    monkeypatch.setenv("ITAD_API_KEY", "env_itad_key")
    config = SteamConfig(config_path=str(config_file))
    assert config.get_itad_api_key() == "env_itad_key"


def test_config_path_from_env(tmp_path, monkeypatch):
    path = tmp_path / "alt.ini"
    path.write_text("[steam]\napi_key=alt_key\nuser_id=alt_user\n")
    monkeypatch.setenv("STEAM_CONFIG_PATH", str(path))
    config = SteamConfig()
    assert config.get_api_key() == "alt_key"


def test_explicit_path_beats_env(config_file, tmp_path, monkeypatch):
    other = tmp_path / "other.ini"
    other.write_text("[steam]\napi_key=other_key\nuser_id=other_user\n")
    monkeypatch.setenv("STEAM_CONFIG_PATH", str(other))
    config = SteamConfig(config_path=str(config_file))
    assert config.get_api_key() == "file_steam_key"


def test_missing_config_file_raises():
    config = SteamConfig(config_path="/nonexistent/does/not/exist.ini")
    with pytest.raises(FileNotFoundError):
        config.get_api_key()


def test_missing_api_key_raises_value_error(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[steam]\nuser_id=some_user\n")
    config = SteamConfig(config_path=str(path))
    with pytest.raises(ValueError, match="No Steam API key"):
        config.get_api_key()


def test_missing_user_id_raises_value_error(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[steam]\napi_key=some_key\n")
    config = SteamConfig(config_path=str(path))
    with pytest.raises(ValueError, match="No Steam user ID"):
        config.get_user_id()


def test_missing_itad_section_raises_value_error(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[steam]\napi_key=k\nuser_id=u\n")
    config = SteamConfig(config_path=str(path))
    with pytest.raises(ValueError, match="No ITAD API key"):
        config.get_itad_api_key()
