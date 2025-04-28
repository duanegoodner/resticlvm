#!/bin/bash

set -euo pipefail

# Parameters:
#   $1 = restic repo path
#   $2 = password file
#   $3 = keep last
#   $4 = keep daily
#   $5 = keep weekly
#   $6 = keep monthly
#   $7 = keep yearly

RESTIC_REPO="$1"
PASSWORD_FILE="$2"
KEEP_LAST="$3"
KEEP_DAILY="$4"
KEEP_WEEKLY="$5"
KEEP_MONTHLY="$6"
KEEP_YEARLY="$7"

echo "🧹 Starting prune for repo: $RESTIC_REPO"

restic -r "$RESTIC_REPO" --password-file="$PASSWORD_FILE" forget --prune \
    --keep-last="$KEEP_LAST" \
    --keep-daily="$KEEP_DAILY" \
    --keep-weekly="$KEEP_WEEKLY" \
    --keep-monthly="$KEEP_MONTHLY" \
    --keep-yearly="$KEEP_YEARLY"

echo "✅ Prune completed for $RESTIC_REPO"
