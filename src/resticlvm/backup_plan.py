from resticlvm.backup_jobs import BootBackupJob, LVMBackupJob


class BackupPlan:
    def __init__(self, jobs: list[BootBackupJob | LVMBackupJob] = None):
        self.jobs = jobs if jobs is not None else []

    def add_job(self, job: BootBackupJob | LVMBackupJob):
        self.jobs.append(job)

    def run(self):
        for job in self.jobs:
            print(f"\n==> Running backup job: {job.__class__.__name__}")
            try:
                job.run()
            except Exception as e:
                print(f"Error while running {job.__class__.__name__}: {e}")
