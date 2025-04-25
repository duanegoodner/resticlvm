#!/bin/bash

root_check() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Please run as root or with sudo."
        exit 1
    fi
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

check_device_path() {
    local device_path="$1"
    if ! [ -e "$device_path" ]; then
        echo "❌ Logical volume $device_path does not exist."
        exit 1
    fi
}

check_mount_point() {
    local device_path="$1"
    local mount_point
    mount_point=$(findmnt -n -o TARGET --source "$device_path")

    if [ -n "$mount_point" ]; then
        echo "$mount_point" # Output only the mount point
    else
        echo "❌  LV $device_path is not currently mounted but must be mounted for backup."
        echo "   → Please mount it before running this script."
        echo "   → Example: mount $device_path /mnt."
        echo "   → Exiting."
        exit 1
    fi
}

confirm_source_in_lv() {
    local real_backup="$1"
    local real_mount="$2"
    local backup_source="$3"

    if [[ "$real_backup" != "$real_mount"* ]]; then
        echo "❌ Error: Backup source '$backup_source' is not within logical volume mount point '$real_mount'"
        echo "   → Resolved path: $real_backup"
        exit 1
    elif [[ ! -e "$real_backup" ]]; then
        echo "❌ Error: Backup source path '$real_backup' does not exist."
        exit 1
    else
        echo "✅ Backup source $backup_source resolves to $real_backup and is valid."
    fi
}

confirm_not_yet_exist_snapshot_mount_point() {
    local snapshot_mount_point="$1"

    if [[ -e "$snapshot_mount_point" ]]; then
        echo "❌ Mount point $snapshot_mount_point already exists. Aborting."
        exit 1
    fi
}

parse_arguments() {
    local usage_function="$1"
    shift

    while [[ $# -gt 0 ]]; do
        case "$1" in
        --vg-name | -g)
            VG_NAME="$2"
            shift 2
            ;;
        --lv-name | -l)
            LV_NAME="$2"
            shift 2
            ;;
        --snap-size | -z)
            SNAP_SIZE="$2"
            shift 2
            ;;
        --restic-repo | -r)
            RESTIC_REPO="$2"
            shift 2
            ;;
        --password-file | -p)
            RESTIC_PASSWORD_FILE="$2"
            shift 2
            ;;
        --backup-source | -s)
            BACKUP_SOURCE="$2"
            shift 2
            ;;
        --exclude-paths | -e)
            EXCLUDE_PATHS="$2"
            shift 2
            ;;
        --dry-run | -n)
            DRY_RUN=true
            shift
            ;;
        -h | --help) "$usage_function" ;;
        *)
            echo "❌ Unknown option: $1"
            "$usage_function"
            ;;
        esac
    done
}

validate_args() {
    local usage_function="$1"
    local missing=0

    if [[ -z "$VG_NAME" ]]; then
        echo "❌ Error: --vg-name is required"
        missing=1
    fi
    if [[ -z "$LV_NAME" ]]; then
        echo "❌ Error: --lv-name is required"
        missing=1
    fi
    if [[ -z "$SNAP_SIZE" ]]; then
        echo "❌ Error: --snap-size is required"
        missing=1
    fi
    if [[ -z "$RESTIC_REPO" ]]; then
        echo "❌ Error: --restic-repo is required"
        missing=1
    fi
    if [[ -z "$RESTIC_PASSWORD_FILE" ]]; then
        echo "❌ Error: --password-file is required"
        missing=1
    fi

    if [[ "$missing" -eq 1 ]]; then
        "$usage_function"
    fi
}

display_snapshot_backup_config() {
    echo ""
    echo "🧾 LVM Snapshot Backup Configuration:"
    echo "  Volume group:          $VG_NAME"
    echo "  Logical volume:        $LV_NAME"
    echo "  Snapshot size:         $SNAP_SIZE"
    echo "  Snapshot name:         $SNAP_NAME"
    echo "  Mount point:           $SNAPSHOT_MOUNT_POINT"
    echo "  Restic repo:           $RESTIC_REPO"
    echo "  Password file:         $RESTIC_PASSWORD_FILE"
    echo "  Exclude paths:         $EXCLUDE_PATHS"
    echo "  Backup source:         $BACKUP_SOURCE"
    echo "  Dry run:               $DRY_RUN"
}

display_dry_run_message() {
    local dry_run="$1"
    if [ "$dry_run" = true ]; then
        echo -e "\n🟡 The following describes what *would* happen if this were a real backup run.\n"
    fi
}

run_or_echo() {
    local dry_run="$1"
    shift
    if [ "$dry_run" = true ]; then
        echo -e "${DRY_RUN_PREFIX} $*"
    else
        eval "$@"
    fi
}
