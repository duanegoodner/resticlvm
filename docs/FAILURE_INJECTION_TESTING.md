# Failure-injection testing for LVM snapshot cleanup

A runbook for proving that a **mid-run failure leaves nothing behind** — no
leaked LVM snapshot, no leftover bind/snapshot mount, no stray temp dir — and
that `rlvm` still exits non-zero. This is the harness that verified the issue
[#24](https://github.com/duanegoodner/resticlvm/issues/24) cleanup trap, kept
around because it's the natural regression check for any future change to the
snapshot create/mount/teardown path (e.g. the multi-repo failure handling in
#46/#57).

The runnable scripts live in [`dev/failure-injection/`](../dev/failure-injection/).

> **Run this in a disposable VM, never on a real system.** Failure injection
> against live root LVM is unsafe. Use the Debian+LVM dev VM — see
> [`FRASER_VM_READY.md`](FRASER_VM_READY.md).

## What it checks

After each injected failure the harness asserts all of:

- `rlvm` exit code is **non-zero**;
- **0** snapshot LVs remain (`lvs | grep _snapshot_`);
- **0** `resticlvm` mounts remain (`mount | grep /tmp/resticlvm-`);
- **0** leftover temp dirs remain (`/tmp/resticlvm-*`).

## Prerequisites

- Root (LVM snapshot + chroot).
- `rlvm` installed. `sudo` scrubs `PATH`, so pass its absolute path as the first
  argument: `sudo bash verify_root.sh "$(command -v rlvm)"`.
- **Root path:** the target LV is mounted at `/`, and an initialized restic repo
  + password file exist. Defaults: `VG=vg0`, `LV=lv_root`,
  `REPO=/srv/backup/root-local`, `PW=/etc/resticlvm/restic-password.txt` —
  override via env vars.
- **Nonroot path:** free extents in `VG` (the harness creates a throwaway 1G LV
  and its snapshot). `setup_nonroot.sh` handles LV/fs/mount/payload/repo.

## Running it

Root path (5 scenarios):

```bash
sudo bash dev/failure-injection/verify_root.sh "$(command -v rlvm)"
```

Nonroot path (throwaway LV; 3 scenarios):

```bash
sudo bash dev/failure-injection/setup_nonroot.sh
sudo bash dev/failure-injection/verify_nonroot.sh "$(command -v rlvm)"
sudo bash dev/failure-injection/teardown_nonroot.sh          # when done
```

Each verify script prints a per-scenario table and a final `N passed, M failed`
summary (exit 0 iff all passed), and prints a control-run command using a
generated good config so you can confirm the happy path still succeeds cleanly.

## Scenarios

| Scenario | Path | How it's injected |
| --- | --- | --- |
| restic fails mid-run | root + nonroot | a repo with a wrong password file — restic fails *after* binds/mount are set up |
| bind step fails | root | a nonexistent local repo path → `mount --bind` fails |
| restic killed mid-backup | root + nonroot | `pkill -9 -x restic` once a backup is in progress |
| SIGTERM to the backup script | root + nonroot | `pkill -TERM -f backup_lv_*.sh`, then kill restic to unblock |
| SIGINT (Ctrl-C emulation) | root | `pkill -INT -f backup_lv_root.sh`, then kill restic to unblock |

The nonroot path additionally exercises **nested** mount-point cleanup
(`/tmp/resticlvm-<ts>/mnt/<...>`), which the root path (single-level mount point)
doesn't hit.

## Gotchas (learned the hard way)

- **Kill restic by exact name, `pkill -x restic` — never `pkill -f restic`.**
  The backup script's own command line contains `restic-password.txt` and the
  repo path, so an `-f` pattern matches and **SIGKILLs the script itself**.
  SIGKILL can't be trapped, so cleanup never runs and you get a *false* leak that
  looks like a real bug.
- **`lvremove` needs a retry window.** Right after a reader (restic) exits and
  the snapshot is unmounted, the device can stay transiently busy; a single
  `lvremove` fails while a retry a moment later succeeds. The cleanup does
  `udevadm settle` + retry — this was caught by the wrong-password scenario,
  which is the only one where restic actually reads the snapshot before failing.
- **Bash defers a trapped signal until the running foreground command returns.**
  So a `SIGTERM`/`SIGINT` sent only to the script won't act until the in-progress
  `restic` finishes. The signal scenarios therefore also kill `restic` to unblock
  the trap promptly. In real interactive use, `Ctrl-C` reaches the whole process
  group (including restic), so this happens naturally.
- **`SIGKILL` (`kill -9`) to the script can't be defended against** — no trap
  runs, so a hard kill of `rlvm`/the script can still leak. The trap covers
  every *catchable* exit (errors, `INT`/`TERM`/`HUP`, normal exit).

## Interpreting a failure

A `FAIL` row prints the offending leaked temp dir(s), then the harness
best-effort cleans up (lazy-unmount anything under `/tmp/resticlvm-*`,
`lvremove -f` any `_snapshot_` LV, remove temp dirs) so the next scenario starts
from a clean slate. If a run leaves anything behind, recover manually:

```bash
SNAP=/tmp/resticlvm-<ts>/<snapshot-dir>
sudo umount -l "$SNAP"/* 2>/dev/null; sudo umount -l "$SNAP" 2>/dev/null
sudo lvremove -f /dev/<vg>/<snapshot-name>
sudo rm -rf /tmp/resticlvm-*
```
