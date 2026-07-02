"""Tests for the backup_plan module."""

import tempfile
from pathlib import Path

import pytest

from resticlvm.orchestration.backup_config import BackupConfig
from resticlvm.orchestration.backup_plan import BackupPlan
from resticlvm.orchestration.data_classes import BackupJob


@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    toml_content = """
[prune_policy.standard]
keep_last = 10
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[prune_policy.light]
keep_last = 5
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[volume.root]
volume_type = "lv_root"
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys"]

[[volume.root.repositories]]
repo_path = "/srv/backup/root"
password_file = "/tmp/password.txt"
prune_policy = "standard"

[volume.boot]
volume_type = "standard_path"
backup_source_path = "/boot"
exclude_paths = []

[[volume.boot.repositories]]
repo_path = "/srv/backup/boot"
password_file = "/tmp/password.txt"
prune_policy = "light"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


def test_backup_plan_initialization(temp_config_file):
    """Test creating a BackupPlan instance."""
    plan = BackupPlan(config_path=temp_config_file, dry_run=False)

    assert plan.config_path == temp_config_file
    assert isinstance(plan._config, BackupConfig)
    assert plan.dry_run is False


def test_backup_plan_dry_run_mode(temp_config_file):
    """Test BackupPlan with dry_run enabled."""
    plan = BackupPlan(config_path=temp_config_file, dry_run=True)
    assert plan.dry_run is True


def test_backup_plan_job_lv_root(temp_config_file):
    """Test that an lv_root job is built correctly."""
    plan = BackupPlan(config_path=temp_config_file)
    jobs = plan.backup_jobs

    job = next(j for j in jobs if j.name == "root")
    assert isinstance(job, BackupJob)
    assert job.category == "lv_root"
    assert job.script_name == "backup_lv_root.sh"
    assert job.config["vg_name"] == "vg0"
    assert job.config["lv_name"] == "lv_root"


def test_backup_plan_job_standard_path(temp_config_file):
    """Test that a standard_path job is built correctly."""
    plan = BackupPlan(config_path=temp_config_file)
    jobs = plan.backup_jobs

    job = next(j for j in jobs if j.name == "boot")
    assert isinstance(job, BackupJob)
    assert job.category == "standard_path"
    assert job.script_name == "backup_path.sh"
    assert job.config["backup_source_path"] == "/boot"


def test_backup_plan_backup_jobs_property(temp_config_file):
    """Test the backup_jobs property returns all jobs."""
    plan = BackupPlan(config_path=temp_config_file)

    jobs = plan.backup_jobs

    assert len(jobs) == 2
    assert all(isinstance(job, BackupJob) for job in jobs)

    job_identifiers = {(job.category, job.name) for job in jobs}
    assert ("lv_root", "root") in job_identifiers
    assert ("standard_path", "boot") in job_identifiers


def test_backup_plan_backup_jobs_empty_config():
    """Test backup_jobs with an empty configuration."""
    toml_content = "# Empty config\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        plan = BackupPlan(config_path=temp_path)
        jobs = plan.backup_jobs
        assert len(jobs) == 0
    finally:
        temp_path.unlink()


def test_backup_plan_single_job_config():
    """Test BackupPlan with a config containing only one job."""
    toml_content = """
[prune_policy.minimal]
keep_last = 3
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[volume.home]
volume_type = "standard_path"
backup_source_path = "/home"
exclude_paths = [".cache"]

[[volume.home.repositories]]
repo_path = "/backup/home"
password_file = "/tmp/pass.txt"
prune_policy = "minimal"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        plan = BackupPlan(config_path=temp_path)
        jobs = plan.backup_jobs

        assert len(jobs) == 1
        assert jobs[0].category == "standard_path"
        assert jobs[0].name == "home"
    finally:
        temp_path.unlink()


def test_backup_plan_with_prune_policy():
    """Repos referencing a named prune policy resolve correctly."""
    toml_content = """
[prune_policy.standard]
keep_last = 10
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[volume.boot]
volume_type = "standard_path"
backup_source_path = "/boot"
exclude_paths = []

[[volume.boot.repositories]]
repo_path = "/srv/backup/boot"
password_file = "/tmp/password.txt"
prune_policy = "standard"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        plan = BackupPlan(config_path=temp_path)
        jobs = plan.backup_jobs

        assert len(jobs) == 1
        repo = jobs[0].repositories[0]
        assert repo.prune_keep_params.last == 10
        assert repo.prune_keep_params.daily == 7
        assert repo.prune_keep_params.yearly == 1
    finally:
        temp_path.unlink()


def test_backup_plan_invalid_prune_policy_reference():
    """Referencing a nonexistent prune policy raises ValueError at init."""
    toml_content = """
[volume.boot]
volume_type = "standard_path"
backup_source_path = "/boot"
exclude_paths = []

[[volume.boot.repositories]]
repo_path = "/srv/backup/boot"
password_file = "/tmp/password.txt"
prune_policy = "nonexistent"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="not found"):
            BackupPlan(config_path=temp_path)
    finally:
        temp_path.unlink()


def test_backup_plan_repos_have_correct_prune_params(temp_config_file):
    """Different jobs can reference different prune policies."""
    plan = BackupPlan(config_path=temp_config_file)
    jobs = plan.backup_jobs

    root_job = next(j for j in jobs if j.name == "root")
    assert root_job.repositories[0].prune_keep_params.last == 10

    boot_job = next(j for j in jobs if j.name == "boot")
    assert boot_job.repositories[0].prune_keep_params.last == 5
