"""Tests for the backup_config module."""

import pytest

from resticlvm.orchestration.backup_config import (
    BackupConfig,
    BackupConfigFactory,
    CopyDestConfig,
    RepoConfig,
    VolumeConfig,
    VolumeType,
)
from resticlvm.orchestration.restic_repo import ResticPruneKeepParams


STANDARD_POLICY = {
    "keep_last": 10,
    "keep_daily": 7,
    "keep_weekly": 4,
    "keep_monthly": 6,
    "keep_yearly": 1,
}

STANDARD_PARAMS = ResticPruneKeepParams(
    last=10, daily=7, weekly=4, monthly=6, yearly=1
)


def _minimal_config():
    """A small but complete raw config dict."""
    return {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "exclude_paths": [],
                "repositories": [
                    {
                        "repo_path": "/srv/backup/boot",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    }
                ],
            }
        },
    }


def test_parses_prune_policies():
    cfg = BackupConfigFactory(_minimal_config()).build()
    assert "standard" in cfg.prune_policies
    assert cfg.prune_policies["standard"] == STANDARD_PARAMS


def test_parses_standard_path_volume():
    cfg = BackupConfigFactory(_minimal_config()).build()
    assert "boot" in cfg.volumes
    vol = cfg.volumes["boot"]
    assert isinstance(vol, VolumeConfig)
    assert vol.volume_type == VolumeType.STANDARD_PATH
    assert vol.backup_source_path == "/boot"
    assert vol.exclude_paths == []
    assert vol.vg_name is None
    assert len(vol.repositories) == 1

    repo = vol.repositories[0]
    assert isinstance(repo, RepoConfig)
    assert repo.repo_path == "/srv/backup/boot"
    assert repo.prune_keep_params == STANDARD_PARAMS


def test_parses_lv_root_volume():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "root": {
                "volume_type": "lv_root",
                "vg_name": "vg0",
                "lv_name": "lv_root",
                "snapshot_size": "30G",
                "backup_source_path": "/",
                "exclude_paths": ["/dev", "/proc"],
                "repositories": [
                    {
                        "repo_path": "/srv/backup/root",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    }
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    vol = cfg.volumes["root"]
    assert vol.volume_type == VolumeType.LV_ROOT
    assert vol.vg_name == "vg0"
    assert vol.lv_name == "lv_root"
    assert vol.snapshot_size == "30G"
    assert vol.exclude_paths == ["/dev", "/proc"]
    assert vol.repositories[0].prune_keep_params == STANDARD_PARAMS


def test_parses_lv_nonroot_volume():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "data": {
                "volume_type": "lv_nonroot",
                "vg_name": "vg_storage",
                "lv_name": "lv_data",
                "snapshot_size": "10G",
                "backup_source_path": "/data",
                "exclude_paths": [],
                "repositories": [
                    {
                        "repo_path": "/srv/backup/data",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    }
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    assert "data" in cfg.volumes
    assert cfg.volumes["data"].volume_type == VolumeType.LV_NONROOT
    assert cfg.volumes["data"].vg_name == "vg_storage"


def test_multiple_policies():
    raw = {
        "prune_policy": {
            "frequent": {
                "keep_last": 20,
                "keep_daily": 14,
                "keep_weekly": 8,
                "keep_monthly": 12,
                "keep_yearly": 3,
            },
            "archival": {
                "keep_last": 3,
                "keep_daily": 1,
                "keep_weekly": 1,
                "keep_monthly": 12,
                "keep_yearly": 10,
            },
        },
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/srv/local/boot",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "frequent",
                    },
                    {
                        "repo_path": "sftp:host:/backup/boot",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "archival",
                    },
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    repos = cfg.volumes["boot"].repositories
    assert repos[0].prune_keep_params.last == 20
    assert repos[1].prune_keep_params.last == 3
    assert repos[1].prune_keep_params.yearly == 10


def test_copy_destinations():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/srv/backup/boot",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                        "copy_to": [
                            {
                                "repo": "sftp:host:/backup/boot",
                                "password_file": "/tmp/remote_pw.txt",
                                "prune_policy": "standard",
                            }
                        ],
                    }
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    repo = cfg.volumes["boot"].repositories[0]
    assert len(repo.copy_destinations) == 1

    dest = repo.copy_destinations[0]
    assert isinstance(dest, CopyDestConfig)
    assert dest.repo_path == "sftp:host:/backup/boot"
    assert dest.prune_keep_params == STANDARD_PARAMS


def test_missing_policy_raises():
    raw = {
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/srv/backup/boot",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "nonexistent",
                    }
                ],
            }
        },
    }
    with pytest.raises(ValueError, match="not found"):
        BackupConfigFactory(raw).build()


def test_invalid_volume_type_raises():
    raw = {
        "volume": {
            "boot": {
                "volume_type": "invalid",
                "backup_source_path": "/boot",
                "repositories": [],
            }
        },
    }
    with pytest.raises(ValueError):
        BackupConfigFactory(raw).build()


def test_empty_config():
    cfg = BackupConfigFactory({}).build()
    assert cfg.prune_policies == {}
    assert cfg.volumes == {}


def test_no_volumes():
    raw = {"prune_policy": {"standard": STANDARD_POLICY}}
    cfg = BackupConfigFactory(raw).build()
    assert cfg.volumes == {}


def test_multiple_repos_per_volume():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/srv/local/boot",
                        "password_file": "/tmp/pw1.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/boot",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "s3:bucket/boot",
                        "password_file": "/tmp/pw3.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    repos = cfg.volumes["boot"].repositories
    assert len(repos) == 3
    assert repos[0].repo_path == "/srv/local/boot"
    assert repos[1].repo_path == "sftp:host:/backup/boot"
    assert repos[2].repo_path == "s3:bucket/boot"


def test_exclude_paths_defaults_to_empty():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/srv/backup/boot",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    }
                ],
            }
        },
    }
    cfg = BackupConfigFactory(raw).build()
    assert cfg.volumes["boot"].exclude_paths == []
