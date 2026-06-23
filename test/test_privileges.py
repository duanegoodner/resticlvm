"""Tests for the root-privilege check (assert-and-fail, no self-elevation)."""

import pytest

from resticlvm.orchestration import privileges


def test_ensure_running_as_root_exits_when_not_root(monkeypatch, capsys):
    """Non-root invocation exits 1 with a clear message (no sudo re-exec)."""
    monkeypatch.setattr(privileges.os, "geteuid", lambda: 1000)

    with pytest.raises(SystemExit) as exc_info:
        privileges.ensure_running_as_root()

    assert exc_info.value.code == 1
    assert "must be run as root" in capsys.readouterr().err


def test_ensure_running_as_root_noop_when_root(monkeypatch):
    """Running as root is a no-op (returns without raising)."""
    monkeypatch.setattr(privileges.os, "geteuid", lambda: 0)
    assert privileges.ensure_running_as_root() is None
