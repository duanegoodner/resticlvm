#!/bin/bash
# Start ssh-agent for root backups if not already running

AGENT_SOCK="/root/.ssh/ssh-agent.sock"

# Check if agent is already running and responsive
if [ -S "$AGENT_SOCK" ] && SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l &>/dev/null; then
    echo "✅ SSH agent already running and has keys loaded"
    SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
    exit 0
fi

# Kill old agent if socket exists but not responsive
if [ -S "$AGENT_SOCK" ]; then
    echo "⚠️  Removing stale agent socket"
    rm -f "$AGENT_SOCK"
fi

# Start new agent
echo "🔑 Starting SSH agent..."
ssh-agent -a "$AGENT_SOCK" > /dev/null

# Add key
echo "📝 Adding SSH key (you'll be prompted for passphrase)..."
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add /root/.ssh/id_backup

# Show loaded keys
echo ""
echo "✅ Agent started. Loaded keys:"
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
