#!/bin/bash

# Prunes old snapshots from a specified Restic repository according to
# provided retention settings.
#
# Arguments:
#   $1  Path to the Restic repository.
#   $2  Path to the Restic password file.
#   $3  Number of last snapshots to keep.
#   $4  Number of daily snapshots to keep.
#   $5  Number of weekly snapshots to keep.
#   $6  Number of monthly snapshots to keep.
#   $7  Number of yearly snapshots to keep.
#
# Usage:
#   This script is intended to be called internally by the ResticLVM tool.
#
# Requirements:
#   - Restic must be installed and available in PATH.
#
# Exit codes:
#   0  Success
#   1  Any fatal error

set -euo pipefail

# Parse input arguments
RESTIC_REPO="$1"
PASSWORD_FILE="$2"
KEEP_LAST="$3"
KEEP_DAILY="$4"
KEEP_WEEKLY="$5"
KEEP_MONTHLY="$6"
KEEP_YEARLY="$7"

echo "🧹 Starting prune for repo: $RESTIC_REPO"

# Run Restic prune operation with specified retention settings
restic -r "$RESTIC_REPO" --password-file="$PASSWORD_FILE" forget --prune \
    --keep-last="$KEEP_LAST" \
    --keep-daily="$KEEP_DAILY" \
    --keep-weekly="$KEEP_WEEKLY" \
    --keep-monthly="$KEEP_MONTHLY" \
    --keep-yearly="$KEEP_YEARLY" \
    --keep-tag protected

echo "✅ Prune completed for $RESTIC_REPO"
