# Root SSH Agent Helper

A single script (`root-ssh-agent.sh`) for managing root's SSH agent on a
dedicated socket. ResticLVM needs root to have SSH access to remote backup
servers; this script is one way to set that up, but any method that provides
`SSH_AUTH_SOCK` to root works.

## Commands

```
root-ssh-agent start       Start the agent
root-ssh-agent stop        Stop the agent and remove the socket
root-ssh-agent status      Show agent state and loaded keys
root-ssh-agent ssh-add ... Run ssh-add against this agent (all ssh-add flags work)
```

The `ssh-add` command is a direct passthrough -- anything `ssh-add` supports
works: `-l` (list), `-d` (remove key), `-D` (remove all), `-t` (lifetime), etc.

## Optional installation

```bash
sudo cp tools/ssh_setup/root-ssh-agent.sh /usr/local/bin/root-ssh-agent
sudo chmod +x /usr/local/bin/root-ssh-agent
```

Or run it directly from the repo without installing.

## Usage

```bash
sudo ./root-ssh-agent.sh start
sudo ./root-ssh-agent.sh ssh-add /root/.ssh/id_backup
sudo ./root-ssh-agent.sh ssh-add -l
sudo ./root-ssh-agent.sh status
sudo ./root-ssh-agent.sh ssh-add -d /root/.ssh/id_backup
sudo ./root-ssh-agent.sh stop
```

All commands accept `--socket PATH` to override the default socket
(`/root/.ssh/ssh-agent.sock`). Run `root-ssh-agent.sh --help` for details.

## Exit codes (start command)

| Code | Meaning |
|------|---------|
| 0 | Agent started |
| 1 | Error |
| 2 | Agent already running on this socket |
