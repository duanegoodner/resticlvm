import shlex
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from resticlvm.utils_run import optional_run, run_with_sudo


def bind_mount_onto(source: Path, target_base: Path) -> None:
    """Bind-mount a source path onto a matching location inside a target base path.

    This function creates a bind mount of the `source` path inside a target root
    directory (`target_base`) such that the mounted path matches the original
    source structure. The result is:
        target = target_base / source.relative_to('/')

    Both the source and the target_base paths must already exist; otherwise,
    a ValueError is raised.

    Example:
        source = Path("/media/data/repos")
        target_base = Path("/mnt/snapshot")
        → This will mount /media/data/repos at /mnt/snapshot/media/data/repos

    Args:
        source (Path): The absolute source path to bind mount.
        target_base (Path): The existing base path to "mount into".

    Raises:
        ValueError: If `source` or `target_base` do not exist.
        subprocess.CalledProcessError: If the mount command fails.
    """
    source = source.resolve(strict=True)
    target_base = target_base.resolve(strict=True)

    if not source.exists():
        raise ValueError(f"Source path does not exist: {source}")
    if not target_base.exists():
        raise ValueError(f"Target base path does not exist: {target_base}")

    # Compute the full target path: target_base + relative source path
    relative = source.relative_to("/")
    full_target = target_base / relative

    if source.is_dir():
        full_target.mkdir(parents=True, exist_ok=True)
    else:
        full_target.parent.mkdir(parents=True, exist_ok=True)
        if not full_target.exists():
            full_target.touch()

    cmd = ["mount", "--bind", str(source), str(full_target)]
    run_with_sudo(cmd=cmd, password="test123")


def prepare_for_chroot(
    chroot_base: Path, extra_sources: list[Path]
) -> list[Path]:
    """
    Bind mounts standard system paths and extra sources into a chroot base.

    Args:
        chroot_base (Path): The root of the chroot environment.
        extra_sources (list[Path]): Additional host paths to mount into the chroot.
        dry_run (bool): If True, do not actually mount, just print what would happen.

    Returns:
        list[Path]: A list of target paths where sources were bind-mounted.
    """
    bind_targets = []

    # Standard system paths to mount inside chroot
    system_paths = [Path("/dev"), Path("/proc"), Path("/sys")]

    for src in system_paths + extra_sources:
        target = bind_mount_onto(src, chroot_base)
        bind_targets.append(target)

    return bind_targets


def post_chroot_cleanup(bind_targets: list[Path]):
    """
    Unmounts a list of bind-mounted paths inside the chroot.

    Args:
        bind_targets (list[Path]): List of target paths to unmount.
        dry_run (bool): If True, only print the unmount commands.
    """
    for target in reversed(bind_targets):
        try:
            run_with_sudo(cmd=["umount", str(target)], password="test123")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to unmount {target}: {e}")


@contextmanager
def chroot_bind_environment(
    chroot_base: Path,
    extra_sources: list[Path],
) -> Iterator[list[Path]]:
    """
    Context manager that prepares and tears down a chroot bind-mount environment.

    Args:
        chroot_base (Path): The root of the chroot environment.
        extra_sources (List[Path]): Additional host paths to mount into the chroot.

    Yields:
        List[Path]: The list of bind-mounted target paths (inside chroot).
    """
    bind_targets = prepare_for_chroot(chroot_base, extra_sources)

    try:
        yield bind_targets
    finally:
        post_chroot_cleanup(bind_targets)


def run_chrooted_command(
    chroot_base: Path,
    command: list[str],
    sudo_password: str,
    check: bool = True,
    capture_output: bool = False,
):
    """
    Run a shell command inside a chroot environment using sudo.

    Args:
        chroot_base (Path): Path to the root of the chroot environment.
        command (List[str]): Command to run (as list of strings).
        sudo_password (str): Sudo password to pass via stdin.
        check (bool): Whether to raise CalledProcessError on failure.
        capture_output (bool): If True, captures and returns stdout/stderr.

    Returns:
        subprocess.CompletedProcess | None: Only returned if capture_output=True.
    """
    command_str = " ".join(shlex.quote(arg) for arg in command)

    base_cmd = [
        "sudo",
        "-S",
        "chroot",
        str(chroot_base),
        "/bin/bash",
        "-c",
        command_str,
    ]

    kwargs = {"input": sudo_password + "\n", "text": True, "check": check}

    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    result = subprocess.run(base_cmd, **kwargs)

    return result if capture_output else None
