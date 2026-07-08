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
  review are resolved as of 0.8.0:
  - **#24 (cleanup-on-failure) — done.** Idempotent `trap` + `--make-private`
    mount isolation. Unattended/scheduled runs are now supported.
  - **#46 (continue on repo failure) — done.** Every repo is attempted; job is
    marked failed if any failed.
  - **#57 / #72 (terminal output after remote failure) — done.** Foreground
    process group restored after each subprocess (Python side) and between repos
    within a job (shell side).
  - **#77 (temp-dir parent leak) — done.**
- **Failure-injection harness:** `dev/failure-injection/` (runbook:
  `docs/FAILURE_INJECTION_TESTING.md`). Run in the `debian13-vm` VM — see
  `docs/FRASER_VM_READY.md`.
- **Remaining open:** eval/space-in-path fragility in shell scripts (deferred,
  see `docs/PRODUCTION_READINESS_REVIEW.md`).
