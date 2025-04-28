# ResticLVM

## Description

ResticLVM is a command-line tool that coordinates the use of [Restic](https://github.com/restic/restic) and LVM snapshots for consistent, atomic backups.

It automates the creation of temporary LVM snapshots to capture a point-in-time view of a filesystem, and then runs Restic to perform the backup. Backups can be local or remote and benefit from Restic's built-in encryption, deduplication, and compression.

ResticLVM uses a simple TOML configuration file format to define backup jobs, and provides CLI commands to run backups or prune old snapshots based on configuration settings.

Interaction with Restic and LVM is handled by bash shell scripts. A Python wrapper provides the CLI and enables installation as a Python package. 


## Requirements
- A Linux system with Logical Volume Manager (LVM) 
- Python 3.11+
- Restic installed and available in your $PATH
- Root privileges required (scripts will request sudo if necessary)
- Existing Restic repositories:  
Repositories need to be manually created (using `restic init`) before using ResticLVM.

## Installing
```
pip install resticlvm
```
After installation, the following CLI commands will be available:

- `rlvm-backup` — Run configured backup jobs

- `rlvm-prune` — Prune Restic snapshots according to your config


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

The example below shows one job configuration for each of the three supported categories. All fields shown for each category of job are required (Note that the fields required for a `standard_path` backup job differ from those required for `logical_volume_root` and `logical_volume_nonroot` jobs.



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

- The Restic repositories must already exist. (Use restic init manually to create each repo before using this tool.)


## CLI Usage

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

### 🔹 Prune Old Snapshots
```
rlvm-prune --config /path/to/your/resticlvm_config.toml
```
- Applies the configured prune_keep_* settings to each Restic repo.

- Handles Restic's `forget` and `--prune` commands.

We can also choost to prune only certain repos:
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

