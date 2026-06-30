#!/bin/bash
# Report SSH agent status for root.

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH]

Check the status of root's SSH agent and list loaded keys.

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

echo "SSH Agent Status (socket: $AGENT_SOCK)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -S "$AGENT_SOCK" ]; then
    echo "Agent not running (socket not found)"
    echo ""
    echo "To start agent, run:"
    echo "  sudo $(dirname "$0")/root-agent-start --socket $AGENT_SOCK"
    exit 1
fi

if SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "Agent running with loaded keys:"
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
else
    echo "Agent running but no keys loaded"
    echo ""
    echo "To add a key, run:"
    echo "  sudo $(dirname "$0")/root-agent-add-key --socket $AGENT_SOCK KEY_PATH"
    exit 1
fi
