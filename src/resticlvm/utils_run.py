import subprocess


def optional_run(cmd: list[str], dry_run: bool = False):
    """
    Run a command if not in dry run mode.

    Args:
        cmd (list[str]): The command and arguments to run.
        dry_run (bool): If True, only print the command without executing it.
    """
    cmd_str = " ".join(cmd)
    print(
        f"[DRY RUN] Pretending to run: {cmd_str}"
        if dry_run
        else f"Running: {cmd_str}"
    )
    if not dry_run:
        subprocess.run(cmd, check=True)


def run_with_sudo(cmd: list[str], dry_run: bool = False, password: str = None):
    """
    Run a command with sudo if not in dry run mode.

    Args:
        cmd (list[str]): The command and arguments to run.
        dry_run (bool): If True, only print the command without executing it.
        password (str): Sudo password if required.
    """
    if password:
        cmd = ["echo", password] + cmd
    subprocess.run(args=cmd, check=True)
