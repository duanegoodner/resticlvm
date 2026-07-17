# ResticLVM — agent context

Config-driven LVM-snapshot backups stored with Restic. A thin Python CLI/orchestration
layer (`src/resticlvm/orchestration`) drives focused Bash scripts
(`src/resticlvm/scripts`) that do the LVM/Restic work.

## Dev environment (pixi)

- `pixi install` — set up the env (Python, pytest, shellcheck, python-build; editable
  install of resticlvm).
- `pixi run test` — run the pytest suite (no VM needed).
- `pixi run lint-sh` — shellcheck the shell scripts.
- `pixi run release-build` — build the wheel + sdist.
- Use pixi, not conda/venv. See the README "Development" section for `pixi.lock`
  handling and the editable-install `--version` gotcha (force a rebuild with
  `rm -rf .pixi && pixi install` after a version bump).

## Running as root (require-root model)

- `rlvm backup` / `rlvm prune` require root and exit 1 otherwise — they do **not**
  self-elevate.
- From the pixi env, `sudo` scrubs `PATH`, so pin the entrypoint:
  `sudo "$(command -v rlvm)" backup`.
- `--config` is optional when `/etc/resticlvm/backup.toml` exists (or
  `$RESTICLVM_CONFIG` is set). Use `--config <path>` to override.

## Conventions

- PR-based: branch off `main`, open a PR with `gh`, never commit directly to `main`.
- The version is single-sourced in `pyproject.toml` and exposed at runtime via
  `importlib.metadata`.
- Releases follow `tools/release/RELEASE_CHECKLIST.md` (wheel + sdist; annotated tag;
  build with `pixi run release-build`).

## Status & next work

- Pre-1.0. All critical and high-priority items from the production-readiness
  review are resolved as of 0.8.0; incremental parent detection fixed in 0.9.0:
  - **#24 (cleanup-on-failure) — done.** Idempotent `trap` + `--make-private`
    mount isolation. Unattended/scheduled runs are now supported.
  - **#46 (continue on repo failure) — done.** Every repo is attempted; job is
    marked failed if any failed.
  - **#57 / #72 (terminal output after remote failure) — done.** Foreground
    process group restored after each subprocess (Python side) and between repos
    within a job (shell side).
  - **#77 (temp-dir parent leak) — done.**
  - **#81 (lv_nonroot parent detection + snapshot paths) — done.** Stable mount
    base (`/tmp/resticlvm`) + mount namespace (`unshare --mount`) so restic
    records real source paths and finds parent snapshots for incremental backups.
  - **#84 (cross-LV snapshot atomicity) — done.** All LVM snapshots are created
    before any backup runs, reducing cross-LV time delta to milliseconds.
    `SnapshotCoordinator` manages batch lifecycle with pre-flight VG space check,
    COW usage reporting, and signal-safe cleanup. Copy operations deferred until
    after snapshot teardown. Optional config: `[snapshot_settings]` in backup TOML.
- **Failure-injection harness:** `dev/failure-injection/` (runbook:
  `docs/FAILURE_INJECTION_TESTING.md`). Run in the `debian13-vm` VM — see
  `docs/FRASER_VM_READY.md`. Includes batch snapshot coordination tests
  (`verify_batch.sh`).
- **Remaining open:** eval/space-in-path fragility in shell scripts (deferred,
  see `docs/PRODUCTION_READINESS_REVIEW.md`).

## Deployment model

- Install resticlvm in a dedicated venv (e.g. `/opt/resticlvm`), not pixi/conda.
  Symlink the entrypoint onto the system PATH:
  `sudo ln -sf /opt/resticlvm/bin/rlvm /usr/local/bin/rlvm`.
  Example docs (`docs/EXAMPLE_SSH_SETUP.md`, `docs/EXAMPLE_B2_SETUP.md`,
  `tools/b2/README.md`) assume this symlink is in place.
- `restic` must be the **system** apt binary — it needs to be inside the root
  snapshot chroot for `lv_root` backups.
- Per-host config lives in `test/test-configs-private/<host>-backup.toml`
  (gitignored); install to `/etc/resticlvm/backup.toml` for production use.
- Three-tier repo structure per volume: local, anchor (sftp), Backblaze B2.
  Password files at `/root/.config/resticlvm/repo-creds/<host>-{local,anchor,b2}`.
  B2 credentials at `/root/.config/resticlvm/b2-env`.
- B2 setup uses scoped application keys with minimal capabilities.
- SSH to anchor uses a dedicated key via `root-ssh-agent` helper (socket at
  `/root/.ssh/ssh-agent.sock`); must `ssh-add` after reboot.

## Multi-machine rollout

- **fraser** — 0.9.0 deployed, manual backups working (all 3 tiers) as of 2026-07-17.
- **rudolph** — 0.9.0 deployed, manual backups working (all 3 tiers) as of 2026-07-17.
- **comet** — 0.9.0 deployed, manual backups working (all 3 tiers) as of 2026-07-17.
- **Cron/systemd scheduling** — next: all machines have manual backups working.
  Coordinate with `workstation-ops` repo `monitoring/` directory.
