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
    
    Also sets SSH_AUTH_SOCK for SSH agent support.

    Raises:
        subprocess.CalledProcessError: If sudo fails to elevate privileges.
    """
    # Set SSH_AUTH_SOCK for SSH agent (if not already set)
    if 'SSH_AUTH_SOCK' not in os.environ:
        agent_sock = '/root/.ssh/ssh-agent.sock'
        if os.path.exists(agent_sock):
            os.environ['SSH_AUTH_SOCK'] = agent_sock
    
    if os.geteuid() != 0:
        print("🔐 Root privileges required. Elevating with sudo...\n")
        try:
            # Preserve SSH_AUTH_SOCK when re-executing with sudo
            env = os.environ.copy()
            if 'SSH_AUTH_SOCK' in env:
                # Pass SSH_AUTH_SOCK to sudo
                subprocess.check_call(
                    ["sudo", f"SSH_AUTH_SOCK={env['SSH_AUTH_SOCK']}", sys.executable] + sys.argv
                )
            else:
                # Re-run the current script with sudo
                subprocess.check_call(["sudo", sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to elevate privileges: {e}")
            sys.exit(1)
        sys.exit(0)  # Important: exit the current non-root process
