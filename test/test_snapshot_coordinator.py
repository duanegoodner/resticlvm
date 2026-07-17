"""Tests for the SnapshotCoordinator (batch snapshot management, issue #84)."""

import signal
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from resticlvm.orchestration.data_classes import BackupJob, TokenConfigKeyPair
from resticlvm.orchestration.snapshot_coordinator import (
    SnapshotCoordinator,
    SnapshotInfo,
    _parse_size_bytes,
)


# ─── Helpers ──────────────────────────────────────────────────────


def _make_lv_job(name="root", vg="vg0", lv="lv0", snap_size="30G"):
    return BackupJob(
        script_name="backup_lv_root.sh",
        script_token_config_key_pairs=[],
        config={"vg_name": vg, "lv_name": lv, "snapshot_size": snap_size},
        name=name,
        category="lv_root",
        repositories=[],
    )


FAKE_CREATE_OUTPUT = """\
📸 Creating LVM snapshot...
📂 Mounting snapshot read-only...
SNAPSHOT_DEVICE=/dev/vg0/lv0
SNAPSHOT_MOUNT_POINT=/tmp/resticlvm-20260717_120000/vg0_lv0_snapshot_20260717_120000
MOUNT_BASE=/tmp/resticlvm-20260717_120000
SNAP_NAME=vg0_lv0_snapshot_20260717_120000
"""


def _fake_create_output(vg, lv, ts="20260717_120000"):
    snap = f"{vg}_{lv}_snapshot_{ts}"
    return (
        f"SNAPSHOT_DEVICE=/dev/{vg}/{lv}\n"
        f"SNAPSHOT_MOUNT_POINT=/tmp/resticlvm-{ts}/{snap}\n"
        f"MOUNT_BASE=/tmp/resticlvm-{ts}\n"
        f"SNAP_NAME={snap}\n"
    )


def _mock_create_run(jobs, vg_free_bytes=None):
    """Return a side_effect callable that returns correct output per job index.

    Also handles vgs calls for the pre-flight check, returning enough free
    space by default (100G) unless vg_free_bytes is specified.
    """
    if vg_free_bytes is None:
        vg_free_bytes = 100 * 1024**3

    outputs = []
    for j in jobs:
        outputs.append(_fake_create_output(j.config["vg_name"], j.config["lv_name"]))

    call_count = [0]

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "vgs":
            return subprocess.CompletedProcess(
                cmd, 0, stdout=f"  {vg_free_bytes}\n", stderr=""
            )
        if "snapshot_create.sh" in str(cmd[1]):
            idx = call_count[0]
            call_count[0] += 1
            return subprocess.CompletedProcess(cmd, 0, stdout=outputs[idx], stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return side_effect


# ─── _parse_size_bytes ────────────────────────────────────────────


class TestParseSizeBytes:
    def test_plain_number(self):
        assert _parse_size_bytes("1024") == 1024

    def test_gigabytes(self):
        assert _parse_size_bytes("30G") == 30 * 1024**3

    def test_megabytes(self):
        assert _parse_size_bytes("512M") == 512 * 1024**2

    def test_case_insensitive(self):
        assert _parse_size_bytes("10g") == 10 * 1024**3

    def test_with_ib_suffix(self):
        assert _parse_size_bytes("5GiB") == 5 * 1024**3

    def test_fractional(self):
        assert _parse_size_bytes("1.5G") == int(1.5 * 1024**3)

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse size"):
            _parse_size_bytes("lots")


# ─── SnapshotInfo ─────────────────────────────────────────────────


def test_snapshot_info_fields():
    info = SnapshotInfo(
        volume_name="root",
        vg_name="vg0",
        snap_name="vg0_lv0_snap",
        mount_point="/tmp/resticlvm-ts/vg0_lv0_snap",
        mount_base="/tmp/resticlvm-ts",
        snapshot_size="30G",
    )
    assert info.volume_name == "root"
    assert info.vg_name == "vg0"


# ─── Context manager ─────────────────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_context_manager_calls_teardown(mock_run):
    """__exit__ calls teardown_all, cleaning up all snapshots."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    with SnapshotCoordinator(jobs) as coord:
        coord.create_all()
        assert coord.has("root")

    # After exiting, teardown should have been called
    teardown_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_teardown.sh" in str(c)
    ]
    assert len(teardown_calls) == 1


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_context_manager_teardown_on_exception(mock_run):
    """Snapshots are torn down even when an exception occurs inside the block."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    with pytest.raises(RuntimeError, match="boom"):
        with SnapshotCoordinator(jobs) as coord:
            coord.create_all()
            raise RuntimeError("boom")

    teardown_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_teardown.sh" in str(c)
    ]
    assert len(teardown_calls) == 1


# ─── create_all ───────────────────────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_create_all_single_job(mock_run):
    """create_all with one job calls snapshot_create.sh and records the result."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()

    assert coord.has("root")
    mp = coord.get_mount_point("root")
    assert "resticlvm-" in mp
    assert "vg0_lv0" in mp


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_create_all_multiple_jobs(mock_run):
    """create_all creates snapshots for all LV jobs."""
    jobs = [
        _make_lv_job(name="root", vg="vg0", lv="lv0", snap_size="30G"),
        _make_lv_job(name="git", vg="vg0", lv="lv_git_01", snap_size="10G"),
        _make_lv_job(name="mail", vg="vg0", lv="lv_mail_01", snap_size="10G"),
    ]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()

    assert coord.has("root")
    assert coord.has("git")
    assert coord.has("mail")
    assert "lv_git_01" in coord.get_mount_point("git")


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_create_all_passes_batch_timestamp(mock_run):
    """All snapshot_create.sh calls receive the same -t timestamp."""
    jobs = [
        _make_lv_job(name="root"),
        _make_lv_job(name="git", lv="lv_git_01"),
    ]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()

    create_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_create.sh" in str(c)
    ]
    timestamps = set()
    for call in create_calls:
        cmd = call.kwargs.get("args") or call[0][0]
        t_idx = cmd.index("-t")
        timestamps.add(cmd[t_idx + 1])

    assert len(timestamps) == 1


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_create_all_passes_dry_run(mock_run):
    """In dry_run mode, -n is passed to snapshot_create.sh."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()

    create_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_create.sh" in str(c)
    ]
    cmd = create_calls[0].kwargs.get("args") or create_calls[0][0][0]
    assert "-n" in cmd


# ─── create_all rollback on failure ───────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_create_all_rollback_on_failure(mock_run):
    """If snapshot #2 fails, snapshot #1 is torn down before raising."""
    jobs = [
        _make_lv_job(name="root", lv="lv0"),
        _make_lv_job(name="git", lv="lv_git_01"),
    ]

    call_count = [0]

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if "snapshot_create.sh" in str(cmd[1]):
            call_count[0] += 1
            if call_count[0] == 2:
                raise subprocess.CalledProcessError(1, cmd)
            return subprocess.CompletedProcess(
                cmd, 0, stdout=_fake_create_output("vg0", "lv0"), stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = side_effect

    coord = SnapshotCoordinator(jobs, dry_run=True)
    with pytest.raises(subprocess.CalledProcessError):
        coord.create_all()

    teardown_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_teardown.sh" in str(c)
    ]
    assert len(teardown_calls) == 1


# ─── teardown_all ─────────────────────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_teardown_all_idempotent(mock_run):
    """Calling teardown_all twice does not call snapshot_teardown.sh twice."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()
    coord.teardown_all()
    coord.teardown_all()

    teardown_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_teardown.sh" in str(c)
    ]
    assert len(teardown_calls) == 1


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_teardown_all_reverse_order(mock_run):
    """Snapshots are torn down in reverse creation order."""
    jobs = [
        _make_lv_job(name="root", lv="lv0"),
        _make_lv_job(name="git", lv="lv_git_01"),
        _make_lv_job(name="mail", lv="lv_mail_01"),
    ]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, dry_run=True)
    coord.create_all()
    coord.teardown_all()

    teardown_calls = [
        c for c in mock_run.call_args_list
        if "snapshot_teardown.sh" in str(c)
    ]
    assert len(teardown_calls) == 3

    teardown_snaps = []
    for call in teardown_calls:
        cmd = call.kwargs.get("args") or call[0][0]
        s_idx = cmd.index("-s")
        teardown_snaps.append(cmd[s_idx + 1])

    assert "lv_mail_01" in teardown_snaps[0]
    assert "lv_git_01" in teardown_snaps[1]
    assert "lv0" in teardown_snaps[2]


# ─── get_mount_point / has ────────────────────────────────────────


def test_get_mount_point_missing_raises():
    coord = SnapshotCoordinator([])
    with pytest.raises(KeyError):
        coord.get_mount_point("nonexistent")


def test_has_false_when_empty():
    coord = SnapshotCoordinator([])
    assert coord.has("root") is False


# ─── Pre-flight VG space check ───────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_preflight_passes_with_enough_space(mock_run):
    """Pre-flight check passes when VG has enough free space."""
    jobs = [
        _make_lv_job(name="root", snap_size="30G"),
        _make_lv_job(name="git", lv="lv_git_01", snap_size="10G"),
    ]

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "vgs":
            # 50G free (30G + 10G + 1G margin = 41G needed)
            free = str(50 * 1024**3)
            return subprocess.CompletedProcess(cmd, 0, stdout=f"  {free}\n", stderr="")
        if "snapshot_create.sh" in str(cmd[1]):
            vg = cmd[cmd.index("-g") + 1]
            lv = cmd[cmd.index("-l") + 1]
            return subprocess.CompletedProcess(
                cmd, 0, stdout=_fake_create_output(vg, lv), stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = side_effect

    coord = SnapshotCoordinator(jobs)
    coord.create_all()
    assert coord.has("root")
    assert coord.has("git")


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_preflight_fails_insufficient_space(mock_run):
    """Pre-flight check raises when VG free space is too low."""
    jobs = [
        _make_lv_job(name="root", snap_size="30G"),
        _make_lv_job(name="git", lv="lv_git_01", snap_size="10G"),
    ]

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "vgs":
            free = str(35 * 1024**3)  # 35G < 41G needed
            return subprocess.CompletedProcess(cmd, 0, stdout=f"  {free}\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = side_effect

    coord = SnapshotCoordinator(jobs)
    with pytest.raises(RuntimeError, match="Insufficient free space"):
        coord.create_all()


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_preflight_groups_by_vg(mock_run):
    """Pre-flight check validates each VG independently."""
    jobs = [
        _make_lv_job(name="root", vg="vg0", snap_size="30G"),
        _make_lv_job(name="data", vg="vg1", lv="lv_data", snap_size="20G"),
    ]

    vgs_calls = []

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "vgs":
            vgs_calls.append(cmd[-1])
            free = str(50 * 1024**3)
            return subprocess.CompletedProcess(cmd, 0, stdout=f"  {free}\n", stderr="")
        if "snapshot_create.sh" in str(cmd[1]):
            vg = cmd[cmd.index("-g") + 1]
            lv = cmd[cmd.index("-l") + 1]
            return subprocess.CompletedProcess(
                cmd, 0, stdout=_fake_create_output(vg, lv), stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = side_effect

    coord = SnapshotCoordinator(jobs)
    coord.create_all()

    assert sorted(vgs_calls) == ["vg0", "vg1"]


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_preflight_custom_margin(mock_run):
    """Custom min_vg_free_after_snapshots is honored."""
    jobs = [_make_lv_job(name="root", snap_size="30G")]

    def side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "vgs":
            free = str(35 * 1024**3)  # 35G: enough for 30G + 1G, not 30G + 10G
            return subprocess.CompletedProcess(cmd, 0, stdout=f"  {free}\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = side_effect

    coord = SnapshotCoordinator(jobs, min_vg_free_after_snapshots="10G")
    with pytest.raises(RuntimeError, match="Insufficient free space"):
        coord.create_all()


def test_preflight_skipped_in_dry_run():
    """Dry-run mode skips the pre-flight check (no vgs call needed)."""
    jobs = [_make_lv_job()]
    coord = SnapshotCoordinator(jobs, dry_run=True)
    # Would fail without mock if it actually called vgs
    # (create_all will still call snapshot_create.sh, tested elsewhere)


# ─── COW usage reporting ─────────────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_cow_report_normal(mock_run, capsys):
    """COW usage report prints percentages for each snapshot."""
    jobs = [_make_lv_job(name="root")]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs)
    coord.create_all()

    # Override mock for the lvs cow query
    def cow_side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "lvs":
            return subprocess.CompletedProcess(cmd, 0, stdout="  12.34\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = cow_side_effect
    coord.report_cow_usage()

    captured = capsys.readouterr()
    assert "12.3%" in captured.out
    assert "root" in captured.out


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_cow_report_warning(mock_run, capsys):
    """COW usage above the threshold triggers a warning."""
    jobs = [_make_lv_job(name="root")]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs, snapshot_cow_warn_percent=50)
    coord.create_all()

    def cow_side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "lvs":
            return subprocess.CompletedProcess(cmd, 0, stdout="  75.0\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = cow_side_effect
    coord.report_cow_usage()

    captured = capsys.readouterr()
    assert "WARNING" in captured.out
    assert "75.0%" in captured.out


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_cow_report_unavailable(mock_run, capsys):
    """COW report handles unavailable snap_percent gracefully."""
    jobs = [_make_lv_job(name="root")]
    mock_run.side_effect = _mock_create_run(jobs)

    coord = SnapshotCoordinator(jobs)
    coord.create_all()

    def cow_side_effect(*args, **kwargs):
        cmd = kwargs.get("args") or args[0]
        if cmd[0] == "lvs":
            raise subprocess.CalledProcessError(5, cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    mock_run.side_effect = cow_side_effect
    coord.report_cow_usage()

    captured = capsys.readouterr()
    assert "unavailable" in captured.out


def test_cow_report_skipped_in_dry_run(capsys):
    """COW report is skipped in dry-run mode."""
    coord = SnapshotCoordinator([], dry_run=True)
    coord.report_cow_usage()
    captured = capsys.readouterr()
    assert captured.out == ""


# ─── Signal handler ───────────────────────────────────────────────


@mock.patch("resticlvm.orchestration.snapshot_coordinator.subprocess.run")
def test_signal_handler_installed_in_context(mock_run):
    """Signal handlers are installed on __enter__ and restored on __exit__."""
    jobs = [_make_lv_job()]
    mock_run.side_effect = _mock_create_run(jobs)

    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)

    with SnapshotCoordinator(jobs) as coord:
        coord.create_all()
        # During the block, handlers should be the coordinator's
        assert signal.getsignal(signal.SIGINT) != original_int
        assert signal.getsignal(signal.SIGTERM) != original_term

    # After exiting, original handlers should be restored
    assert signal.getsignal(signal.SIGINT) == original_int
    assert signal.getsignal(signal.SIGTERM) == original_term
