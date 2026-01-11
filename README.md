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
- Restic repositories must be created (following procedures in [restic docs](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#)) before using ResticLVM.
- For remote repositories: Authentication must be configured for automated access (e.g., SSH keys for SFTP, environment variables for cloud storage). See [Remote Repository Setup](#remote-repository-setup) for details.


## Getting Started

### Installing

Install ResticLVM directly from GitHub using pip:

#### Install a specific version (recommended)
```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@v0.1.2
```
Replace `v0.1.2` with the desired version tag from the [releases page](https://github.com/duanegoodner/resticlvm/releases).

#### Install from main branch (latest, but not guaranteed stable)
```bash
pip install git+https://github.com/duanegoodner/resticlvm.git@main
```

This installs the CLI tools:

- `rlvm-backup` — Run backup jobs as defined in your configuration file.

- `rlvm-prune` —  Prune Restic snapshots according to the retention settings in your configuration.

### Config File Setup

ResticLVM is configured through a simple `.toml` file and supports three types of backup jobs:

| Backup Type                | Section Example                      | Description |
|:----------------------------|:-------------------------------------|:------------|
| Standard filesystem path    | `[standard_path.boot]`               | Back up a normal directory (e.g., `/boot`) |
| LVM volume (mounted at `/`)  | `[logical_volume_root.lv_root]`      | Back up an LVM logical volume that is mounted at root |
| LVM volume (mounted elsewhere) | `[logical_volume_nonroot.data]`    | Back up an LVM volume mounted at another location (e.g., `/home`) |

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

1. **Local repository** — Fast backups and quick recovery
2. **Copy to SFTP** — Local repo copied to remote ([see below](#data-transfer-methods) for details on `copy_to`)
3. **Direct SFTP** — Direct backup to different remote path
4. **Direct B2 cloud** — Direct backup to offsite cloud storage

```toml
# /boot/efi partition (EFI System Partition)
[standard_path.boot-efi]
backup_source_path = "/boot/efi"
exclude_paths = []
remount_readonly = false

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
remount_readonly = false

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

To execute all backup jobs specified in a .toml run:

```
rlvm-backup --config /path/to/your/backup-config.toml
```
See [below](#running-specific-jobs-from-config-file) for instructions on how to run specific (i.e. not all) jobs shown in a config file.

## Additional Details

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

- **`[<volume_type>.<volume_id>]`** — Top-level section defining the volume to back up
  - `<volume_type>` specifies the type of volume:
    - `standard_path` — Standard filesystem path (e.g., `/boot`, `/boot/efi`)
    - `logical_volume_root` — LVM logical volume mounted at `/`
    - `logical_volume_nonroot` — LVM logical volume mounted elsewhere (e.g., `/home`, `/data`)
  - `<volume_id>` is your chosen identifier for that specific volume (any valid name without spaces)

- **`[[<volume_type>.<volume_id>.repositories]]`** — Direct backup destination (can have multiple)
  - Defines where to send backups directly from the source

- **`[[<volume_type>.<volume_id>.repositories.copy_to]]`** — Copy destination (can have multiple per repository)
  - Copies snapshots from the parent repository after backup completes

**⚠️ CRITICAL WARNING:** If backing up a standard partition mounted at `/` using `standard_path`, you **MUST** set `remount_readonly = false`. Attempting to remount the root filesystem read-only will cause system instability or failure.


### Running Specific Jobs from Config File

The `--category` and/or `--name` options can be used if we only want to run some (not all) of the backup jobs specified in a .toml file.

```
# Run all jobs in a category
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path

# Run a single specific job
rlvm-backup --config /path/to/resticlvm_config.toml --category standard_path --name boot
```

### Data Transfer Methods

ResticLVM supports two methods for transferring data to backup repositories:

1. **Direct backup from source** — Restic reads directly from the backup source (mounted LVM snapshot or filesystem) and sends data to the repository. In the example above, this is used for the local repos and the direct SFTP and B2 destinations.

2. **Copy from existing repository** — Restic copies snapshots from one repository to another using `restic copy`. In the example above, this is used for the `boot-efi-copy`, `boot-copy`, `root-copy`, and `home-copy` destinations (configured via `[[repositories.copy_to]]` blocks).

**Pros and cons of each approach:**

- **Direct backups** provide detailed real-time output during the backup process, making troubleshooting easier. However, the LVM snapshot must remain mounted for the entire duration of the backup, which can be lengthy for large volumes or slow network connections.

- **`copy_to`** releases LVM snapshots faster since copying happens *after* snapshot cleanup. This minimizes snapshot lifetime, which matters for systems with high write activity or when backing up large volumes over slow connections. The tradeoff is less detailed output during the copy phase.

You can add `copy_to` destinations under *any* repository entry (local or remote). Each `copy_to` destination is a fully independent restic repository with its own retention policy — it does not need to match the pruning settings of the source repository. For simplicity, choose **either** direct backup **or** `copy_to` for each specific destination — using both to the same location is redundant.


### Remote Repository Setup

For remote destinations, you'll need to configure credentials according to the backend type:

**SFTP:** See [docs/EXAMPLE_SSH_SETUP.md](docs/EXAMPLE_SSH_SETUP.md) for SSH key setup with passwordless authentication.

**Backblaze B2:**
```bash
export B2_ACCOUNT_ID=<your_account_id>
export B2_ACCOUNT_KEY=<your_account_key>
**Backblaze B2 (S3-Compatible - Recommended):**
```bash
export AWS_ACCESS_KEY_ID=<your_key_id>
export AWS_SECRET_ACCESS_KEY=<your_secret_key>
restic -r s3:s3.us-west-004.backblazeb2.com/bucket-name/path init
```
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
- **`remount_readonly`** (standard_path only) temporarily remounts the source read-only during backup.
- **Multiple repos per job** — All `[[repositories]]` receive the same snapshot data.
- **`copy_to` destinations** — Receive copies after local backup completes.
- **All repositories must exist** — Use `restic init` to create each repo before first use.


### Pruning Snapshots

#### Prune All Configured Repositories

```
rlvm-prune --config /path/to/your/resticlvm_config.toml
```
- Applies the configured prune_keep_* settings to each Restic repo.

- Handles Restic's `forget` and `--prune` commands.

#### Prune by Category or Job Name

We can also choose to prune only certain repos:
```
# Prune by category
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root

# Prune by specific job name
sudo rlvm-prune --config /path/to/resticlvm_config.toml --category logical_volume_root --name lv_root
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

## CLI Help
To see available options for `rlvm-backup`:
```
rlvm-backup --help
```

And to see available `rlvm-prune` options:
```
rlvm-prune --help
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


