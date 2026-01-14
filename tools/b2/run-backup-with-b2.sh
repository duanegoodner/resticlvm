#!/bin/bash
#
# Wrapper script to run rlvm-backup with B2 credentials loaded
#
# This script sources the B2 environment file containing AWS credentials
# needed for Backblaze B2 S3-compatible storage, then executes rlvm-backup
# with any arguments you provide.
#
# Usage:
#   ./run-backup-with-b2.sh --config /path/to/config.toml [other options]
#   ./run-backup-with-b2.sh --name boot --config /path/to/config.toml
#   ./run-backup-with-b2.sh --category standard_path --config /path/to/config.toml
#
# Setup:
#   1. Create /root/.config/resticlvm/b2-env with your B2 credentials:
#      export AWS_ACCESS_KEY_ID=your_b2_key_id
#      export AWS_SECRET_ACCESS_KEY=your_b2_application_key
#
#   2. Make this script executable:
#      chmod +x run-backup-with-b2.sh
#
#   3. For cron usage, add to root's crontab:
#      0 2 * * * /path/to/run-backup-with-b2.sh --config /path/to/config.toml
#

set -euo pipefail

# Ensure system binaries are in PATH for LVM commands
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

# Path to the B2 environment file
B2_ENV_FILE="/root/.config/resticlvm/b2-env"

# Check if the environment file exists
if [[ ! -f "$B2_ENV_FILE" ]]; then
    echo "❌ Error: B2 environment file not found at $B2_ENV_FILE"
    echo "   Please create this file with your B2 credentials:"
    echo "   export AWS_ACCESS_KEY_ID=your_b2_key_id"
    echo "   export AWS_SECRET_ACCESS_KEY=your_b2_application_key"
    exit 1
fi

# Source the B2 credentials
# shellcheck disable=SC1090
source "$B2_ENV_FILE"

# Verify credentials were loaded
if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]] || [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    echo "❌ Error: AWS credentials not found after sourcing $B2_ENV_FILE"
    echo "   Make sure the file contains:"
    echo "   export AWS_ACCESS_KEY_ID=your_b2_key_id"
    echo "   export AWS_SECRET_ACCESS_KEY=your_b2_application_key"
    exit 1
fi

# Find rlvm-backup (could be in conda env or system path)
RLVM_BACKUP=$(which rlvm-backup 2>/dev/null || echo "")

if [[ -z "$RLVM_BACKUP" ]]; then
    echo "❌ Error: rlvm-backup not found in PATH"
    echo "   Make sure rlvm-backup is installed and accessible"
    exit 1
fi

# Execute rlvm-backup with all provided arguments
exec "$RLVM_BACKUP" "$@"
