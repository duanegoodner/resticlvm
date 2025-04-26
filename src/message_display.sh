#!/bin/bash

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
