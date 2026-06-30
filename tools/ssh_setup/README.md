# Root SSH Agent Management Tools

Helper scripts for managing root's SSH agent for automated SFTP backups.

## Scripts

| Script | Purpose |
|--------|---------|
| `root-agent-start.sh` | Start an SSH agent on a well-known socket |
| `root-agent-stop.sh` | Stop the agent and remove the socket |
| `root-agent-status.sh` | Show agent status and loaded keys |
| `root-agent-add-key.sh` | Add an SSH key to the running agent |
| `root-agent-remove-key.sh` | Remove a key (or all keys) from the agent |

## Purpose

These scripts manage a persistent SSH agent that runs as root and holds
passphrase-protected SSH keys in memory. This allows ResticLVM to perform
automated backups to SFTP repositories without password prompts.

Agent lifecycle (start/stop) is separate from key management (add/remove),
so you can start the agent once and add or rotate keys independently.

## Installation

Copy the scripts to `/usr/local/bin/` for system-wide use:

```bash
sudo cp tools/ssh_setup/root-agent-*.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/root-agent-*.sh
```

## Usage

```bash
# Start the agent
sudo root-agent-start.sh

# Add a key (you'll be prompted for its passphrase)
sudo root-agent-add-key.sh /root/.ssh/id_restic_backup

# Check status
sudo root-agent-status.sh

# Remove a specific key
sudo root-agent-remove-key.sh /root/.ssh/id_restic_backup

# Remove all keys
sudo root-agent-remove-key.sh --all

# Stop the agent
sudo root-agent-stop.sh
```

All scripts accept `--socket` to override the default socket path
(`/root/.ssh/ssh-agent.sock`) and `--help` for full usage details.

## Exit Codes (root-agent-start)

| Code | Meaning |
|------|---------|
| 0 | Agent started successfully |
| 1 | Error |
| 2 | Agent already running on this socket (no action taken) |

## Documentation

For complete SSH setup instructions including client/server configuration,
see [docs/EXAMPLE_SSH_SETUP.md](../../docs/EXAMPLE_SSH_SETUP.md).
