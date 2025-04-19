from local_classes import BootDir
from restic_snapshot import ResticBootSnapshot, ResticLVMSnapshot


class LVMBackupJob:
    def __init__(self, restic_snapshot: ResticLVMSnapshot):
        self.lvm_snapshot = restic_snapshot.lvm_snapshot
        self.restic_snapshot = restic_snapshot

    def run(self):
        try:
            self.lvm_snapshot.create()
            self.lvm_snapshot.mount()
            self.lvm_snapshot.bind_mount(source="/dev", target_rel="dev")
            self.lvm_snapshot.bind_mount(source="/proc", target_rel="proc")
            self.lvm_snapshot.bind_mount(source="/sys", target_rel="sys")
            # If restic repo is on the same disk, bind it too
            self.lvm_snapshot.bind_mount(
                source="/path/to/repo", target_rel="path/to/repo"
            )

            self.restic_snapshot.send()

        finally:
            self.snapshot.cleanup()


class BootBackupJob:
    def __init__(self, boot_snapshot: ResticBootSnapshot):
        self.boot_snapshot = boot_snapshot

    def run(self):
        self.boot_snapshot.send()
