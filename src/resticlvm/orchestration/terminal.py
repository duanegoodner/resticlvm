"""Terminal-state guarding around subprocesses that may spawn ssh.

restic's SFTP backend runs ``ssh``, which takes over the controlling terminal's
**foreground process group** to read a host-key/password prompt and, on failure,
does not restore it — leaving the terminal's foreground group pointing at ssh's
(now dead) process group. restic, like most tools with terminal progress output,
suppresses *all* of its terminal output when it detects it is not the foreground
process. So after one remote failure every subsequent ``restic`` prints nothing,
even though the backups still succeed (issue #57). (Plain ``print``/``echo``
still show because they don't do that foreground check.)

:func:`preserved_terminal` snapshots the terminal's foreground process group
before a subprocess and restores it afterward, the way a job-control shell does.
"""

import os
import signal
import sys
from contextlib import contextmanager


def _tty_fds():
    """Yield the distinct TTY file descriptors among stdin/stdout/stderr."""
    seen = set()
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            fd = stream.fileno()
        except (AttributeError, OSError, ValueError):
            continue
        if fd in seen:
            continue
        seen.add(fd)
        try:
            if os.isatty(fd):
                yield fd
        except OSError:
            continue


def _set_foreground_pgrp(fd, pgrp):
    """Set fd's terminal foreground process group to ``pgrp``.

    Calling this from a process that is not currently in the foreground group
    would itself raise ``SIGTTOU`` (whose default action stops us), so ignore
    ``SIGTTOU`` for the duration — the standard job-control idiom.
    """
    try:
        old = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    except (ValueError, OSError):
        old = None  # not the main thread; best-effort without masking SIGTTOU
    try:
        os.tcsetpgrp(fd, pgrp)
    finally:
        if old is not None:
            try:
                signal.signal(signal.SIGTTOU, old)
            except (ValueError, OSError):
                pass


@contextmanager
def preserved_terminal():
    """Restore the terminal's foreground process group after the wrapped block.

    Wrap any ``subprocess.run`` that may spawn ssh (backup, copy, prune) so a
    remote failure can't leave the terminal's foreground group pointing at a dead
    process and silence later output (issue #57). No-op when not attached to a
    TTY (cron, pipes).
    """
    saved = {}
    for fd in _tty_fds():
        try:
            saved[fd] = os.tcgetpgrp(fd)
        except OSError:
            continue
    try:
        yield
    finally:
        for fd, pgrp in saved.items():
            try:
                if os.tcgetpgrp(fd) != pgrp:
                    _set_foreground_pgrp(fd, pgrp)
            except OSError:
                pass
