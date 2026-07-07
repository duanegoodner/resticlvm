#!/bin/bash

# Provides utility functions for running shell commands safely,
# supporting dry-run mode and chroot execution environments.
#
# Usage:
#   Intended to be sourced by other scripts within the ResticLVM tool.
#
# Exit codes:
#   0  Success
#   Non-zero if any command execution fails (unless in dry-run mode).

# Run a command normally or echo it if in dry-run mode.
run_or_echo() {
    local dry_run="$1"
    shift
    if [ "$dry_run" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}

# Run a command inside a chroot environment or echo it if in dry-run mode.
# Preserves SSH_AUTH_SOCK environment variable for remote repos.
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"
run_in_chroot_or_echo() {
    local dry_run="$1"
    local mount_point="$2"
    local cmd="$3"
    shift
    if [ "$dry_run" = true ]; then
        echo -e "${DRY_RUN_PREFIX} chroot $*"
    else
        # Pass SSH_AUTH_SOCK to chroot if it's set (needed for SFTP repos)
        if [ -n "${SSH_AUTH_SOCK:-}" ]; then
            chroot "$mount_point" /bin/bash -c "export SSH_AUTH_SOCK='$SSH_AUTH_SOCK' && $cmd"
        else
            chroot "$mount_point" /bin/bash -c "$cmd"
        fi
    fi
}

# Restore the controlling terminal's foreground process group to this script's
# own group. restic's ssh (for a remote repo) can take over the terminal's
# foreground group to show a prompt and, on failure, not restore it — which
# makes the NEXT restic in the loop believe it is backgrounded and suppress its
# output (issue #72, the within-job residual of #57). Call it after each repo.
# No-op without a controlling terminal on stdout or without python3, so cron and
# piped runs are unaffected. The Python child shares this script's process
# group, so os.getpgrp() is the group we want to be foreground.
restore_terminal_foreground() {
    [ -t 1 ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    python3 - <<'PY' 2>/dev/null || true
import os
import signal
try:
    if os.isatty(1) and os.tcgetpgrp(1) != os.getpgrp():
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        os.tcsetpgrp(1, os.getpgrp())
except Exception:
    pass
PY
}
