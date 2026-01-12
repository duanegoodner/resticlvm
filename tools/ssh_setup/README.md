# SSH Agent Management Tools

Helper scripts for managing SSH agents for automated SFTP backups.

## Files

- `backup-agent-start.sh` - Start SSH agent and load backup key
- `backup-agent-stop.sh` - Stop SSH agent and remove socket
- `backup-ssh-status.sh` - Check SSH agent status and loaded keys

## Purpose

These scripts manage a persistent SSH agent that runs as root and holds a passphrase-protected SSH key in memory. This allows ResticLVM to perform automated backups to SFTP repositories without password prompts.

## Installation

Copy the scripts to `/usr/local/bin/` for system-wide use:

```bash
sudo cp backup-agent-start.sh /usr/local/bin/backup-agent-start
sudo cp backup-agent-stop.sh /usr/local/bin/backup-agent-stop
sudo cp backup-ssh-status.sh /usr/local/bin/backup-ssh-status
sudo chmod +x /usr/local/bin/backup-agent-*
sudo chmod +x /usr/local/bin/backup-ssh-status
```

## Usage

```bash
# Start the agent (will prompt for SSH key passphrase)
sudo /usr/local/bin/backup-agent-start

# Check agent status
sudo /usr/local/bin/backup-ssh-status

# Stop the agent
sudo /usr/local/bin/backup-agent-stop
```

## Configuration

By default, these scripts use:
- Socket: `/root/.ssh/ssh-agent.sock`
- SSH key: `/root/.ssh/id_backup`

Edit the scripts if you need different paths.

## Documentation

For complete SSH setup instructions including client/server configuration, see [docs/EXAMPLE_SSH_SETUP.md](../../docs/EXAMPLE_SSH_SETUP.md).
