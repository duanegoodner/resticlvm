"""Tests for config_validator module."""

import logging

import pytest

from resticlvm.orchestration.backup_config import BackupConfigFactory
from resticlvm.orchestration.config_validator import (
    repo_name_from_path,
    validate_config,
    warn_on_validation_issues,
)


STANDARD_POLICY = {
    "keep_last": 10,
    "keep_daily": 7,
    "keep_weekly": 4,
    "keep_monthly": 6,
    "keep_yearly": 1,
}


# --- repo_name_from_path ---


@pytest.mark.parametrize(
    "repo_path, expected",
    [
        ("/srv/backup/efi-01", "efi-01"),
        ("/backup/resticlvm/efi-01/", "efi-01"),
        ("sftp:user@host:/data/resticlvm/efi-01", "efi-01"),
        (
            "s3:s3.us-west-004.backblazeb2.com/bucket/resticlvm/efi-01",
            "efi-01",
        ),
        ("sftp:user@host:/efi-01/", "efi-01"),
        ("s3:bucket/efi-01/", "efi-01"),
        ("/efi-01", "efi-01"),
    ],
)
def test_repo_name_from_path(repo_path, expected):
    assert repo_name_from_path(repo_path) == expected


# --- validate_config: matching names ---


def _build_config(raw):
    return BackupConfigFactory(raw).build()


def test_matching_repo_names_no_warnings():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "efi": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot/efi",
                "repositories": [
                    {
                        "repo_path": "/backup/efi-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/efi-01",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "s3:bucket/efi-01",
                        "password_file": "/tmp/pw3.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    assert validate_config(_build_config(raw)) == []


def test_single_repo_no_warnings():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/backup/boot-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    assert validate_config(_build_config(raw)) == []


def test_no_repos_no_warnings():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [],
            }
        },
    }
    assert validate_config(_build_config(raw)) == []


def test_empty_config_no_warnings():
    assert validate_config(_build_config({})) == []


# --- validate_config: mismatched names ---


def test_mismatched_repo_names_warns():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "efi": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot/efi",
                "repositories": [
                    {
                        "repo_path": "/backup/efi-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/egi-01",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    warnings = validate_config(_build_config(raw))
    assert len(warnings) == 1
    assert "efi" in warnings[0]
    assert "efi-01" in warnings[0]
    assert "egi-01" in warnings[0]


def test_mismatched_copy_dest_warns():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/backup/boot-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                        "copy_to": [
                            {
                                "repo": "sftp:host:/backup/boot-02",
                                "password_file": "/tmp/pw2.txt",
                                "prune_policy": "standard",
                            },
                        ],
                    },
                ],
            }
        },
    }
    warnings = validate_config(_build_config(raw))
    assert len(warnings) == 1
    assert "boot-01" in warnings[0]
    assert "boot-02" in warnings[0]


def test_matching_with_copy_dest_no_warnings():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "boot": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot",
                "repositories": [
                    {
                        "repo_path": "/backup/boot-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                        "copy_to": [
                            {
                                "repo": "sftp:host:/backup/boot-01",
                                "password_file": "/tmp/pw2.txt",
                                "prune_policy": "standard",
                            },
                        ],
                    },
                    {
                        "repo_path": "s3:bucket/boot-01",
                        "password_file": "/tmp/pw3.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    assert validate_config(_build_config(raw)) == []


def test_multiple_volumes_warns_only_mismatched():
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "efi": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot/efi",
                "repositories": [
                    {
                        "repo_path": "/backup/efi-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/efi-01",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                ],
            },
            "root": {
                "volume_type": "standard_path",
                "backup_source_path": "/",
                "repositories": [
                    {
                        "repo_path": "/backup/root-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/root-99",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                ],
            },
        },
    }
    warnings = validate_config(_build_config(raw))
    assert len(warnings) == 1
    assert "root" in warnings[0]
    assert "root-01" in warnings[0]
    assert "root-99" in warnings[0]


# --- warn_on_validation_issues logs warnings ---


def test_warn_on_validation_issues_logs(caplog):
    raw = {
        "prune_policy": {"standard": STANDARD_POLICY},
        "volume": {
            "efi": {
                "volume_type": "standard_path",
                "backup_source_path": "/boot/efi",
                "repositories": [
                    {
                        "repo_path": "/backup/efi-01",
                        "password_file": "/tmp/pw.txt",
                        "prune_policy": "standard",
                    },
                    {
                        "repo_path": "sftp:host:/backup/egi-01",
                        "password_file": "/tmp/pw2.txt",
                        "prune_policy": "standard",
                    },
                ],
            }
        },
    }
    config = _build_config(raw)
    with caplog.at_level(logging.WARNING):
        warn_on_validation_issues(config)

    assert len(caplog.records) == 1
    assert "efi" in caplog.records[0].message
    assert caplog.records[0].levelno == logging.WARNING
