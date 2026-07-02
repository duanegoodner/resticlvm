"""Tests for the backup_plan module."""

import tempfile
from pathlib import Path

import pytest

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

[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
restic_repo = "/srv/backup/root"
restic_password_file = "/tmp/password.txt"
backup_source_path = "/"
exclude_paths = ["/dev", "/proc", "/sys"]
prune_policy = "standard"

[standard_path.boot]
backup_source_path = "/boot"
restic_repo = "/srv/backup/boot"
restic_password_file = "/tmp/password.txt"
exclude_paths = []
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
    assert isinstance(plan.full_config, dict)
    assert plan.dry_run is False
    assert "logical_volume_root" in plan.full_config
    assert "standard_path" in plan.full_config


def test_backup_plan_dry_run_mode(temp_config_file):
    """Test BackupPlan with dry_run enabled."""
    plan = BackupPlan(config_path=temp_config_file, dry_run=True)
    assert plan.dry_run is True


def test_backup_plan_create_backup_job_logical_volume(temp_config_file):
    """Test creating a backup job for logical_volume_root category."""
    plan = BackupPlan(config_path=temp_config_file)
    
    job = plan.create_backup_job(category="logical_volume_root", name="root")
    
    assert isinstance(job, BackupJob)
    assert job.category == "logical_volume_root"
    assert job.name == "root"
    assert job.script_name == "backup_lv_root.sh"
    assert job.config["vg_name"] == "vg0"
    assert job.config["lv_name"] == "lv_root"
    assert job.config["restic_repo"] == "/srv/backup/root"


def test_backup_plan_create_backup_job_standard_path(temp_config_file):
    """Test creating a backup job for standard_path category."""
    plan = BackupPlan(config_path=temp_config_file)
    
    job = plan.create_backup_job(category="standard_path", name="boot")
    
    assert isinstance(job, BackupJob)
    assert job.category == "standard_path"
    assert job.name == "boot"
    assert job.script_name == "backup_path.sh"
    assert job.config["backup_source_path"] == "/boot"



def test_backup_plan_create_backup_job_invalid_category(temp_config_file):
    """Test that invalid category raises ValueError."""
    plan = BackupPlan(config_path=temp_config_file)
    
    with pytest.raises(ValueError, match="Invalid backup category"):
        plan.create_backup_job(category="invalid_category", name="test")


def test_backup_plan_backup_jobs_property(temp_config_file):
    """Test the backup_jobs property returns all jobs."""
    plan = BackupPlan(config_path=temp_config_file)
    
    jobs = plan.backup_jobs
    
    assert len(jobs) == 2
    assert all(isinstance(job, BackupJob) for job in jobs)
    
    # Check that we have both expected jobs
    job_identifiers = {(job.category, job.name) for job in jobs}
    assert ("logical_volume_root", "root") in job_identifiers
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

[standard_path.home]
backup_source_path = "/home"
restic_repo = "/backup/home"
restic_password_file = "/tmp/pass.txt"
exclude_paths = [".cache"]
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

[standard_path.boot]
backup_source_path = "/boot"
exclude_paths = []

[[standard_path.boot.repositories]]
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


def test_backup_plan_prune_policy_skipped_in_jobs_list():
    """The prune_policy section does not produce a backup job."""
    toml_content = """
[prune_policy.standard]
keep_last = 10
keep_daily = 7
keep_weekly = 4
keep_monthly = 6
keep_yearly = 1

[logical_volume_root.root]
vg_name = "vg0"
lv_name = "lv_root"
snapshot_size = "2G"
backup_source_path = "/"
exclude_paths = []

[[logical_volume_root.root.repositories]]
repo_path = "/srv/backup/root"
password_file = "/tmp/password.txt"
prune_policy = "standard"

[standard_path.boot]
backup_source_path = "/boot"
exclude_paths = []

[[standard_path.boot.repositories]]
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

        assert len(jobs) == 2
        categories = {j.category for j in jobs}
        assert "prune_policy" not in categories
    finally:
        temp_path.unlink()


def test_backup_plan_invalid_prune_policy_reference():
    """Referencing a nonexistent prune policy raises ValueError."""
    toml_content = """
[standard_path.boot]
backup_source_path = "/boot"
exclude_paths = []

[[standard_path.boot.repositories]]
repo_path = "/srv/backup/boot"
password_file = "/tmp/password.txt"
prune_policy = "nonexistent"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        temp_path = Path(f.name)

    try:
        plan = BackupPlan(config_path=temp_path)
        with pytest.raises(ValueError, match="not found"):
            plan.backup_jobs
    finally:
        temp_path.unlink()


def test_backup_plan_old_single_repo_format_with_policy(temp_config_file):
    """Old single-repo format works when prune_policy is used."""
    plan = BackupPlan(config_path=temp_config_file)
    jobs = plan.backup_jobs

    root_job = next(j for j in jobs if j.name == "root")
    assert root_job.repositories[0].prune_keep_params.last == 10

    boot_job = next(j for j in jobs if j.name == "boot")
    assert boot_job.repositories[0].prune_keep_params.last == 5
