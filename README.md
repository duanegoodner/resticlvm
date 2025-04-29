# ResticLVM

> **A config-based tool for atomic, incremental backups — powered by [Restic](https://github.com/restic/restic) and [LVM2](https://sourceware.org/lvm2/).**

## Description

ResticLVM is a Linux command-line tool that combines the snapshot features of Logical Volume Manager (LVM) with the data deduplication and encryption features of the [Restic](https://github.com/restic/restic) backup tool to create consistent, efficient backups of active systems with minimal downtime.

ResticLVM uses a simple TOML configuration file format to define backup jobs, and provides CLI commands to run backups or prune old snapshots based on configuration settings.

Interaction with Restic and LVM is handled by a set of [Bash shell scripts](src/resticlvm/scripts/README.md), while a lightweight Python wrapper orchestrates the backup flow, provides the CLI interface, and enables installation as a Python package.


## How It Works:

- 📦 Creates a timestamped LVM snapshot of each logical volume to be backed up.

- 🔒 Mounts the snapshot to a temporary mount point.

- 📤 Runs Restic to back up the mounted snapshot to the configured repository.

- 🧹 Cleans up the snapshot automatically after backup completes.

This approach ensures that backup operations are fast, safe, and do not interfere with the running system.

## Requirements
- A Linux system with Logical Volume Manager (LVM).
- Python 3.11+.
- Restic installed and available in your $PATH.
- Root privileges required (direct root user or via sudo).
- Restic repositories must be manually created (using `restic init`) before using ResticLVM.


## Installing

The recommended way to install ResticLVM is to download the .whl file from the [latest GitHub release](https://github.com/duanegoodner/resticlvm/releases/latest), then install it using pip:

```
pip install /path/to/resticlvm-<latest_version>-py3-none-any.whl
```

This installs the CLI tools:

- `rlvm-backup` — Run backup jobs as defined in your configuration file.

- `rlvm-prune` —  Prune Restic snapshots according to the retention settings in your configuration.

## Config File Setup

ResticLVM is configured through a simple `.toml` file and supports three types of backup jobs:

| Backup Type                | Section Example                      | Description |
|:----------------------------|:-------------------------------------|:------------|
| Standard filesystem path    | `[standard_path.boot]`               | Back up a normal directory (e.g., `/boot`) |
| LVM volume (mounted at `/`)  | `[logical_volume_root.lv_root]`      | Back up an LVM logical volume that is mounted at root |
| LVM volume (mounted elsewhere) | `[logical_volume_nonroot.data]`    | Back up an LVM volume mounted at another location (e.g., `/data`) |


### Backup Job Category and Name Hierarchy

Each section must be named according to this pattern:
```
<backup_category>.<job_name>
```
Where:

- `<backup_category>` must be one of:

    - `standard_path` — for regular file or directory paths.

    - `logical_volume_root` — for full logical volumes mounted at /.

    - `logical_volume_nonroot` — for logical volumes mounted elsewhere.

- `<job_name>` is a user-chosen identifier for that backup job (any valid name without spaces).


### Example `.toml` File

The example below shows one job configuration for each of the three supported categories. All fields shown for each category of job are required (Note that the fields required for a `standard_path` backup job differ from those required for `logical_volume_root` and `logical_volume_nonroot` jobs).



```toml
[standard_path.boot]
backup_source_path = "/boot"
restic_repo = "/backups/restic-boot"
restic_password_file = "/path/to/repopassword.txt"
exclude_paths = []
remount_readonly = true
prune_keep_last = 10
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1

[logical_volume_root.lv_root]
vg_name = "vg0"
lv_name = "lv0"
snapshot_size = "5G"
restic_repo = "/backups/restic-root"
restic_password_file = "/path/to/repopassword.txt"
backup_source_path = "/"
exclude_paths = [
  "/dev", "/proc", "/sys", "/tmp", "/var/tmp", "/run", "/media", "/mnt"
]
prune_keep_last = 10
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1

[logical_volume_nonroot.data]
vg_name = "vg_data"
lv_name = "lv_data"
snapshot_size = "5G"
restic_repo = "/backups/restic-data"
restic_password_file = "/path/to/repopassword.txt"
backup_source_path = "/data"
exclude_paths = ["/data/temp", "/data/cache"]
prune_keep_last = 10
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1
```
### Notes:
- `snapshot_size` must be large enough to capture any changes that occur to the original logical volume during the backup. A small snapshot size can lead to backup failure if the snapshot overflows.

- `exclude_paths` is a space-separated list (within the TOML array) of paths that will be excluded from the backup.

- `remount_readonly` applies only to standard_path backups; if true, the backup source will be temporarily remounted read-only during the backup.

- Each backup job must use a unique `restic_repo` path. Duplicate repositories across jobs are not allowed because Restic pruning operates at the repository level.

- The Restic repositories must already exist. (Use `restic init` manually to create each repo before using this tool.)


## Running Backups

### 🔹 Run all backup jobs:
```
rlvm-backup --config /path/to/your/resticlvm_config.toml
```
- Runs **all** backup jobs defined in the config.

- Automatically handles snapshots, bindings, Restic commands, and cleanup.

### 🔹 Run a Specific Backup Job
The `--category` and/or `--name` options can be used if we only want to run certain backup jobs.
```
# Run all jobs in a category
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path

# Run a single specific job
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path --name boot
```

## Pruning Snapshots

### 🔹Prune All Configured Repositories

```
rlvm-prune --config /path/to/your/resticlvm_config.toml
```
- Applies the configured prune_keep_* settings to each Restic repo.

- Handles Restic's `forget` and `--prune` commands.

### 🔹 Prune by Category or Job Name

We can also choose to prune only certain repos:
```
# Prune by category
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root

# Prune by specific job name
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root --name lv_root
```

### 🔹Protecting Specific Snapshots from Deletion

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

## CLI Help
To see available options for `rlvm-backup`:
```
rlvm-backup --help
```
Output:
```
usage: rlvm-backup [-h] [--dry-run] [--category CATEGORY] [--name NAME] --config CONFIG

Run backup jobs.

options:
  -h, --help           show this help message and exit
  --dry-run            Show what would be backed up without actually running
  --category CATEGORY  Only run backups of this specific category
  --name NAME          Only run backups with this specific job name
  --config CONFIG      Path to configuration TOML file
```
And to see available `rlvm-prune` options:
```
rlvm-prune --help
```
Output:
```
usage: rlvm-prune [-h] --config CONFIG [--dry-run] [--category CATEGORY] [--name NAME]

Prune restic repos.

options:
  -h, --help           show this help message and exit
  --config CONFIG      Path to config file (.toml).
  --dry-run            Show what would be pruned without actually pruning.
  --category CATEGORY  Only prune repos in this backup category.
  --name NAME          Only prune repo matching this backup job name.
```

## Project Layout

- 📄 **LICENSE** — MIT license
- 📄 **pyproject.toml** — Python package config
- 📄 **README.md** — Project overview and usage
- 📂 **src/resticlvm/**
  - 📂 **Python Modules**
    - 📄 `backup_plan.py` — Build backup jobs from config
    - 📄 `backup_runner.py` — CLI entry for backups
    - 📄 `config_loader.py` — Load TOML config
    - 📄 `data_classes.py` — Backup job dataclasses
    - 📄 `dispatch.py` — Maps config sections to scripts
    - 📄 `privileges.py` — Ensure root/sudo execution
    - 📄 `prune_runner.py` — CLI entry for pruning
    - 📄 `restic_repo.py` — Repo objects and prune ops
    - 📄 `__init__.py`
  - 📂 **Bash Scripts**
    - 📄 `backup_helpers.sh` — Import funnel for helpers
    - 📄 `backup_lv_nonroot.sh` — Backup non-root volumes
    - 📄 `backup_lv_root.sh` — Backup root volumes
    - 📄 `backup_path.sh` — Backup standard paths
    - 📄 `prune_repo.sh` — Prune repos with restic
    - 📂 **lib/**
      - 📄 `arg_handlers.sh` — Parse CLI args
      - 📄 `command_builders.sh` — Build backup commands
      - 📄 `command_runners.sh` — Run/dry-run shell commands
      - 📄 `lv_snapshots.sh` — Create and clean up snapshots
      - 📄 `message_display.sh` — Show configs/dry-run notices
      - 📄 `mounts.sh` — Mount/bind operations
      - 📄 `pre_checks.sh` — Validate environment and inputs
      - 📄 `usage_commands.sh` — CLI help output
    - 📄 `README.md` — Bash scripts overview


## Alternate Installation Methods


These methods are useful for development or direct-from-source usage.


### 1️⃣ Install from GitHub tag (source)

```
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.1.2
```
Builds the project from source at the specified Git tag (v0.1.2 in this example).


### 2️⃣ Install from a cloned repo (local source)
```
git clone https://github.com/yourusername/resticlvm.git
cd resticlvm
pip install .
```
For development mode (auto-reflects source code changes):
```
pip install -e .
```


## Contributing

Contributions, suggestions, and improvements are welcome!

If you find a bug, have a feature request, or want to submit a pull request,
please open an issue or submit a PR on GitHub.

This project aims to stay lightweight, reliable, and focused, so proposed
changes should align with those goals.

Thanks for helping improve ResticLVM!


## Links

- [Submit Issues](https://github.com/yourusername/resticlvm/issues)
- [License (MIT)](./LICENSE)
- [Restic Project (GitHub)](https://github.com/restic/restic)
- [LVM2 (Sourceware upstream)](https://sourceware.org/lvm2/)
- [LVM Guide (Fedora/Red Hat Documentation)](https://docs.fedoraproject.org/en-US/fedora/latest/system-administrators-guide/storage/LVM/)


