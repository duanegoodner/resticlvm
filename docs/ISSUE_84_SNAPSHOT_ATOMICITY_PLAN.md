# Issue #84 — Cross-LV Snapshot Atomicity: Implementation Plan

## Motivation

resticlvm currently runs each LV backup as a self-contained shell script that
creates a snapshot, backs up to all repos, and tears down the snapshot before
moving to the next volume. For a config with 4 LV volumes × 3 repos each, the
snapshot of the last LV is taken ~45 minutes after the first. If data on one LV
is coordinated with data on another, a restore from these backups reflects an
inconsistent point-in-time across volumes.

**Goal:** Take all LVM snapshots before sending any data to repos — reducing
the cross-LV time delta from minutes to milliseconds.

## Current architecture

```
Python (backup_runner.py):
  for each volume (sequential):
      BackupJob.run()  →  subprocess: backup_lv_root.sh / backup_lv_nonroot.sh
          create_snapshot()
          mount_snapshot()
          [chroot setup, for root only]
          for each repo:
              restic backup
          teardown everything
          RLVM_CLEANUP_DONE=1
```

Key properties:
- Each shell script owns its full lifecycle (create → backup → teardown).
- Cleanup trap is installed per-script, immediately after `create_snapshot()`.
- `cleanup_snapshot_resources()` discovers mounts dynamically via `findmnt`.
- `standard_path` volumes have no LVM involvement (no snapshot needed).

## Proposed architecture

Split the backup flow into three phases, coordinated from Python:

```
Phase 1 — Snapshot all LVs
  Python: for each LV volume:
      call snapshot_lv.sh  →  create + mount snapshot
      record snapshot info (device, mount point)

Phase 2 — Backup all volumes
  Python: for each volume (LV and standard_path):
      call backup script  →  restic backup using pre-mounted snapshot
      (standard_path volumes run unchanged)

Phase 3 — Teardown all snapshots
  Python: for each LV volume (reverse order):
      call teardown_lv.sh  →  unmount + remove snapshot
```

### Why split at the Python/Bash boundary

- Python is the natural coordinator for multi-volume state. It already iterates
  volumes, collects results, and handles per-job isolation.
- Bash remains responsible for the LVM/mount operations it already handles well.
- The split avoids a mega-script that takes all volume info at once.

## Implementation steps

### Step 1: New shell scripts for snapshot lifecycle

Create two new scripts in `src/resticlvm/scripts/`:

**`snapshot_create.sh`** — Create and mount one LVM snapshot.

Accepts: `-g VG -l LV -z SIZE`  
Does: `create_snapshot()`, `mount_snapshot()` (from existing `lib/lv_snapshots.sh`)  
Outputs: snapshot device path and mount point to stdout (machine-parseable)  
Does NOT install a cleanup trap (Python owns lifecycle coordination).

**`snapshot_teardown.sh`** — Tear down one LVM snapshot.

Accepts: `-d SNAP_DEVICE -m MOUNT_POINT -b MOUNT_BASE`  
Does: `cleanup_snapshot_resources()` (existing function from `lib/lv_snapshots.sh`)  
Idempotent — safe to call even if already cleaned up.

Both scripts source `lib/lv_snapshots.sh` for the actual LVM operations.

### Step 2: Refactor backup scripts to accept pre-mounted snapshots

Add a `--snapshot-mount` flag to `backup_lv_root.sh` and `backup_lv_nonroot.sh`.

When `--snapshot-mount <path>` is provided:
- Skip `create_snapshot()`, `mount_snapshot()`, and cleanup trap installation.
- Use the provided path as `SNAPSHOT_MOUNT_POINT`.
- Skip teardown at end of script.
- Everything else (chroot setup/teardown for root, repo loop, restic invocation,
  mount namespace for nonroot) runs unchanged.

When `--snapshot-mount` is NOT provided:
- Existing behavior preserved exactly (create, backup, teardown — all in one).
- This keeps the scripts usable standalone and simplifies rollback.

### Step 3: New Python coordinator class

Create `src/resticlvm/orchestration/snapshot_coordinator.py`:

```python
class SnapshotCoordinator:
    """Manages batch snapshot creation and teardown for cross-LV atomicity."""

    def create_all(self, lv_jobs: list[BackupJob]) -> dict[str, SnapshotInfo]:
        """Create and mount snapshots for all LV volumes.

        If any snapshot fails to create, tears down all previously created
        snapshots and raises.
        """

    def teardown_all(self, reverse=True) -> None:
        """Tear down all active snapshots. Idempotent."""

    def get_mount_point(self, volume_name: str) -> str:
        """Return the snapshot mount point for a volume."""
```

`SnapshotInfo` is a small dataclass holding `device`, `mount_point`,
`mount_base`, and `volume_name`.

Error handling in `create_all`: if snapshot #3 fails, tear down snapshots #1
and #2 before raising. The caller never sees a partial state.

### Step 4: Python signal handler for cleanup

Install a signal handler in `BackupJobRunner` (or the coordinator) that calls
`teardown_all()` on SIGINT/SIGTERM. This covers the case where Python itself
is killed between Phase 1 and Phase 3.

Use `atexit.register()` as a secondary safety net for unhandled exceptions.

The coordinator's `__enter__`/`__exit__` methods make it usable as a context
manager:

```python
with SnapshotCoordinator(lv_jobs) as snapshots:
    snapshots.create_all()
    for job in all_jobs:
        mount = snapshots.get_mount_point(job.name) if job.is_lv else None
        job.run(snapshot_mount=mount)
# __exit__ calls teardown_all() unconditionally
```

### Step 5: Update BackupJobRunner and BackupJob

Modify `BackupJobRunner.run_all()`:
1. Partition jobs into LV jobs and non-LV jobs.
2. Use `SnapshotCoordinator` to create all LV snapshots.
3. Run all jobs (LV and non-LV), passing `--snapshot-mount` to LV jobs.
4. Teardown all snapshots (via context manager exit).

Modify `BackupJob`:
- Add optional `snapshot_mount` parameter to `run()`.
- When set, prepend `--snapshot-mount <path>` to the shell command args.
- No changes needed for `standard_path` jobs.

### Step 6: Pre-flight VG space check with safety margin

Before creating any snapshots, check that the VG has enough free space for all
requested snapshot sizes combined **plus a safety margin**. This is a new
pre-check in `SnapshotCoordinator.create_all()`:

```bash
vgs --noheadings --nosuffix --units b -o vg_free VG_NAME
```

Validation rule:

```
vg_free  >=  sum(snapshot_sizes) + min_vg_free_after_snapshots
```

`min_vg_free_after_snapshots` defaults to `1G` and is configurable in the
backup TOML (top-level setting, not per-volume). The margin exists because the
VG free space serves double duty — it backs the snapshot COW areas *and* the
running system. If all free space is consumed by snapshot allocations, the
system has zero headroom for normal filesystem operations, thin-pool growth, or
unexpected writes during the backup window.

Fail with a clear message if insufficient, listing: VG free space, total
snapshot allocation requested, configured margin, and the shortfall.

### Step 7: Post-backup snapshot COW usage reporting

Before tearing down each snapshot, query its actual COW utilization:

```bash
lvs --noheadings --nosuffix -o snap_percent /dev/VG/SNAP_NAME
```

`snap_percent` is the percentage of the allocated COW area that was actually
consumed by writes to the origin during the snapshot's lifetime.

Report this per-snapshot in the backup summary output, e.g.:

```
Snapshot COW usage:
  root      (30G allocated):   12.3%  (3.7G used)
  git       (10G allocated):    2.1%  (215M used)
  mail      (10G allocated):    0.4%  (41M used)
```

Add a warning threshold (default 70%, configurable in backup TOML as
`snapshot_cow_warn_percent`). When a snapshot exceeds this threshold, print a
prominent warning advising the operator to increase `snapshot_size` for that
volume in the config. This gives early visibility into snapshots that are
approaching overflow — an overflow would invalidate the snapshot and lose that
volume's backup entirely.

#### COW overflow behavior (for reference)

When a snapshot's COW area fills completely, the kernel immediately invalidates
the snapshot. Reads from the snapshot device return I/O errors, and any
in-progress restic backup against that snapshot fails. The snapshot LV remains
on disk (marked invalid) and can still be removed with `lvremove`. The origin
LV is unaffected — the running system continues normally. The consequence is a
lost backup for that volume, not a system outage. The COW usage reporting
described above is specifically designed to catch this risk before it
materializes.

### Step 8: Update dispatch table

Add entries to `dispatch.py` for the new `snapshot_create.sh` and
`snapshot_teardown.sh` scripts. These don't need the full token-mapping
machinery — they have a simpler argument interface.

## Design decisions

### Why not move all LVM operations to Python?

The LVM/mount operations are well-tested in Bash and benefit from shell idioms
(`set -euo pipefail`, traps, `findmnt` parsing). Reimplementing them in Python
would be a larger change with more risk and no clear benefit.

### Why keep standalone mode in the backup scripts?

Backward compatibility and debuggability. A developer can still run
`backup_lv_root.sh` directly for a single volume without the Python
coordinator. This also makes the change easier to roll back.

### Why not a config option to choose batch vs. sequential?

Batch mode is strictly better when it works (near-zero time delta, same total
COW). The only constraint is VG free space, which we validate up front. There's
no reason to offer the old behavior as a user-facing option. The standalone
script mode serves as the implicit fallback for manual/debug use.

### New config settings

Two new optional top-level TOML settings (not per-volume):

```toml
# Minimum VG free space to preserve after allocating all snapshots.
# Ensures the running system retains headroom during backups.
# Default: "1G"
min_vg_free_after_snapshots = "2G"

# Warn if any snapshot's COW usage exceeds this percentage.
# Helps catch undersized snapshot_size before an overflow occurs.
# Default: 70
snapshot_cow_warn_percent = 70
```

Both are optional with sensible defaults — existing configs continue to work
unchanged.

### Multiple VGs

The pre-flight VG space check must handle configs where LVs span multiple VGs
(even though the current fraser config has everything in `vg0`). Group snapshot
size requirements by VG and validate each VG independently — each must have
enough free space for its own snapshots plus the safety margin.

### Copy-to timing

Currently `_run_copy_operations()` runs immediately after each job's backup
succeeds (within what becomes Phase 2). Copy operations work on restic repos,
not on the LVM snapshot, so they can be deferred to after Phase 3 teardown.
Deferring frees snapshot COW space sooner, reducing the window for COW overflow.

Approach: collect successful copy tasks during Phase 2, execute them after
Phase 3 teardown completes. A volume whose backup failed still skips its
copies (existing behavior preserved).

### Batch timestamp

Currently each backup script generates its own timestamped snapshot name
independently. With batch snapshot creation, use a single shared timestamp for
all snapshots in a batch. This makes it easy to identify which snapshots belong
to the same atomic group (useful in `lvs` output during debugging or if
cleanup needs to find orphaned batch snapshots).

Generate the timestamp once in the Python coordinator and pass it to each
`snapshot_create.sh` invocation.

### Ordering of volumes in Phase 2

The backup order within Phase 2 doesn't affect atomicity (all snapshots already
exist). Keep the current config-file ordering. Root volume should probably go
first since it's typically the largest and most important.

## Testing

### Unit tests (no VM needed)

- `SnapshotCoordinator`: mock subprocess calls, verify create/teardown ordering,
  verify rollback on partial failure, verify signal handler registration.
- `BackupJob` arg construction: verify `--snapshot-mount` is passed correctly.
- `BackupJobRunner` phase logic: verify LV/non-LV partitioning, verify
  coordinator is used as context manager.
- Pre-flight VG space check: verify margin enforcement, verify failure message
  includes all relevant numbers, verify custom margin from config.
- COW usage reporting: verify `snap_percent` parsing, verify warning threshold
  logic, verify custom threshold from config.

### Shell script tests

- `snapshot_create.sh`: verify output format (parseable by Python).
- `snapshot_teardown.sh`: verify idempotency (call twice, second is a no-op).
- Existing backup scripts with `--snapshot-mount`: verify they skip create/teardown.

### VM integration tests (failure-injection harness)

Using the existing `debian13-vm` setup from `docs/FAILURE_INJECTION_TESTING.md`:

- Happy path: 3 LV volumes, verify all snapshots exist simultaneously (check
  with `lvs` between Phase 1 and Phase 2). Verify COW usage is reported for
  each snapshot in the summary output.
- Mid-backup kill: SIGTERM Python during Phase 2, verify all snapshots are
  cleaned up.
- Snapshot creation failure: fill VG so snapshot #2 fails, verify snapshot #1
  is torn down.
- Pre-flight space rejection: configure snapshot sizes that exceed available VG
  free space (accounting for margin), verify the check fails before any
  snapshots are created.
- COW overflow: write heavily to an origin during backup, verify the backup
  for that volume fails gracefully while other volumes complete, and verify
  the invalidated snapshot is still cleaned up.
- COW warning threshold: write moderately to an origin during backup to push
  COW usage above the warning threshold, verify the warning appears in output.

## Risks

- **VG free space**: Batch mode requires free space for all snapshots
  simultaneously. The pre-flight check with safety margin (Step 6) mitigates
  this, but operators need to be aware when sizing VGs. The configurable
  `min_vg_free_after_snapshots` margin (default 1G) ensures the running system
  retains headroom even while all snapshots are active.
- **Snapshot COW overflow**: If the system is unusually busy during a backup,
  writes to an origin LV can fill the snapshot's COW area, invalidating the
  snapshot and losing that volume's backup. The post-backup COW usage report
  (Step 7) provides early warning — operators can increase `snapshot_size`
  before an overflow actually occurs. The 70% default warning threshold gives
  meaningful headroom.
- **Longer snapshot lifetime**: The first snapshot exists for the entire backup
  duration (all volumes). More writes accumulate in its COW area. For mostly-idle
  workstations this is negligible, but high-write-rate servers would need larger
  snapshot allocations. The COW usage report makes this visible rather than a
  silent risk.
- **Cleanup complexity**: The Python signal handler + context manager must be
  rock-solid. A bug here could leak snapshots. The idempotent
  `cleanup_snapshot_resources()` and the standalone `snapshot_teardown.sh`
  provide manual recovery options if the coordinator fails.

## Sequencing

Suggested PR order (each is independently mergeable):

1. **Shell scripts**: `snapshot_create.sh`, `snapshot_teardown.sh`, and
   `--snapshot-mount` flag on existing backup scripts. Unit/shell tests.
2. **Python coordinator**: `SnapshotCoordinator`, signal handler, context
   manager. Unit tests with mocked subprocess.
3. **Integration**: Wire coordinator into `BackupJobRunner`, add VG space
   pre-check. VM integration tests.
4. **Docs**: Update `CLAUDE.md` status section, close #84.
