# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [0.2.1] — 2026-01-14

### 🔌 API Changes
None

### ✨ New Features
- **B2 helper scripts**: Added four wrapper scripts in `tools/b2/` to simplify Backblaze B2 operations
  - `run-backup-with-b2.sh`: Run backups with B2 credentials automatically loaded
  - `restic-b2.sh`: Execute restic commands against B2 repositories
  - `b2-cli.sh`: Run B2 CLI commands with credentials pre-loaded
  - `init-b2-repos.sh`: Initialize new restic repositories on B2 (moved from `tools/repo_init/`)
- **Improved mount management**: Snapshot mounts now use timestamped directories under `/tmp/`
  - Changed from `/srv/<snapshot_name>` to `/tmp/resticlvm-<timestamp>/<snapshot_name>`
  - Timestamps make it easy to identify stale mounts from failed backups
  - Semantically correct location for temporary operations

### 📚 Documentation
- Added `tools/b2/README.md` with comprehensive B2 helper script documentation
  - Usage examples for all helper scripts
  - B2 setup and configuration instructions
  - Cron job setup examples
  - Troubleshooting guide
- Added "Troubleshooting" section to README with cleanup procedures
  - Step-by-step instructions for cleaning up after failed backups
  - Commands to identify leftover snapshots, mounts, and directories
  - Safety warnings and prevention tips
- Added warning in "Running" section about manual cleanup requirements
- Reorganized README structure:
  - Simplified installation section showing latest release
  - Added "Alternate Installation Methods" section
  - Renamed "Additional Details" → "Additional Details for Running"
  - Added "Helper Tools" section highlighting tools directory
  - Promoted "Development VM" to its own top-level section
- Deleted `tools/repo_init/README.md` (content migrated to `tools/b2/README.md`)

### 🔧 Internal
- Added `b2` as optional dependency in `pyproject.toml`
  - Install with: `pip install "resticlvm[b2]"` or `pip install -e ".[b2]"`
- Added `generate_mount_base()` function in `lv_snapshots.sh` for timestamped mount directories
- Updated `backup_lv_root.sh` to use `/tmp/resticlvm-<timestamp>/` mount points
- Updated `backup_lv_nonroot.sh` to use `/tmp/resticlvm-<timestamp>/` mount points

---

## [0.2.0] — 2026-01-11

### 🔌 API Changes
- **ADDED**: Support for multiple Restic repositories per backup job
  - Each backup job can now send to multiple repositories simultaneously
  - Configure with `repositories = ["repo1", "repo2"]` in backup job configuration
- **ADDED**: Repository-to-repository copying via `copy_to` parameter
  - Copy snapshots from one repository to another using `copy_to = ["repo2", "repo3"]`
  - Useful for creating off-site copies or migrating between storage providers
- **REMOVED**: `remount_readonly` configuration parameter for `standard_path` backups
  - This feature posed safety risks by potentially blocking kernel/bootloader updates
  - Use LVM snapshots for filesystems requiring consistency guarantees
  - Existing configs using `remount_readonly` should remove this parameter

### ✨ New Features
- **Backblaze B2 cloud storage support**: Added full support for B2 repositories via S3-compatible API
- **SSH agent management tools**: Added helper scripts for managing persistent SSH agents
  - `backup-agent-start.sh`: Start SSH agent and load backup key
  - `backup-agent-stop.sh`: Stop SSH agent and clean up
  - `backup-ssh-status.sh`: Check agent status and loaded keys

### 📚 Documentation
- Added `docs/EXAMPLE_B2_SETUP.md` with comprehensive B2 configuration guide
- Added `docs/EXAMPLE_SSH_SETUP.md` with SSH setup instructions for SFTP backups
- Updated README with B2 and SSH backup examples
- Updated `tools/README.md` to document new directory structure

### 🔧 Internal
- **Added comprehensive test suite**: Python unit tests with pytest for core orchestration logic
  - Tests for configuration loading, backup planning, dispatching, and data classes
  - 33 tests covering backup job validation, repository management, and argument handling
  - Test fixtures for repository and backup job configuration
- Reorganized `tools/` directory into subdirectories:
  - `tools/release/`: Build and packaging tools
  - `tools/repo_init/`: Repository initialization scripts
  - `tools/ssh_setup/`: SSH agent management scripts
- Added `tools/repo_init/init-b2-repos.sh` for initializing B2 repositories
- Each tools subdirectory now has its own README with usage instructions
- Removed `remount_readonly` from all test configurations and test cases

---

## [0.1.3] — 2025-12-17

### � API Changes
- Changed recommended install method to use `pip install git+...` instead of downloading wheel files

### 📚 Documentation
- Updated README with git-based installation instructions
- Added instructions for development environment setup
- Simplified categories within CHANGELOG entries (no info removed; just rearranges)

### 🔧 Internal
- Added build helper `./tools/build-release.sh` (replaces `Makefile`)
- Added `./tools/environment.yml` for creating development environment


## [0.1.2] — 2025-04-29

### 🔌 API Changes
None

### 📚 Documentation
- Added installation method instructions to README

### 🔧 Internal
- Added `Makefile` to streamline build, install, and release workflows
- Corrected Python version requirement in `pyproject.toml` to `>=3.11`
- Updated `.gitignore` to exclude `dist/`, `build/`, and `.egg-info` artifacts


## [0.1.1] — 2025-04-29

### 🔌 API Changes
- Snapshots tagged `protected` are now preserved automatically during pruning

### 📚 Documentation
- Updated README with instructions for tagging protected snapshots

### 🔧 Internal
- Minor improvements to prune script behavior and dry-run handling


## [0.1.0] - 2025-04-28

### 🔌 API Changes
- Initial public release
- Config-driven backup and prune tooling combining Restic and LVM
- Support for backing up:
  - Standard filesystem paths
  - Root logical volumes (with chroot snapshot backup)
  - Non-root logical volumes (direct snapshot backup)
- Dry-run support for both backup and prune operations

### 📚 Documentation
- Initial README with basic documentation and usage examples

### 🔧 Internal
- Lightweight, modular design with Python CLI wrapper and Bash scripts for system interactions








