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

- Pre-1.0. The main correctness gaps from the production-readiness review have now
  shipped:
  - **Cleanup-on-failure (issue #24) — done.** A mid-run failure (restic error,
    CoW overflow, failed mount, `Ctrl-C`/`SIGTERM`) now unwinds the LVM snapshot
    and its mounts automatically via an idempotent `trap` (Part B, PR #68), and
    the chroot binds are detached from shared mount propagation with
    `--make-private` to avoid the `/dev` `EBUSY` leak (Part A, PR #65). Design:
    `docs/ISSUE_24_CLEANUP_FIX_PLAN.md`. (The old "run attended or it leaks"
    caveat no longer applies for catchable failures; a hard `kill -9` still can't
    be trapped.)
  - **#46 — done (PR #70).** A failing repository no longer aborts the job: every
    repo is attempted, and the job is marked failed if any failed.
  - **#57 — done (PR #71).** restic's output is no longer suppressed for later
    jobs after a remote (ssh) failure — the terminal's foreground process group is
    restored after each subprocess.
- **Failure-injection harness:** `dev/failure-injection/` (runbook:
  `docs/FAILURE_INJECTION_TESTING.md`) is the regression tool for snapshot
  teardown and multi-repo resilience. Run it in the `debian13-vm` VM — see
  `docs/FRASER_VM_READY.md`.
- **Next / open:**
  - **Within-job residual of #57** (follow-up issue): a remote repo failing
    *before* a local repo in the *same* job still suppresses the local repo's
    output, because a job is one subprocess so the foreground-pgroup restore only
    runs between jobs. Fix is a bash-level pgroup reset in the repo loop.
  - Remaining items in `docs/PRODUCTION_READINESS_REVIEW.md`.
- Issue #55 (warn on mismatched repo names across a volume's locations) shipped in 0.7.0.
