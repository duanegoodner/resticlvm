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

Install ResticLVM directly from GitHub using pip:

### Install a specific version (recommended)
```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.1.2
```
Replace `v0.1.2` with the desired version tag from the [releases page](https://github.com/duanegoodner/resticlvm/releases).

### Install from main branch (latest, but not guaranteed stable)
```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@main
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


### Multi-Repository Support

ResticLVM supports sending a single snapshot to **multiple repositories** simultaneously. This enables:
- 🔄 **Redundancy** — Back up to multiple local destinations
- ☁️ **Remote replication** — Copy to remote locations (SFTP, B2, S3, Azure, etc.)
- 📦 **Flexible retention** — Different prune policies per repository

#### Configuration Examples

See **[docs/test-config-examples/](docs/test-config-examples/)** for complete configuration examples covering:

- **[Single local repository](docs/test-config-examples/single-local-repo.toml)** - Simplest setup
- **[Local with remote copy](docs/test-config-examples/local-with-remote-copy.toml)** - Recommended approach
- **[Direct SFTP backup](docs/test-config-examples/direct-sftp-backup.toml)** - Direct remote backup
- **[Multiple copy destinations](docs/test-config-examples/multiple-copy-destinations.toml)** - Multi-cloud strategy
- **[And more...](docs/test-config-examples/README.md)** - See full list with descriptions

#### How `copy_to` Works

The `copy_to` feature uses `restic copy` to replicate snapshots from a source repository to remote destinations:

1. **Backup phase** — Creates LVM snapshot and backs up to all `[[repositories]]`
2. **Cleanup phase** — Removes LVM snapshot immediately (minimizes disk usage)
3. **Copy phase** — For each repository with `[[repositories.copy_to]]` destinations, copies new snapshots to those destinations
4. **Independent pruning** — Each destination can have its own retention policy

**Why use `copy_to` instead of direct remote backups?**
- ✅ **Explicit source control** — Each repository specifies its own copy destinations
- ✅ **Fast local backups** — No network delays during snapshot lifetime
- ✅ **Flexible retention** — Aggressive local pruning, conservative remote retention
- ✅ **Works with any backend** — SFTP, B2, S3, Azure, GCS, rclone, etc.
- ✅ **Fully independent repos** — Each destination is a complete, standalone restic repository

#### Configuration Structure

Each repository can have optional `[[repositories.copy_to]]` destinations:

```toml
[[logical_volume_root.root.repositories]]
repo_path = "/backups/root-local"
password_file = "/path/to/password.txt"
prune_keep_last = 7
# ... other prune settings ...

  [[logical_volume_root.root.repositories.copy_to]]
  repo = "sftp:backup@server.example.com:/backups/root"
  password_file = "/path/to/password.txt"
  prune_keep_last = 60
  # ... independent prune settings ...
```

See the **[configuration examples directory](docs/test-config-examples/)** for complete working examples.
prune_keep_yearly = 10
```

### Remote Repository Setup

For remote destinations, you'll need to configure credentials according to the backend type:

**SFTP:** See [EXAMPLE_SSH_SETUP.md](EXAMPLE_SSH_SETUP.md) for SSH key setup with passwordless authentication.

**Backblaze B2:**
```bash
export B2_ACCOUNT_ID=<your_account_id>
export B2_ACCOUNT_KEY=<your_account_key>
restic -r b2:bucket-name:path/to/repo init
```

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
- **`remount_readonly`** (standard_path only) temporarily remounts the source read-only during backup.
- **Multiple repos per job** — All `[[repositories]]` receive the same snapshot data.
- **`copy_to` destinations** — Receive copies after local backup completes.
- **All repositories must exist** — Use `restic init` to create each repo before first use.


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


## Development Setup

To set up a development environment:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/duanegoodner/resticlvm.git
   cd resticlvm
   ```

2. **Create and activate the conda environment:**
   ```bash
   conda env create -f tools/environment.yml
   conda activate resticlvm-dev
   ```

3. **Install the package in editable mode:**
   ```bash
   pip install -e .
   ```

This setup allows you to make changes to the source code and see them reflected immediately without reinstalling.


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


