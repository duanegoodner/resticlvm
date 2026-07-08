# ResticLVM — Production-Readiness Review

_Date: 2026-06-21_

A focused review done before ResticLVM becomes an essential part of a production
backup workflow. Scope was deliberately narrow: the core backup paths
(orchestration layer + the LVM-snapshot shell scripts), looking for **obvious,
high-value, or critical** issues — not an exhaustive audit and not a refactor.

## Status (updated 2026-07-08)

Both criticals and the `SSH_AUTH_SOCK` minor are **resolved**. This review is kept
for historical context; the original per-item analysis is preserved below with
resolution notes added inline.

- ✅ **Critical #1** (silent failure / exits 0 on failure) — resolved:
  `BackupJobRunner.run_all()` returns a failure count and prints a "BACKUP FAILED"
  summary, and `run()` calls `sys.exit(1)` when any job or copy fails.
- ✅ **Critical #2** (no cleanup trap → leaks snapshot/mounts) — resolved in
  **0.8.0** via issue #24 (PR #65 `--make-private`, PR #68 cleanup trap).
- ✅ **Minor** — `$SSH_AUTH_SOCK` unbound under `set -u` — resolved: all uses are
  now `${SSH_AUTH_SOCK:-}`.
- ⬜ **Minor** — restic command strings `eval`'d; paths with spaces break — still
  open, intentionally deferred (tracked separately).

> The earlier "run **attended only** until Critical #2 is fixed" directive **no
> longer applies**: a mid-run failure now cleans up automatically for any
> catchable exit (a hard `kill -9` still can't be trapped). Unattended/scheduled
> runs are supported as of 0.8.0.

---

## 🔴 Critical #1 — Backup failures are silent; the process exits 0 on failure

> **✅ Resolved.** `run_all()` collects results, prints a failure summary, and
> returns a failure count; `run()` exits non-zero when anything failed. Historical
> analysis follows.

**Where:** `src/resticlvm/orchestration/data_classes.py`, `BackupJob.run()`
(and `_run_copy_operations()`); `src/resticlvm/orchestration/backup_runner.py`,
`main()` / `BackupJobRunner.run_all()`.

**What:** `run()` catches the subprocess failure and only prints it — no re-raise,
no error flag:

```python
except subprocess.CalledProcessError as e:
    print(f"❌ Command failed [{self.category}.{self.name}]: {e}")   # swallowed
except FileNotFoundError as e:
    print(f"❌ Script not found [{self.category}.{self.name}]: {e}")  # swallowed
```

`run_all()` never inspects results and `main()` never sets an exit status, so the
whole run **exits 0 even if some or all backup jobs failed.** `_run_copy_operations()`
swallows `CalledProcessError` the same way. (Note: `run()`'s docstring claims it
`Raises CalledProcessError` — the implementation contradicts the docstring.)

**Why it's critical:** any scheduler or monitor keys off the exit code —
`systemd OnFailure=`, cron's exit status / `MAILTO`, a dead-man's-switch heartbeat
that pings on success. With a 0 exit on failure, a failed backup looks successful:
no failure alert fires, and a success-heartbeat is sent anyway. For a backup tool,
"reports success when it failed" is the worst observability failure mode — you
believe you're protected when you aren't. (The deployment this review was done for
relies specifically on exit-code-driven email + heartbeat alerting.)

**Recommended fix (small, no VM):**
- Make `run()` report outcome — either re-raise, or return a success/failure result
  (a bool, or a small result object capturing job name + status).
- Have `run_all()` collect failures across all jobs, print a clear end-of-run
  summary (which jobs/copies failed), and return a failure count.
- Have `main()` `sys.exit(1)` if anything failed.
- **Keep jobs isolated:** one failed job should still let the others run (current
  behavior, since failures are swallowed) — preserve that, just stop hiding it.
- Count copy-operation failures too.
- Add a unit test: mock `subprocess.run` to raise `CalledProcessError`, assert
  `run_all()` reports the failure and that `main()` exits non-zero. (The existing
  `test/` suite uses pytest; this fits there with no VM.)

---

## 🔴 Critical #2 — No cleanup trap: a mid-run failure leaks the LVM snapshot (and bind-mounts)

> **✅ Resolved in 0.8.0** — issue #24: `--make-private` hardening (PR #65) plus an
> idempotent `trap`-based cleanup armed right after snapshot creation (PR #68),
> verified with VM failure injection (`dev/failure-injection/`). Historical
> analysis follows.

**Where:** `src/resticlvm/scripts/backup_lv_nonroot.sh` and
`src/resticlvm/scripts/backup_lv_root.sh`; cleanup helpers in
`src/resticlvm/scripts/lib/lv_snapshots.sh` (`clean_up_snapshot`) and
`src/resticlvm/scripts/lib/mounts.sh` (`unmount_chroot_essentials`, etc.).

**What:** Both scripts run `set -euo pipefail` and clean up **only on the happy
path**. The snapshot is created near the top and cleaned up at the very end, with
no `trap` in between:

- `backup_lv_nonroot.sh`: `create_snapshot` (~line 100) → … → `clean_up_snapshot`
  (line 133).
- `backup_lv_root.sh`: `create_snapshot` (line 91), `mount_snapshot` (92),
  `bind_chroot_essentials_to_mounted_snapshot` (95), per-repo bind/restic loop
  (109–142) → `unmount_chroot_essentials` + `clean_up_snapshot` (146–147).

If anything between creation and cleanup fails — a transient `restic` error
(network blip, stale lock, remote hiccup), a full/invalidated snapshot, etc. —
`set -e` aborts the script and the cleanup never runs. Left behind:

- The **LVM snapshot** (which keeps growing against its origin until it fills and
  is invalidated, and consumes VG space).
- For the **root** path, dangling `/dev`, `/proc`, `/sys`, `resolv.conf`, SSH-socket,
  and repo **bind-mounts** under `/tmp/resticlvm-*` — which also pin the snapshot
  busy so it can't be `lvremove`d.

On an unattended/scheduled job, a single transient `restic` failure means
leftovers accumulate run after run — eventually filling the VG and/or wedging
future runs. **This is why ResticLVM should be run manually/attended only until
this is fixed.**

**Recommended fix (needs VM testing):**
- Define an idempotent, **best-effort** `cleanup()` and register it with
  `trap cleanup EXIT` (arm it immediately *after* the snapshot is created, so it
  doesn't fire before there's anything to clean).
- Best-effort semantics: guard each step (`mountpoint -q` before `umount`),
  fall back to `umount -l` (lazy) when busy, run `lvremove -f` regardless of prior
  step results, `rmdir` last — never let one failing step abort the rest.
- Root path: the trap must also unbind the repo and the `/dev`,`/proc`,`/sys`,
  `resolv.conf`, SSH-socket binds (reverse order) before removing the snapshot.
- Make the existing end-of-script cleanup a no-op-if-already-clean so it doesn't
  double-run alongside the trap.
- The current `clean_up_snapshot` (`lib/lv_snapshots.sh:41`) does plain
  `umount`/`lvremove`/`rmdir` with no guards — under `set -e` a failed `umount`
  stops the `lvremove`. Make it (or the trap version) best-effort.
- **Test in a VM** by injecting failures: point one repo at an unreachable host so
  `restic` fails mid-run, then assert no leftover snapshot (`lvs`) and no leftover
  mounts (`findmnt`/`mount`) afterward — for both the nonroot and root paths.

---

## 🟡 Minor

- **(✅ Resolved)** **`$SSH_AUTH_SOCK` referenced without a default under `set -u`**
  — `lib/command_runners.sh:36`, `lib/mounts.sh:115,167`. All references now use
  `${SSH_AUTH_SOCK:-}`, so running a script directly with no agent no longer
  crashes with `SSH_AUTH_SOCK: unbound variable`.
- **(⬜ Open — deferred)** **Command strings built then `eval`'d / run via `chroot bash -c`** —
  `backup_lv_root.sh`, `backup_lv_nonroot.sh` build the restic command (and flatten
  exclude/repo args) into a single string. Paths containing spaces would break.
  Works fine for tidy paths; flagged as a known fragility, **not** worth a refactor
  now. (Would be the thing to revisit if argument handling is ever reworked.)

---

## Suggested sequencing

1. **Critical #1** — implement + unit test now. Pure Python, safe, no VM.
2. **Critical #2** — file an Issue; tackle in a VM session. Highest operational
   risk, but needs LVM/mount testing to change safely.
3. **Minor items** — fold in alongside #2 (the `${SSH_AUTH_SOCK:-}` one is a
   two-line safety fix that could ride with #1 if convenient).
