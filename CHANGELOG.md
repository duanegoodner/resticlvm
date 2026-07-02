# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [0.6.0] — 2026-07-02

### 🔌 API Changes
- **New config format: `[volume.<name>]` with `volume_type`.**
  The three top-level category sections (`standard_path`, `logical_volume_root`,
  `logical_volume_nonroot`) are replaced by a single `[volume.<name>]` section
  where each entry has a `volume_type` field (`standard_path`, `lv_root`, or
  `lv_nonroot`). **Action:** update config files — see README for the new format.
- **Named prune policies replace inline prune params.**
  Define retention policies once in `[prune_policy.<name>]` sections and reference
  them with `prune_policy = "<name>"` on each repository. Inline `prune_keep_*`
  keys are no longer supported.

### 🔧 Internal
- `VolumeType` enum replaces string-based category dispatch.
- `VolumeConfig` dataclass replaces `StandardPathJobConfig` / `LvJobConfig`.
- `BackupConfig` simplified to `prune_policies` + `volumes` (was three separate dicts).
- `BackupPlan` uses `BackupConfig`/`BackupConfigFactory` instead of raw config dicts;
  deeply nested `create_backup_job` replaced by flat `_build_backup_job`.
- `prune_runner` uses `BackupConfig` directly; `confirm_unique_repos` and
  `resolve_prune_params` removed from `restic_repo.py`.

### 📚 Documentation
- README config examples, quickstart, and CLI docs updated for the new format.

---

## [0.5.1] — 2026-07-01

### 🐛 Bug Fixes
- **`--dry-run` now works.** The flag was parsed by the CLI but never passed to the
  shell scripts, so `rlvm backup --dry-run` performed a real backup. Fixed in both
  the backup scripts and copy operations. (#48, #49)

---

## [0.5.0] — 2026-07-01

### 🔌 API Changes
- **Unified CLI.** The separate `rlvm-backup` and `rlvm-prune` commands are replaced
  by a single `rlvm` command with subcommands: `rlvm backup` and `rlvm prune`.
  **Action:** update cron jobs, systemd units, and scripts —
  `sudo rlvm-backup --config …` becomes `sudo rlvm backup --config …`;
  `sudo rlvm-prune --config …` becomes `sudo rlvm prune --config …`.

### 🔧 Internal
- New `resticlvm.orchestration.cli` module dispatches subcommands; the runner
  modules expose `run(args)` for the CLI to call.
- SSH agent helper scripts (`tools/ssh_setup/`) consolidated from five separate
  scripts into a single `root-ssh-agent.sh` with subcommands (`start`, `stop`,
  `status`, `ssh-add`). Key management delegates directly to `ssh-add`, so the
  full `ssh-add` interface is available. These scripts are not part of the
  installed package.

### 📚 Documentation
- Added `CLAUDE.md` for agent kickoff context.
- SSH setup docs reframed: root SSH access is a prerequisite users can fulfill
  however they prefer; the helper script is one option.
- All docs, examples, and error messages updated for the `rlvm backup`/`rlvm prune`
  syntax.

### ⚠️ Known Limitations
- A mid-run failure can still leak the LVM snapshot and bind-mounts (no cleanup trap
  yet) — tracked in #24. Continue running ResticLVM **attended/manual only** until
  that is fixed.
- A repo failure within a multi-repo job stops backup to remaining repos in that
  job — tracked in #46. Other jobs in the same run are unaffected.

---

## [0.4.1] — 2026-06-23

### 📚 Documentation
- Reworked the top-level README (the project's primary documentation): added a
  Table of Contents, a **Quickstart**, a **Design Notes** section, and a
  consolidated **Status and Known Limitations** note.
- Accuracy fixes to match 0.4.0 behavior: run/prune examples now show `sudo` (root
  is required), `--dry-run` and `--version` are documented, a duplicate Backblaze
  B2 credential block was removed, the "future feature" note on `--dry-run` (which
  already exists) was dropped, the Issues link placeholder was fixed, and install
  snippets point at the current release.

_No code changes._

---

## [0.4.0] — 2026-06-23

### 🔌 API Changes
- **No more automatic privilege elevation.** `rlvm-backup` / `rlvm-prune` no longer
  re-exec themselves under `sudo`. If not run as root they now print a clear message
  and exit 1 — run them via `sudo`, a systemd unit, or a root cron job. (Self-elevation
  was incompatible with credential loading: `sudo` scrubs the environment, dropping
  `AWS_*` / `SSH_AUTH_SOCK`.)
- **`tools/b2/run-backup-with-b2.sh` removed.** It's no longer needed — see below.
  Migrate cron/systemd to `sudo rlvm-backup --config …` (absolute path).

### ✨ New Features
- **`rlvm-backup` loads B2 credentials natively.** When a config contains a B2 (`s3:`)
  repository, `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` are loaded automatically —
  from the environment if present, else from `/root/.config/resticlvm/b2-env`
  (override with `RESTICLVM_B2_ENV`). Backups to non-B2 repos run fine with no
  credentials present. No wrapper, no `RLVM_BACKUP` pinning:
  `sudo rlvm-backup --config /path/to/config.toml`.
- **`--version` flag** on `rlvm-backup` and `rlvm-prune` (works without root).
- **Unmissable failure summary.** When any job fails, the end-of-run summary is a
  barred `BACKUP FAILED — N of M job(s) did NOT succeed` banner listing each failure;
  a clean run prints a calm success line.

### 🔧 Internal
- Version is exposed at runtime via `importlib.metadata` (single-sourced in
  `pyproject.toml`).
- `--version` / `--help` are parsed before the root check, so they need no `sudo`.
- A missing-credentials B2 job fails in isolation (clear message), so other jobs in
  the same run still execute; the process still exits 1.
- `SSH_AUTH_SOCK` respects an existing value (`env.setdefault`); shell reads guarded
  as `${SSH_AUTH_SOCK:-}` under `set -u`.
- B2 credential-handling hardening: no credential values printed; `b2-env` perms
  warning; sharpened least-privilege / Object Lock guidance.
- Tooling/docs: generic release checklist under `tools/release/`; `shellcheck` in the
  pixi dev env; README/tools docs made consistent with the current run model; removed
  the now-unused `tools/b2/with-b2-creds.sh`.

### ⚠️ Known Limitations
- A mid-run failure can still leak the LVM snapshot and bind-mounts (no cleanup trap
  yet) — tracked in #24. Continue running ResticLVM **attended/manual only** until
  that is fixed.

---

## [0.3.0] — 2026-06-22

### 🔌 API Changes
- **Backup runs now exit non-zero on failure.** Previously `rlvm-backup` exited 0
  even when a backup job or copy operation failed, silently defeating exit-code
  based alerting (systemd `OnFailure=`, cron `MAILTO`, success heartbeats). It now
  exits 1 if any job or copy fails. **Action:** if you had automation tolerating
  the old always-0 exit, expect real failures to now surface as exit 1.

### ✨ New Features
- **End-of-run summary**: after all jobs run, a summary lists how many jobs ran and
  names any failed jobs and failed copy destinations.
- Jobs remain isolated — one failed job still lets the others run; failures are
  reported rather than hidden.

### 🔧 Internal
- `BackupJob.run()` now returns a `JobResult`; `run_all()` returns a failure count.
- Added pixi dev environment (`pixi.toml` / `pixi.lock`); run tests with `pixi run test`.
- Single-sourced the package version in `pyproject.toml` (removed the duplicate from
  `pixi.toml`).
- Added a `release-build` pixi task and bundled the `python-build` frontend.
- Added unit tests covering failure reporting, copy failures, job isolation, and the
  non-zero exit code.

### ⚠️ Known Limitations
- A mid-run failure can still leak the LVM snapshot and bind-mounts (no cleanup
  trap yet) — tracked in #24. Continue running ResticLVM **attended/manual only**
  until that is fixed.

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








