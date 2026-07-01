# ResticLVM

Consistent backups of live Linux systems, using LVM snapshots and Restic.

## Description

ResticLVM is a Linux command-line tool that combines the snapshot features of Logical Volume Manager (LVM) with the data deduplication and encryption features of the [Restic](https://github.com/restic/restic) backup tool to create consistent, efficient backups of active systems, without taking the system offline.

ResticLVM uses a simple TOML configuration file format to define backup jobs, and provides CLI commands to run backups or prune old snapshots based on configuration settings.

Interaction with Restic and LVM is handled by a set of [Bash shell scripts](src/resticlvm/scripts/README.md), while a lightweight Python wrapper orchestrates the backup flow, provides the CLI interface, and enables installation as a Python package.

## Table of Contents

- [How It Works](#how-it-works)
- [Design Notes](#design-notes)
- [Status and Known Limitations](#status-and-known-limitations)
- [Requirements](#requirements)
- [Quickstart](#quickstart)
- [Getting Started](#getting-started)
- [Additional Details for Running](#additional-details-for-running)
- [Alternate Installation Methods](#alternate-installation-methods)
- [CLI Help](#cli-help)
- [Helper Tools](#helper-tools)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Links](#links)

## How It Works

ResticLVM backs up **LVM logical volumes** from a temporary snapshot, a consistent point-in-time copy of an actively-used filesystem:

- Creates a timestamped LVM snapshot of each logical volume to be backed up.
- Mounts the snapshot read-only at a temporary mount point.
- Runs Restic to back up the mounted snapshot to the configured repository(ies).
- Cleans up the snapshot after the backup completes.

It also backs up **regular partitions** (e.g. `/boot`, `/boot/efi`) directly, without a snapshot. Snapshotting keeps LVM backups consistent without interrupting the running system.

## Design Notes

A few design choices worth calling out:

- **Consistent point-in-time snapshots.** Each LVM volume is backed up from a snapshot taken at a single instant, so files that change during a long backup are captured as they were at the start, not smeared across the run, while the system keeps running.
- **Full-system coverage, including the live root.** Backs up regular partitions (e.g. `/boot`, `/boot/efi`) and LVM volumes, *including* the `/`-mounted root logical volume, handled transparently via snapshot + chroot. A running root filesystem is the hard case that simpler tools often skip.
- **Declarative, multi-destination config.** One TOML file describes every source and its repositories; each repository (and each `copy_to` copy) carries its own independent retention policy.
- **Direct vs. `copy_to` tradeoff.** Back up directly from the snapshot, or copy to a remote repo *after* the snapshot is released, minimizing snapshot lifetime on busy systems (see [Data Transfer Methods](#data-transfer-methods)).
- **Exit-code observability.** A run exits non-zero if any job or copy fails and prints an unmissable end-of-run summary, so cron, systemd `OnFailure=`, and heartbeat alerting behave as expected. A failed job is reported but does not abort the others.
- **Thin Python over Bash.** A small Python layer handles config, orchestration, and the CLI; the LVM/Restic mechanics live in focused, testable shell scripts.

## Status and Known Limitations

ResticLVM is pre-1.0. One limitation is worth knowing before you rely on it:

- **Run attended for now.** If a backup fails mid-run, the LVM snapshot and its mounts may be left behind. Cleanup-on-failure is not yet automatic (tracked in [#24](https://github.com/duanegoodner/resticlvm/issues/24)). Until that lands, run ResticLVM manually/attended rather than fully unattended on a schedule, and see [Troubleshooting](#troubleshooting) for cleanup steps. The exit-code and end-of-run summary behavior makes such failures easy to detect.

## Requirements
- A Linux system with Logical Volume Manager (LVM).
- Python 3.11+.
- Restic installed and available in your $PATH.
- Root privileges required (direct root user or via sudo).
- Restic repositories must be created (following procedures in [restic docs](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#)) before using ResticLVM.
- For remote repositories: Authentication must be configured for automated access (e.g., SSH keys for SFTP, environment variables for cloud storage). See [Remote Repository Setup](#remote-repository-setup) for details.


## Quickstart

A minimal end-to-end example that backs up the `/home` logical volume to a local Restic repository:

```bash
# 1. Install
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.5.0

# 2. Create a password file and initialize the Restic repository (one-time)
sudo mkdir -p /root/.config/resticlvm/repo-creds
echo "choose-a-strong-passphrase" | sudo tee /root/.config/resticlvm/repo-creds/home.txt > /dev/null
sudo chmod 600 /root/.config/resticlvm/repo-creds/home.txt
sudo restic init --repo /srv/backup/home \
  --password-file /root/.config/resticlvm/repo-creds/home.txt

# 3. Write a config (backup.toml), adjusting vg_name/lv_name to your system
cat > backup.toml <<'EOF'
[logical_volume_nonroot.home]
vg_name = "vg0"
lv_name = "lv_home"
snapshot_size = "2G"
backup_source_path = "/home"
exclude_paths = []

  [[logical_volume_nonroot.home.repositories]]
  repo_path = "/srv/backup/home"
  password_file = "/root/.config/resticlvm/repo-creds/home.txt"
  prune_keep_last = 7
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 3
  prune_keep_yearly = 1
EOF

# 4. Preview, then run (must be root)
sudo rlvm backup --config backup.toml --dry-run
sudo rlvm backup --config backup.toml
```

For the full configuration reference (multiple/remote/cloud repositories, `copy_to`, root and standard-partition backups), see [Config File Setup](#config-file-setup).


## Getting Started

### Installing

Install the latest release directly from GitHub:

```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.5.0
```

This installs the CLI tools:

- `rlvm backup`: Run backup jobs as defined in your configuration file.

- `rlvm prune`: Prune Restic snapshots according to the retention settings in your configuration.

For other installation methods, see [Alternate Installation Methods](#alternate-installation-methods).


### What Can Be Backed Up

ResticLVM supports backing up both **LVM logical volumes** and **regular filesystem partitions**:

- **LVM logical volumes**: ResticLVM creates a temporary snapshot of the logical volume, mounts it, backs up from the snapshot, then automatically removes it. This ensures backup consistency even for actively-used filesystems. (Note: LVM volumes mounted at `/` require special handling internally, but this is transparent to the user.)

- **Regular partitions**: ResticLVM can back up any mounted partition (e.g., `/boot`, `/boot/efi`) directly without creating a snapshot. The partition remains mounted read-write during backup.

> **⚠️ Note on Regular Partition Backups:** Unlike LVM backups, regular partition backups are not atomic. Earlier versions of ResticLVM supported remounting these partitions as read-only during backup, but this feature was removed because having an in-use partition mounted read-only can cause system problems, particularly during critical operations like kernel or bootloader updates.

### Config File Setup

ResticLVM is configured through a simple `.toml` file.

#### Example Configuration

Consider a common UEFI system layout with one disk and LVM:

```
/dev/vda
├── vda1  →  /boot/efi (EFI System Partition)
├── vda2  →  /boot (standard partition)
└── vda3  →  Physical Volume in vg0
    └── vg0 (Volume Group)
        ├── lv_root  →  / (root filesystem)
        └── lv_home  →  /home (user data)
```

This example demonstrates **four backup destinations** per volume using a combination of strategies:

1. **Local repository**: Fast backups and quick recovery
2. **Copy to SFTP**: Local repo copied to remote ([see below](#data-transfer-methods) for details on `copy_to`)
3. **Direct SFTP**: Direct backup to different remote path
4. **Direct B2 cloud**: Direct backup to offsite cloud storage

```toml
# /boot/efi partition (EFI System Partition)
[standard_path.boot-efi]
backup_source_path = "/boot/efi"
exclude_paths = []

  [[standard_path.boot-efi.repositories]]
  repo_path = "/path/to/boot-efi-repo"
  password_file = "/path/to/boot-efi-repo-password.txt"
  prune_keep_last = 7
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 3
  prune_keep_yearly = 1

    # Optional: Copy to another repo after local backup completes
    [[standard_path.boot-efi.repositories.copy_to]]
    repo = "sftp:backupuser@backup.example.com:/backups/hostname/boot-efi-copy"
    password_file = "/path/to/boot-efi-repo-password.txt"
    prune_keep_last = 30
    prune_keep_daily = 30
    prune_keep_weekly = 12
    prune_keep_monthly = 12
    prune_keep_yearly = 3

  [[standard_path.boot-efi.repositories]]
  repo_path = "sftp:backupuser@backup.example.com:/backups/hostname/boot-efi"
  password_file = "/path/to/boot-efi-repo-password.txt"
  prune_keep_last = 30
  prune_keep_daily = 30
  prune_keep_weekly = 12
  prune_keep_monthly = 12
  prune_keep_yearly = 3

  [[standard_path.boot-efi.repositories]]
  repo_path = "s3:s3.us-west-004.backblazeb2.com/bucket-name/hostname/boot-efi"
  password_file = "/path/to/boot-efi-repo-password.txt"
  prune_keep_last = 14
  prune_keep_daily = 14
  prune_keep_weekly = 8
  prune_keep_monthly = 6
  prune_keep_yearly = 2

# /boot partition (kernel and initramfs)
[standard_path.boot]
backup_source_path = "/boot"
exclude_paths = []

  [[standard_path.boot.repositories]]
  repo_path = "/path/to/boot-repo"
  password_file = "/path/to/boot-repo-password.txt"
  prune_keep_last = 7
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 3
  prune_keep_yearly = 1

    # Optional: Copy to another repo after local backup completes
    [[standard_path.boot.repositories.copy_to]]
    repo = "sftp:backupuser@backup.example.com:/backups/hostname/boot-copy"
    password_file = "/path/to/boot-repo-password.txt"
    prune_keep_last = 30
    prune_keep_daily = 30
    prune_keep_weekly = 12
    prune_keep_monthly = 12
    prune_keep_yearly = 3

  [[standard_path.boot.repositories]]
  repo_path = "sftp:backupuser@backup.example.com:/backups/hostname/boot"
  password_file = "/path/to/boot-repo-password.txt"
  prune_keep_last = 30
  prune_keep_daily = 30
  prune_keep_weekly = 12
  prune_keep_monthly = 12
  prune_keep_yearly = 3

  [[standard_path.boot.repositories]]
  repo_path = "s3:s3.us-west-004.backblazeb2.com/bucket-name/hostname/boot"
  password_file = "/path/to/boot-repo-password.txt"
  prune_keep_last = 14
  prune_keep_daily = 14
  prune_keep_weekly = 8
  prune_keep_monthly = 6
  prune_keep_yearly = 2

# Root filesystem (LVM logical volume mounted at /)
[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys", "/tmp", "/var/tmp", "/run"]

  [[logical_volume_root.root.repositories]]
  repo_path = "/path/to/root-repo"
  password_file = "/path/to/root-repo-password.txt"
  prune_keep_last = 7
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 3
  prune_keep_yearly = 1

    # Optional: Copy to another repo after local backup completes
    [[logical_volume_root.root.repositories.copy_to]]
    repo = "sftp:backupuser@backup.example.com:/backups/hostname/root-copy"
    password_file = "/path/to/root-repo-password.txt"
    prune_keep_last = 30
    prune_keep_daily = 30
    prune_keep_weekly = 12
    prune_keep_monthly = 12
    prune_keep_yearly = 3

  [[logical_volume_root.root.repositories]]
  repo_path = "sftp:backupuser@backup.example.com:/backups/hostname/root"
  password_file = "/path/to/root-repo-password.txt"
  prune_keep_last = 30
  prune_keep_daily = 30
  prune_keep_weekly = 12
  prune_keep_monthly = 12
  prune_keep_yearly = 3

  [[logical_volume_root.root.repositories]]
  repo_path = "s3:s3.us-west-004.backblazeb2.com/bucket-name/hostname/root"
  password_file = "/path/to/root-repo-password.txt"
  prune_keep_last = 14
  prune_keep_daily = 14
  prune_keep_weekly = 8
  prune_keep_monthly = 6
  prune_keep_yearly = 2

# /home filesystem (LVM logical volume mounted elsewhere)
[logical_volume_nonroot.home]
vg_name = "vg0"
lv_name = "lv_home"
snapshot_size = "2G"
backup_source_path = "/home"
exclude_paths = []

  [[logical_volume_nonroot.home.repositories]]
  repo_path = "/path/to/home-repo"
  password_file = "/path/to/home-repo-password.txt"
  prune_keep_last = 7
  prune_keep_daily = 7
  prune_keep_weekly = 4
  prune_keep_monthly = 3
  prune_keep_yearly = 1

    # Optional: Copy to another repo after local backup completes
    [[logical_volume_nonroot.home.repositories.copy_to]]
    repo = "sftp:backupuser@backup.example.com:/backups/hostname/home-copy"
    password_file = "/path/to/home-repo-password.txt"
    prune_keep_last = 30
    prune_keep_daily = 30
    prune_keep_weekly = 12
    prune_keep_monthly = 12
    prune_keep_yearly = 3

  [[logical_volume_nonroot.home.repositories]]
  repo_path = "sftp:backupuser@backup.example.com:/backups/hostname/home"
  password_file = "/path/to/home-repo-password.txt"
  prune_keep_last = 30
  prune_keep_daily = 30
  prune_keep_weekly = 12
  prune_keep_monthly = 12
  prune_keep_yearly = 3

  [[logical_volume_nonroot.home.repositories]]
  repo_path = "s3:s3.us-west-004.backblazeb2.com/bucket-name/hostname/home"
  password_file = "/path/to/home-repo-password.txt"
  prune_keep_last = 14
  prune_keep_daily = 14
  prune_keep_weekly = 8
  prune_keep_monthly = 6
  prune_keep_yearly = 2
```

### Running

Run all backup jobs defined in a config (ResticLVM must run as root):

```bash
sudo rlvm backup --config /path/to/your/backup-config.toml
```

Preview what would happen, without writing any backups, using `--dry-run`:

```bash
sudo rlvm backup --config /path/to/your/backup-config.toml --dry-run
```

See [below](#running-specific-jobs-from-config-file) for running specific (not all) jobs from a config file.

> **⚠️ If a run fails,** ResticLVM may leave behind an LVM snapshot and its mounts; cleanup-on-failure isn't automatic yet (see [Status and Known Limitations](#status-and-known-limitations)). Check with `sudo lvs | grep snapshot` and `mount | grep resticlvm`, and see [Troubleshooting](#troubleshooting) for cleanup steps.

## Additional Details for Running

### Config File Structure

ResticLVM configuration files use TOML format with the following hierarchical structure:

```toml
[<volume_type>.<volume_id>]
backup_source_path = "/path/to/source"
# ... other volume-specific settings ...

  [[<volume_type>.<volume_id>.repositories]]
  repo_path = "/path/to/local-repo"
  password_file = "/path/to/password.txt"
  # ... prune settings ...

    [[<volume_type>.<volume_id>.repositories.copy_to]]
    repo = "sftp:user@host:/remote/repo"
    password_file = "/path/to/password.txt"
    # ... independent prune settings ...
```

**Structure components:**

- **`[<volume_type>.<volume_id>]`**: Top-level section defining the volume to back up
  - `<volume_type>` specifies the type of volume:
    - `standard_path`: Standard filesystem path (e.g., `/boot`, `/boot/efi`)
    - `logical_volume_root`: LVM logical volume mounted at `/`
    - `logical_volume_nonroot`: LVM logical volume mounted elsewhere (e.g., `/home`, `/data`)
  - `<volume_id>` is your chosen identifier for that specific volume (any valid name without spaces)

- **`[[<volume_type>.<volume_id>.repositories]]`**: Direct backup destination (can have multiple)
  - Defines where to send backups directly from the source

- **`[[<volume_type>.<volume_id>.repositories.copy_to]]`**: Copy destination (can have multiple per repository)
  - Copies snapshots from the parent repository after backup completes


### Running Specific Jobs from Config File

The `--category` and/or `--name` options can be used if we only want to run some (not all) of the backup jobs specified in a .toml file.

```
# Run all jobs in a category
sudo rlvm backup --config /path/to/resticlvm_config.toml --category standard_path

# Run a single specific job
sudo rlvm backup --config /path/to/resticlvm_config.toml --category standard_path --name boot
```

### Data Transfer Methods

ResticLVM supports two methods for transferring data to backup repositories:

1. **Direct backup from source**: Restic reads directly from the backup source (mounted LVM snapshot or filesystem) and sends data to the repository. In the example above, this is used for the local repos and the direct SFTP and B2 destinations.

2. **Copy from existing repository**: Restic copies snapshots from one repository to another using `restic copy`. In the example above, this is used for the `boot-efi-copy`, `boot-copy`, `root-copy`, and `home-copy` destinations (configured via `[[repositories.copy_to]]` blocks).

**Pros and cons of each approach:**

- **Direct backups** provide detailed real-time output during the backup process, making troubleshooting easier. However, the LVM snapshot must remain mounted for the entire duration of the backup, which can be lengthy for large volumes or slow network connections.

- **`copy_to`** releases LVM snapshots faster since copying happens *after* snapshot cleanup. This minimizes snapshot lifetime, which matters for systems with high write activity or when backing up large volumes over slow connections. The tradeoff is less detailed output during the copy phase.

You can add `copy_to` destinations under *any* repository entry (local or remote). Each `copy_to` destination is a fully independent restic repository with its own retention policy; it does not need to match the pruning settings of the source repository. For simplicity, choose **either** direct backup **or** `copy_to` for each specific destination. Using both to the same location is redundant.


### Remote Repository Setup

For remote destinations, you'll need to configure credentials according to the backend type:

**SFTP:** See [docs/EXAMPLE_SSH_SETUP.md](docs/EXAMPLE_SSH_SETUP.md) for SSH key setup with passwordless authentication.

**Backblaze B2 (S3-Compatible, recommended):**
```bash
export AWS_ACCESS_KEY_ID=<your_key_id>
export AWS_SECRET_ACCESS_KEY=<your_secret_key>
restic -r s3:s3.us-west-004.backblazeb2.com/bucket-name/path init
```

For automated runs you don't need to export these yourself: when a config contains
a B2 (`s3:`) repo, `rlvm backup` loads `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
from `/root/.config/resticlvm/b2-env` automatically (credentials already in the
environment take precedence). Backups to non-B2 repos run fine with no credentials
present.

See [docs/EXAMPLE_B2_SETUP.md](docs/EXAMPLE_B2_SETUP.md) for detailed B2 configuration.

**Backblaze B2 (Native - Not Recommended):**
```bash
export B2_ACCOUNT_ID=<your_account_id>
export B2_ACCOUNT_KEY=<your_app_key>
restic -r b2:bucket-name:path/to/repo init
```
Note: Native B2 API has error handling issues. Use S3-compatible instead.

**Amazon S3:**
```bash
export AWS_ACCESS_KEY_ID=<your_key_id>
export AWS_SECRET_ACCESS_KEY=<your_secret_key>
restic -r s3:s3.amazonaws.com/bucket-name init
```

See [Restic documentation](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html) for other backends.

### Configuration Notes

- **`snapshot_size`** must be large enough to capture changes during backup. Overflow causes backup failure.
- **`exclude_paths`** is a TOML array of paths to exclude from backup.
- **Multiple repos per job**: All `[[repositories]]` receive the same snapshot data.
- **`copy_to` destinations**: Receive copies after local backup completes.
- **All repositories must exist**: Use `restic init` to create each repo before first use.


### Pruning Snapshots

#### Prune All Configured Repositories

```bash
sudo rlvm prune --config /path/to/your/resticlvm_config.toml
```
- Applies the configured prune_keep_* settings to each Restic repo.

- Handles Restic's `forget` and `--prune` commands.

#### Prune by Category or Job Name

We can also choose to prune only certain repos:
```
# Prune by category
sudo rlvm prune --config /path/to/resticlvm_config.toml --category logical_volume_root

# Prune by specific job name
sudo rlvm prune --config /path/to/resticlvm_config.toml --category logical_volume_root --name lv_root
```

#### Protecting Specific Snapshots from Deletion

By default, all snapshots are subject to pruning according to your configured retention policies.

If you want to permanently protect a particular snapshot from being pruned:

1. List your current snapshots to find the snapshot ID:

   ```bash
   restic -r /path/to/restic-repo --password-file /path/to/password/file snapshots
   ```
2. Tag the snapshot you want to protect:

    ```
    restic tag --add protected --snapshot <snapshot-ID>
    ```
Snapshots tagged protected will automatically be preserved during pruning, regardless of age or retention rules. ResticLVM's pruning logic uses --keep-tag protected to ensure these snapshots are not deleted.

### Alternate Installation Methods

#### Install a Specific Version

Replace the version tag with any release from the [releases page](https://github.com/duanegoodner/resticlvm/releases):

```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.5.0
```

#### Install from Main Branch

Install the latest development version (not guaranteed stable):

```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@main
```

#### Install with Optional Dependencies

Install with B2 CLI support for Backblaze B2 management:

```bash
pip install "git+https://github.com/duanegoodner/resticlvm.git@v0.5.0#egg=resticlvm[b2]"
```

Install with development tools (pytest):

```bash
pip install "git+https://github.com/duanegoodner/resticlvm.git@v0.5.0#egg=resticlvm[dev]"
```

Install with both B2 and development dependencies:

```bash
pip install "git+https://github.com/duanegoodner/resticlvm.git@v0.5.0#egg=resticlvm[dev,b2]"
```

#### Clone and Install in Development Mode

For making changes to the source code:

```bash
# Clone the repository
git clone https://github.com/duanegoodner/resticlvm.git
cd resticlvm

# Install in editable mode
pip install -e .

# Or with optional dependencies
pip install -e ".[dev,b2]"
```

Changes to the source code are reflected immediately without reinstalling.

> For the **preferred pixi-based dev workflow**, and important editable-install
> gotchas (`--version` reporting and `pixi.lock` handling), see
> [Development](#development).

### CLI Help

Both commands accept `--config`, `--category`, `--name`, `--dry-run`, `--version`, and
`--help`. `--help` and `--version` work without root; running an actual backup or prune
requires root.

```bash
rlvm backup --help      # full option list
rlvm backup --version   # print the installed version (no root needed)
rlvm prune --help
```

## Helper Tools

ResticLVM includes various helper scripts in the [tools/](tools/) directory for repository initialization, SSH setup, B2 cloud storage integration, and release building.

Each subdirectory contains its own README with detailed instructions:

- **[b2/](tools/b2/)** - Backblaze B2 helper scripts for backups and repository management
- **[release/](tools/release/)** - Build and packaging tools
- **[ssh_setup/](tools/ssh_setup/)** - SSH agent management for automated backups

For more information, see [tools/README.md](tools/README.md).

## Development

### Preferred dev env management: pixi

Development and testing use a [pixi](https://pixi.sh) workspace (defined in
`pixi.toml`) rather than conda/venv. It provisions Python plus the dev tools
(`pytest`, `shellcheck`, `python-build`) and installs ResticLVM itself in **editable
mode**, so source changes are picked up without reinstalling.

```bash
pixi install        # create/refresh the env from pixi.toml + pixi.lock
pixi run test       # run the test suite (python -m pytest)
pixi shell          # drop into an activated shell (leave with: exit)
```

The editable install is declared in `pixi.toml`:

```toml
[pypi-dependencies]
resticlvm = { path = ".", editable = true }
```

#### Working with `pixi.lock`

`pixi.lock` is a **generated file that we commit** for reproducible environments.
Pixi rewrites it whenever it re-solves (`pixi install` / `pixi update`), so a stray
`modified: pixi.lock` is normal. Treat the committed version as the source of truth:

- If you **changed dependencies** (edited `pixi.toml`), commit the updated `pixi.lock`.
- If you **didn't** intend a dependency change (a pixi command just rewrote it),
  discard it, especially before pulling:
  ```bash
  git restore pixi.lock   # then: git pull
  ```
- On a machine you only *run* backups on (not develop), you'll almost always want to
  discard local `pixi.lock` churn and take what's in the repo.

#### `--version` can lag in an editable install

`rlvm backup --version` reads the package *metadata* snapshot written at install
time, **not** `pyproject.toml`. After a version bump, a `git pull` updates the code
but not that snapshot, and `pixi install` / `pixi update` won't refresh it either.
Force a full rebuild:

```bash
rm -rf .pixi src/resticlvm.egg-info && pixi install
```

The running *code* is always current; only the printed number lags. (A real
`pip install <wheel>` deployment always reports correctly.)

#### Running as root from the pixi env

`sudo` resets `PATH`, so `sudo rlvm backup …` may report "command not found" even
when `rlvm` works without `sudo`. Pin the absolute path:

```bash
sudo "$(command -v rlvm)" backup --config /path/to/config.toml
```

### LVM Test VM

For testing ResticLVM without modifying your local system's LVM configuration, use the included Infrastructure-as-Code (IaC) in `dev/vm-builder/` to build and deploy a Debian 13 test VM with LVM already configured.

Supported platforms:
- **Local:** QEMU/KVM virtual machine
- **AWS:** EC2 instance

The VM comes pre-configured with:
- LVM root filesystem with multiple logical volumes
- Standard `/boot` and `/boot/efi` partitions
- Filesystem structure ready for testing ResticLVM backup scenarios

For detailed instructions, see [dev/vm-builder/README.md](dev/vm-builder/README.md).


## Troubleshooting

### Cleaning Up After Failed Backups

If a backup fails (e.g., due to network issues, incorrect credentials, or insufficient disk space), ResticLVM may leave behind LVM snapshots and temporary mount points. These must be cleaned up manually.

#### Identifying Leftover Resources

Check for lingering LVM snapshots:
```bash
sudo lvs | grep snapshot
```

Check for mounted snapshots:
```bash
mount | grep resticlvm
```

Check for temporary directories:
```bash
ls -la /tmp/ | grep resticlvm
```

#### Cleanup Procedure

**1. Unmount all ResticLVM mounts** (in reverse order, deepest paths first):

```bash
# List all mounts
mount | grep resticlvm | awk '{print $3}' | sort -r

# Unmount each one (or use a loop)
sudo umount /tmp/resticlvm-TIMESTAMP/path/to/mount
```

For root volume snapshots with multiple bind mounts, you may need to unmount several paths:
```bash
# Example: unmount all mounts under a specific snapshot directory
for mount in $(mount | grep '/tmp/resticlvm-TIMESTAMP/vg0_lv_root_snapshot_TIMESTAMP' | awk '{print $3}' | sort -r); do
    sudo umount "$mount"
done
```

**2. Remove snapshot logical volumes:**

```bash
# List snapshots to identify volume group and snapshot names
sudo lvs | grep snapshot

# Remove each snapshot (adjust VG and LV names as needed)
sudo lvremove -f /dev/VG_NAME/SNAPSHOT_NAME
```

Example:
```bash
sudo lvremove -f /dev/vg0/vg0_lv_root_snapshot_20260114_185220
sudo lvremove -f /dev/vg2/vg2_lv_data_snapshot_20260114_185221
```

**3. Remove temporary directories:**

```bash
sudo rm -rf /tmp/resticlvm-*
```

**⚠️ Important:** Only remove `/tmp/resticlvm-*` directories if you're certain no backups are currently running.

#### Prevention

To minimize cleanup issues:
- Verify repository paths and credentials before running backups
- Test configurations with `--dry-run` first
- Ensure sufficient disk space for snapshots
- Monitor backup logs for errors


## Contributing

Contributions, suggestions, and improvements are welcome!

If you find a bug, have a feature request, or want to submit a pull request,
please open an issue or submit a PR on GitHub.

This project aims to stay lightweight, reliable, and focused, so proposed
changes should align with those goals.

Thanks for helping improve ResticLVM!


## Links

- [Submit Issues](https://github.com/duanegoodner/resticlvm/issues)
- [License (MIT)](./LICENSE)
- [Restic Project (GitHub)](https://github.com/restic/restic)
- [LVM2 (Sourceware upstream)](https://sourceware.org/lvm2/)
- [LVM Guide (Fedora/Red Hat Documentation)](https://docs.fedoraproject.org/en-US/fedora/latest/system-administrators-guide/storage/LVM/)


