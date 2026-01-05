"""
Defines core data classes used for running backup jobs in ResticLVM,
including token-to-config mappings and job execution logic.
"""

import importlib.resources as pkg_resources
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from resticlvm import scripts
from resticlvm.orchestration.restic_repo import ResticRepo


@dataclass
class TokenConfigKeyPair:
    """Represents a mapping between a script token and a config file key."""

    token: str
    config_key: str

    @classmethod
    def from_token_key_map(cls, token_key_map: dict[str, str]):
        """Create a list of TokenConfigKeyPair instances from a token-key map.

        Args:
            token_key_map (dict[str, str]): Mapping of CLI tokens to config keys.

        Returns:
            list[TokenConfigKeyPair]: List of generated TokenConfigKeyPair objects.
        """
        return [
            cls(token, config_key)
            for token, config_key in token_key_map.items()
        ]


@dataclass
class BackupJob:
    """Represents a backup job to be executed via a shell script."""

    script_name: str
    script_token_config_key_pairs: list[TokenConfigKeyPair]
    config: dict
    name: str
    category: str
    repositories: list[ResticRepo] = field(default_factory=list)
    dry_run: bool = False

    def get_arg_entry(self, pair: TokenConfigKeyPair) -> list[str]:
        """Generate CLI arguments for a given token-config pair.

        Args:
            pair (TokenConfigKeyPair): The token-config mapping for a script argument.

        Returns:
            list[str]: A list containing the token and its associated value.

        Raises:
            TypeError: If the config value is of an unsupported type.
        """
        value = self.config[pair.config_key]
        if isinstance(value, list):
            return [pair.token, " ".join(value)]
        elif isinstance(value, (str, bool, int, float)):
            return [
                pair.token,
                str(value).lower() if isinstance(value, bool) else str(value),
            ]
        else:
            raise TypeError(
                f"Unsupported type for config key {pair.config_key}: {type(value)}"
            )

    def get_args_list_for_repo(self, repo: ResticRepo) -> list[str]:
        """Construct script arguments for a specific repository.

        Args:
            repo (ResticRepo): The repository to generate arguments for.

        Returns:
            list[str]: List of script argument strings including repo and password.
        """
        args = []
        for pair in self.script_token_config_key_pairs:
            # Skip repo and password tokens - we'll add them from ResticRepo
            if pair.token in ["-r", "-p"]:
                continue
            args += self.get_arg_entry(pair)
        
        # Add repository-specific arguments
        args += ["-r", str(repo.repo_path)]
        args += ["-p", str(repo.password_file)]
        
        return args

    @property
    def args_list(self) -> list[str]:
        """Construct the full list of script arguments for the backup job.

        Note: For multi-repo jobs, use get_args_list_for_repo() instead.
        This property is maintained for backward compatibility.

        Returns:
            list[str]: List of script argument strings.
        """
        args = []
        for pair in self.script_token_config_key_pairs:
            args += self.get_arg_entry(pair)
        return args

    @property
    def script_path(self) -> Path:
        """Get the resolved filesystem path to the backup script.

        Returns:
            Path: Filesystem path to the associated shell script.
        """
        return pkg_resources.files(scripts) / self.script_name

    def get_cmd_for_repo(self, repo: ResticRepo) -> list[str]:
        """Build the shell command for a specific repository.

        Args:
            repo (ResticRepo): The repository to build the command for.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.get_args_list_for_repo(repo)

    @property
    def cmd(self) -> list[str]:
        """Build the full shell command to run the backup job.

        Note: For multi-repo jobs, use get_cmd_for_repo() instead.
        This property is maintained for backward compatibility.

        Returns:
            list[str]: Full command as a list suitable for subprocess.
        """
        return ["bash", str(self.script_path)] + self.args_list

    def run(self):
        """Execute the backup job by running the script for each repository.

        Routes to category-specific backup methods:
        - LVM jobs: Creates snapshot once, backs up to all repos, then cleans up
        - Standard path jobs: Remounts readonly once (if configured), backs up to all repos

        Raises:
            subprocess.CalledProcessError: If the script exits with an error code.
            FileNotFoundError: If the script file is missing.
            Exception: For any other unexpected errors during execution.
        """
        if not self.repositories:
            print(f"⚠️  Warning: No repositories configured for [{self.category}.{self.name}]")
            return
        
        print(f"▶️  Running backup job: [{self.category}.{self.name}] -> {len(self.repositories)} repo(s)")
        
        # Route to appropriate backup method based on category
        if self.category in ["logical_volume_root", "logical_volume_nonroot"]:
            self._run_lvm_backup()
        else:
            self._run_standard_backup()
    
    def _run_standard_backup(self):
        """Execute standard path backup with remount optimization.
        
        For backups with remount_readonly=true, remounts the filesystem readonly once,
        backs up to all repositories, then remounts read-write.
        """
        backup_source_path = self.config["backup_source_path"]
        exclude_paths = self.config.get("exclude_paths", [])
        remount_readonly = self.config.get("remount_readonly", False)
        
        failed_repos = []
        successful_repos = []
        
        try:
            # Remount readonly if needed (ONCE)
            if remount_readonly:
                print(f"🔒 Remounting {backup_source_path} as read-only...")
                subprocess.run(
                    ["mount", "-o", "remount,ro", backup_source_path],
                    check=True,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            
            # Backup to each repository
            for i, repo in enumerate(self.repositories, 1):
                repo_label = f"[{self.category}.{self.name}] repo {i}/{len(self.repositories)}: {repo.repo_path}"
                print(f"\n▶️  Backing up {backup_source_path} to {repo_label}")
                
                try:
                    # Build restic command
                    restic_cmd = [
                        "restic", "-r", str(repo.repo_path),
                        "--password-file", str(repo.password_file),
                        "backup", backup_source_path
                    ]
                    
                    # Add excludes
                    for exclude in exclude_paths:
                        restic_cmd.extend(["--exclude", exclude])
                    
                    # Run backup
                    subprocess.run(
                        restic_cmd,
                        check=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                    )
                    print(f"✅ Backup to {repo.repo_path} completed.")
                    successful_repos.append(repo.repo_path)
                except subprocess.CalledProcessError as e:
                    print(f"❌ Backup failed for {repo.repo_path}: {e}")
                    failed_repos.append(repo.repo_path)
                except Exception as e:
                    print(f"❌ Unexpected error for {repo.repo_path}: {e}")
                    failed_repos.append(repo.repo_path)
        
        finally:
            # Remount read-write if we remounted readonly (ONCE)
            if remount_readonly:
                print(f"\n🔓 Remounting {backup_source_path} as read-write...")
                subprocess.run(
                    ["mount", "-o", "remount,rw", backup_source_path],
                    check=False,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
        
        # Print summary
        self._print_backup_summary(successful_repos, failed_repos)
    
    def _run_lvm_backup(self):
        """Execute LVM backup with snapshot optimization.
        
        Creates LVM snapshot once, mounts it, backs up to all repositories,
        then unmounts and removes the snapshot.
        """
        # Extract LVM configuration
        vg_name = self.config["vg_name"]
        lv_name = self.config["lv_name"]
        snapshot_size = self.config["snapshot_size"]
        backup_source_path = self.config["backup_source_path"]
        exclude_paths = self.config.get("exclude_paths", [])
        
        # Create unique snapshot name
        snapshot_name = f"{lv_name}_snapshot_{int(time.time())}"
        mount_point = f"/mnt/resticlvm_{snapshot_name}"
        
        failed_repos = []
        successful_repos = []
        snapshot_created = False
        snapshot_mounted = False
        
        try:
            # Create LVM snapshot (ONCE)
            print(f"📸 Creating LVM snapshot: {vg_name}/{snapshot_name} (size: {snapshot_size})")
            subprocess.run(
                [
                    "lvcreate", "--snapshot",
                    f"--size={snapshot_size}",
                    f"--name={snapshot_name}",
                    f"{vg_name}/{lv_name}"
                ],
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            snapshot_created = True
            print(f"✅ Snapshot created: /dev/{vg_name}/{snapshot_name}")
            
            # Create mount point
            os.makedirs(mount_point, exist_ok=True)
            
            # Mount snapshot (ONCE)
            print(f"📂 Mounting snapshot at {mount_point}...")
            subprocess.run(
                ["mount", f"/dev/{vg_name}/{snapshot_name}", mount_point],
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            snapshot_mounted = True
            print(f"✅ Snapshot mounted")
            
            # Backup to each repository from the mounted snapshot
            for i, repo in enumerate(self.repositories, 1):
                repo_label = f"[{self.category}.{self.name}] repo {i}/{len(self.repositories)}: {repo.repo_path}"
                print(f"\n▶️  Backing up snapshot to {repo_label}")
                
                try:
                    # Build restic command - backup from mounted snapshot
                    restic_cmd = [
                        "restic", "-r", str(repo.repo_path),
                        "--password-file", str(repo.password_file),
                        "backup", mount_point
                    ]
                    
                    # Add excludes - adjust paths to be relative to mount_point
                    for exclude in exclude_paths:
                        # Remove leading slash and prepend mount_point
                        exclude_adjusted = os.path.join(mount_point, exclude.lstrip('/'))
                        restic_cmd.extend(["--exclude", exclude_adjusted])
                    
                    # Run backup
                    subprocess.run(
                        restic_cmd,
                        check=True,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                    )
                    print(f"✅ Backup to {repo.repo_path} completed.")
                    successful_repos.append(repo.repo_path)
                except subprocess.CalledProcessError as e:
                    print(f"❌ Backup failed for {repo.repo_path}: {e}")
                    failed_repos.append(repo.repo_path)
                except Exception as e:
                    print(f"❌ Unexpected error for {repo.repo_path}: {e}")
                    failed_repos.append(repo.repo_path)
        
        finally:
            # Cleanup snapshot (ONCE) - always attempt even if backup failed
            if snapshot_mounted:
                print(f"\n🗑️  Unmounting snapshot from {mount_point}...")
                result = subprocess.run(
                    ["umount", mount_point],
                    check=False,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                if result.returncode == 0:
                    print(f"✅ Snapshot unmounted")
                else:
                    print(f"⚠️  Warning: Failed to unmount {mount_point}")
            
            if snapshot_created:
                print(f"🗑️  Removing LVM snapshot: {vg_name}/{snapshot_name}...")
                result = subprocess.run(
                    ["lvremove", "-f", f"{vg_name}/{snapshot_name}"],
                    check=False,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
                if result.returncode == 0:
                    print(f"✅ Snapshot removed")
                else:
                    print(f"⚠️  Warning: Failed to remove snapshot {vg_name}/{snapshot_name}")
            
            # Remove mount point directory
            try:
                if os.path.exists(mount_point):
                    os.rmdir(mount_point)
            except Exception as e:
                print(f"⚠️  Warning: Could not remove mount point {mount_point}: {e}")
        
        # Print summary
        self._print_backup_summary(successful_repos, failed_repos)
    
    def _print_backup_summary(self, successful_repos: list, failed_repos: list):
        """Print a summary of the backup operation.
        
        Args:
            successful_repos (list): List of successfully backed up repository paths.
            failed_repos (list): List of failed repository paths.
        """
        print(f"\n{'='*70}")
        print(f"Backup job [{self.category}.{self.name}] summary:")
        print(f"  ✅ Successful: {len(successful_repos)}/{len(self.repositories)}")
        print(f"  ❌ Failed: {len(failed_repos)}/{len(self.repositories)}")
        if failed_repos:
            print(f"\nFailed repositories:")
            for repo_path in failed_repos:
                print(f"  - {repo_path}")
        print(f"{'='*70}\n")
