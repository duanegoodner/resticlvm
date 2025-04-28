# Backup and Prune Scripts

This folder contains the Bash scripts used by ResticLVM to perform
backup and pruning operations.

Scripts are split into:

- **Main Scripts**:
  - `backup_path.sh`: Backup a regular filesystem path.
  - `backup_lv_root.sh`: Backup a logical volume mounted at `/` (root).
  - `backup_lv_nonroot.sh`: Backup a logical volume mounted elsewhere (e.g., `/data`).
  - `prune_repo.sh`: Prune old Restic snapshots based on retention settings.

- **Shared Helpers**:
  - `backup_helpers.sh`: Aggregates helper libraries for easy sourcing.

- **Helper Libraries (`lib/`)**:
  - `arg_handlers.sh`: CLI argument parsing and validation.
  - `command_builders.sh`: Construct Restic command arguments and tags.
  - `command_runners.sh`: Run or dry-run shell commands safely.
  - `lv_snapshots.sh`: Create, mount, and clean up LVM snapshots.
  - `message_display.sh`: Display backup configurations and dry-run messages.
  - `mounts.sh`: Manage mounting, remounting, and bind mounts for chroot.
  - `pre_checks.sh`: Perform environment and logical volume validations.
  - `usage_commands.sh`: Provide usage/help messages for each script type.

## Notes

- All scripts assume they are sourced/run internally by the ResticLVM Python interface.
- Scripts must be run with root privileges (directly or via `sudo`).
- Scripts honor a `--dry-run` option to preview operations safely.
- Environment utilities like `restic`, `mount`, `findmnt`, and `realpath` must be available.

---

For more details on how these scripts are orchestrated, see the [main README](../../../../README.md).
