"""Tests for the data_classes module."""

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from resticlvm.orchestration.data_classes import (
    BackupJob,
    JobResult,
    TokenConfigKeyPair,
)
from resticlvm.orchestration.restic_repo import (
    CopyDestination,
    ResticRepo,
    ResticPruneKeepParams,
)


def _make_prune_params():
    return ResticPruneKeepParams(last=10, daily=7, weekly=4, monthly=6, yearly=1)


def _make_job(repositories=None):
    """Build a minimal BackupJob suitable for exercising run()."""
    return BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[],
        config={},
        name="test_job",
        category="standard_path",
        repositories=repositories if repositories is not None else [],
    )


def test_token_config_key_pair_creation():
    """Test creating a TokenConfigKeyPair."""
    pair = TokenConfigKeyPair(token="-r", config_key="restic_repo")
    assert pair.token == "-r"
    assert pair.config_key == "restic_repo"


def test_token_config_key_pair_from_token_key_map():
    """Test creating TokenConfigKeyPair instances from a map."""
    token_key_map = {
        "-r": "restic_repo",
        "-p": "restic_password_file",
        "-s": "backup_source_path",
    }
    pairs = TokenConfigKeyPair.from_token_key_map(token_key_map)
    
    assert len(pairs) == 3
    assert all(isinstance(p, TokenConfigKeyPair) for p in pairs)
    
    # Check that all mappings are present
    tokens = {p.token for p in pairs}
    assert tokens == {"-r", "-p", "-s"}
    
    # Find specific pair
    repo_pair = next(p for p in pairs if p.token == "-r")
    assert repo_pair.config_key == "restic_repo"


def test_backup_job_creation():
    """Test creating a BackupJob instance."""
    config = {
        "restic_repo": "/srv/backup/test",
        "restic_password_file": "/tmp/password.txt",
        "backup_source_path": "/",
    }
    pairs = [
        TokenConfigKeyPair(token="-r", config_key="restic_repo"),
        TokenConfigKeyPair(token="-p", config_key="restic_password_file"),
        TokenConfigKeyPair(token="-s", config_key="backup_source_path"),
    ]
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=pairs,
        config=config,
        name="test_backup",
        category="standard_path",
        repositories=[],
        dry_run=False,
    )
    
    assert job.script_name == "backup_path.sh"
    assert job.name == "test_backup"
    assert job.category == "standard_path"
    assert job.dry_run is False


def test_backup_job_get_arg_entry_string():
    """Test get_arg_entry with a string value."""
    config = {"restic_repo": "/srv/backup/test"}
    pair = TokenConfigKeyPair(token="-r", config_key="restic_repo")
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="standard_path",
        repositories=[],
    )
    
    arg_entry = job.get_arg_entry(pair)
    assert arg_entry == ["-r", "/srv/backup/test"]


def test_backup_job_get_arg_entry_list():
    """Test get_arg_entry with a list value."""
    config = {"exclude_paths": ["/dev", "/proc", "/sys"]}
    pair = TokenConfigKeyPair(token="-e", config_key="exclude_paths")
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="standard_path",
        repositories=[],
    )
    
    arg_entry = job.get_arg_entry(pair)
    assert arg_entry == ["-e", "/dev /proc /sys"]


def test_backup_job_get_arg_entry_int():
    """Test get_arg_entry with an integer value."""
    config = {"snapshot_size": 2048}
    pair = TokenConfigKeyPair(token="-z", config_key="snapshot_size")
    
    job = BackupJob(
        script_name="backup_lv_root.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="lv_root",
        repositories=[],
    )
    
    arg_entry = job.get_arg_entry(pair)
    assert arg_entry == ["-z", "2048"]


def test_backup_job_get_arg_entry_unsupported_type():
    """Test that unsupported config value types raise TypeError."""
    config = {"invalid": {"nested": "dict"}}
    pair = TokenConfigKeyPair(token="-x", config_key="invalid")
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="standard_path",
        repositories=[],
    )
    
    with pytest.raises(TypeError, match="Unsupported type"):
        job.get_arg_entry(pair)


def test_backup_job_args_list():
    """Test generating the full args_list with repositories."""
    config = {
        "backup_source_path": "/boot",
        "exclude_paths": ["/boot/grub"],
    }
    pairs = [
        TokenConfigKeyPair(token="-s", config_key="backup_source_path"),
        TokenConfigKeyPair(token="-e", config_key="exclude_paths"),
    ]
    
    # Create a ResticRepo object
    repo = ResticRepo(
        repo_path=Path("/srv/backup/test"),
        password_file=Path("/tmp/password.txt"),
        prune_keep_params=ResticPruneKeepParams(
            last=10, daily=7, weekly=4, monthly=6, yearly=1
        ),
    )
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=pairs,
        config=config,
        name="boot",
        category="standard_path",
        repositories=[repo],
    )
    
    args = job.args_list
    # Now args should have non-repo args first, then -r/-p from repositories
    assert args == [
        "-s", "/boot",
        "-e", "/boot/grub",
        "-r", "/srv/backup/test",
        "-p", "/tmp/password.txt",
    ]


def test_backup_job_args_list_dry_run():
    """Test that args_list includes --dry-run when dry_run is True."""
    config = {
        "backup_source_path": "/boot",
        "exclude_paths": [],
    }
    pairs = [
        TokenConfigKeyPair(token="-s", config_key="backup_source_path"),
        TokenConfigKeyPair(token="-e", config_key="exclude_paths"),
    ]
    repo = ResticRepo(
        repo_path=Path("/srv/backup/test"),
        password_file=Path("/tmp/password.txt"),
        prune_keep_params=_make_prune_params(),
    )

    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=pairs,
        config=config,
        name="boot",
        category="standard_path",
        repositories=[repo],
        dry_run=True,
    )

    args = job.args_list
    assert args[-1] == "--dry-run"


def test_backup_job_cmd():
    """Test generating the full command list with repositories."""
    config = {}
    pairs = []
    
    # Create a ResticRepo object
    repo = ResticRepo(
        repo_path=Path("/srv/backup/test"),
        password_file=Path("/tmp/password.txt"),
        prune_keep_params=ResticPruneKeepParams(
            last=10, daily=7, weekly=4, monthly=6, yearly=1
        ),
    )
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=pairs,
        config=config,
        name="test",
        category="standard_path",
        repositories=[repo],
    )
    
    cmd = job.cmd
    assert cmd[0] == "bash"
    assert "backup_path.sh" in cmd[1]
    # Should have -r and -p from the repository
    assert cmd[2:] == ["-r", "/srv/backup/test", "-p", "/tmp/password.txt"]


# ─── JobResult / BackupJob.run() outcome reporting ──────────────────────────


def test_job_result_ok_property():
    """JobResult.ok is True only when the script succeeded and no copies failed."""
    assert JobResult("c", "n", script_ok=True, failed_copies=[]).ok is True
    assert JobResult("c", "n", script_ok=False, failed_copies=[]).ok is False
    assert JobResult("c", "n", script_ok=True, failed_copies=["/dest"]).ok is False


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_full_success(mock_run):
    """A clean backup with no copy destinations returns an ok JobResult."""
    job = _make_job()

    result = job.run()

    assert result.script_ok is True
    assert result.failed_copies == []
    assert result.ok is True
    mock_run.assert_called_once()


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_script_failure(mock_run):
    """A failed backup script returns a not-ok JobResult (no exception raised)."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "bash")

    result = job_result = _make_job().run()

    assert job_result.script_ok is False
    assert result.ok is False


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_script_missing(mock_run):
    """A missing script (FileNotFoundError) is reported as a failure, not raised."""
    mock_run.side_effect = FileNotFoundError("backup_path.sh")

    result = _make_job().run()

    assert result.script_ok is False
    assert result.ok is False


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_defer_copies_skips_copy(mock_run):
    """With defer_copies=True, copy operations are not run inline."""
    copy_dest = CopyDestination(
        repo_path="/srv/backup/remote",
        password_file=Path("/tmp/remote_pw.txt"),
        prune_keep_params=_make_prune_params(),
    )
    repo = ResticRepo(
        repo_path=Path("/srv/backup/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
        copy_destinations=[copy_dest],
    )

    result = _make_job(repositories=[repo]).run(defer_copies=True)

    assert result.script_ok is True
    assert result.failed_copies == []
    assert mock_run.call_count == 1  # only the backup script, no copy


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_deferred_copies(mock_run):
    """run_deferred_copies() executes copy operations separately."""
    copy_dest = CopyDestination(
        repo_path="/srv/backup/remote",
        password_file=Path("/tmp/remote_pw.txt"),
        prune_keep_params=_make_prune_params(),
    )
    repo = ResticRepo(
        repo_path=Path("/srv/backup/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
        copy_destinations=[copy_dest],
    )

    job = _make_job(repositories=[repo])
    failed = job.run_deferred_copies()

    assert failed == []
    assert mock_run.call_count == 1  # copy script only
    cmd = mock_run.call_args.kwargs.get("args") or mock_run.call_args[0][0]
    assert "copy_repo.sh" in str(cmd[1])


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_copy_failure(mock_run):
    """Backup succeeds but a copy fails: script_ok True, copy recorded, not ok."""
    copy_dest = CopyDestination(
        repo_path="/srv/backup/remote",
        password_file=Path("/tmp/remote_pw.txt"),
        prune_keep_params=_make_prune_params(),
    )
    repo = ResticRepo(
        repo_path=Path("/srv/backup/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
        copy_destinations=[copy_dest],
    )
    # First call = backup script (succeeds); second call = copy (fails).
    mock_run.side_effect = [
        mock.DEFAULT,
        subprocess.CalledProcessError(1, "copy_repo.sh"),
    ]

    result = _make_job(repositories=[repo]).run()

    assert result.script_ok is True
    assert result.failed_copies == ["/srv/backup/remote"]
    assert result.ok is False
    assert mock_run.call_count == 2


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_copy_passes_dry_run(mock_run):
    """Copy operations pass -n to copy_repo.sh when dry_run is True."""
    copy_dest = CopyDestination(
        repo_path="/srv/backup/remote",
        password_file=Path("/tmp/remote_pw.txt"),
        prune_keep_params=_make_prune_params(),
    )
    repo = ResticRepo(
        repo_path=Path("/srv/backup/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
        copy_destinations=[copy_dest],
    )
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[],
        config={},
        name="test_job",
        category="standard_path",
        repositories=[repo],
        dry_run=True,
    )

    job.run()

    assert mock_run.call_count == 2
    copy_cmd = mock_run.call_args_list[1].kwargs.get("args") or mock_run.call_args_list[1][0][0]
    assert "-n" in copy_cmd


# ─── Snapshot mount (batch mode, issue #84) ────────────────────────────────


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_without_snapshot_mount_does_not_add_flag(mock_run):
    """Without snapshot_mount, --snapshot-mount is absent from the command."""
    _make_job().run()

    cmd = mock_run.call_args.kwargs.get("args") or mock_run.call_args[0][0]
    assert "--snapshot-mount" not in cmd


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_with_snapshot_mount_appends_flag(mock_run):
    """When snapshot_mount is given, --snapshot-mount and path are appended."""
    _make_job().run(snapshot_mount="/tmp/resticlvm-20260717/snap")

    cmd = mock_run.call_args.kwargs.get("args") or mock_run.call_args[0][0]
    idx = cmd.index("--snapshot-mount")
    assert cmd[idx + 1] == "/tmp/resticlvm-20260717/snap"


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_snapshot_mount_none_is_same_as_omitted(mock_run):
    """Passing snapshot_mount=None explicitly is equivalent to omitting it."""
    _make_job().run(snapshot_mount=None)

    cmd = mock_run.call_args.kwargs.get("args") or mock_run.call_args[0][0]
    assert "--snapshot-mount" not in cmd


# ─── SSH_AUTH_SOCK threading ────────────────────────────────────────────────


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_preserves_existing_ssh_auth_sock(mock_run, monkeypatch):
    """An SSH_AUTH_SOCK already in the environment is respected, not overridden."""
    monkeypatch.setenv("SSH_AUTH_SOCK", "/custom/agent.sock")

    _make_job().run()

    env = mock_run.call_args.kwargs["env"]
    assert env["SSH_AUTH_SOCK"] == "/custom/agent.sock"


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_defaults_ssh_auth_sock_when_unset(mock_run, monkeypatch):
    """With no SSH_AUTH_SOCK set, the conventional root agent socket is used."""
    monkeypatch.delenv("SSH_AUTH_SOCK", raising=False)

    _make_job().run()

    env = mock_run.call_args.kwargs["env"]
    assert env["SSH_AUTH_SOCK"] == "/root/.ssh/ssh-agent.sock"


# ─── Native B2 credential loading ───────────────────────────────────────────


def _b2_repo():
    return ResticRepo(
        repo_path=Path("s3:s3.us-west-004.backblazeb2.com/bucket/path"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
    )


def test_uses_b2_detection():
    """_uses_b2 is True for an s3: repo, False for a local-only job."""
    assert _make_job(repositories=[_b2_repo()])._uses_b2() is True
    local = ResticRepo(
        repo_path=Path("/media/backups/local"),
        password_file=Path("/tmp/pw.txt"),
        prune_keep_params=_make_prune_params(),
    )
    assert _make_job(repositories=[local])._uses_b2() is False


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_b2_job_without_credentials_fails_isolated(mock_run, monkeypatch):
    """A B2 job with no creds fails as a JobResult; the script is never run."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setenv("RESTICLVM_B2_ENV", "/nonexistent/b2-env")

    result = _make_job(repositories=[_b2_repo()]).run()

    assert result.script_ok is False
    assert result.ok is False
    mock_run.assert_not_called()  # we fail before invoking restic


@mock.patch("resticlvm.orchestration.data_classes.subprocess.run")
def test_run_b2_job_loads_credentials_into_env(mock_run, monkeypatch):
    """B2 creds available in the environment are threaded to the subprocess."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    result = _make_job(repositories=[_b2_repo()]).run()

    assert result.script_ok is True
    env = mock_run.call_args.kwargs["env"]
    assert env["AWS_ACCESS_KEY_ID"] == "id"
    assert env["AWS_SECRET_ACCESS_KEY"] == "secret"
