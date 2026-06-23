# Backblaze B2 Helper Scripts

This directory contains helper scripts for working with Backblaze B2 cloud storage, including backup operations, repository management, and B2 CLI interactions.

All scripts load B2 credentials from `/root/.config/resticlvm/b2-env`, which should contain:

```bash
export AWS_ACCESS_KEY_ID=your_b2_key_id
export AWS_SECRET_ACCESS_KEY=your_b2_application_key
```

(Override the location with the `B2_ENV_FILE` environment variable.)

## Scripts

### 0. with-b2-creds.sh (generic credential loader)

Loads B2 credentials, then `exec`s whatever command you give it. This is the
building block the backup wrapper uses; reach for it directly when you want to run
any command with B2 creds loaded.

**Usage:**
```bash
sudo ./with-b2-creds.sh -- rlvm-backup --config /path/to/config.toml
sudo ./with-b2-creds.sh -- restic -r s3:... -p /path/to/pw.txt snapshots
```

It deliberately does **not** locate any entrypoint — you pass the exact command to
run, so there is no fragile `which` lookup or PATH guessing.

### 1. run-backup-with-b2.sh

Convenience wrapper for running `rlvm-backup` with B2 credentials loaded. It
delegates credential-loading to `with-b2-creds.sh` and resolves the `rlvm-backup`
entrypoint explicitly.

**Purpose:** Execute ResticLVM backups that include B2 repositories.

**Usage:**
```bash
# Run full backup configuration (rlvm-backup resolved from PATH)
sudo ./run-backup-with-b2.sh --config /path/to/config.toml

# Pin the entrypoint explicitly (recommended for cron/systemd)
sudo RLVM_BACKUP=/usr/local/bin/rlvm-backup ./run-backup-with-b2.sh --config /path/to/config.toml

# Run a specific backup by name / category
sudo ./run-backup-with-b2.sh --name boot --config /path/to/config.toml
sudo ./run-backup-with-b2.sh --category standard_path --config /path/to/config.toml
```

**Notes:**
- Delegates credential-loading to `with-b2-creds.sh` (single responsibility).
- Resolves `rlvm-backup` via the `RLVM_BACKUP` env var, falling back to a PATH
  lookup — no fragile bare `which`. Set `RLVM_BACKUP` to an absolute path for
  unattended runs so resolution never depends on the ambient PATH.
- Run as root (via `sudo`, or from a root cron/systemd unit).

### 2. restic-b2.sh

Wrapper for running restic commands against B2 repositories.

**Purpose:** Manually interact with B2 restic repositories (view snapshots, check integrity, restore files, etc.).

**Usage:**
```bash
# List snapshots
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /root/.config/resticlvm/repo-creds/password.txt snapshots

# Check repository integrity
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /root/.config/resticlvm/repo-creds/password.txt check

# List files in latest snapshot
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /root/.config/resticlvm/repo-creds/password.txt ls latest

# Show repository stats
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /root/.config/resticlvm/repo-creds/password.txt stats

# Prune old snapshots
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /root/.config/resticlvm/repo-creds/password.txt prune
```

**Common Restic Commands:**
- `snapshots` - List all snapshots
- `ls SNAPSHOT_ID` - List files in a snapshot (or `latest`)
- `check` - Verify repository integrity
- `stats` - Show repository statistics
- `prune` - Remove unreferenced data
- `forget` - Remove specific snapshots
- `restore SNAPSHOT_ID --target /restore/path` - Restore files

### 3. b2-cli.sh

Wrapper for running Backblaze B2 CLI commands with credentials loaded.

**Purpose:** Explore B2 bucket contents, manage files, view storage usage (requires `b2` package: `pip install -e ".[b2]"`).

**Usage:**
```bash
# List files in repository path (preserve PATH for conda env)
sudo env "PATH=$PATH" ./b2-cli.sh ls --long --recursive b2://bucket/path/

# Get bucket information
sudo env "PATH=$PATH" ./b2-cli.sh get-bucket bucket-name

# List all files (short format)
sudo env "PATH=$PATH" ./b2-cli.sh ls b2://bucket/path/

# Download a file
sudo env "PATH=$PATH" ./b2-cli.sh download-file-by-name bucket-name remote/file.txt local-file.txt
```

**Common B2 CLI Commands:**
- `ls [--long] [--recursive] b2://bucket/path/` - List files
- `get-bucket bucket-name` - Show bucket details
- `download-file-by-name bucket file remote.txt local.txt` - Download file
- `delete-file-version file-id` - Delete specific file version
- `file-info b2://bucket/file` - Show file metadata

**Installation:**
```bash
# Install B2 CLI as optional dependency
pip install -e ".[b2]"

# Or install directly
pip install b2
```

### 4. init-b2-repos.sh

Initialize new restic repositories on Backblaze B2.

**Purpose:** Create new B2-based restic repositories for backup destinations.

**Usage:**
```bash
# Initialize single repository
source /root/.config/resticlvm/b2-env
./init-b2-repos.sh -b my-bucket -r us-west-004 -P /path/to/password.txt my-repo

# Initialize with path prefix
./init-b2-repos.sh -b my-bucket -r us-west-004 -p hostname -P /path/to/password.txt repo1 repo2

# Initialize multiple repositories at once
./init-b2-repos.sh -b kernelstate-backups -r us-west-004 \
  -p resticlvm/hostname \
  -P /root/.config/resticlvm/repo-creds/b2-password.txt \
  boot-01 root-01 data-01
```

**Arguments:**
- `-b, --bucket BUCKET` - B2 bucket name (required)
- `-r, --region REGION` - B2 region (required, e.g., us-west-004)
- `-p, --prefix PREFIX` - Path prefix within bucket (optional)
- `-P, --password FILE` - Restic password file (required)
- `REPO_NAME [REPO_NAME...]` - One or more repository names

**Environment:**
Requires `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables (automatically sourced from `/root/.config/resticlvm/b2-env` by wrapper scripts).

## Setup

### 1. Create B2 Credentials File

Create `/root/.config/resticlvm/b2-env`:

```bash
sudo mkdir -p /root/.config/resticlvm
sudo bash -c 'cat > /root/.config/resticlvm/b2-env << EOF
export AWS_ACCESS_KEY_ID=your_b2_key_id
export AWS_SECRET_ACCESS_KEY=your_b2_application_key
EOF'
sudo chmod 600 /root/.config/resticlvm/b2-env
```

### 2. Create Repository Password Files

Create password files for each repository:

```bash
sudo mkdir -p /root/.config/resticlvm/repo-creds
sudo bash -c 'echo "your-secure-password" > /root/.config/resticlvm/repo-creds/b2-boot-01.txt'
sudo chmod 600 /root/.config/resticlvm/repo-creds/b2-boot-01.txt
```

### 3. Initialize Repositories

Use `init-b2-repos.sh` to create repositories in B2:

```bash
source /root/.config/resticlvm/b2-env
./init-b2-repos.sh -b kernelstate-backups -r us-west-004 \
  -p resticlvm/rudolph \
  -P /root/.config/resticlvm/repo-creds/b2-boot-01.txt \
  boot-01
```

### 4. Configure Backups

Add B2 repositories to your ResticLVM config file (e.g., `backup-config.toml`):

```toml
[[standard_path.boot.repositories]]
repo_path = "s3:s3.us-west-004.backblazeb2.com/kernelstate-backups/resticlvm/rudolph/boot-01"
password_file = "/root/.config/resticlvm/repo-creds/b2-boot-01.txt"
prune_keep_last = 10
prune_keep_daily = 7
prune_keep_weekly = 4
prune_keep_monthly = 6
prune_keep_yearly = 1
```

## Cron Setup

For automated backups, add to root's crontab (`sudo crontab -e`). Pin the
entrypoint with an absolute path via `RLVM_BACKUP` so resolution never depends on
cron's minimal PATH — no need to bake a conda/pixi `bin` directory into the
crontab `PATH`:

```cron
# Run daily backup at 2 AM. Set RLVM_BACKUP to the absolute path of the
# installed entrypoint (find it with: command -v rlvm-backup).
0 2 * * * RLVM_BACKUP=/usr/local/bin/rlvm-backup /path/to/resticlvm/tools/b2/run-backup-with-b2.sh --config /path/to/config.toml
```

## Troubleshooting

### B2 Credentials Not Found

If you see "no credentials found" errors:
- Verify `/root/.config/resticlvm/b2-env` exists and contains credentials
- Check file permissions: `sudo chmod 600 /root/.config/resticlvm/b2-env`
- Ensure credentials are exported (checks presence without printing the secret):
  `sudo bash -c 'source /root/.config/resticlvm/b2-env && [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ] && echo "credentials are set"'`

### Command Not Found (b2, rlvm-backup, lvcreate)

When using sudo, commands may not be in PATH:
- Use `sudo env "PATH=$PATH"` to preserve your user's PATH
- For cron jobs, explicitly set PATH in the crontab

### Checking B2 Storage Usage

Use the B2 web UI or:
```bash
sudo env "PATH=$PATH" ./b2-cli.sh get-bucket kernelstate-backups
```

### Cleaning Up Unreferenced Data

After interrupted backups or deleting snapshots:
```bash
sudo ./restic-b2.sh -r s3:s3.us-west-004.backblazeb2.com/bucket/path \
  -p /path/to/password.txt prune --max-unused 0
```
