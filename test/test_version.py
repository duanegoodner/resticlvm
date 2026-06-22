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


@pytest.mark.parametrize("module_name", [
    "resticlvm.orchestration.backup_runner",
    "resticlvm.orchestration.prune_runner",
])
def test_cli_version_flag_no_root_needed(module_name, capsys, monkeypatch):
    """`--version` prints and exits 0 WITHOUT triggering the root check.

    Regression guard: the root check must run after argument parsing so
    --version/--help work without elevation.
    """
    import importlib

    module = importlib.import_module(module_name)

    # If the root check were reached, this would blow up the test.
    def _fail_if_called():
        raise AssertionError("root check ran before --version was handled")

    monkeypatch.setattr(module, "ensure_running_as_root", _fail_if_called)
    monkeypatch.setattr("sys.argv", [module_name, "--version"])

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert resticlvm.__version__ in out
