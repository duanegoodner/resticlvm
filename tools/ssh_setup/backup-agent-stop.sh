#!/bin/bash
# Stop ssh-agent for root backups

AGENT_SOCK="/root/.ssh/ssh-agent.sock"

if [ ! -S "$AGENT_SOCK" ]; then
    echo "ℹ️  SSH agent is not running (socket not found)"
    exit 0
fi

# Check if agent is running
if SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    # Get the agent PID and kill it
    echo "🛑 Stopping SSH agent..."
    
    # The agent PID is the parent of the ssh-add process
    # But easier: just remove the socket - the agent will clean itself up
    # OR we can explicitly kill it by finding the process
    
    # Find the ssh-agent process listening on this socket
    AGENT_PID=$(lsof -t "$AGENT_SOCK" 2>/dev/null | head -n1)
    
    if [ -n "$AGENT_PID" ]; then
        kill "$AGENT_PID"
        echo "✅ SSH agent (PID $AGENT_PID) stopped"
    fi
    
    # Clean up socket
    rm -f "$AGENT_SOCK"
else
    echo "⚠️  Removing stale agent socket"
    rm -f "$AGENT_SOCK"
fi

echo "✅ SSH agent cleaned up"
