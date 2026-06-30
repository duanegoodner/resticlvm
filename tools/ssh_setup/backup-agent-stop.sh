#!/bin/bash
# Stop ssh-agent for root backups.
set -euo pipefail

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH]

Stop the SSH agent and remove the socket.

Options:
  --socket SOCKET_PATH Agent socket path (default: $DEFAULT_SOCK)
  -h, --help           Show this help message
EOF
}

AGENT_SOCK="$DEFAULT_SOCK"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --socket) AGENT_SOCK="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [ ! -S "$AGENT_SOCK" ]; then
    echo "SSH agent is not running (socket not found at $AGENT_SOCK)"
    exit 0
fi

if SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "Stopping SSH agent..."
    AGENT_PID=$(lsof -t "$AGENT_SOCK" 2>/dev/null | head -n1)

    if [ -n "$AGENT_PID" ]; then
        kill "$AGENT_PID"
        echo "SSH agent (PID $AGENT_PID) stopped"
    fi

    rm -f "$AGENT_SOCK"
else
    echo "Removing stale agent socket"
    rm -f "$AGENT_SOCK"
fi

echo "SSH agent cleaned up"
