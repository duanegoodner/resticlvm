#!/bin/bash
# Start an SSH agent for root.
set -euo pipefail

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH]

Start an SSH agent bound to a well-known socket. Does not add any keys;
use root-agent-add-key to load keys after the agent is running.

Options:
  --socket SOCKET_PATH Agent socket path (default: $DEFAULT_SOCK)
  -h, --help           Show this help message

Exit codes:
  0  Agent started successfully
  1  Error
  2  Agent already running on this socket (no action taken)
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

# If an agent is already running on this socket, report and exit.
if [ -S "$AGENT_SOCK" ] && SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "Agent already running on $AGENT_SOCK with these keys:"
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
    echo ""
    echo "To stop it first:"
    echo "  $(dirname "$0")/root-agent-stop.sh --socket $AGENT_SOCK"
    exit 2
fi

# Clean up stale socket if present
if [ -S "$AGENT_SOCK" ]; then
    echo "Removing stale agent socket"
    rm -f "$AGENT_SOCK"
fi

echo "Starting SSH agent on $AGENT_SOCK ..."
ssh-agent -a "$AGENT_SOCK" > /dev/null
echo "Agent started."
