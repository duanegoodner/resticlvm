"""Tests for the restic_repo module."""

from pathlib import Path
from unittest import mock

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


def _make_prune_params():
    return ResticPruneKeepParams(last=5, daily=7, weekly=4, monthly=6, yearly=1)


def _b2_repo():
    return ResticRepo(
        repo_path=Path("s3:s3.us-west-004.backblazeb2.com/bucket/path"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
    )


def _local_repo():
    return ResticRepo(
        repo_path=Path("/media/backups/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
    )


# ─── Prune B2 credential loading ──────────────────────────────────────────


@mock.patch("resticlvm.orchestration.restic_repo.subprocess.run")
def test_prune_b2_repo_without_credentials_skips(mock_run, monkeypatch):
    """A B2 prune with no creds prints an error and never invokes restic."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setenv("RESTICLVM_B2_ENV", "/nonexistent/b2-env")

    _b2_repo().prune()

    mock_run.assert_not_called()


@mock.patch("resticlvm.orchestration.restic_repo.subprocess.run")
def test_prune_b2_repo_loads_credentials_into_env(mock_run, monkeypatch):
    """B2 creds available in the environment are threaded to the subprocess."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    _b2_repo().prune()

    env = mock_run.call_args.kwargs["env"]
    assert env["AWS_ACCESS_KEY_ID"] == "id"
    assert env["AWS_SECRET_ACCESS_KEY"] == "secret"


@mock.patch("resticlvm.orchestration.restic_repo.subprocess.run")
def test_prune_local_repo_no_b2_credentials_needed(mock_run, monkeypatch):
    """A local repo prune succeeds without any B2 credentials."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setenv("RESTICLVM_B2_ENV", "/nonexistent/b2-env")

    _local_repo().prune()

    mock_run.assert_called_once()


@mock.patch("resticlvm.orchestration.restic_repo.subprocess.run")
def test_prune_respects_existing_ssh_auth_sock(mock_run, monkeypatch):
    """SSH_AUTH_SOCK already set by the caller is not overwritten."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/custom/agent.sock")

    _local_repo().prune()

    env = mock_run.call_args.kwargs["env"]
    assert env["SSH_AUTH_SOCK"] == "/custom/agent.sock"
