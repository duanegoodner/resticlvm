"""Tests for the restic_repo module."""

from pathlib import Path

import pytest

from resticlvm.orchestration.restic_repo import (
    ResticPruneKeepParams,
    ResticRepo,
    confirm_unique_repos,
    resolve_prune_params,
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


# ─── resolve_prune_params ──────────────────────────────────────────────────


def test_resolve_prune_params_named_policy():
    """A prune_policy reference resolves from the full config."""
    entry = {"prune_policy": "standard"}
    full_config = {
        "prune_policy": {
            "standard": {
                "keep_last": 5,
                "keep_daily": 3,
                "keep_weekly": 2,
                "keep_monthly": 1,
                "keep_yearly": 0,
            }
        }
    }
    params = resolve_prune_params(entry, full_config)
    assert params == ResticPruneKeepParams(
        last=5, daily=3, weekly=2, monthly=1, yearly=0
    )


def test_resolve_prune_params_missing_policy_raises():
    """Referencing a nonexistent policy name is an error."""
    entry = {"prune_policy": "nonexistent"}
    with pytest.raises(ValueError, match="not found"):
        resolve_prune_params(entry, {})


def test_resolve_prune_params_no_policy_raises():
    """Missing prune_policy key is an error."""
    with pytest.raises(ValueError, match="must include"):
        resolve_prune_params({}, {})


# ─── confirm_unique_repos ─────────────────────────────────────────────────


def test_confirm_unique_repos_success():
    """Test that unique repositories are accepted."""
    config = {
        "prune_policy": {
            "standard": {
                "keep_last": 10,
                "keep_daily": 7,
                "keep_weekly": 4,
                "keep_monthly": 6,
                "keep_yearly": 1,
            },
        },
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/root",
                "restic_password_file": "/tmp/pass1.txt",
                "prune_policy": "standard",
            }
        },
        "standard_path": {
            "boot": {
                "restic_repo": "/srv/backup/boot",
                "restic_password_file": "/tmp/pass2.txt",
                "prune_policy": "standard",
            }
        },
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 2
    assert ("logical_volume_root", "root") in repos
    assert ("standard_path", "boot") in repos

    root_repos = repos[("logical_volume_root", "root")]
    assert isinstance(root_repos, list)
    assert len(root_repos) == 1
    assert root_repos[0].repo_path == Path("/srv/backup/root")
    assert root_repos[0].password_file == Path("/tmp/pass1.txt")
    assert root_repos[0].prune_keep_params.last == 10


def test_confirm_unique_repos_duplicate_fails():
    """Test that duplicate repository paths within the same job raise ValueError."""
    config = {
        "prune_policy": {
            "standard": {
                "keep_last": 10,
                "keep_daily": 7,
                "keep_weekly": 4,
                "keep_monthly": 6,
                "keep_yearly": 1,
            },
        },
        "logical_volume_root": {
            "root": {
                "repositories": [
                    {
                        "repo_path": "/srv/backup/duplicate",
                        "password_file": "/tmp/pass1.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "/srv/backup/duplicate",
                        "password_file": "/tmp/pass2.txt",
                        "prune_policy": "standard",
                    },
                ]
            }
        },
    }

    with pytest.raises(ValueError, match="Duplicate repo.*in job"):
        confirm_unique_repos(config)


def test_confirm_unique_repos_single_job():
    """Test confirm_unique_repos with a single job."""
    config = {
        "prune_policy": {
            "standard": {
                "keep_last": 10,
                "keep_daily": 7,
                "keep_weekly": 4,
                "keep_monthly": 6,
                "keep_yearly": 1,
            },
        },
        "logical_volume_root": {
            "root": {
                "restic_repo": "/srv/backup/root",
                "restic_password_file": "/tmp/pass.txt",
                "prune_policy": "standard",
            }
        }
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 1
    assert ("logical_volume_root", "root") in repos


def test_confirm_unique_repos_skips_prune_policy_key():
    """The prune_policy top-level key is skipped, not treated as a category."""
    config = {
        "prune_policy": {
            "standard": {
                "keep_last": 10,
                "keep_daily": 7,
                "keep_weekly": 4,
                "keep_monthly": 6,
                "keep_yearly": 1,
            }
        },
        "standard_path": {
            "boot": {
                "repositories": [
                    {
                        "repo_path": "/srv/backup/boot",
                        "password_file": "/tmp/pass.txt",
                        "prune_policy": "standard",
                    }
                ]
            }
        },
    }

    repos = confirm_unique_repos(config)
    assert len(repos) == 1
    assert ("standard_path", "boot") in repos
    assert repos[("standard_path", "boot")][0].prune_keep_params.last == 10


def test_confirm_unique_repos_with_named_policy():
    """Repos using prune_policy references resolve correctly."""
    config = {
        "prune_policy": {
            "archival": {
                "keep_last": 3,
                "keep_daily": 1,
                "keep_weekly": 1,
                "keep_monthly": 12,
                "keep_yearly": 5,
            }
        },
        "logical_volume_root": {
            "root": {
                "repositories": [
                    {
                        "repo_path": "/srv/backup/root",
                        "password_file": "/tmp/pass.txt",
                        "prune_policy": "archival",
                    }
                ]
            }
        },
    }

    repos = confirm_unique_repos(config)
    params = repos[("logical_volume_root", "root")][0].prune_keep_params
    assert params.last == 3
    assert params.monthly == 12
    assert params.yearly == 5
