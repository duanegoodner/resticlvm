# Release Checklist

A reusable, version-agnostic guide for cutting a ResticLVM release. Replace
`vX.Y.Z` with the target version throughout.

> **Versioning:** follow [Semantic Versioning](https://semver.org/). Pre-1.0, treat
> the **minor** slot as the breaking/behavioral slot and the patch as the safe-fix
> slot — a change to an externally-observable contract (exit codes, CLI flags, the
> way it's run) is a minor bump, not a patch.

---

## Phase 0 — Pre-flight validation (on the production host)

- [ ] All substantive changes for the release are merged into `main`.
- [ ] On the production host: pull latest `main`, set up/refresh the env
      (`pixi install`), and run a **real backup** → succeeds.
- [ ] Run any behavior-specific smoke tests for what changed this release
      (e.g. exit-code behavior, new flags).
- [ ] Clean `main` checkout: `pixi run test` → all tests pass.

> **Gate:** only proceed if the real backup and the relevant smoke tests pass.

---

## Phase 1 — Version bump + CHANGELOG (one PR off `main`)

- [ ] Branch off updated `main` (e.g. `release-X.Y.Z`).
- [ ] Bump the version in the **single source**, `pyproject.toml` (`version = "X.Y.Z"`).
      It is exposed at runtime via `importlib.metadata`, so nothing else needs editing.
- [ ] Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md`, using the standard
      blocks: `### 🔌 API Changes`, `### ✨ New Features`, `### 📚 Documentation`,
      `### 🔧 Internal`, `### ⚠️ Known Limitations` (omit empty ones, or write "None").
- [ ] `pixi run test` green.
- [ ] Open PR, merge into `main`.

---

## Phase 2 — Build

- [ ] `git checkout main && git pull` so you build the exact merged bump commit.
- [ ] `pixi run release-build` (runs `tools/release/build-release.sh` inside the
      pixi env — `python-build` is bundled there).
- [ ] Verify output: artifacts are `resticlvm-X.Y.Z-py3-none-any.whl` **and**
      `resticlvm-X.Y.Z.tar.gz`, and the `Requires-Python` check passes.

---

## Phase 3 — Tag + GitHub release

- [ ] `git tag -a vX.Y.Z -m "vX.Y.Z — <one-line headline>"` (annotated, on the
      merged bump commit on `main`).
- [ ] `git push origin vX.Y.Z`
- [ ] Create the GitHub release for `vX.Y.Z`: paste the CHANGELOG `[X.Y.Z]` section
      as the notes, and attach **both** the wheel and the sdist
      (`dist/resticlvm-X.Y.Z-py3-none-any.whl` and `dist/resticlvm-X.Y.Z.tar.gz`).

> **Standing rule:** every release attaches **wheel + sdist**. (GitHub also
> auto-attaches "Source code" tarballs from the tag — those are separate.)

---

## Phase 4 — Post-release sanity

- [ ] Fresh-install check: `pip install` the published wheel in a throwaway venv;
      confirm version `X.Y.Z` and that `rlvm-backup`/`rlvm-prune` import.
- [ ] Confirm the GitHub release shows both artifacts and the correct `vX.Y.Z` tag.
- [ ] If the README pins a "latest release" install tag, bump it to `vX.Y.Z`.
