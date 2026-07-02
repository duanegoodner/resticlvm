"""Tests for the restic_repo module."""

from pathlib import Path

from resticlvm.orchestration.restic_repo import (
    ResticPruneKeepParams,
    ResticRepo,
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
