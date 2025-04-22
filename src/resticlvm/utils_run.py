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


def run_with_sudo(cmd: list[str], password: str):
    """
    Run a command with sudo.

    Args:
        cmd (list[str]): The command to run (e.g., ["ls", "-l"]).
        password (str): If provided, used for sudo via stdin.
    """
    sudo_cmd = ["sudo", "-S"] + cmd

    try:
        result = subprocess.run(
            sudo_cmd,
            input=f"{password}\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            # capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Command failed")
        print("STDERR:", e.stderr)
        print("STDOUT:", e.stdout)
        exit(1)

    return result
