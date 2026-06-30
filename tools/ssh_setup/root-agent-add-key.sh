#!/bin/bash
# Add an SSH key to root's running agent.
set -euo pipefail

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH] KEY_PATH

Add an SSH key to root's running agent. You will be prompted for the
key's passphrase if it has one.

Arguments:
  KEY_PATH             Path to the SSH private key to add (required)

Options:
  --socket SOCKET_PATH Agent socket path (default: $DEFAULT_SOCK)
  -h, --help           Show this help message
EOF
}

AGENT_SOCK="$DEFAULT_SOCK"
KEY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --socket) AGENT_SOCK="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        -*)  echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
        *)
            if [ -z "$KEY" ]; then
                KEY="$1"; shift
            else
                echo "Unexpected argument: $1" >&2; usage >&2; exit 1
            fi
            ;;
    esac
done

if [ -z "$KEY" ]; then
    echo "Error: KEY_PATH is required" >&2
    usage >&2
    exit 1
fi

if [ ! -f "$KEY" ]; then
    echo "Error: key file not found: $KEY" >&2
    exit 1
fi

if [ ! -S "$AGENT_SOCK" ]; then
    echo "Error: no agent running on $AGENT_SOCK" >&2
    echo "Start one first:" >&2
    echo "  sudo $(dirname "$0")/root-agent-start.sh --socket $AGENT_SOCK" >&2
    exit 1
fi
rc=0
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 2 ]; then
    echo "Error: agent socket exists but agent is not responding" >&2
    echo "Try restarting:" >&2
    echo "  sudo $(dirname "$0")/root-agent-stop.sh --socket $AGENT_SOCK" >&2
    echo "  sudo $(dirname "$0")/root-agent-start.sh --socket $AGENT_SOCK" >&2
    exit 1
fi

echo "Adding key $KEY (you may be prompted for passphrase)..."
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add "$KEY"

echo ""
echo "Loaded keys:"
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
