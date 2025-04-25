#!/bin/bash

# shellcheck disable=SC1091
source "$(dirname "$0")/usage_commands.sh"

root_check() {
    if [ "$EUID" -ne 0 ]; then
        echo "❌ Please run as root or with sudo."
        exit 1
    fi
}

check_if_path_exists() {
    local path="$1"
    if ! [ -e "$path" ]; then
        echo "❌ Path $path does not exist."
        exit 1
    fi
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

remount_as_read_only() {
    local dry_run="$1"
    local backup_source="$2"

    if mountpoint -q "$backup_source"; then
        local dev
        dev=$(findmnt -n -o SOURCE --target "$backup_source")
        echo "🔒 Remounting $dev as read-only..."
        run_or_echo "$dry_run" "mount -o remount,ro $dev"
    else
        echo "⚠️ $backup_source is not a mount point. Cannot use remount-as-ro option."
        exit 1
    fi
}

remount_as_read_write() {
    local dry_run="$1"
    local backup_source="$2"

    if mountpoint -q "$backup_source"; then
        local dev
        dev=$(findmnt -n -o SOURCE --target "$backup_source")
        echo "🔓 Remounting $dev as read-write..."
        run_or_echo "$dry_run" "mount -o remount,rw $dev"
    else
        echo "⚠️ $backup_source is not a mount point. Cannot remount as read-write."
        exit 1
    fi
}

parse_arguments() {
    local usage_function="$1"
    shift
    local allowed_flags="$1"
    shift

    while [[ $# -gt 0 ]]; do
        case "$1" in
        -g | --vg-name)
            if [[ "$allowed_flags" == *"vg-name"* ]]; then
                VG_NAME="$2"
                shift 2
            else
                echo "❌ Unexpected option: $1"
                "$usage_function"
            fi
            ;;
        -l | --lv-name)
            if [[ "$allowed_flags" == *"lv-name"* ]]; then
                LV_NAME="$2"
                shift 2
            else
                echo "❌ Unexpected option: $1"
                "$usage_function"
            fi
            ;;
        -z | --snap-size)
            if [[ "$allowed_flags" == *"snap-size"* ]]; then
                SNAP_SIZE="$2"
                shift 2
            else
                echo "❌ Unexpected option: $1"
                "$usage_function"
            fi
            ;;
        -r | --restic-repo)
            RESTIC_REPO="$2"
            shift 2
            ;;
        -p | --password-file)
            RESTIC_PASSWORD_FILE="$2"
            shift 2
            ;;
        -s | --backup-source)
            BACKUP_SOURCE="$2"
            shift 2
            ;;
        -e | --exclude-paths)
            EXCLUDE_PATHS="$2"
            shift 2
            ;;
        -m | --remount-as-ro)
            if [[ "$allowed_flags" == *"remount-as-ro"* ]]; then
                REMOUNT_AS_RO="$2"
                shift 2
            else
                echo "❌ Unexpected option: $1"
                "$usage_function"
            fi
            ;;
        -n | --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h | --help)
            "$usage_function"
            ;;
        *)
            echo "❌ Unknown option: $1"
            "$usage_function"
            ;;
        esac
    done
}

validate_args() {
    local usage_function="$1"
    shift
    local required_vars=("$@")
    local missing=0

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            echo "❌ Error: --${var,,} is required"
            missing=1
        fi
    done

    if [[ "$missing" -eq 1 ]]; then
        "$usage_function"
    fi
}

display_config() {
    local title="$1"
    shift
    local vars=("$@")

    echo ""
    echo "🧾 $title"
    for var in "${vars[@]}"; do
        printf "  %-22s %s\n" "$(prettify_var_name "$var"):" "${!var}"
    done
}

prettify_var_name() {
    local var_name="$1"
    var_name="${var_name//_/-}"                                 # Replace underscores with dashes
    var_name="$(echo "$var_name" | tr '[:lower:]' '[:upper:]')" # Capitalize (optional)
    echo "$var_name"
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

create_snapshot() {
    echo "📸 Creating LVM snapshot..."
    local dry_run=$1
    local snap_size=$2
    local snap_name=$3
    local vg_name=$4
    local lv_name=$5

    run_or_echo "$dry_run" "lvcreate --size $snap_size --snapshot --name $snap_name /dev/$vg_name/$lv_name"
}

mount_snapshot() {
    local dry_run=$1
    local snapshot_mount_point=$2
    local vg_name=$3
    local snap_name=$4

    echo "📂 Mounting snapshot..."
    run_or_echo "$dry_run" "mkdir -p $snapshot_mount_point"
    run_or_echo "$dry_run" "mount /dev/$vg_name/$snap_name $snapshot_mount_point"
}

clean_up_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local vg_name="$3"
    local snap_name="$4"

    echo "🧹 Cleaning up..."
    run_or_echo "$dry_run" "umount \"$snapshot_mount_point\""
    run_or_echo "$dry_run" "lvremove -y \"/dev/$vg_name/$snap_name\""
    run_or_echo "$dry_run" "rmdir \"$snapshot_mount_point\""
}

populate_exclude_paths() {
    local -n exclude_args=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        exclude_args+=("--exclude=$path")
    done
}

populate_restic_tags() {
    local -n restic_tags=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        tag_path="${path#/}" # Remove leading slash for tag
        restic_tags+=("--tag=excl:/$tag_path")
    done
}

bind_repo_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local restic_repo="$3"
    local chroot_repo_full="$4"

    echo "🪝 Binding Restic repo into chroot..."
    echo "  Snapshot mount point: $snapshot_mount_point"
    echo "  Restic repo: $restic_repo"
    echo "  Chroot repo path: $chroot_repo_full"
    run_or_echo "$dry_run" "mkdir -p $snapshot_mount_point/$chroot_repo_full"
    run_or_echo "$dry_run" "mount --bind $restic_repo $snapshot_mount_point/$chroot_repo_full"
}

bind_chroot_essentials_to_mounted_snapshot() {
    local dry_run="$1"
    local snapshot_mount_point="$2"

    echo "🔧 Preparing chroot environment..."
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "mount --bind $path $snapshot_mount_point$path"
    done
}

unmount_chroot_bindings() {
    local dry_run="$1"
    local snapshot_mount_point="$2"
    local chroot_repo_full="$3"

    run_or_echo "$dry_run" "umount \"$snapshot_mount_point/$chroot_repo_full\""
    for path in /dev /proc /sys; do
        run_or_echo "$dry_run" "umount \"$snapshot_mount_point$path\""
    done
}
