# Multi-Repository Implementation Notes & Lessons Learned

**Branch:** `multiple-repos-per-snapshot`  
**Status:** Reference Implementation (Architectural Deviation - Do Not Merge)  
**Date:** January 5-6, 2026

## Overview

This branch explored implementing multi-repository backup support to enable sending a single LVM snapshot to multiple destinations (local repos, SFTP remotes, B2, etc.). The goal was to optimize the backup process: **one snapshot creation → multiple destinations** instead of **one snapshot per destination**.

## What We Accomplished ✅

### Phase 1-2: Data Model & Configuration (Correct Approach)

**Files Modified:**
- `src/resticlvm/orchestration/restic_repo.py`
- `src/resticlvm/orchestration/data_classes.py`
- `src/resticlvm/orchestration/backup_plan.py`
- `src/resticlvm/orchestration/prune_runner.py`

**Changes:**
1. **New TOML Format:** Changed from single `restic_repo` to `[[...repositories]]` array:
   ```toml
   # Old format (still supported)
   [logical_volume_root.root]
   restic_repo = "/srv/backup/root"
   restic_password_file = "/path/to/password.txt"
   
   # New format
   [logical_volume_root.root]
   [[logical_volume_root.root.repositories]]
   repo_path = "/srv/backup/root-a"
   password_file = "/path/to/password.txt"
   
   [[logical_volume_root.root.repositories]]
   repo_path = "sftp:user@host:/path"
   password_file = "/path/to/password.txt"
   ```

2. **Backward Compatibility:** Config loader detects format and converts old format to new internally

3. **Data Model Updates:**
   - `BackupJob.repositories: list[ResticRepo]` (was single repo)
   - `confirm_unique_repos()` returns `dict[tuple, list[ResticRepo]]` (was single ResticRepo)
   - Prune runner iterates over repo lists

4. **Repository Validation:**
   - No duplicate repos within same job (enforced)
   - Same repo can be used across different jobs (allowed)

**Result:** ✅ Clean, well-tested data model supporting multiple repositories per job

---

### SSH & Security Setup (Valuable Knowledge)

**File Created:** `EXAMPLE_SSH_SETUP.md`

**Key Discoveries:**
1. **SSH Agent with Passphrase-Protected Keys:**
   - Helper scripts: `backup-agent-start`, `backup-ssh-status`
   - Agent persists at `/root/.ssh/ssh-agent.sock`
   - Must re-add key after reboot (acceptable tradeoff)

2. **Dedicated Backup User Per Client:**
   - Remote server: One user per backup source machine
   - Limits blast radius if credentials compromised
   - Example: `backup-debian13vm@192.168.50.210`

3. **SSH Key Management:**
   - Passphrase-protected key more secure than passphrase-less
   - Agent keeps decrypted key in memory (cleared on reboot)
   - Cannot extract key from agent (only use it)

4. **Cron Job Approach:**
   - Wrapper script checks for agent/keys before running backup
   - Sends notification if agent not ready
   - Uses `SSH_AUTH_SOCK` environment variable

5. **privileges.py Enhancement:**
   - Automatically sets `SSH_AUTH_SOCK` if agent socket exists
   - Preserves environment when re-executing with sudo

**Result:** ✅ Production-ready SSH setup documentation

---

### VM Testing Infrastructure

**Files Modified:**
- `dev/vm-builder/common/config/vm-sizes.sh`
- `dev/vm-builder/packer-local/debian-cloud.pkr.hcl`
- `dev/vm-builder/packer-local/ansible/lvm-migrate.sh`
- `dev/vm-builder/deploy-local/deploy.sh`

**Changes:**
- Added 2 additional virtual disks (6 total)
- Created test partitions for all backup scenarios:
  - LV root (`/`) on `/dev/vda3`
  - LV non-root (`/srv/data_lv`) on `/dev/vde`
  - Standard partition (`/srv/data_standard_partition`) on `/dev/vdf1`

**Result:** ✅ Comprehensive testing environment

---

## ⚠️ WHERE WE DEVIATED FROM ARCHITECTURE ⚠️

### Phase 3: The Architectural Mistake

**Original Design Principle:**
> **Python orchestrates, Bash executes**
> - Python: High-level flow control, argument preparation
> - Bash scripts: LVM operations, mounts, chroot, restic execution
> - Benefit: Scripts can be run/tested independently, easier troubleshooting

**What We Did Wrong:**

**File:** `src/resticlvm/orchestration/data_classes.py`

We added `_run_lvm_backup()` and `_run_standard_backup()` methods that **bypassed the bash scripts entirely** and made direct subprocess calls to:
- `lvcreate` (snapshot creation)
- `mount` (mounting snapshots)
- `restic` (backups)
- `umount` (unmounting)
- `lvremove` (cleanup)

**Original (Correct) Approach:**
```python
def run(self):
    """Execute backup by calling bash script."""
    for repo in self.repositories:
        cmd = ["bash", str(self.script_path)] + self.get_args_list_for_repo(repo)
        subprocess.run(cmd, check=True)
```

**What We Implemented (WRONG):**
```python
def run(self):
    """Execute backup with Python handling everything."""
    if self.category in ["logical_volume_root", "logical_volume_nonroot"]:
        self._run_lvm_backup()  # ❌ Python does LVM operations
    else:
        self._run_standard_backup()  # ❌ Python does mount operations
    
def _run_lvm_backup(self):
    # ❌ Direct subprocess calls instead of calling bash scripts
    subprocess.run(["lvcreate", ...])
    subprocess.run(["mount", ...])
    subprocess.run(["restic", ...])
    subprocess.run(["umount", ...])
    subprocess.run(["lvremove", ...])
```

**Why This Was Wrong:**
1. ❌ Bash scripts become unused/dead code
2. ❌ Can't manually run/test individual backup operations
3. ❌ LVM error messages harder to debug
4. ❌ Violates single responsibility principle
5. ❌ Duplicates logic that already exists in carefully crafted bash scripts
6. ❌ Loses chroot functionality (root backups store wrong paths)

**Additional Problems Discovered:**
- **Path Issue:** Backing up `/mnt/resticlvm_lv_root_snapshot_*` instead of `/`
  - Old bash script uses chroot to make paths relative
  - New Python code backed up mount point directly
  - Restic snapshots stored wrong paths (not compatible with existing backups)

---

## What Should Have Been Done (Correct Approach)

### Modify Bash Scripts to Handle Multiple Repositories

**File:** `src/resticlvm/scripts/backup_lv_root.sh`

```bash
#!/bin/bash

# Add arrays for multiple repos
RESTIC_REPOS=()
RESTIC_PASSWORD_FILES=()

# Parse arguments (allow multiple -r and -p)
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r) RESTIC_REPOS+=("$2"); shift 2;;
        -p) RESTIC_PASSWORD_FILES+=("$2"); shift 2;;
        -g) VG_NAME="$2"; shift 2;;
        # ... other args
    esac
done

# Validate we have same number of repos and passwords
if [ ${#RESTIC_REPOS[@]} -ne ${#RESTIC_PASSWORD_FILES[@]} ]; then
    echo "Error: Number of repos must match number of password files"
    exit 1
fi

# CREATE SNAPSHOT ONCE
create_snapshot "$DRY_RUN" "$SNAPSHOT_SIZE" "$SNAP_NAME" "$VG_NAME" "$LV_NAME"
mount_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"
bind_repo_to_mounted_snapshot ...
bind_chroot_essentials_to_mounted_snapshot ...

# LOOP OVER REPOSITORIES
for i in "${!RESTIC_REPOS[@]}"; do
    RESTIC_REPO="${RESTIC_REPOS[$i]}"
    RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILES[$i]}"
    
    echo "▶️  Backing up to repo $((i+1))/${#RESTIC_REPOS[@]}: $RESTIC_REPO"
    
    # Build and run restic command for this repo
    CHROOT_REPO_FULL="$CHROOT_REPO_PATH/$(basename "$RESTIC_REPO")"
    RESTIC_CMD="export RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE && restic"
    RESTIC_CMD+=" ${EXCLUDE_ARGS[*]} ${RESTIC_TAGS[*]}"
    RESTIC_CMD+=" -r $CHROOT_REPO_FULL backup $BACKUP_SOURCE_PATH --verbose"
    
    run_in_chroot_or_echo "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$RESTIC_CMD"
done

# CLEANUP SNAPSHOT ONCE
unmount_chroot_bindings "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$CHROOT_REPO_FULL"
clean_up_snapshot "$DRY_RUN" "$SNAPSHOT_MOUNT_POINT" "$VG_NAME" "$SNAP_NAME"
```

### Python Stays Simple

**File:** `src/resticlvm/orchestration/data_classes.py`

```python
def run(self):
    """Execute backup by calling bash script with multiple -r/-p args."""
    if not self.repositories:
        print(f"⚠️  Warning: No repositories configured")
        return
    
    print(f"▶️  Running backup job: [{self.category}.{self.name}] -> {len(self.repositories)} repo(s)")
    
    # Build command with multiple -r and -p arguments
    cmd = ["bash", str(self.script_path)]
    
    # Add non-repo arguments first
    for pair in self.script_token_config_key_pairs:
        if pair.token not in ["-r", "-p"]:
            cmd += self.get_arg_entry(pair)
    
    # Add all repositories
    for repo in self.repositories:
        cmd += ["-r", str(repo.repo_path)]
        cmd += ["-p", str(repo.password_file)]
    
    # Execute bash script (it handles snapshot lifecycle)
    subprocess.run(cmd, check=True)
```

**Benefits of This Approach:**
- ✅ Bash scripts remain authoritative for LVM operations
- ✅ Can test bash scripts independently
- ✅ Chroot functionality preserved (correct paths)
- ✅ Python stays thin (orchestration only)
- ✅ Easier to debug (run `.sh` with `-x` flag)
- ✅ Dry-run mode still works

---

## Testing Results

**Test Suite:** 40 tests, all passing
- `test_backup_plan.py`: 10 tests
- `test_config_loader.py`: 4 tests
- `test_data_classes.py`: 12 tests
- `test_dispatch.py`: 7 tests
- `test_restic_repo.py`: 7 tests

**Manual Testing:**
- ✅ Local repositories (2 local repos per job)
- ✅ SFTP repositories (dedicated user per client)
- ✅ SSH agent integration
- ⚠️ Path storage issue (stores mount point path instead of `/`)

---

## Files to Keep for Next Attempt

### Definitely Keep (Good Changes)
1. **`EXAMPLE_SSH_SETUP.md`** - Comprehensive SSH documentation
2. **`src/resticlvm/orchestration/restic_repo.py`** - Multi-repo data model
3. **`src/resticlvm/orchestration/backup_plan.py`** - Config parsing (new format)
4. **`src/resticlvm/orchestration/prune_runner.py`** - Prune with repo lists
5. **`src/resticlvm/orchestration/privileges.py`** - SSH_AUTH_SOCK handling
6. **`test/test-configs/backup-test-new.toml`** - Example multi-repo config
7. **All test updates** - Extended test coverage

### Modify/Revert
1. **`src/resticlvm/orchestration/data_classes.py`**
   - Keep: `repositories` field, `get_args_list_for_repo()`
   - Revert: Remove `_run_lvm_backup()`, `_run_standard_backup()`, `_print_backup_summary()`
   - Fix: Make `run()` call bash scripts with multi-repo args

### Bash Scripts to Modify
1. **`src/resticlvm/scripts/backup_lv_root.sh`** - Add multi-repo loop
2. **`src/resticlvm/scripts/backup_lv_nonroot.sh`** - Add multi-repo loop
3. **`src/resticlvm/scripts/backup_path.sh`** - Add multi-repo loop

---

## Lessons Learned

### Technical Insights
1. **SSH Agent Pattern:** Persistent agent socket + helper scripts works well for automated backups
2. **Security Model:** Dedicated users per client + passphrase keys + agent = good balance
3. **TOML Arrays:** `[[table.array]]` syntax clean for multi-repo configs
4. **Backward Compatibility:** Important to maintain for existing deployments

### Architectural Lessons
1. **Stick to Design Principles:** "Python orchestrates, bash executes" exists for good reasons
2. **Don't Reinvent:** We had working bash scripts - should have extended them
3. **Chroot Matters:** Root backups need special handling for path correctness
4. **Test Early:** Should have tested actual backup paths sooner

### Process Insights
1. **Document Deviations:** When changing architecture, document why immediately
2. **Small Commits:** Would have been easier to revert if we committed after Phase 2
3. **Manual Testing:** Automated tests passed but actual backups showed path issues

---

## Recommendations for Next Implementation

### Step-by-Step Plan

1. **Create New Branch:** `multiple-repos-bash-approach`

2. **Phase 1: Copy Good Changes**
   - Copy data model changes from this branch
   - Copy SSH setup documentation
   - Copy test updates
   - Copy privileges.py changes

3. **Phase 2: Modify Bash Scripts**
   - Update argument parsing to accept multiple `-r` and `-p`
   - Add validation (same count of repos and passwords)
   - Add loop over repositories
   - Keep single snapshot/mount lifecycle
   - Test scripts manually with multiple repos

4. **Phase 3: Update Python Orchestration**
   - Modify `BackupJob.run()` to pass multiple `-r`/`-p` args
   - Keep it simple - just call the script
   - No direct subprocess calls to LVM/mount/restic

5. **Phase 4: Test Everything**
   - Run test suite
   - Manual backup tests
   - Verify correct paths in snapshots (`/` not `/mnt/...`)
   - Test with local + SFTP repos

6. **Phase 5: Documentation**
   - Update README.md with new config format
   - Document migration path from old to new format
   - Add example configs

---

## Git Strategy

### Current Branch
```bash
# Commit current state as reference
git add -A
git commit -m "Multi-repo implementation - reference only (architectural deviation)

This implementation works but violates the 'Python orchestrates, bash executes'
architectural principle. Python code directly calls lvcreate/mount/restic
instead of delegating to bash scripts.

DO NOT MERGE - Use as reference for correct bash-based approach.

See MULTI_REPO_IMPLEMENTATION_NOTES.md for details."

git push origin multiple-repos-per-snapshot
```

### Next Attempt
```bash
# Create new branch from main
git checkout main
git checkout -b multiple-repos-bash-approach

# Cherry-pick good commits from old branch
git cherry-pick <phase1-commit>  # Data model changes
git cherry-pick <phase2-commit>  # Config parsing

# Now modify bash scripts...
```

---

## Quick Reference: What Works vs What Doesn't

### ✅ Working (Keep These)
- Multi-repository data model
- TOML array configuration format
- Backward compatibility detection
- SSH agent integration
- Dedicated backup users
- Test infrastructure
- Repository uniqueness validation

### ❌ Broken (Fix These)
- Snapshot paths stored as `/mnt/...` instead of `/`
- Python bypassing bash scripts
- Direct subprocess calls to LVM tools
- No chroot for root backups

### 🔧 Needs Work (Modify These)
- Bash scripts need multi-repo loops
- Python needs simpler run() method
- May need to handle remount for standard_path differently

---

## Final Notes

This branch represents valuable exploration and learning, even though it took a wrong architectural turn. The SSH setup, security patterns, and data model design are all solid. The mistake was in Phase 3 where we tried to "optimize" by moving logic from bash to Python.

**Key Takeaway:** The bash scripts aren't just "legacy code" - they're the designed abstraction layer for complex LVM operations. Respect that design.

**Next Steps:**
1. Keep this branch for reference
2. Start fresh with bash-based approach
3. Reuse all the good discoveries from this branch
4. Get to production faster by not reinventing the wheel
