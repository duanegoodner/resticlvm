#!/bin/bash
#
# Generic wrapper: load Backblaze B2 (S3-compatible) credentials, then exec the
# given command.
#
# Single responsibility — this script knows nothing about rlvm-backup or any
# particular entrypoint. It loads credentials and hands off to whatever command
# you give it. This keeps "load B2 creds" separate from "find/run the program".
#
# Usage:
#   sudo ./with-b2-creds.sh -- <command> [args...]
#   sudo ./with-b2-creds.sh <command> [args...]
#
# Examples:
#   sudo ./with-b2-creds.sh -- rlvm-backup --config /path/to/config.toml
#   sudo ./with-b2-creds.sh -- restic -r s3:... -p /path/to/pw.txt snapshots
#
# The credentials file (default /root/.config/resticlvm/b2-env, override with the
# B2_ENV_FILE env var) must export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

set -euo pipefail

B2_ENV_FILE="${B2_ENV_FILE:-/root/.config/resticlvm/b2-env}"

# Drop an optional leading "--" separator (so both calling styles work).
if [[ "${1:-}" == "--" ]]; then
    shift
fi

if [[ $# -eq 0 ]]; then
    echo "❌ Error: no command given." >&2
    echo "   Usage: $0 -- <command> [args...]" >&2
    exit 1
fi

if [[ ! -f "$B2_ENV_FILE" ]]; then
    echo "❌ Error: B2 environment file not found at $B2_ENV_FILE" >&2
    echo "   Create it with your B2 credentials:" >&2
    echo "   export AWS_ACCESS_KEY_ID=your_b2_key_id" >&2
    echo "   export AWS_SECRET_ACCESS_KEY=your_b2_application_key" >&2
    exit 1
fi

# Warn (don't fail) if the credentials file is readable by group/other.
perms="$(stat -c '%a' "$B2_ENV_FILE" 2>/dev/null || true)"
if [[ -n "$perms" && $(( 8#$perms & 8#077 )) -ne 0 ]]; then
    echo "⚠️  Warning: $B2_ENV_FILE is accessible to group/other (mode $perms)." >&2
    echo "   It holds your B2 credentials — restrict it: chmod 600 $B2_ENV_FILE" >&2
fi

# shellcheck disable=SC1090
source "$B2_ENV_FILE"

if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]] || [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    echo "❌ Error: AWS credentials not found after sourcing $B2_ENV_FILE" >&2
    echo "   Make sure the file exports AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY." >&2
    exit 1
fi

exec "$@"
