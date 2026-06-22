#!/bin/bash
#
# Convenience wrapper: run rlvm-backup with B2 credentials loaded.
#
# Credential-loading and entrypoint resolution are now separate concerns:
#   - B2 credentials are loaded by with-b2-creds.sh (this script delegates to it).
#   - The rlvm-backup entrypoint is resolved explicitly via the RLVM_BACKUP env
#     var, falling back to a PATH lookup — no fragile bare `which`.
#
# Usage:
#   sudo ./run-backup-with-b2.sh --config /path/to/config.toml [other options]
#   sudo RLVM_BACKUP=/abs/path/to/rlvm-backup ./run-backup-with-b2.sh --config ...
#
# For a fully generic "load B2 creds then run any command", use with-b2-creds.sh:
#   sudo ./with-b2-creds.sh -- rlvm-backup --config /path/to/config.toml
#
# Setup:
#   1. Create /root/.config/resticlvm/b2-env exporting AWS_ACCESS_KEY_ID and
#      AWS_SECRET_ACCESS_KEY.
#   2. For cron, run as root and pin the entrypoint with an absolute path, e.g.:
#      0 2 * * * RLVM_BACKUP=/usr/local/bin/rlvm-backup \
#        /path/to/run-backup-with-b2.sh --config /path/to/config.toml

set -euo pipefail

# Ensure system binaries (LVM, etc.) are reachable.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve the rlvm-backup entrypoint explicitly: prefer an RLVM_BACKUP override
# (e.g. an absolute path from cron/systemd), then fall back to a PATH lookup.
RLVM_BACKUP="${RLVM_BACKUP:-$(command -v rlvm-backup || true)}"

if [[ -z "$RLVM_BACKUP" ]]; then
    echo "❌ Error: rlvm-backup not found." >&2
    echo "   Set RLVM_BACKUP to its absolute path, or ensure it is on PATH." >&2
    echo "   e.g. sudo RLVM_BACKUP=/usr/local/bin/rlvm-backup $0 --config ..." >&2
    exit 1
fi

# Load B2 creds (separate concern), then run the resolved entrypoint.
exec "$SCRIPT_DIR/with-b2-creds.sh" -- "$RLVM_BACKUP" "$@"
