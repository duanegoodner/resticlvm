# ResticLVM

## Description
ResticLVM is a simple and flexible tool that orchestrates Restic and LVM to enable safe, atomic backups.

By automatically creating LVM snapshots, ResticLVM ensures that every backup captures a consistent, point-in-time state of your filesystem — even when the system is live and actively changing.
It then uses Restic to handle the actual backup: encrypted, deduplicated, efficient, and optionally stored remotely over SFTP.

ResticLVM provides a friendly command-line interface (CLI) and a clean TOML configuration file format to streamline backup operations.

> [!NOTE]
> ResticLVM is not a replacement for Restic itself.
It automates the creation of atomic LVM snapshots and organizes Restic operations in a simple, configuration-driven way — allowing you to fully leverage Restic’s built-in capabilities like encryption, remote storage, and snapshot management.

## Features

- 🔒 Atomic Backups:
Use LVM snapshots to guarantee a consistent view of your filesystem at the moment of backup.

- 📦 Flexible Backup Targets:
Back up entire LVM volumes, specific subpaths inside logical volumes, or standard filesystem paths (like /boot).

- ⚡ Restic Integration:
Automate Restic’s powerful encryption, deduplication, compression, and remote backup features.

- 📂 Config-Driven Workflow:
Define all backup jobs and pruning rules in a single .toml configuration file.
Configuration options allow you to:

    - Set dry-run mode for safe testing

    - Specify Restic retention policies (prune settings)

    - Use local or remote SFTP repositories

    - Customize paths to exclude from backups

- 🛠️ Simple Command Line Interface:
Install via pip, then run:

    - `rlvm-backup` to back up all configured targets

    - `rlvm-prune` to prune old Restic snapshots based on your retention settings

🔑 Secure Password Handling:
Repositories are secured using external password files you manage.


## Requirements
- Python 3.11+
- Restic installed and available in your $PATH
- LVM tools available (lvcreate, lvremove, etc.) for snapshot creation
- Root privileges required (scripts will request sudo if necessary)
- Existing Restic repositories:  
You must manually create your Restic repositories (restic init) before using ResticLVM.

## Installing
```
pip install resticlvm
```
After installation, the following CLI commands will be available:

- `rlvm-backup` — Run configured backup jobs

- `rlvm-prune` — Prune Restic snapshots according to your config


## Config File Setup

ResticLVM is configured through a simple `.toml` file.
You can organize backup jobs into three types:

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

> [!IMPORTANT]
> - You must create your Restic repositories manually before using `resticlvm` (e.g., with `restic init`).
> - Each backup job must point to a unique Restic repository.  
(Having multiple jobs share a repo is not supported and will raise an error.)

## CLI Usage

### 🔹 Run all backup jobs:
```
rlvm-backup --config /path/to/your/resticlvm_config.toml
```
- Runs **all** backup jobs defined in the config.

- Automatically handles snapshots, bindings, Restic commands, and cleanup.

### 🔹 Run a Specific Backup Job
You can target just a specific *category* or even a *single job*:
```
# Run all jobs in a category
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path

# Run a single specific job
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path --name boot
```

### 🔹 Prune Old Snapshots
```
rlvm-prune --config /path/to/your/resticlvm_config.toml
```
- Applies your configured prune_keep_* settings to each Restic repo.

- Handles Restic's `forget` and `--prune` commands.
You can also prune only certain repos:
```
# Prune by category
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root

# Prune by specific job name
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root --name lv_root

```



### 🔹 CLI Help
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
  --dry-run            Dry run mode
  --category CATEGORY  Only run specific category
  --name NAME          Only run specific job name
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
  --config CONFIG      Path to config file (.toml)
  --dry-run            Show what would be pruned without actually pruning
  --category CATEGORY  Only prune repos in this backup category 
  --name NAME          Only prune repo matching this backup job name.
```

