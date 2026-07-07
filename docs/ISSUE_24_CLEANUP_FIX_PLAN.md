# Issue #24 — Cleanup-on-failure: root cause + fix plan

Working plan for [#24](https://github.com/duanegoodner/resticlvm/issues/24) ("Critical: no cleanup
trap — a mid-run failure leaks the LVM snapshot and bind-mounts"), informed by a real leak observed
during a full-system backup of `fraser` on 2026-07-05. See also
[`PRODUCTION_READINESS_REVIEW.md`](PRODUCTION_READINESS_REVIEW.md) (Critical #2).

## Background: two distinct problems

Issue #24 is really two things, and it's worth fixing them as separate PRs:

1. **A specific, intermittent failure mode** — the `/dev` bind unmount fails with `EBUSY` during
   otherwise-successful `lv_root` teardown, due to **shared mount propagation**. This is the trigger
   we actually hit. Fix is small and deterministic (**`--make-private`**).
2. **The structural gap** — there is no cleanup **trap**, so *any* mid-run failure (restic error,
   snapshot CoW overflow, a mount failure, `Ctrl-C`, OOM) aborts under `set -euo pipefail` before
   `clean_up_snapshot` runs, leaking the snapshot + bind-mounts. Fix is a real cleanup handler.

`--make-private` removes the most common everyday trigger; the trap is the actual close of #24. Do
both; neither substitutes for the other.

## Root cause of the observed leak (problem 1)

During the `fraser` backup, every `lv_root` restic repo backed up successfully, then teardown failed:

```
umount: /tmp/resticlvm-<ts>/vg0_lv0_snapshot_<ts>/dev: target is busy.
```

Only `/dev` failed — `/proc`, `/sys`, `/etc/resolv.conf`, the SSH-socket bind, and the local-repo
bind all unmounted cleanly. Diagnosis:

- The chroot binds are created with plain `mount --bind` and **inherit systemd's `shared`
  propagation** (`findmnt -o TARGET,PROPAGATION` shows `/`, `/dev`, `/proc`, `/sys` all `shared`).
- Unmounting a shared bind **propagates** to its peer group. The real `/dev` (devtmpfs) peer is busy
  because desktop processes have device nodes **mmap'd** (`/dev/dri/*`, `/dev/nvidia*`, `/dev/shm`),
  so the propagated unmount returns `EBUSY`. `/proc`/`/sys` peers aren't held that way, hence
  `/dev`-specific.
- It is a **race**: the same config leaked on one run and cleaned up fine on the very next identical
  run (depends on whether `/dev` is held at the instant of the propagated unmount). More likely on a
  desktop than a headless box.

Diagnostic gotchas (documented so future debugging doesn't go down the wrong path):
- `fuser -m <snap>/dev` is misleading — it matches the whole shared devtmpfs superblock and lists
  host desktop processes using the *real* `/dev`, not processes pinning the bind.
- `lsof` over the snapshot path returns nothing — consistent with "propagation, not an open fd."

## Fix plan

### Part A — `--make-private` (quick, deterministic)

In the bind-setup helper (`scripts/lib/mounts.sh`, `bind_chroot_essentials_to_mounted_snapshot` —
confirm exact name/location against current code), detach each bind from propagation immediately
after creating it:

```bash
mount --bind /dev  "$snap/dev"  && mount --make-private "$snap/dev"
mount --bind /proc "$snap/proc" && mount --make-private "$snap/proc"
mount --bind /sys  "$snap/sys"  && mount --make-private "$snap/sys"
# ...same for the /etc/resolv.conf and SSH-socket binds
```

With the binds `private`, teardown can't propagate into the host `/dev`, so the normal `umount`
won't hit `EBUSY`. This is the standard container-runtime approach. (A weaker alternative is
`umount -l`/`MNT_DETACH` in cleanup, but that papers over the race rather than removing it.)

**Scope:** `scripts/lib/mounts.sh` (bind setup). Applies to the `lv_root` path (which does the chroot
binds); confirm whether any non-root path binds `/dev`.

### Part B — cleanup trap (the real #24 fix)

Add a `trap`-based cleanup that unwinds whatever was created, on **every** exit path (success,
error, signal), in `scripts/lib/backup_lv_root.sh` (and the analogous non-root script). Requirements:

- Register the trap as soon as each resource is created (snapshot LV, mountpoint, each bind, each
  local-repo bind), and have it idempotently unwind in reverse order: unmount binds → unmount
  snapshot → `lvremove -y` the snapshot → `rmdir` the temp dir.
- Must be **idempotent** and safe to run when a resource was never created (guard each step).
- Must cover the multi-repo loop failure (issue #46 territory): a failing repo currently aborts the
  loop *and* skips cleanup — the trap fixes the cleanup half regardless of how #46 is resolved.
- Target the snapshot by its exact timestamped name (never a glob) when calling `lvremove`.
- Preserve the correct exit code (don't let cleanup mask the original failure).

Open design questions are listed in the GitHub issue (#24 lists 4). Resolve those in the PR
discussion.

## Testing strategy — in a VM, not on bare metal

Failure injection against real root LVM is unsafe, so this work is done in a disposable Debian+LVM
KVM VM built from [`dev/vm-builder/`](../dev/vm-builder/) (layout has `vg0-lv_root` with free extents,
a backup LV, a non-root data LV, and a standard partition). Host tooling setup for fraser is
documented in `workstation-ops/workstations/fraser/vm-dev-tooling.md`.

- **Part A verification:** run an `lv_root` backup; confirm teardown is clean and `findmnt` shows the
  chroot binds as `private` during the run.
- **Part B verification (failure injection):** each of these must leave **no** leaked snapshot/mounts
  (`sudo lvs | grep snapshot` and `mount | grep resticlvm` empty afterward), and return a non-zero
  exit code:
  - kill `restic` mid-backup;
  - force snapshot CoW overflow (undersize `snapshot_size` + write load);
  - break a bind/mount step;
  - `Ctrl-C` / `SIGTERM` mid-run;
  - a remote-repo failure partway through the multi-repo loop.

## References

- Issue #24 (this plan is mirrored in a comment there).
- `docs/PRODUCTION_READINESS_REVIEW.md` — Critical #2.
- Manual recovery when a leak does occur:
  ```bash
  SNAP=/tmp/resticlvm-<ts>/vg0_lv0_snapshot_<ts>
  sudo umount -l "$SNAP/dev"; sudo umount "$SNAP"
  sudo lvremove -y /dev/<vg>/<snapshot-name>
  sudo rm -rf "$(dirname "$SNAP")"
  ```
