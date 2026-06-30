"""Ensure the process is running as root.

ResticLVM needs root for LVM snapshots, mounts, and chroot operations. Rather than
silently self-elevating with ``sudo``, it requires the caller to run it as root
(via ``sudo``, a systemd unit, or a root cron job) and fails fast with a clear
message otherwise.

Self-elevation was removed deliberately: re-running under ``sudo`` scrubs the
environment, which would drop credentials (e.g. ``AWS_*`` for B2, ``SSH_AUTH_SOCK``)
loaded by the caller — so "run it as root yourself" is the predictable, composable
contract.
"""

import os
import sys


def ensure_running_as_root():
    """Exit with a clear error unless the current process is running as root.

    Does not attempt to elevate privileges. If the effective UID is not 0, prints
    guidance to stderr and exits with status 1.
    """
    if os.geteuid() != 0:
        print(
            "❌ ResticLVM must be run as root.\n"
            "   Re-run with sudo, or from a root systemd unit / cron job, e.g.:\n"
            "       sudo rlvm backup --config /path/to/config.toml",
            file=sys.stderr,
        )
        sys.exit(1)
