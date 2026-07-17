"""Tests for the backup_runner module (run_all summary + main exit code)."""

from unittest import mock

import pytest

from resticlvm.orchestration import backup_runner
from resticlvm.orchestration.backup_config import SnapshotSettings
from resticlvm.orchestration.backup_runner import BackupJobRunner
from resticlvm.orchestration.data_classes import JobResult


def _fake_job(category, name, result):
    """A stand-in BackupJob whose run() returns a preset JobResult."""
    job = mock.Mock()
    job.category = category
    job.name = name
    job.run.return_value = result
    return job


def _fake_lv_job(name, result, dry_run=False):
    """A stand-in LV BackupJob with config dict for the coordinator."""
    job = mock.Mock()
    job.category = "lv_root"
    job.name = name
    job.dry_run = dry_run
    job.config = {"vg_name": "vg0", "lv_name": f"lv_{name}", "snapshot_size": "10G"}
    job.run.return_value = result
    job.run_deferred_copies.return_value = []
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


def test_run_all_prints_loud_banner_on_failure(capsys):
    """Failures get an unmissable banner naming each failed job."""
    jobs = [
        _fake_job("standard_path", "ok",
                  JobResult("standard_path", "ok", script_ok=True, failed_copies=[])),
        _fake_job("standard_path", "bad",
                  JobResult("standard_path", "bad", script_ok=False, failed_copies=[])),
    ]

    BackupJobRunner(jobs).run_all()

    out = capsys.readouterr().out
    assert "BACKUP FAILED" in out
    assert "1 of 2" in out
    assert "!!!!!" in out  # the loud bar
    assert "standard_path.bad" in out


def test_run_all_prints_calm_success_summary(capsys):
    """All-success prints a plain success line, no failure banner."""
    job = _fake_job("standard_path", "ok",
                    JobResult("standard_path", "ok", script_ok=True, failed_copies=[]))

    BackupJobRunner([job]).run_all()

    out = capsys.readouterr().out
    assert "completed successfully" in out
    assert "BACKUP FAILED" not in out


def test_run_all_respects_category_and_name_filters():
    """Filtered-out jobs are not run."""
    a = _fake_job("standard_path", "a",
                  JobResult("standard_path", "a", script_ok=True, failed_copies=[]))
    b = _fake_job("lv_root", "b",
                  JobResult("lv_root", "b", script_ok=True, failed_copies=[]))

    BackupJobRunner([a, b]).run_all(category="standard_path")

    a.run.assert_called_once()
    b.run.assert_not_called()


def _run_with_failure_count(monkeypatch, failure_count):
    """Invoke run() with mocked deps and a forced run_all failure count."""
    monkeypatch.setattr(backup_runner, "BackupPlan", mock.Mock())
    monkeypatch.setattr(
        BackupJobRunner, "run_all",
        lambda self, category=None, name=None: failure_count,
    )
    args = mock.Mock(
        config="/tmp/config.toml",
        dry_run=False,
        category=None,
        name=None,
    )
    backup_runner.run(args)


def test_run_exits_nonzero_on_failure(monkeypatch):
    """run() exits with code 1 when any job failed."""
    with pytest.raises(SystemExit) as exc_info:
        _run_with_failure_count(monkeypatch, failure_count=1)
    assert exc_info.value.code == 1


def test_run_exits_zero_on_success(monkeypatch):
    """run() returns normally (no SystemExit) when nothing failed."""
    _run_with_failure_count(monkeypatch, failure_count=0)


# ─── Batch snapshot coordination (issue #84) ──────────────────────


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_lv_jobs_use_coordinator(MockCoord):
    """LV jobs are run through the SnapshotCoordinator."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/resticlvm/snap"

    job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=True, failed_copies=[]),
    )

    runner = BackupJobRunner([job])
    runner.run_all()

    MockCoord.assert_called_once()
    coord.create_all.assert_called_once()
    job.run.assert_called_once_with(
        snapshot_mount="/tmp/resticlvm/snap", defer_copies=True,
    )


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_non_lv_jobs_skip_coordinator(MockCoord):
    """Standard-path jobs do not go through the coordinator."""
    job = _fake_job(
        "standard_path", "boot",
        JobResult("standard_path", "boot", script_ok=True, failed_copies=[]),
    )

    runner = BackupJobRunner([job])
    runner.run_all()

    MockCoord.assert_not_called()
    job.run.assert_called_once()


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_mixed_lv_and_non_lv_jobs(MockCoord):
    """Both LV and non-LV jobs run, LV through coordinator, non-LV directly."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/snap"

    lv_job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=True, failed_copies=[]),
    )
    path_job = _fake_job(
        "standard_path", "boot",
        JobResult("standard_path", "boot", script_ok=True, failed_copies=[]),
    )

    runner = BackupJobRunner([lv_job, path_job])
    result = runner.run_all()

    assert result == 0
    lv_job.run.assert_called_once_with(
        snapshot_mount="/tmp/snap", defer_copies=True,
    )
    path_job.run.assert_called_once()


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_deferred_copies_run_after_teardown(MockCoord):
    """Copy operations for LV jobs run after the coordinator context exits."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/snap"

    job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=True, failed_copies=[]),
    )

    runner = BackupJobRunner([job])
    runner.run_all()

    job.run_deferred_copies.assert_called_once()


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_failed_lv_job_skips_deferred_copies(MockCoord):
    """Copy operations are not run for LV jobs whose backup failed."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/snap"

    job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=False, failed_copies=[]),
    )

    runner = BackupJobRunner([job])
    runner.run_all()

    job.run_deferred_copies.assert_not_called()


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_deferred_copy_failure_counted(MockCoord, capsys):
    """A deferred copy failure is reflected in the final failure count."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/snap"

    job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=True, failed_copies=[]),
    )
    job.run_deferred_copies.return_value = ["/srv/backup/remote"]

    runner = BackupJobRunner([job])
    result = runner.run_all()

    assert result == 1
    out = capsys.readouterr().out
    assert "BACKUP FAILED" in out
    assert "/srv/backup/remote" in out


@mock.patch("resticlvm.orchestration.backup_runner.SnapshotCoordinator")
def test_snapshot_settings_passed_to_coordinator(MockCoord):
    """Custom snapshot settings are forwarded to the coordinator."""
    coord = MockCoord.return_value
    coord.__enter__ = mock.Mock(return_value=coord)
    coord.__exit__ = mock.Mock(return_value=False)
    coord.get_mount_point.return_value = "/tmp/snap"

    job = _fake_lv_job(
        "root",
        JobResult("lv_root", "root", script_ok=True, failed_copies=[]),
    )
    settings = SnapshotSettings(
        min_vg_free_after_snapshots="5G",
        snapshot_cow_warn_percent=80,
    )

    runner = BackupJobRunner([job], snapshot_settings=settings)
    runner.run_all()

    call_kwargs = MockCoord.call_args.kwargs
    assert call_kwargs["min_vg_free_after_snapshots"] == "5G"
    assert call_kwargs["snapshot_cow_warn_percent"] == 80
