# Configuration Examples

This directory contains example TOML configuration files demonstrating various ResticLVM backup scenarios. Each example is self-contained and includes comments explaining the use case and setup requirements.

## Quick Start Examples

**New to ResticLVM?** Start here:

- **[single-local-repo.toml](single-local-repo.toml)** - Simplest configuration with one local repository

**Want offsite backups?** Choose your approach:

- **[local-with-remote-copy.toml](local-with-remote-copy.toml)** - ⭐ **Recommended**: Fast local backup, then copy to remote
- **[direct-sftp-backup.toml](direct-sftp-backup.toml)** - Direct backup to SFTP server
- **[direct-b2-backup.toml](direct-b2-backup.toml)** - Direct backup to Backblaze B2 cloud

## All Examples

### Basic Configurations
- **[single-local-repo.toml](single-local-repo.toml)** - One local repository (simplest setup)
- **[multiple-local-repos.toml](multiple-local-repos.toml)** - Multiple local repositories for redundancy

### Remote Backup Strategies
- **[direct-sftp-backup.toml](direct-sftp-backup.toml)** - Direct SFTP backup with SSH authentication
- **[direct-b2-backup.toml](direct-b2-backup.toml)** - Direct Backblaze B2 cloud backup
- **[local-with-remote-copy.toml](local-with-remote-copy.toml)** - Local backup with remote copy (recommended)

### Advanced Scenarios
- **[mixed-backup-types.toml](mixed-backup-types.toml)** - Multiple backup types in one config (root LV, data LV, standard partition)
- **[multiple-copy-destinations.toml](multiple-copy-destinations.toml)** - One local repo copying to multiple remote destinations (multi-cloud)
- **[backup-comprehensive-example.toml](backup-comprehensive-example.toml)** - Kitchen sink: all features demonstrated

## Configuration Structure

Each backup job requires:
- **Job type**: `logical_volume_root`, `logical_volume_nonroot`, or `standard_path`
- **Job name**: Identifies the backup (e.g., `root`, `data`, `boot`)
- **At least one repository**: Local path or remote URL

### Repository Configuration

Repositories are defined using `[[repositories]]` array syntax:

```toml
[[logical_volume_root.root.repositories]]
repo_path = "/path/to/repo"
password_file = "/path/to/password.txt"
prune_keep_last = 7
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 2
```

### Copy Destinations (Optional)

Each repository can have its own copy destinations using nested `[[repositories.copy_to]]`:

```toml
[[logical_volume_root.root.repositories]]
repo_path = "/backups/root-local"
password_file = "/path/to/password.txt"
# ... prune settings ...

  [[logical_volume_root.root.repositories.copy_to]]
  repo = "sftp:backup@server.example.com:/backups/root"
  password_file = "/path/to/password.txt"
  # ... independent prune settings ...
```

## Backend Support

ResticLVM supports all restic backends:

- **Local**: `/path/to/repo`
- **SFTP**: `sftp:user@host:/path` (requires SSH setup, see [EXAMPLE_SSH_SETUP.md](../EXAMPLE_SSH_SETUP.md))
- **Backblaze B2**: `b2:bucket-name:prefix` (requires B2_ACCOUNT_ID and B2_ACCOUNT_KEY)
- **AWS S3**: `s3:s3.amazonaws.com/bucket/prefix`
- **Azure**: `azure:container:/prefix`
- **Google Cloud**: `gs:bucket-name:/prefix`
- **Rclone**: `rclone:remote:path`
- **REST Server**: `rest:http://host:8000/`

See the [main README](../../README.md) for backend-specific setup instructions.

## Usage

1. Copy an example that matches your use case
2. Edit paths, repository URLs, and retention policies
3. Run: `rlvm-backup --config /path/to/your-config.toml`

For selective backups, use categories:
```bash
rlvm-backup --config config.toml --category logical_volume_root
rlvm-backup --config config.toml --category standard_path
```
