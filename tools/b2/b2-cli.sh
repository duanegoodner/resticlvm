#!/bin/bash
#
# Wrapper script to run B2 CLI commands with credentials loaded
#
# This script sources the B2 environment file and executes b2 CLI commands.
#
# Usage:
#   ./b2-cli.sh ls --long --recursive b2://bucketName/path/
#   ./b2-cli.sh ls b2://kernelstate-backups/resticlvm/rudolph/
#   ./b2-cli.sh get-bucket kernelstate-backups
#
# Examples:
#   sudo ./b2-cli.sh ls --long --recursive b2://kernelstate-backups/resticlvm/rudolph/root-01/
#   sudo ./b2-cli.sh ls b2://kernelstate-backups/resticlvm/rudolph/

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

# Find b2 CLI in PATH
B2_CLI=$(which b2 2>/dev/null || echo "")

if [[ -z "$B2_CLI" ]]; then
    echo "❌ Error: b2 CLI not found in PATH"
    echo "   Install it with: pip install b2"
    echo "   Or: pip install -e \".[b2]\""
    echo ""
    echo "   When running with sudo, preserve your PATH:"
    echo "   sudo env \"PATH=\$PATH\" ./tools/b2-cli.sh [arguments]"
    exit 1
fi

# Authorize with B2 (only if not already authorized)
if ! "$B2_CLI" account get 2>/dev/null | grep -q "accountId"; then
    "$B2_CLI" account authorize "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" >/dev/null
fi

# Execute b2 CLI with all provided arguments
exec "$B2_CLI" "$@"
