"""Tests for native B2 (S3-compatible) credential loading."""

import pytest

from resticlvm.orchestration.credentials import (
    B2CredentialsError,
    _parse_env_file,
    b2_env_file,
    load_b2_credentials,
    repo_uses_b2,
)


@pytest.mark.parametrize("repo_path,expected", [
    ("s3:s3.us-west-004.backblazeb2.com/bucket/path", True),
    ("/media/backups/local", False),
    ("sftp:user@host:/backups", False),
    ("b2:bucket:path", False),  # native b2 backend uses different env vars
])
def test_repo_uses_b2(repo_path, expected):
    assert repo_uses_b2(repo_path) is expected


def test_b2_env_file_default_and_override(monkeypatch):
    monkeypatch.delenv("RESTICLVM_B2_ENV", raising=False)
    assert str(b2_env_file()) == "/root/.config/resticlvm/b2-env"
    monkeypatch.setenv("RESTICLVM_B2_ENV", "/custom/b2-env")
    assert str(b2_env_file()) == "/custom/b2-env"


def test_parse_env_file(tmp_path):
    f = tmp_path / "b2-env"
    f.write_text(
        "# a comment\n"
        'export AWS_ACCESS_KEY_ID="key-id"\n'
        "export AWS_SECRET_ACCESS_KEY=secret-key\n"
        "\n"
    )
    creds = _parse_env_file(f)
    assert creds["AWS_ACCESS_KEY_ID"] == "key-id"
    assert creds["AWS_SECRET_ACCESS_KEY"] == "secret-key"


def test_load_respects_existing_env(monkeypatch):
    """Credentials already in env are kept; the file is not consulted."""
    monkeypatch.setenv("RESTICLVM_B2_ENV", "/nonexistent/b2-env")
    env = {"AWS_ACCESS_KEY_ID": "from-env", "AWS_SECRET_ACCESS_KEY": "from-env"}
    load_b2_credentials(env)  # must not raise despite missing file
    assert env["AWS_ACCESS_KEY_ID"] == "from-env"


def test_load_reads_from_file(tmp_path, monkeypatch):
    f = tmp_path / "b2-env"
    f.write_text(
        'export AWS_ACCESS_KEY_ID="file-id"\n'
        'export AWS_SECRET_ACCESS_KEY="file-secret"\n'
    )
    monkeypatch.setenv("RESTICLVM_B2_ENV", str(f))
    env = {}
    load_b2_credentials(env)
    assert env["AWS_ACCESS_KEY_ID"] == "file-id"
    assert env["AWS_SECRET_ACCESS_KEY"] == "file-secret"


def test_load_raises_when_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("RESTICLVM_B2_ENV", str(tmp_path / "does-not-exist"))
    with pytest.raises(B2CredentialsError, match="B2 repository requires"):
        load_b2_credentials({})
