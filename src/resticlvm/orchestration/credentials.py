"""Load Backblaze B2 (S3-compatible) credentials for jobs that need them.

ResticLVM backs up to B2 via restic's S3-compatible backend (`s3:` repos), which
authenticates with ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``. Rather than
requiring a separate credential-loading wrapper, ``rlvm backup`` loads these itself
when — and only when — a job actually targets a B2 repo. Jobs with no B2 repo run
without any credentials present.

Credential precedence: values already in the environment win (e.g. set by a systemd
unit or exported in the shell); otherwise they are read from the b2-env file
(default ``/root/.config/resticlvm/b2-env``, overridable with ``RESTICLVM_B2_ENV``).
"""

import os
from pathlib import Path

DEFAULT_B2_ENV_FILE = Path("/root/.config/resticlvm/b2-env")
_AWS_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


class B2CredentialsError(Exception):
    """Raised when a B2 (s3:) repo needs credentials that cannot be found."""


def repo_uses_b2(repo_path) -> bool:
    """Return True if ``repo_path`` targets the B2 (S3-compatible) backend."""
    return str(repo_path).startswith("s3:")


def b2_env_file() -> Path:
    """Path to the b2-env credentials file (override with ``RESTICLVM_B2_ENV``)."""
    override = os.environ.get("RESTICLVM_B2_ENV")
    return Path(override) if override else DEFAULT_B2_ENV_FILE


def load_b2_credentials(env: dict) -> None:
    """Ensure ``AWS_*`` credentials are present in ``env`` for B2/S3 access.

    Respects credentials already in ``env``; otherwise fills them in from the
    b2-env file. Mutates ``env`` in place.

    Raises:
        B2CredentialsError: if both keys cannot be sourced from the environment
            or the b2-env file.
    """
    if all(env.get(key) for key in _AWS_KEYS):
        return  # already provided by the environment

    path = b2_env_file()
    file_creds = _parse_env_file(path) if path.is_file() else {}
    for key in _AWS_KEYS:
        if not env.get(key) and file_creds.get(key):
            env[key] = file_creds[key]

    missing = [key for key in _AWS_KEYS if not env.get(key)]
    if missing:
        raise B2CredentialsError(
            "B2 repository requires "
            f"{' and '.join(_AWS_KEYS)}, but {' and '.join(missing)} could not "
            f"be found (checked the environment and {path}).\n"
            f"   Provide them in {path} (export AWS_ACCESS_KEY_ID=... etc.) "
            "or as environment variables."
        )


def _parse_env_file(path: Path) -> dict:
    """Parse ``export KEY=VALUE`` / ``KEY=VALUE`` lines from a b2-env file.

    Handles the documented b2-env format (optional ``export``, optional quotes);
    it is not a full shell parser.
    """
    creds = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, sep, val = line.partition("=")
        if not sep:
            continue
        creds[key.strip()] = val.strip().strip('"').strip("'")
    return creds
