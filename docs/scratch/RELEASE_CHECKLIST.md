# Release Checklist — v0.3.0

> **Scratch / work-in-progress doc.** Specific to the 0.3.0 release. After 0.3.0
> ships, we can distill a *generic* release checklist into `tools/release/`.
>
> Headline of this release: **backup runs now exit non-zero on failure** (Critical
> #1 from `docs/PRODUCTION_READINESS_REVIEW.md`). This is a behavior/contract
> change to the CLI's exit code, which is why it's a **minor** bump (0.2.1 → 0.3.0)
> rather than a patch.

---

## Phase 0 — Pre-flight validation (on rudolph, before any version bump)

- [ ] **PR #26 (Critical #1 fix) is merged into `main`.** No other substantive work outstanding.
- [ ] On rudolph: pull latest `main`, run a **real backup** with the new code → succeeds normally.
- [ ] On rudolph: **exit-code smoke test** — point a job at a bad/unreachable repo, run it,
      `echo $?` → expect **1** (was 0); confirm the end-of-run summary names the failed job.
- [ ] Clean `main` checkout: `pixi run test` → all tests pass.

> **Gate:** only proceed if the real backup *and* the exit-code test both behave correctly.

---

## Phase 1 — Release-prep + version bump (one PR off `main`)

Branch: e.g. `release-0.3.0`. This PR bundles the two release-infra improvements with
the actual bump + CHANGELOG. (Split into two PRs if you'd rather — infra first, bump
second — but one cohesive "cut 0.3.0" PR is fine.)

### 1a. Add the build frontend to pixi
- [ ] Add the conda-forge build frontend to `pixi.toml` dev deps so `python -m build` works in-env.
      Likely `pixi add python-build` — **verify** that's the package that provides `python -m build`
      (check `pixi run python -m build --version` afterward).
- [ ] (Optional, fits the `[tasks]` pattern) add a task, e.g.
      `release-build = "bash tools/release/build-release.sh"`, so the build runs inside the pixi env.
- [ ] `pixi install`; commit the updated `pixi.lock`.

### 1b. Single source of truth for the version
- [ ] Make `pyproject.toml` the **canonical** version source.
- [ ] Remove the `version` field from `pixi.toml` (the `[workspace] version` is optional and is
      only cosmetic metadata — the editable install gets its version from `pyproject.toml` at build
      time). **Verify** `pixi install` still succeeds with no `version` in `pixi.toml`.
  - If pixi turns out to require it, fall back to keeping it but document the lockstep rule; a
      fancier "derive from package `__version__`" approach is a possible *future* nicety, not for 0.3.0.

### 1c. Bump + CHANGELOG
- [ ] Set version to **0.3.0** in the canonical source (`pyproject.toml`; and `pixi.toml` only if
      1b left it in place).
- [ ] Add the `## [0.3.0]` section to `CHANGELOG.md` (draft below).
- [ ] `pixi run test` green.
- [ ] Open PR, merge into `main`.

---

## Phase 2 — Build

- [ ] `git checkout main && git pull` so you build the exact merged bump commit.
- [ ] Build inside the pixi env (now that 1a added the frontend):
      `pixi run release-build`  (or `pixi run bash tools/release/build-release.sh`).
- [ ] Verify output: wheel filename is `resticlvm-0.3.0-*.whl` and the `Requires-Python` check passes.

---

## Phase 3 — Tag + GitHub release (the script's reminder)

- [ ] `git tag v0.3.0`   (on the merged bump commit on `main`)
- [ ] `git push origin v0.3.0`
- [ ] Create the GitHub release for `v0.3.0`: paste the CHANGELOG 0.3.0 section as the notes,
      attach `dist/*.whl`.

---

## Phase 4 — Post-release sanity

- [ ] Fresh-install check: `pip install` the published wheel in a throwaway env →
      `rlvm-backup --help` works.
- [ ] Confirm the GitHub release shows the wheel and the correct `v0.3.0` tag.

---

## Proposed CHANGELOG entry (ready to paste)

```markdown
## [0.3.0] — 2026-06-22

### 🔌 API Changes
- **Backup runs now exit non-zero on failure.** Previously `rlvm-backup` exited 0
  even when a backup job or copy operation failed, silently defeating exit-code
  based alerting (systemd `OnFailure=`, cron `MAILTO`, success heartbeats). It now
  exits 1 if any job or copy fails. **Action:** if you had automation tolerating
  the old always-0 exit, expect real failures to now surface as exit 1.

### ✨ New Features
- **End-of-run summary**: after all jobs run, a summary lists how many jobs ran and
  names any failed jobs and failed copy destinations.
- Jobs remain isolated — one failed job still lets the others run; failures are
  reported rather than hidden.

### 🔧 Internal
- `BackupJob.run()` now returns a `JobResult`; `run_all()` returns a failure count.
- Added pixi dev environment (`pixi.toml` / `pixi.lock`); run tests with `pixi run test`.
- Single-sourced the package version in `pyproject.toml`.
- Added unit tests covering failure reporting, copy failures, job isolation, and the
  non-zero exit code.

### ⚠️ Known Limitations
- A mid-run failure can still leak the LVM snapshot and bind-mounts (no cleanup
  trap yet) — tracked in #24. Continue running ResticLVM **attended/manual only**
  until that is fixed.
```

---

## Notes / decisions parked for after 0.3.0

- Distill a **generic** release checklist into `tools/release/` (this doc is 0.3.0-specific scratch).
- Optional future versioning nicety: derive `pyproject` version dynamically from a package
  `__version__` if we ever want the version importable at runtime.
- **Clean up the "way of running".** The current invocation
  (`sudo env PATH=$PATH ./tools/b2/run-backup-with-b2.sh --config ...` + the wrapper's
  `RLVM_BACKUP=$(which rlvm-backup)`) is fragile: it depends on the right env being on `PATH`
  through `sudo`, and `which` can silently resolve to the wrong/old install. The B2 wrapper also
  conflates two concerns — loading B2 credentials and locating the `rlvm-backup` entrypoint.
  Rework as its own scoped change (not wedged into a release): e.g. make entrypoint resolution
  explicit/robust, separate credential-loading from invocation, and document a clean
  root-execution recipe for both pixi-env and pip-installed setups.
