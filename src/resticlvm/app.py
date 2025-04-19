import os
import sys

from resticlvm.backup_jobs import BootBackupJob, LVMBackupJob
from resticlvm.backup_plan import BackupPlan
from resticlvm.local_classes import BootDir, LVMSnapshot, LogicalVolume
from resticlvm.restic_classes import ResticRepo
from resticlvm.restic_snapshot import ResticBootSnapshot, ResticLVMSnapshot


def main(dry_run: bool):
    if not dry_run and os.geteuid() != 0:
        print("Please run as root.")
        sys.exit(1)

    # Build LVM-based restic backup
    lv = LogicalVolume(vg_name="my_vg_name", lv_name="my_system_lv_name")
    snapshot = LVMSnapshot.of_logical_volume(
        logical_volume=lv,
        snap_size="10G",
        mount_point="/srv/my_lvm_snapshot_mount_point",
        dry_run=dry_run,
    )

    restic_repo_root = ResticRepo(
        repo_path="/path/to/my/system/restic/repo/",
        password_file="/path/to/my/system-resticpasswordfile",
        dry_run=dry_run,
    )

    restic_snapshot = ResticLVMSnapshot(
        lvm_snapshot=snapshot,
        restic_repo=restic_repo_root,
        paths_for_backup=["/"],
        exclude_paths=[
            "/dev",
            "/media",
            "/mnt",
            "/proc",
            "/run",
            "/sys",
            "/tmp",
            "/var/tmp",
            "/var/lib/libvirt/images",
        ],
    )

    # Boot backup
    boot = BootDir(
        password_file="/path/to/my/boot/restic/repo/",
        repo_path="/path/to/my/boot-resticpasswordfile",
        dry_run=DRY_RUN,
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
    DRY_RUN = True
    main(dry_run=DRY_RUN)
