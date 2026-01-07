"""Tests for the data_classes module."""

from pathlib import Path

import pytest

from resticlvm.orchestration.data_classes import (
    BackupJob,
    TokenConfigKeyPair,
)
from resticlvm.orchestration.restic_repo import ResticRepo, ResticPruneKeepParams


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


def test_backup_job_get_arg_entry_bool():
    """Test get_arg_entry with a boolean value."""
    config = {"remount_readonly": True}
    pair = TokenConfigKeyPair(token="-m", config_key="remount_readonly")
    
    job = BackupJob(
        script_name="backup_path.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="standard_path",
        repositories=[],
    )
    
    arg_entry = job.get_arg_entry(pair)
    assert arg_entry == ["-m", "true"]


def test_backup_job_get_arg_entry_int():
    """Test get_arg_entry with an integer value."""
    config = {"snapshot_size": 2048}
    pair = TokenConfigKeyPair(token="-z", config_key="snapshot_size")
    
    job = BackupJob(
        script_name="backup_lv_root.sh",
        script_token_config_key_pairs=[pair],
        config=config,
        name="test",
        category="logical_volume_root",
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
