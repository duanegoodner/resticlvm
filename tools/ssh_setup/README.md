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

# Use a different key
sudo /usr/local/bin/backup-agent-start --key /root/.ssh/id_restic_backup

# Check agent status
sudo /usr/local/bin/backup-ssh-status

# Stop the agent
sudo /usr/local/bin/backup-agent-stop
```

All three scripts accept `--help` for full option details.

## Configuration

Default paths (override with CLI flags):
- Socket: `/root/.ssh/ssh-agent.sock` (`--socket`)
- SSH key: `/root/.ssh/id_backup` (`--key`, start script only)

## Exit Codes (backup-agent-start)

| Code | Meaning |
|------|---------|
| 0    | Agent started and key loaded successfully |
| 1    | Error |
| 2    | Agent already running on this socket (no action taken) |

When exit code is 2, the script lists the currently loaded keys and prints
instructions for either adding your key to the existing agent or stopping
it first.

## Documentation

For complete SSH setup instructions including client/server configuration, see [docs/EXAMPLE_SSH_SETUP.md](../../docs/EXAMPLE_SSH_SETUP.md).
