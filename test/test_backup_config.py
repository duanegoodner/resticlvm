"""Tests for the backup_config module."""

import pytest

from resticlvm.orchestration.backup_config import (
    BackupConfig,
    BackupConfigFactory,
    CopyDestConfig,
    LvJobConfig,
    RepoConfig,
    StandardPathJobConfig,
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
        "standard_path": {
            "boot": {
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


def test_from_dict_parses_prune_policies():
    cfg = BackupConfigFactory(_minimal_config()).build()
    assert "standard" in cfg.prune_policies
    assert cfg.prune_policies["standard"] == STANDARD_PARAMS


def test_from_dict_parses_standard_path():
    cfg = BackupConfigFactory(_minimal_config()).build()
    assert "boot" in cfg.standard_paths
    job = cfg.standard_paths["boot"]
    assert isinstance(job, StandardPathJobConfig)
    assert job.backup_source_path == "/boot"
    assert job.exclude_paths == []
    assert len(job.repositories) == 1

    repo = job.repositories[0]
    assert isinstance(repo, RepoConfig)
    assert repo.repo_path == "/srv/backup/boot"
    assert repo.prune_keep_params == STANDARD_PARAMS


def test_from_dict_parses_logical_volume_root():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "logical_volume_root": {
            "root": {
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
    job = cfg.logical_volume_roots["root"]
    assert isinstance(job, LvJobConfig)
    assert job.vg_name == "vg0"
    assert job.lv_name == "lv_root"
    assert job.snapshot_size == "30G"
    assert job.exclude_paths == ["/dev", "/proc"]
    assert job.repositories[0].prune_keep_params == STANDARD_PARAMS


def test_from_dict_parses_logical_volume_nonroot():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "logical_volume_nonroot": {
            "data": {
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
    assert "data" in cfg.logical_volume_nonroots
    assert cfg.logical_volume_nonroots["data"].vg_name == "vg_storage"


def test_from_dict_multiple_policies():
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
        "standard_path": {
            "boot": {
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
    repos = cfg.standard_paths["boot"].repositories
    assert repos[0].prune_keep_params.last == 20
    assert repos[1].prune_keep_params.last == 3
    assert repos[1].prune_keep_params.yearly == 10


def test_from_dict_with_copy_destinations():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "standard_path": {
            "boot": {
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
    repo = cfg.standard_paths["boot"].repositories[0]
    assert len(repo.copy_destinations) == 1

    dest = repo.copy_destinations[0]
    assert isinstance(dest, CopyDestConfig)
    assert dest.repo_path == "sftp:host:/backup/boot"
    assert dest.prune_keep_params == STANDARD_PARAMS


def test_from_dict_missing_policy_raises():
    raw = {
        "standard_path": {
            "boot": {
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


def test_from_dict_empty_config():
    cfg = BackupConfigFactory({}).build()
    assert cfg.prune_policies == {}
    assert cfg.standard_paths == {}
    assert cfg.logical_volume_roots == {}
    assert cfg.logical_volume_nonroots == {}


def test_from_dict_empty_categories():
    raw = {"prune_policy": {"standard": STANDARD_POLICY}}
    cfg = BackupConfigFactory(raw).build()
    assert cfg.standard_paths == {}
    assert cfg.logical_volume_roots == {}
    assert cfg.logical_volume_nonroots == {}


def test_from_dict_multiple_repos_per_job():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "standard_path": {
            "boot": {
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
    repos = cfg.standard_paths["boot"].repositories
    assert len(repos) == 3
    assert repos[0].repo_path == "/srv/local/boot"
    assert repos[1].repo_path == "sftp:host:/backup/boot"
    assert repos[2].repo_path == "s3:bucket/boot"


def test_from_dict_exclude_paths_defaults_to_empty():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "standard_path": {
            "boot": {
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
    assert cfg.standard_paths["boot"].exclude_paths == []
