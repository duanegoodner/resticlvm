#!/bin/bash
# Manage root's SSH agent on a well-known socket.
# Part of ResticLVM — https://github.com/duanegoodner/resticlvm/tools/ssh_setup/
set -euo pipefail

DEFAULT_SOCK="/root/.ssh/ssh-agent.sock"
AGENT_SOCK="$DEFAULT_SOCK"

usage() {
    cat <<EOF
Usage: $(basename "$0") [--socket SOCKET_PATH] <command> [args...]

Manage root's SSH agent on a dedicated socket.

Commands:
  start       Start the agent (exits 2 if already running)
  stop        Stop the agent and remove the socket
  status      Show agent state and loaded keys
  ssh-add     Run ssh-add against this agent (all ssh-add flags supported)

Global options:
  --socket SOCKET_PATH  Agent socket path (default: $DEFAULT_SOCK)
  -h, --help            Show this help message

Examples:
  $(basename "$0") start
  $(basename "$0") ssh-add /root/.ssh/id_backup
  $(basename "$0") ssh-add -l
  $(basename "$0") ssh-add -d /root/.ssh/id_backup
  $(basename "$0") ssh-add -D
  $(basename "$0") status
  $(basename "$0") stop
EOF
}

usage_start() {
    cat <<EOF
Usage: $(basename "$0") start [--socket SOCKET_PATH]

Start an SSH agent bound to the socket. Exits 2 if an agent is already
running on the socket.
EOF
}

usage_stop() {
    cat <<EOF
Usage: $(basename "$0") stop [--socket SOCKET_PATH]

Stop the SSH agent and remove the socket.
EOF
}

usage_status() {
    cat <<EOF
Usage: $(basename "$0") status [--socket SOCKET_PATH]

Show whether the agent is running and list its loaded keys.
EOF
}

usage_ssh_add() {
    cat <<EOF
Usage: $(basename "$0") ssh-add [--socket SOCKET_PATH] [ssh-add args...]

Run ssh-add against this agent. All ssh-add flags are supported.

Examples:
  $(basename "$0") ssh-add /root/.ssh/id_backup       # add a key
  $(basename "$0") ssh-add -l                          # list keys
  $(basename "$0") ssh-add -d /root/.ssh/id_backup     # remove a key
  $(basename "$0") ssh-add -D                          # remove all keys
  $(basename "$0") ssh-add -t 3600 /root/.ssh/id_backup  # add with lifetime
EOF
}

check_help() {
    for arg in "$@"; do
        case "$arg" in
            -h|--help) return 0 ;;
        esac
    done
    return 1
}

cmd_start() {
    if check_help "$@"; then usage_start; exit 0; fi

    if [ -S "$AGENT_SOCK" ] && SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
        echo "Agent already running on $AGENT_SOCK with these keys:"
        SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
        echo ""
        echo "To stop it first:"
        echo "  $(basename "$0") stop"
        exit 2
    fi

    if [ -S "$AGENT_SOCK" ]; then
        echo "Removing stale agent socket"
        rm -f "$AGENT_SOCK"
    fi

    echo "Starting SSH agent on $AGENT_SOCK ..."
    ssh-agent -a "$AGENT_SOCK" > /dev/null
    echo "Agent started."
}

cmd_stop() {
    if check_help "$@"; then usage_stop; exit 0; fi

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
}

cmd_status() {
    if check_help "$@"; then usage_status; exit 0; fi

    echo "SSH Agent Status (socket: $AGENT_SOCK)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [ ! -S "$AGENT_SOCK" ]; then
        echo "Agent not running (socket not found)"
        echo ""
        echo "To start agent, run:"
        echo "  sudo $(basename "$0") start"
        exit 1
    fi

    rc=0
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null 2>&1 || rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "Agent running with loaded keys:"
        SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
    elif [ "$rc" -eq 1 ]; then
        echo "Agent running but no keys loaded"
        echo ""
        echo "To add a key, run:"
        echo "  sudo $(basename "$0") ssh-add KEY_PATH"
        exit 1
    else
        echo "Agent socket exists but agent is not responding"
        echo ""
        echo "Try restarting:"
        echo "  sudo $(basename "$0") stop"
        echo "  sudo $(basename "$0") start"
        exit 1
    fi
}

cmd_ssh_add() {
    if check_help "$@"; then usage_ssh_add; exit 0; fi

    if [ ! -S "$AGENT_SOCK" ]; then
        echo "Error: no agent running on $AGENT_SOCK" >&2
        echo "Start one first:" >&2
        echo "  sudo $(basename "$0") start" >&2
        exit 1
    fi

    rc=0
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null 2>&1 || rc=$?
    if [ "$rc" -eq 2 ]; then
        echo "Error: agent socket exists but agent is not responding" >&2
        echo "Try restarting:" >&2
        echo "  sudo $(basename "$0") stop" >&2
        echo "  sudo $(basename "$0") start" >&2
        exit 1
    fi

    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add "$@"
}

# Parse global options before the subcommand
while [[ $# -gt 0 ]]; do
    case "$1" in
        --socket) AGENT_SOCK="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
        *) break ;;
    esac
done

if [ $# -eq 0 ]; then
    usage
    exit 0
fi

COMMAND="$1"
shift

case "$COMMAND" in
    start)   cmd_start "$@" ;;
    stop)    cmd_stop "$@" ;;
    status)  cmd_status "$@" ;;
    ssh-add) cmd_ssh_add "$@" ;;
    *)
        echo "Unknown command: $COMMAND" >&2
        usage >&2
        exit 1
        ;;
esac
