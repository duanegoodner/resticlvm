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
    assert boot_backup_job.restic_repo is not None


def test_run_boot_backup_job(boot_config):
    boot_backup_job = ResticPathBackupJob.from_config(config=boot_config)
    orig_num_snapshots = boot_backup_job.restic_repo.num_snapshots
    boot_backup_job.run()
    assert boot_backup_job.restic_repo.num_snapshots == orig_num_snapshots + 1


def test_root_backup_job_init(root_config):
    root_backup_job = ResticLVMBackupJob.from_config(config=root_config)
    assert root_backup_job.logical_volume.device_path.exists()
    assert len(root_backup_job.exclude_args) != 0
    assert len(root_backup_job.exclude_args) == len(
        root_config["exclude_paths"]
    )
    assert len(root_backup_job.restic_path_backup_jobs) == 1
    assert len(root_backup_job.restic_path_backup_jobs) == len(
        root_config["paths_for_backup"]
    )


def test_run_root_backup_job(root_config):
    root_backup_job = ResticLVMBackupJob.from_config(config=root_config)
    root_backup_job.run()


def test_storage_backup_init(storage_config):
    storage_backup_job = ResticLVMBackupJob.from_config(config=storage_config)
    assert storage_backup_job.logical_volume.device_path.exists()
    assert len(storage_backup_job.exclude_args) == 1
    assert len(storage_backup_job.exclude_paths) == 1
    assert storage_backup_job.exclude_paths[0].exists()
    assert len(storage_backup_job.restic_path_backup_jobs) == 1
    assert storage_backup_job.restic_path_backup_jobs[0].source.exists()
