import os
import subprocess
import sys


def ensure_running_as_root():
    if os.geteuid() != 0:
        print("🔐 Root privileges required. Elevating with sudo...\n")
        try:
            # Re-run the current script with sudo
            subprocess.check_call(["sudo", sys.executable] + sys.argv)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to elevate privileges: {e}")
            sys.exit(1)
        sys.exit(0)  # Important: exit the current non-root process
