"""Tests for the terminal foreground-process-group guard (issue #57)."""

import os

import pytest

from resticlvm.orchestration import terminal


def test_restores_foreground_pgrp_when_ssh_changed_it(monkeypatch):
    """If a subprocess leaves the terminal's foreground pgrp changed, it's
    restored to what it was before the block."""
    fg = {"pgrp": 100}
    set_calls = []
    monkeypatch.setattr(terminal, "_tty_fds", lambda: iter([7]))
    monkeypatch.setattr(os, "tcgetpgrp", lambda fd: fg["pgrp"])

    def fake_set(fd, pgrp):
        set_calls.append((fd, pgrp))
        fg["pgrp"] = pgrp

    monkeypatch.setattr(os, "tcsetpgrp", fake_set)

    with terminal.preserved_terminal():
        fg["pgrp"] = 999  # simulate ssh grabbing the terminal

    assert set_calls == [(7, 100)]


def test_no_restore_when_pgrp_unchanged(monkeypatch):
    """No tcsetpgrp when nothing disturbed the foreground group."""
    set_calls = []
    monkeypatch.setattr(terminal, "_tty_fds", lambda: iter([7]))
    monkeypatch.setattr(os, "tcgetpgrp", lambda fd: 100)
    monkeypatch.setattr(os, "tcsetpgrp",
                        lambda fd, pgrp: set_calls.append((fd, pgrp)))

    with terminal.preserved_terminal():
        pass

    assert set_calls == []


def test_restores_pgrp_even_on_exception(monkeypatch):
    """The foreground group is restored even if the wrapped block raises."""
    fg = {"pgrp": 100}
    set_calls = []
    monkeypatch.setattr(terminal, "_tty_fds", lambda: iter([7]))
    monkeypatch.setattr(os, "tcgetpgrp", lambda fd: fg["pgrp"])

    def fake_set(fd, pgrp):
        set_calls.append((fd, pgrp))
        fg["pgrp"] = pgrp

    monkeypatch.setattr(os, "tcsetpgrp", fake_set)

    with pytest.raises(RuntimeError):
        with terminal.preserved_terminal():
            fg["pgrp"] = 999
            raise RuntimeError("boom")

    assert set_calls == [(7, 100)]


def test_noop_when_not_a_tty(monkeypatch):
    """No tcsetpgrp attempted when there's no TTY (cron, pipes)."""
    set_calls = []
    monkeypatch.setattr(terminal, "_tty_fds", lambda: iter([]))
    monkeypatch.setattr(os, "tcsetpgrp",
                        lambda fd, pgrp: set_calls.append((fd, pgrp)))

    with terminal.preserved_terminal():
        pass

    assert set_calls == []
