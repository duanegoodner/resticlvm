# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [0.1.2] — 2025-04-29

### 🚀 What's New
- None

### 🛠️ Changes and Improvements
- Added `Makefile` to streamline build, install, and release workflows.

### 🐛 Bug Fixes
- Corrected Python version requirement in `pyproject.toml`.
  - Now correctly specifies `requires-python = ">=3.11"`.
  - Prevents accidental installation under unsupported Python versions (e.g., 3.10).

### ⚙️ Upgrade Notes
- No user-facing changes. Existing backups and configs continue to work.

### 📚 Documentation Updates
- Instructions on installation methods in README

### 🔧 Internal / Maintenance
- Updated `.gitignore` to exclude `dist/`, `build/`, and `.egg-info` artifacts.



## [0.1.1] — 2025-04-29

### 🚀 What's New
- Snapshots tagged `protected` are now preserved automatically during pruning.

### 🛠️ Changes and Improvements
- Minor improvements to prune script behavior and dry-run handling.

### 🐛 Bug Fixes
None

### ⚙️ Upgrade Notes
- No configuration changes are required.
- Existing workflows continue to work normally.
- Snapshots manually tagged `protected` will not be pruned.

### 📚 Documentation Updates
- Updated README with instructions for tagging protected snapshots.

### 🔧 Internal / Maintenance
None




## [0.1.0] - 2025-04-28

### 🚀 What's New
- Initial public release
- Config-driven backup and prune tooling combining Restic and LVM
- Support for backing up:
  - Standard filesystem paths
  - Root logical volumes (with chroot snapshot backup)
  - Non-root logical volumes (direct snapshot backup)
- Dry-run support for both backup and prune operations
- Lightweight, modular design:
  - Python CLI wrapper
  - Bash scripts for system interactions
- Basic documentation and usage examples

### 🛠️ Changes and Improvements
None

### 🐛 Bug Fixes
None

### ⚙️ Upgrade Notes
None

### 📚 Documentation Updates
None

### 🔧 Internal / Maintenance
None








