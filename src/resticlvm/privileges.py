"""
Handles privilege escalation by ensuring the script is running as root.

If the current process is not root, it re-executes itself using sudo.
"""

import os
import subprocess
import sys


def ensure_running_as_root():
    """Ensure the current process is running with root privileges.

    If not running as root, the script re-executes itself with sudo. If
    privilege escalation fails, the program exits with an error.

    Raises:
        subprocess.CalledProcessError: If sudo fails to elevate privileges.
    """
    if os.geteuid() != 0:
        print("🔐 Root privileges required. Elevating with sudo...\n")
        try:
            # Re-run the current script with sudo
            subprocess.check_call(["sudo", sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to elevate privileges: {e}")
            sys.exit(1)
        sys.exit(0)  # Important: exit the current non-root process
