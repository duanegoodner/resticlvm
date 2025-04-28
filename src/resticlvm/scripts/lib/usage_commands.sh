#!/bin/bash

usage_path() {
    echo "Usage:"
    echo "$0 -r REPO -p PASSFILE -s SRC [-e EXCLUDES] [-m] [-n]"
    echo ""
    echo "Options:"
    echo "  -r, --restic-repo      Restic repository path"
    echo "  -p, --password-file    Path to password file"
    echo "  -s, --backup-source    Path to back up"
    echo "  -e, --exclude-paths    Space-separated paths to exclude"
    echo "  -m, --remount-as-ro   Remount source as read-only (default: false)"
    echo "  -n, --dry-run          Dry run mode (preview only)"
    echo "  -h, --help             Display this message and exit"
    exit 1
}

usage_lv_root() {
    echo "Usage:"
    echo "$0 -g VG -l LV -z SIZE -r REPO -p PASSFILE [-e EXCLUDES] [-s SRC]  [-n]"
    echo ""
    echo "Options:"
    echo "  -g, --vg-name          Volume group name"
    echo "  -l, --lv-name          Logical volume name"
    echo "  -z, --snap-size        Snapshot size (e.g., 1G)"
    echo "  -r, --restic-repo      Restic repository path"
    echo "  -p, --password-file    Path to password file"
    echo "  -e, --exclude-paths    Space-separated paths to exclude (default: /dev /media /mnt /proc /run /sys /tmp /var/tmp /var/lib/libvirt/images)"
    echo "  -s, --backup-source    Path inside snapshot to back up (default: /)"
    echo "  -n, --dry-run          Dry run mode (preview only)"
    echo "  -h, --help             Display this message and exit"
    exit 1
}

usage_lv_nonroot() {
    echo "Usage:"
    echo "$0 -g VG -l LV -z SIZE -r REPO -p PASSFILE -e EXCLUDES -s SRC  [-n]"
    echo ""
    echo "Options:"
    echo "  -g, --vg-name          Volume group name"
    echo "  -l, --lv-name          Logical volume name"
    echo "  -z, --snap-size        Snapshot size (e.g., 1G)"
    echo "  -r, --restic-repo      Restic repository path"
    echo "  -p, --password-file    Path to password file"
    echo "  -e, --exclude-paths    Space-separated paths to exclude"
    echo "  -s, --backup-source    Path inside snapshot to back up"
    echo "  -n, --dry-run          Dry run mode (preview only)"
    echo "  -h, --help             Display this message and exit"
    exit 1
}
