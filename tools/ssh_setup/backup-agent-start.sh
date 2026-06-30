#!/bin/bash
# Start ssh-agent for root backups and load the specified key.
set -euo pipefail

DEFAULT_KEY="/root/.ssh/id_backup"
DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--key KEY_PATH] [--socket SOCKET_PATH]

Start an SSH agent for backup operations and load the specified key.

Options:
  --key KEY_PATH       SSH key to load (default: $DEFAULT_KEY)
  --socket SOCKET_PATH Agent socket path (default: $DEFAULT_SOCK)
  -h, --help           Show this help message

Exit codes:
  0  Agent started and key loaded successfully
  1  Error
  2  Agent already running on this socket (no action taken)
EOF
}

KEY="$DEFAULT_KEY"
AGENT_SOCK="$DEFAULT_SOCK"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --key)    KEY="$2"; shift 2 ;;
        --socket) AGENT_SOCK="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

# If an agent is already running on this socket, report its state and stop.
if [ -S "$AGENT_SOCK" ] && SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "Agent already running on $AGENT_SOCK with these keys:"
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
    echo ""
    echo "To add your backup key to this agent:"
    echo "  SSH_AUTH_SOCK=$AGENT_SOCK ssh-add $KEY"
    echo ""
    echo "To start fresh, stop the agent first then re-run this script:"
    echo "  $(dirname "$0")/backup-agent-stop --socket $AGENT_SOCK"
    exit 2
fi

# Clean up stale socket if present
if [ -S "$AGENT_SOCK" ]; then
    echo "Removing stale agent socket"
    rm -f "$AGENT_SOCK"
fi

echo "Starting SSH agent..."
ssh-agent -a "$AGENT_SOCK" > /dev/null

echo "Adding SSH key (you will be prompted for passphrase)..."
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add "$KEY"

echo ""
echo "Agent started. Loaded keys:"
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
