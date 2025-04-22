from pathlib import Path
from resticlvm.restic_classes import ResticRepo


def test_restic_repo_init():
    boot_repo = ResticRepo(
        repo_path=Path("/backups/resticlvm/restic-boot"),
        password_file=Path("/home/duane/resticlvm/test/test_password.txt"),
    )
    assert len(boot_repo.base_command) == 4
    assert isinstance(boot_repo.snapshots_as_json, (type(None), list))
    assert isinstance(boot_repo.latest_snapshot, (type(None), str))
    assert boot_repo.num_snapshots is not None
