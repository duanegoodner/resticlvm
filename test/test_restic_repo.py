"""Tests for the restic_repo module."""

from pathlib import Path

import pytest

from resticlvm.orchestration.restic_repo import (
    ResticPruneKeepParams,
    ResticRepo,
    confirm_unique_repos,
)


def test_restic_prune_keep_params_creation():
    """Test creating ResticPruneKeepParams."""
    params = ResticPruneKeepParams(
        last=10, daily=7, weekly=4, monthly=6, yearly=1
    )
    assert params.last == 10
    assert params.daily == 7
    assert params.weekly == 4
    assert params.monthly == 6
    assert params.yearly == 1


def test_restic_repo_creation():
    """Test creating a ResticRepo instance."""
    prune_params = ResticPruneKeepParams(
        last=10, daily=7, weekly=4, monthly=6, yearly=1
    )
    repo = ResticRepo(
        repo_path=Path("/srv/backup/test"),
        password_file=Path("/tmp/password.txt"),
        prune_keep_params=prune_params,
    )
    assert repo.repo_path == Path("/srv/backup/test")
    assert repo.password_file == Path("/tmp/password.txt")
    assert repo.prune_keep_params == prune_params


def test_confirm_unique_repos_success():
    """Test that unique repositories are accepted."""
    config = {
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/root",
                "restic_password_file": "/tmp/pass1.txt",
                "prune_keep_last": 10,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
        "standard_path": {
            "boot": {
                "restic_repo": "/srv/backup/boot",
                "restic_password_file": "/tmp/pass2.txt",
                "prune_keep_last": 5,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 2
    assert ("logical_volume_root", "root") in repos
    assert ("standard_path", "boot") in repos
    
    root_repo = repos[("logical_volume_root", "root")]
    assert root_repo.repo_path == Path("/srv/backup/root")
    assert root_repo.password_file == Path("/tmp/pass1.txt")
    assert root_repo.prune_keep_params.last == 10


def test_confirm_unique_repos_duplicate_fails():
    """Test that duplicate repository paths raise ValueError."""
    config = {
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/duplicate",
                "restic_password_file": "/tmp/pass1.txt",
                "prune_keep_last": 10,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
        "standard_path": {
            "boot": {
                "restic_repo": "/srv/backup/duplicate",  # Duplicate!
                "restic_password_file": "/tmp/pass2.txt",
                "prune_keep_last": 5,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
    }

    with pytest.raises(ValueError, match="Duplicate repo detected"):
        confirm_unique_repos(config)


def test_confirm_unique_repos_single_job():
    """Test confirm_unique_repos with a single job."""
    config = {
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/root",
                "restic_password_file": "/tmp/pass.txt",
                "prune_keep_last": 10,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        }
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 1
    assert ("logical_volume_root", "root") in repos
