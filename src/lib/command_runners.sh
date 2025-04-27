#!/bin/bash

run_or_echo() {
    local dry_run="$1"
    shift
    if [ "$dry_run" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}

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
