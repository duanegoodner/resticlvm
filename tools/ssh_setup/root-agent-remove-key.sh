#!/bin/bash
# Remove an SSH key from root's running agent.
set -euo pipefail

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH] [--all] [KEY_PATH]

Remove an SSH key from root's running agent, or remove all keys.

Arguments:
  KEY_PATH             Path to the SSH private key to remove

Options:
  --all                Remove all keys from the agent
  --socket SOCKET_PATH Agent socket path (default: $DEFAULT_SOCK)
  -h, --help           Show this help message

Provide either KEY_PATH or --all, not both.
EOF
}

AGENT_SOCK="$DEFAULT_SOCK"
KEY=""
REMOVE_ALL=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --socket) AGENT_SOCK="$2"; shift 2 ;;
        --all)    REMOVE_ALL=true; shift ;;
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

if [ "$REMOVE_ALL" = false ] && [ -z "$KEY" ]; then
    echo "Error: provide KEY_PATH or --all" >&2
    usage >&2
    exit 1
fi

if [ "$REMOVE_ALL" = true ] && [ -n "$KEY" ]; then
    echo "Error: cannot use --all with a KEY_PATH" >&2
    usage >&2
    exit 1
fi

if [ ! -S "$AGENT_SOCK" ]; then
    echo "Error: no agent running on $AGENT_SOCK" >&2
    exit 1
fi
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null 2>&1
rc=$?
if [ "$rc" -eq 2 ]; then
    echo "Error: agent socket exists but agent is not responding" >&2
    exit 1
fi

if [ "$REMOVE_ALL" = true ]; then
    echo "Removing all keys from agent..."
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -D
else
    if [ ! -f "$KEY" ]; then
        echo "Error: key file not found: $KEY" >&2
        exit 1
    fi
    echo "Removing key $KEY ..."
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -d "$KEY"
fi

echo ""
echo "Remaining keys:"
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l 2>/dev/null || echo "  (none)"
