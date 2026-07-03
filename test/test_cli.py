"""Tests for CLI config resolution and help output."""

import pytest

from resticlvm.orchestration.cli import (
    CONFIG_ENV_VAR,
    DEFAULT_CONFIG_PATH,
    resolve_config,
)


# --- resolve_config precedence and error handling ---


def test_explicit_config_returned(tmp_path):
    f = tmp_path / "explicit.toml"
    f.write_text("[prune_policy]\n")
    assert resolve_config(str(f)) == f


def test_explicit_config_missing_exits(tmp_path):
    missing = tmp_path / "nope.toml"
    with pytest.raises(SystemExit, match=str(missing)):
        resolve_config(str(missing))


def test_env_var_used_when_no_flag(tmp_path, monkeypatch):
    f = tmp_path / "env.toml"
    f.write_text("[prune_policy]\n")
    monkeypatch.setenv(CONFIG_ENV_VAR, str(f))
    assert resolve_config(None) == f


def test_env_var_missing_file_exits(tmp_path, monkeypatch):
    missing = tmp_path / "nope.toml"
    monkeypatch.setenv(CONFIG_ENV_VAR, str(missing))
    with pytest.raises(SystemExit, match=CONFIG_ENV_VAR):
        resolve_config(None)


def test_default_path_used_when_exists(tmp_path, monkeypatch):
    f = tmp_path / "backup.toml"
    f.write_text("[prune_policy]\n")
    monkeypatch.setattr(
        "resticlvm.orchestration.cli.DEFAULT_CONFIG_PATH", f
    )
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    assert resolve_config(None) == f


def test_nothing_found_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "resticlvm.orchestration.cli.DEFAULT_CONFIG_PATH",
        tmp_path / "nonexistent.toml",
    )
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)
    with pytest.raises(SystemExit, match="no config file found"):
        resolve_config(None)


def test_explicit_wins_over_env_and_default(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit.toml"
    env_file = tmp_path / "env.toml"
    default = tmp_path / "backup.toml"
    for f in (explicit, env_file, default):
        f.write_text("[prune_policy]\n")

    monkeypatch.setenv(CONFIG_ENV_VAR, str(env_file))
    monkeypatch.setattr(
        "resticlvm.orchestration.cli.DEFAULT_CONFIG_PATH", default
    )
    assert resolve_config(str(explicit)) == explicit


def test_env_wins_over_default(tmp_path, monkeypatch):
    env_file = tmp_path / "env.toml"
    default = tmp_path / "backup.toml"
    for f in (env_file, default):
        f.write_text("[prune_policy]\n")

    monkeypatch.setenv(CONFIG_ENV_VAR, str(env_file))
    monkeypatch.setattr(
        "resticlvm.orchestration.cli.DEFAULT_CONFIG_PATH", default
    )
    assert resolve_config(None) == env_file


# --- CLI help output ---


def test_help_shows_default_path_and_env_var(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["rlvm", "backup", "--help"])

    from resticlvm.orchestration.cli import main

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert str(DEFAULT_CONFIG_PATH) in out
    assert CONFIG_ENV_VAR in out
