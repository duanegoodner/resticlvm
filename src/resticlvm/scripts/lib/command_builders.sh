#!/bin/bash

# Provides functions to build Restic command-line arguments for backups,
# including exclusion rules and backup tags.
#
# Usage:
#   Intended to be sourced by other scripts within the ResticLVM tool.
#
# Requirements:
#   - Environment variables like SNAPSHOT_MOUNT_POINT must be available
#     when working with LVM non-root backups.
#
# Exit codes:
#   N/A (helper functions only).

# Populate --exclude flags for a standard path backup.
populate_exclude_paths() {
    declare -n exclude_args=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        exclude_args+=("--exclude=$path")
    done
}

# Populate --exclude flags for an LVM non-root snapshot backup.
populate_exclude_paths_for_lv_nonroot() {
    declare -n exclude_args=$1
    local exclude_paths=$2
    local lv_mount_point=$3

    for path in $exclude_paths; do
        rel="${path#$lv_mount_point}"
        abs="$SNAPSHOT_MOUNT_POINT$rel"
        exclude_args+=("--exclude=$abs")
    done
}

# Populate --tag flags to label excluded paths in a backup.
populate_restic_tags() {
    local -n restic_tags=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        tag_path="${path#/}" # Remove leading slash for tag
        restic_tags+=("--tag=excl:/$tag_path")
    done
}

# Populate --tag flags for excluded paths in an LVM non-root backup.
populate_restic_tags_for_lv_nonroot() {
    local -n restic_tags=$1
    local exclude_paths=$2
    local lv_mount_point=$3

    for path in $exclude_paths; do
        rel="${path#$lv_mount_point}"
        tag_path="${rel#/}" # Remove leading slash for tag
        restic_tags+=("--tag=excl:/$tag_path")
    done
}
