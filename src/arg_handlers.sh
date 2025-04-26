#!/bin/bash

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
