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
DRY_RUN_PREFIX="\033[1;33m[DRY RUN]\033[0m"
run_in_chroot_or_echo() {
    local dry_run="$1"
    local mount_point="$2"
    local cmd="$3"
    shift
    if [ "$dry_run" = true ]; then
        echo -e "${DRY_RUN_PREFIX} chroot $*"
    else
        chroot "$mount_point" /bin/bash -c "$cmd"
    fi
}
