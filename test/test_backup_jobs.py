import pytest
from pathlib import Path

from resticlvm.backup_jobs_new import ResticLVMBackupJob, ResticPathBackupJob
from resticlvm.config_loader import load_config


@pytest.fixture
def full_config():
    config_path = Path(__file__).parent / "resticlvm_config.toml"
    return load_config(path=config_path)


@pytest.fixture
def boot_config(full_config):
    return full_config["path_sources"]["boot"]


@pytest.fixture
def root_config(full_config):
    return full_config["logical_volume_sources"]["root"]


@pytest.fixture
def storage_config(full_config):
    return full_config["logical_volume_sources"]["storage"]


def test_boot_backup_job_init(boot_config):
    boot_backup_job = ResticPathBackupJob.from_config(config=boot_config)
    assert boot_backup_job.is_for_mount_point
    assert boot_backup_job.exclude_args == []
    assert boot_backup_job.backup_cmd == [
        "export",
        "RESTIC_PASSWORD_FILE=/home/duane/resticlvm/test/test_password.txt",
        "restic",
        "-r",
        str(Path("/backups/resticlvm/restic-boot")),
        "backup",
        str(Path("/boot")),
        "--verbose",
    ]


def test_root_backup_job_init(root_config):
    root_backup_job = ResticLVMBackupJob.from_config(config=root_config)


def test_storage_backup_init(storage_config):
    storage_backup_job = ResticLVMBackupJob.from_config(config=storage_config)
