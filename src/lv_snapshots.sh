#!/bin/bash

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

generate_snapshot_name() {
    local vg_name="$1"
    local lv_name="$2"
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    echo "${vg_name}_${lv_name}_snapshot_${timestamp}"
}
