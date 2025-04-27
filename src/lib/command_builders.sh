#!/bin/bash

populate_exclude_paths() {
    declare -n exclude_args=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        exclude_args+=("--exclude=$path")
    done
}

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

populate_restic_tags() {
    local -n restic_tags=$1
    local exclude_paths=$2

    for path in $exclude_paths; do
        tag_path="${path#/}" # Remove leading slash for tag
        restic_tags+=("--tag=excl:/$tag_path")
    done
}

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
