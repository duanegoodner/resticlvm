# SSH Setup for Remote SFTP Backups

This document describes the SSH authentication setup used for sending backups to remote repositories via SFTP.

## Overview

ResticLVM runs as root to create LVM snapshots and read all system files. For SFTP backups, we use:
- **Passphrase-protected SSH key** for security
- **SSH agent** to avoid passphrase prompts during automated backups
- **Dedicated backup user on remote** to limit blast radius if compromised

## Architecture

```
┌─────────────────────────────────┐          ┌──────────────────────────────┐
│  Client (clienthost)            │          │  Remote Backup Server        │
│                                 │          │  (backup-server.example.com) │
│  ┌──────────────────┐          │          │                              │
│  │ Root user        │          │   SSH    │  ┌────────────────────────┐  │
│  │ - Runs backups   │──────────┼─────────▶│  │ backup-clienthost      │  │
│  │ - Has SSH key    │          │   SFTP   │  │ - Owns backup dirs     │  │
│  │ - Uses agent     │          │          │  │ - Shell: /bin/bash     │  │
│  └──────────────────┘          │          │  │ - No sudo access       │  │
│                                 │          │  └────────────────────────┘  │
│  ┌──────────────────┐          │          │                              │
│  │ SSH Agent        │          │          │  /srv/client_backups/        │
│  │ - Holds key      │          │          │  └── clienthost/             │
│  │ - In memory      │          │          │      ├── root/               │
│  │ - No passphrase  │          │          │      ├── data-lv/            │
│  │   prompts        │          │          │      └── data-partition/     │
│  └──────────────────┘          │          │                              │
└─────────────────────────────────┘          └──────────────────────────────┘
```

## Setup Steps

### 1. Client Setup (clienthost)

#### 1.1 Create SSH Key with Passphrase

```bash
# Generate SSH key as root with a passphrase
sudo ssh-keygen -t ed25519 -f /root/.ssh/id_restic_backup -C "root@clienthost"
# Enter a strong passphrase when prompted
```

#### 1.2 Configure SSH Client

Create SSH config to use the correct key:

```bash
sudo tee /root/.ssh/config > /dev/null << 'EOF'
Host backup-server.example.com
    IdentityFile /root/.ssh/id_restic_backup
    IdentitiesOnly yes
EOF

sudo chmod 600 /root/.ssh/config
```

#### 1.3 Install Helper Scripts

Create `backup-agent-start` to manage the SSH agent:

```bash
sudo tee /usr/local/bin/backup-agent-start << 'EOF'
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
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add /root/.ssh/id_restic_backup

# Show loaded keys
echo ""
echo "✅ Agent started. Loaded keys:"
SSH_AUTH_SOCK="$AGENT_SOCK" ssh-add -l
EOF

sudo chmod +x /usr/local/bin/backup-agent-start
```

Create `backup-ssh-status` to check agent status:

```bash
sudo tee /usr/local/bin/backup-ssh-status << 'EOF'
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
EOF

sudo chmod +x /usr/local/bin/backup-ssh-status
```

### 2. Remote Server Setup

#### 2.1 Create Dedicated Backup User

Create a user specifically for this client machine:

```bash
# On remote server
sudo useradd -r -m -s /bin/bash backup-clienthost
```

**Security note:** Using `-s /bin/bash` allows shell access for easier management. For maximum security, use `-s /usr/sbin/nologin`, though this requires creating all directories before use.

#### 2.2 Create Backup Directory Structure

```bash
# Create directory for this client's backups
sudo mkdir -p /srv/client_backups/clienthost/{root,data-lv,data-partition}

# Set ownership
sudo chown -R backup-clienthost:backup-clienthost /srv/client_backups/clienthost

# Restrict permissions (only this user can access)
sudo chmod 700 /srv/client_backups/clienthost
```

#### 2.3 Set Up SSH Key Authentication

From the **client machine** (clienthost), copy the public key to the remote:

```bash
# Copy SSH key to remote server
sudo ssh-copy-id -i /root/.ssh/id_restic_backup backup-clienthost@backup-server.example.com
# Enter passphrase when prompted
```

Alternatively, manually add the key on the remote server:

```bash
# On remote server
sudo mkdir -p /home/backup-clienthost/.ssh
sudo chmod 700 /home/backup-clienthost/.ssh

# Copy the public key content here
sudo tee /home/backup-clienthost/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3Nza... root@clienthost
EOF

sudo chmod 600 /home/backup-clienthost/.ssh/authorized_keys
sudo chown -R backup-clienthost:backup-clienthost /home/backup-clienthost/.ssh
```

### 3. Initialize Restic Repositories

From the client, initialize the restic repositories on the remote:

```bash
# Start SSH agent and add key (do this once after reboot)
sudo /usr/local/bin/backup-agent-start
# Enter passphrase when prompted

# Initialize repositories
sudo SSH_AUTH_SOCK=/root/.ssh/ssh-agent.sock \
  restic -r sftp:backup-clienthost@backup-server.example.com:/srv/client_backups/clienthost/root \
  init --password-file /path/to/restic-password.txt

sudo SSH_AUTH_SOCK=/root/.ssh/ssh-agent.sock \
  restic -r sftp:backup-clienthost@backup-server.example.com:/srv/client_backups/clienthost/data-lv \
  init --password-file /path/to/restic-password.txt

sudo SSH_AUTH_SOCK=/root/.ssh/ssh-agent.sock \
  restic -r sftp:backup-clienthost@backup-server.example.com:/srv/client_backups/clienthost/data-partition \
  init --password-file /path/to/restic-password.txt
```

### 4. Daily Usage

#### 4.1 After System Reboot

The SSH agent doesn't persist across reboots. After reboot, start it and add the key:

```bash
sudo /usr/local/bin/backup-agent-start
# Enter passphrase once
```

#### 4.2 Check Agent Status

```bash
sudo backup-ssh-status
```

#### 4.3 Run Backups

Once the agent is running with the key loaded, backups work automatically:

```bash
rlvm-backup --config /path/to/config.toml
# No passphrase prompt - uses agent!
```

### 5. Cron Job Setup

Create a wrapper script for automated backups:

```bash
sudo tee /usr/local/bin/backup-with-notification.sh << 'EOF'
#!/bin/bash

LOGFILE="/var/log/resticlvm/backup-$(date +%Y%m%d-%H%M%S).log"
mkdir -p /var/log/resticlvm

# Use the persistent agent
export SSH_AUTH_SOCK=/root/.ssh/ssh-agent.sock

# Check if agent has keys loaded
if ! ssh-add -l &>/dev/null; then
    echo "❌ SSH agent not running or no keys loaded" | tee "$LOGFILE"
    echo "Run: sudo /usr/local/bin/backup-agent-start" | tee -a "$LOGFILE"
    # Send notification
    mail -s "⚠️ Backup Failed - SSH Agent Not Ready" admin@example.com < "$LOGFILE"
    exit 1
fi

# Run backup
/usr/local/bin/rlvm-backup --config /etc/resticlvm/backup.toml &> "$LOGFILE"

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    # Send failure notification
    cat "$LOGFILE" | mail -s "⚠️ Backup Failed on $(hostname)" admin@example.com
else
    # Success
    echo "✅ Backup completed successfully at $(date)" >> /var/log/resticlvm/success.log
fi

exit $EXIT_CODE
EOF

sudo chmod +x /usr/local/bin/backup-with-notification.sh
```

Add to cron:

```bash
sudo crontab -e

# Add line:
0 2 * * * /usr/local/bin/backup-with-notification.sh
```

## Security Considerations

### Why Dedicated User Per Client?

If you're backing up multiple machines to the same remote server:

```
Remote Server
├── backup-client1     (UID 999)  → /srv/client_backups/client1/
├── backup-laptop      (UID 998)  → /srv/client_backups/laptop/
└── backup-webserver   (UID 997)  → /srv/client_backups/webserver/
```

**Benefits:**
- ✅ **Blast radius limitation:** Compromised laptop can't access webserver backups
- ✅ **Accountability:** Clear audit trail per machine
- ✅ **Easy revocation:** Disable one user without affecting others
- ✅ **Granular permissions:** Each user owns only their backup directories

### SSH Agent Security

**Passphrase-protected key + Agent:**
- ✅ Private key encrypted on disk (useless without passphrase)
- ✅ Decrypted key only in memory while agent running
- ✅ Agent cleared on reboot
- ✅ Cannot extract key from agent (can only use it)

**Tradeoffs:**
- ⚠️ Must re-add key after reboot (enter passphrase once)
- ⚠️ While agent running, can be used by anyone with root access
- ⚠️ Automated cron jobs require agent to be running

**Alternative (not recommended for production):**
- Passphrase-less key: No manual intervention after reboot, but less secure

## Troubleshooting

### "Permission denied (publickey)"

```bash
# Check agent status
sudo backup-ssh-status

# If agent not running:
sudo /usr/local/bin/backup-agent-start

# Test SSH connection
sudo SSH_AUTH_SOCK=/root/.ssh/ssh-agent.sock \
  ssh backup-clienthost@backup-server.example.com echo "Success"
```

### "Packet too long" or "Connection closed"

This usually means shell startup files are producing output. On the remote:

```bash
# Ensure .bashrc doesn't output for non-interactive sessions
sudo nano /home/backup-clienthost/.bashrc

# Wrap any output in:
if [[ $- == *i* ]]; then
    # Interactive commands here
fi
```

### Agent Not Persisting

The agent socket is at `/root/.ssh/ssh-agent.sock`. If this file doesn't exist, the agent isn't running. Restart it:

```bash
sudo /usr/local/bin/backup-agent-start
```

## Configuration Example

In your ResticLVM config (`backup.toml`):

```toml
[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys", "/tmp"]

# Local repository
[[logical_volume_root.root.repositories]]
repo_path = "/srv/backup/root-local"
password_file = "/etc/resticlvm/restic-password.txt"

# Remote SFTP repository (dedicated user)
[[logical_volume_root.root.repositories]]
repo_path = "sftp:backup-clienthost@backup-server.example.com:/srv/client_backups/clienthost/root"
password_file = "/etc/resticlvm/restic-password.txt"
```

## Additional Hardening (Optional)

### Restrict SSH to SFTP-Only

On the remote server, edit `/etc/ssh/sshd_config`:

```bash
sudo tee -a /etc/ssh/sshd_config << 'EOF'

Match User backup-*
    ForceCommand internal-sftp
    ChrootDirectory /srv/client_backups
    PermitTunnel no
    AllowAgentForwarding no
    AllowTcpForwarding no
    X11Forwarding no
EOF

sudo systemctl reload sshd
```

This restricts all `backup-*` users to SFTP only (no shell access).

### Use Append-Only Repositories

On the remote server, run restic rest-server in append-only mode to prevent deletion of old backups even if credentials are compromised.