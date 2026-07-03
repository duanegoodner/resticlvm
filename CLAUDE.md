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
  mounts (cleanup-on-failure is not yet automatic).
- **Next immediate task: issue #55** — warn when repo names within a volume don't
  match across locations. New feature (config validation), minor version bump.
- **Queued bug fixes:** #46 (continue backing up to remaining repos when one fails)
  and #57 (verbose output suppressed after remote repo failure). Both are patches.
- **Next major task: Critical #2 / issue #24** (the LVM cleanup trap).
  - Background: `docs/PRODUCTION_READINESS_REVIEW.md` (Critical #2) and issue #24
    itself, which lists 4 open design questions.
  - Needs a VM with LVM for failure-injection testing: see `dev/vm-builder/`.
