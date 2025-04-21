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


def run_with_sudo(cmd: list[str], password: str = None):
    """
    Run a command with sudo.

    Args:
        cmd (list[str]): The command to run (e.g., ["ls", "-l"]).
        password (str): If provided, used for sudo via stdin.
    """
    sudo_cmd = ["sudo", "-S"] + cmd

    if password:
        result = subprocess.run(
            sudo_cmd,
            input=f"{password}\n",
            text=True,
            capture_output=True,
            check=True,
        )
    else:
        result = subprocess.run(sudo_cmd, check=True)

    return result
