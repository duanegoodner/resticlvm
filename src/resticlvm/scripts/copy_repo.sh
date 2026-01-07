#!/bin/bash

# Copy snapshots from a source Restic repository to a destination repository.
#
# Arguments:
#   -s  Source repository path.
#   -p  Source repository password file.
#   -d  Destination repository path.
#   -q  Destination repository password file.
#   -n  (Optional) Dry run mode.
#
# Usage:
#   This script is intended to be called internally by the ResticLVM tool.
#
# Requirements:
#   - Must be run with root privileges (direct root or via sudo).
#   - Restic must be installed and available in PATH.
#
# Exit codes:
#   0  Success
#   1  Any fatal error

set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/backup_helpers.sh"

# ─── Require Running as Root ─────────────────────────────────────
root_check

# ─── Default Values ──────────────────────────────────────────────
SOURCE_REPO=""
SOURCE_PASSWORD_FILE=""
DEST_REPO=""
DEST_PASSWORD_FILE=""
DRY_RUN=false

# ─── Usage Function ──────────────────────────────────────────────
usage() {
    cat <<EOF
Usage:
$(basename "$0") -s SOURCE_REPO -p SOURCE_PASS -d DEST_REPO -q DEST_PASS [-n]

Options:
  -s, --source-repo          Source Restic repository path
  -p, --source-password      Source repository password file
  -d, --dest-repo            Destination Restic repository path
  -q, --dest-password        Destination repository password file
  -n, --dry-run              Dry run mode (preview only)
  -h, --help                 Display this message and exit

Example:
  $(basename "$0") -s /srv/backup/root -p /root/.restic-root \\
    -d sftp:user@host:/backups/root -q /root/.restic-remote
EOF
    exit 1
}

# ─── Parse Arguments ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--source-repo)
            SOURCE_REPO="$2"
            shift 2
            ;;
        -p|--source-password)
            SOURCE_PASSWORD_FILE="$2"
            shift 2
            ;;
        -d|--dest-repo)
            DEST_REPO="$2"
            shift 2
            ;;
        -q|--dest-password)
            DEST_PASSWORD_FILE="$2"
            shift 2
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "❌ Unexpected option: $1"
            usage
            ;;
    esac
done

# ─── Validate Arguments ──────────────────────────────────────────
if [ -z "$SOURCE_REPO" ] || [ -z "$SOURCE_PASSWORD_FILE" ] || \
   [ -z "$DEST_REPO" ] || [ -z "$DEST_PASSWORD_FILE" ]; then
    echo "❌ Error: All repository and password file arguments are required"
    usage
fi

if [ ! -f "$SOURCE_PASSWORD_FILE" ]; then
    echo "❌ Error: Source password file not found: $SOURCE_PASSWORD_FILE"
    exit 1
fi

if [ ! -f "$DEST_PASSWORD_FILE" ]; then
    echo "❌ Error: Destination password file not found: $DEST_PASSWORD_FILE"
    exit 1
fi

# ─── Display Configuration ───────────────────────────────────────
echo ""
echo "🔄 Restic Copy Configuration"
echo "  SOURCE-REPO:           $SOURCE_REPO"
echo "  DEST-REPO:             $DEST_REPO"
echo "  DRY-RUN:               $DRY_RUN"
echo ""

display_dry_run_message "$DRY_RUN"

# ─── Execute Copy ────────────────────────────────────────────────
echo "🚀 Copying snapshots from source to destination..."
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would execute:"
    echo "  restic -r $DEST_REPO --password-file $DEST_PASSWORD_FILE \\"
    echo "    copy --from-repo $SOURCE_REPO --from-password-file $SOURCE_PASSWORD_FILE"
else
    restic -r "$DEST_REPO" --password-file "$DEST_PASSWORD_FILE" \
        copy --from-repo "$SOURCE_REPO" --from-password-file "$SOURCE_PASSWORD_FILE" \
        --verbose
fi

echo ""
echo "✅ Copy completed successfully (or would have, in dry-run mode)."
