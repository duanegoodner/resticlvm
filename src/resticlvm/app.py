import argparse
import os
import sys
from pathlib import Path

from resticlvm.backup_jobs import BootBackupJob, LVMBackupJob
from resticlvm.backup_plan import BackupPlan
from resticlvm.config_loader import load_config
from resticlvm.local_classes import BootDir, LogicalVolume, LVMSnapshot
from resticlvm.restic_classes import ResticRepo
from resticlvm.restic_snapshot import ResticBootSnapshot, ResticLVMSnapshot


def get_args():
    parser = argparse.ArgumentParser(
        description="Backup plan for LVM-based restic backup."
    )
    parser.add_argument(
        "--config_path",
        type=str,
        help="Path to the backup configuration file.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="Run in dry-run mode without making any changes.",
    )
    return parser.parse_args()


def main(config_path: Path, dry_run: bool = True):

    backup_config = load_config(config_path)

    if not dry_run and os.geteuid() != 0:
        print("Please run as root.")
        sys.exit(1)

    # Build LVM-based restic backup
    lv = LogicalVolume(
        vg_name=backup_config["logical_volumes"]["rudolph_root"]["vg_name"],
        lv_name=backup_config["logical_volumes"]["rudolph_root"]["lv_name"],
    )
    snapshot = LVMSnapshot.of_logical_volume(
        logical_volume=lv,
        snap_size=backup_config["logical_volumes"]["rudolph_root"][
            "snapshot_size"
        ],
        mount_point=backup_config["logical_volumes"]["rudolph_root"][
            "mount_point"
        ],
        dry_run=dry_run,
    )

    restic_repo_root = ResticRepo(
        repo_path=backup_config["logical_volumes"]["rudolph_root"][
            "repo_path"
        ],
        password_file=backup_config["logical_volumes"]["rudolph_root"][
            "repo_password_file"
        ],
        dry_run=dry_run,
    )

    restic_snapshot = ResticLVMSnapshot(
        lvm_snapshot=snapshot,
        restic_repo=restic_repo_root,
        paths_for_backup=backup_config["logical_volumes"]["rudolph_root"][
            "paths_for_backup"
        ],
        exclude_paths=backup_config["logical_volumes"]["rudolph_root"][
            "exclude_paths"
        ],
    )

    # Boot backup
    boot = BootDir(
        password_file=backup_config["partitions"]["boot"][
            "repo_password_file"
        ],
        repo_path=backup_config["partitions"]["boot"]["repo_path"],
        dry_run=dry_run,
    )

    boot_snapshot = ResticBootSnapshot(
        boot_dir=boot,
        restic_repo=restic_repo_root,
    )

    # Wrap each job
    lvm_job = LVMBackupJob(restic_snapshot=restic_snapshot)
    boot_job = BootBackupJob(boot_snapshot=boot_snapshot)

    # Compose backup plan
    plan = BackupPlan()
    plan.add_job(job=lvm_job)
    plan.add_job(job=boot_job)

    # Run the plan
    plan.run()


if __name__ == "__main__":
    args = get_args()
    DRY_RUN = True
    config_path = Path(__file__).parent.parent.parent / "backup_config.toml"
    main(config_path=args.config_path, dry_run=args.dry_run)
