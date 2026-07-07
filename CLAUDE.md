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

- Pre-1.0. Run **attended**: a mid-run failure can leak the LVM snapshot and its
  mounts (cleanup-on-failure is not yet automatic — this is issue #24, below).
- **Next major task: Critical #2 / issue #24** (the LVM cleanup trap). The most common
  leak is now root-caused: the `/dev` bind unmount intermittently fails `EBUSY` from
  shared mount propagation (observed on a real full-system run). Two-part fix — a quick
  `--make-private` hardening in `scripts/lib/mounts.sh`, plus the actual cleanup trap.
  - **Plan of attack: `docs/ISSUE_24_CLEANUP_FIX_PLAN.md`** (also references
    `docs/PRODUCTION_READINESS_REVIEW.md` Critical #2 and the 4 design questions in the
    issue).
  - VM with LVM is deployed on fraser (`debian13-vm`) — ready for failure-injection
    testing. Rebuild/reconnect: see `docs/FRASER_VM_READY.md`.
- **Queued bug fixes:** #46 (continue backing up to remaining repos when one fails)
  and #57 (verbose output suppressed after remote repo failure). Both are patches.
- Issue #55 (warn on mismatched repo names across a volume's locations) shipped in 0.7.0.
