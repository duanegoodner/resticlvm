# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [0.1.3] — 2025-12-17

### � API Changes
- Changed recommended install method to use `pip install git+...` instead of downloading wheel files

### 📚 Documentation
- Updated README with git-based installation instructions
- Added instructions for development environment setup
- Simplified categories within CHANGELOG entries (no info removed; just rearranges)

### 🔧 Internal
- Added build helper `./tools/build-release.sh` (replaces `Makefile`)
- Added `./tools/environment.yml` for creating development environment


## [0.1.2] — 2025-04-29

### 🔌 API Changes
None

### 📚 Documentation
- Added installation method instructions to README

### 🔧 Internal
- Added `Makefile` to streamline build, install, and release workflows
- Corrected Python version requirement in `pyproject.toml` to `>=3.11`
- Updated `.gitignore` to exclude `dist/`, `build/`, and `.egg-info` artifacts


## [0.1.1] — 2025-04-29

### 🔌 API Changes
- Snapshots tagged `protected` are now preserved automatically during pruning

### 📚 Documentation
- Updated README with instructions for tagging protected snapshots

### 🔧 Internal
- Minor improvements to prune script behavior and dry-run handling


## [0.1.0] - 2025-04-28

### 🔌 API Changes
- Initial public release
- Config-driven backup and prune tooling combining Restic and LVM
- Support for backing up:
  - Standard filesystem paths
  - Root logical volumes (with chroot snapshot backup)
  - Non-root logical volumes (direct snapshot backup)
- Dry-run support for both backup and prune operations

### 📚 Documentation
- Initial README with basic documentation and usage examples

### 🔧 Internal
- Lightweight, modular design with Python CLI wrapper and Bash scripts for system interactions








