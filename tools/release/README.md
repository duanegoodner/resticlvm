# Release Tools

Tools for building and packaging ResticLVM releases.

## Files

- `RELEASE_CHECKLIST.md` - Step-by-step, version-agnostic guide for cutting a release.
- `build-release.sh` - Builds the wheel + sdist and checks `Requires-Python`.

## Usage

Build inside the pixi env (which provides the `python-build` frontend):

```bash
pixi run release-build
```

This runs `build-release.sh` and produces `dist/resticlvm-X.Y.Z-py3-none-any.whl`
and `dist/resticlvm-X.Y.Z.tar.gz`.

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the full release process
(pre-flight validation, version bump, build, tag, GitHub release, post-release checks).
