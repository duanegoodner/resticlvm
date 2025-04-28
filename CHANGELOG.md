# Changelog

All notable changes to this project will be documented in this file.

This project follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] - 2025-04-28

### Added
- Initial public release.
- Config-driven backup and prune tooling combining Restic and LVM.
- Support for backing up:
  - Standard filesystem paths
  - Root logical volumes (with chroot snapshot backup)
  - Non-root logical volumes (direct snapshot backup)
- Dry-run support for both backup and prune operations.
- Lightweight, modular design:
  - Python CLI wrapper
  - Bash scripts for system interactions
- Basic documentation and usage examples.