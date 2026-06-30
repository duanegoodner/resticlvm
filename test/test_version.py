"""Tests for runtime version exposure and the --version CLI flag."""

from importlib.metadata import version

import pytest

import resticlvm


def test_package_exposes_version():
    """resticlvm.__version__ is a non-empty string."""
    assert isinstance(resticlvm.__version__, str)
    assert resticlvm.__version__


def test_version_matches_installed_metadata():
    """__version__ matches the installed package metadata (single source)."""
    assert resticlvm.__version__ == version("resticlvm")


def test_cli_version_flag_no_root_needed(capsys, monkeypatch):
    """`rlvm --version` prints and exits 0 WITHOUT triggering the root check.

    Regression guard: the root check must run after argument parsing so
    --version/--help work without elevation.
    """
    from resticlvm.orchestration import cli

    def _fail_if_called():
        raise AssertionError("root check ran before --version was handled")

    monkeypatch.setattr(cli, "ensure_running_as_root", _fail_if_called)
    monkeypatch.setattr("sys.argv", ["rlvm", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert resticlvm.__version__ in out
