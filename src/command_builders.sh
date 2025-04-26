#!/bin/bash

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
