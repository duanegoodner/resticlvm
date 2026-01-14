#!/bin/bash
#
# Wrapper script to run restic commands against B2 repositories with credentials loaded
#
# This script sources the B2 environment file and executes restic commands.
#
# Usage:
#   ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path -p /path/to/password snapshots
#   ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path -p /path/to/password ls latest
#   ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path -p /path/to/password check
#
# Example for boot repo:
#   sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/kernelstate-backups/resticlvm/rudolph/boot-01 \
#     -p /root/.config/resticlvm/repo-creds/b2-boot-01.txt snapshots

set -euo pipefail

# Ensure system binaries are in PATH
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

# Execute restic with all provided arguments
exec restic "$@"
