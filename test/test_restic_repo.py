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
    
    # Each job should have a list of repos
    root_repos = repos[("logical_volume_root", "root")]
    assert isinstance(root_repos, list)
    assert len(root_repos) == 1
    assert root_repos[0].repo_path == Path("/srv/backup/root")
    assert root_repos[0].password_file == Path("/tmp/pass1.txt")
    assert root_repos[0].prune_keep_params.last == 10


def test_confirm_unique_repos_duplicate_fails():
    """Test that duplicate repository paths within the same job raise ValueError."""
    config = {
        "logical_volume_root": {
            "root": {
                "repositories": [
                    {
                        "repo_path": "/srv/backup/duplicate",
                        "password_file": "/tmp/pass1.txt",
                        "prune_keep_last": 10,
                        "prune_keep_daily": 7,
                        "prune_keep_weekly": 4,
                        "prune_keep_monthly": 6,
                        "prune_keep_yearly": 1,
                    },
                    {
                        "repo_path": "/srv/backup/duplicate",  # Duplicate within same job!
                        "password_file": "/tmp/pass2.txt",
                        "prune_keep_last": 5,
                        "prune_keep_daily": 7,
                        "prune_keep_weekly": 4,
                        "prune_keep_monthly": 6,
                        "prune_keep_yearly": 1,
                    }
                ]
            }
        }
    }

    with pytest.raises(ValueError, match="Duplicate repo within job"):
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
    assert len(repos[("logical_volume_root", "root")]) == 1


def test_confirm_unique_repos_new_format_multiple_repos():
    """Test confirm_unique_repos with new format having multiple repos per job."""
    config = {
        "logical_volume_root": {
            "root": {
                "repositories": [
                    {
                        "repo_path": "/srv/backup/root-a",
                        "password_file": "/tmp/pass1.txt",
                        "prune_keep_last": 10,
                        "prune_keep_daily": 7,
                        "prune_keep_weekly": 4,
                        "prune_keep_monthly": 6,
                        "prune_keep_yearly": 1,
                    },
                    {
                        "repo_path": "/srv/backup/root-b",
                        "password_file": "/tmp/pass2.txt",
                        "prune_keep_last": 5,
                        "prune_keep_daily": 7,
                        "prune_keep_weekly": 4,
                        "prune_keep_monthly": 6,
                        "prune_keep_yearly": 1,
                    }
                ]
            }
        }
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 1
    root_repos = repos[("logical_volume_root", "root")]
    assert len(root_repos) == 2
    assert root_repos[0].repo_path == Path("/srv/backup/root-a")
    assert root_repos[1].repo_path == Path("/srv/backup/root-b")


def test_confirm_unique_repos_same_repo_different_jobs():
    """Test that same repo path can be used in different jobs."""
    config = {
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/shared",
                "restic_password_file": "/tmp/pass.txt",
                "prune_keep_last": 10,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
        "standard_path": {
            "boot": {
                "restic_repo": "/srv/backup/shared",  # Same repo, different job - OK
                "restic_password_file": "/tmp/pass.txt",
                "prune_keep_last": 5,
                "prune_keep_daily": 7,
                "prune_keep_weekly": 4,
                "prune_keep_monthly": 6,
                "prune_keep_yearly": 1,
            }
        },
    }

    # Should not raise - same repo across different jobs is allowed
    repos = confirm_unique_repos(config)
    assert len(repos) == 2
    assert ("logical_volume_root", "root") in repos
    assert ("standard_path", "boot") in repos
