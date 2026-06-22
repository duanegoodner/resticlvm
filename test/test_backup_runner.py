"""Tests for the backup_runner module (run_all summary + main exit code)."""

from unittest import mock

import pytest

from resticlvm.orchestration import backup_runner
from resticlvm.orchestration.backup_runner import BackupJobRunner
from resticlvm.orchestration.data_classes import JobResult


def _fake_job(category, name, result):
    """A stand-in BackupJob whose run() returns a preset JobResult."""
    job = mock.Mock()
    job.category = category
    job.name = name
    job.run.return_value = result
    return job


def test_run_all_returns_failure_count_and_isolates_jobs():
    """A failing job is counted but does not stop later jobs from running."""
    failing = _fake_job(
        "standard_path", "a",
        JobResult("standard_path", "a", script_ok=False, failed_copies=[]),
    )
    ok = _fake_job(
        "standard_path", "b",
        JobResult("standard_path", "b", script_ok=True, failed_copies=[]),
    )

    runner = BackupJobRunner([failing, ok])
    failure_count = runner.run_all()

    assert failure_count == 1
    # Isolation: both jobs ran even though the first failed.
    failing.run.assert_called_once()
    ok.run.assert_called_once()


def test_run_all_counts_copy_failure_as_job_failure():
    """A job whose backup succeeded but a copy failed counts as a failure."""
    job = _fake_job(
        "standard_path", "a",
        JobResult("standard_path", "a", script_ok=True,
                  failed_copies=["/srv/backup/remote"]),
    )

    assert BackupJobRunner([job]).run_all() == 1


def test_run_all_all_success_returns_zero():
    """All jobs succeeding yields a zero failure count."""
    jobs = [
        _fake_job("standard_path", "a",
                  JobResult("standard_path", "a", script_ok=True, failed_copies=[])),
        _fake_job("standard_path", "b",
                  JobResult("standard_path", "b", script_ok=True, failed_copies=[])),
    ]

    assert BackupJobRunner(jobs).run_all() == 0


def test_run_all_respects_category_and_name_filters():
    """Filtered-out jobs are not run."""
    a = _fake_job("standard_path", "a",
                  JobResult("standard_path", "a", script_ok=True, failed_copies=[]))
    b = _fake_job("logical_volume_root", "b",
                  JobResult("logical_volume_root", "b", script_ok=True, failed_copies=[]))

    BackupJobRunner([a, b]).run_all(category="standard_path")

    a.run.assert_called_once()
    b.run.assert_not_called()


def _run_main_with_failure_count(monkeypatch, failure_count):
    """Invoke main() with mocked deps and a forced run_all failure count."""
    monkeypatch.setattr(backup_runner, "ensure_running_as_root", lambda: None)
    monkeypatch.setattr(backup_runner, "BackupPlan", mock.Mock())
    monkeypatch.setattr(
        BackupJobRunner, "run_all",
        lambda self, category=None, name=None: failure_count,
    )
    monkeypatch.setattr(
        backup_runner.sys, "argv",
        ["resticlvm-backup", "--config", "/tmp/config.toml"],
    )
    backup_runner.main()


def test_main_exits_nonzero_on_failure(monkeypatch):
    """main() exits with code 1 when any job failed."""
    with pytest.raises(SystemExit) as exc_info:
        _run_main_with_failure_count(monkeypatch, failure_count=1)
    assert exc_info.value.code == 1


def test_main_exits_zero_on_success(monkeypatch):
    """main() returns normally (no SystemExit) when nothing failed."""
    _run_main_with_failure_count(monkeypatch, failure_count=0)
