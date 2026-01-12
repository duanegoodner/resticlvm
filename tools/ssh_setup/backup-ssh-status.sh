#!/bin/bash
AGENT_SOCK="/root/.ssh/ssh-agent.sock"

echo "SSH Agent Status for Root:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -S "$AGENT_SOCK" ]; then
    echo "❌ Agent not running (socket not found)"
    echo ""
    echo "To start agent, run:"
    echo "  sudo /usr/local/bin/backup-agent-start"
    exit 1
fi

if SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "✅ Agent running with loaded keys:"
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
else
    echo "⚠️  Agent running but no keys loaded"
    echo ""
    echo "To add keys, run:"
    echo "  sudo /usr/local/bin/backup-agent-start"
    exit 1
fi
