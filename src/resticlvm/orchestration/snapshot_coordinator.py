"""Batch LVM snapshot coordinator for cross-LV atomicity (issue #84).

Creates all LVM snapshots before any backup runs, reducing the cross-LV
time delta from minutes to milliseconds. Manages the full lifecycle:
pre-flight VG space check, batch creation, COW usage reporting, and
idempotent teardown.
"""

import atexit
import importlib.resources as pkg_resources
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime

from resticlvm import scripts
from resticlvm.orchestration.data_classes import BackupJob


@dataclass
class SnapshotInfo:
    """Metadata for a single active LVM snapshot."""

    volume_name: str
    vg_name: str
    snap_name: str
    mount_point: str
    mount_base: str
    snapshot_size: str


_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*([KMGTP]?)(?:i?B)?$", re.IGNORECASE)
_MULTIPLIERS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}


def _parse_size_bytes(size_str: str) -> int:
    m = _SIZE_RE.match(size_str.strip())
    if not m:
        raise ValueError(f"Cannot parse size: {size_str!r}")
    return int(float(m.group(1)) * _MULTIPLIERS[m.group(2).upper()])


class SnapshotCoordinator:
    """Manages batch snapshot creation and teardown for cross-LV atomicity.

    Use as a context manager to guarantee teardown:

        with SnapshotCoordinator(lv_jobs) as coord:
            coord.create_all()
            for job in all_jobs:
                mount = coord.get_mount_point(job.name) if coord.has(job.name) else None
                job.run(snapshot_mount=mount)
        # teardown_all() runs automatically on exit
    """

    def __init__(
        self,
        lv_jobs: list[BackupJob],
        dry_run: bool = False,
        min_vg_free_after_snapshots: str = "1G",
        snapshot_cow_warn_percent: int = 70,
    ):
        self._lv_jobs = lv_jobs
        self._dry_run = dry_run
        self._min_free = min_vg_free_after_snapshots
        self._cow_warn_pct = snapshot_cow_warn_percent
        self._snapshots: dict[str, SnapshotInfo] = {}
        self._timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._original_sigint = None
        self._original_sigterm = None
        self._torn_down = False

    def __enter__(self):
        self._install_signal_handlers()
        atexit.register(self.teardown_all)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.report_cow_usage()
        self.teardown_all()
        self._restore_signal_handlers()
        atexit.unregister(self.teardown_all)
        return False

    # ─── Public API ───────────────────────────────────────────────

    def create_all(self) -> None:
        """Create and mount snapshots for all LV volumes.

        Runs a pre-flight VG space check, then creates snapshots one by one.
        If any snapshot fails to create, tears down all previously created
        snapshots and raises.
        """
        self._preflight_vg_space_check()

        for job in self._lv_jobs:
            try:
                info = self._create_one(job)
                self._snapshots[job.name] = info
            except Exception:
                print(
                    f"❌ Snapshot creation failed for {job.name} — "
                    f"tearing down {len(self._snapshots)} previously created snapshot(s).",
                    file=sys.stderr,
                )
                self.teardown_all()
                raise

    def teardown_all(self) -> None:
        """Tear down all active snapshots. Idempotent."""
        if self._torn_down or not self._snapshots:
            return

        names = list(reversed(self._snapshots.keys()))
        for name in names:
            info = self._snapshots[name]
            self._teardown_one(info)

        self._snapshots.clear()
        self._torn_down = True

    def get_mount_point(self, volume_name: str) -> str:
        """Return the snapshot mount point for a volume."""
        return self._snapshots[volume_name].mount_point

    def has(self, volume_name: str) -> bool:
        """True if a snapshot exists for this volume name."""
        return volume_name in self._snapshots

    def report_cow_usage(self) -> None:
        """Query and print COW utilization for each active snapshot."""
        if self._dry_run or not self._snapshots:
            return

        print("\n📊 Snapshot COW usage:")
        for name, info in self._snapshots.items():
            pct = self._query_cow_percent(info)
            if pct is None:
                print(f"  {name:20s} ({info.snapshot_size} allocated):  unavailable")
                continue

            alloc_bytes = _parse_size_bytes(info.snapshot_size)
            used_bytes = int(alloc_bytes * pct / 100)
            used_str = self._format_bytes(used_bytes)
            print(f"  {name:20s} ({info.snapshot_size} allocated):  {pct:5.1f}%  ({used_str} used)")

            if pct >= self._cow_warn_pct:
                print(
                    f"  ⚠️  WARNING: {name} COW usage ({pct:.1f}%) exceeds "
                    f"{self._cow_warn_pct}% threshold — consider increasing "
                    f"snapshot_size in your backup config."
                )

    # ─── Internal ─────────────────────────────────────────────────

    def _create_one(self, job: BackupJob) -> SnapshotInfo:
        script = str(pkg_resources.files(scripts) / "snapshot_create.sh")
        cmd = [
            "bash", script,
            "-g", job.config["vg_name"],
            "-l", job.config["lv_name"],
            "-z", str(job.config["snapshot_size"]),
            "-t", self._timestamp,
        ]
        if self._dry_run:
            cmd.append("-n")

        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True,
        )

        return self._parse_create_output(job, result.stdout)

    def _parse_create_output(self, job: BackupJob, stdout: str) -> SnapshotInfo:
        kv = {}
        for line in stdout.strip().splitlines():
            if "=" in line:
                key, _, val = line.partition("=")
                kv[key.strip()] = val.strip()

        return SnapshotInfo(
            volume_name=job.name,
            vg_name=job.config["vg_name"],
            snap_name=kv["SNAP_NAME"],
            mount_point=kv["SNAPSHOT_MOUNT_POINT"],
            mount_base=kv["MOUNT_BASE"],
            snapshot_size=str(job.config["snapshot_size"]),
        )

    def _teardown_one(self, info: SnapshotInfo) -> None:
        script = str(pkg_resources.files(scripts) / "snapshot_teardown.sh")
        cmd = [
            "bash", script,
            "-g", info.vg_name,
            "-s", info.snap_name,
            "-m", info.mount_point,
            "-b", info.mount_base,
        ]
        if self._dry_run:
            cmd.append("-n")

        try:
            subprocess.run(
                cmd, check=False, stdout=sys.stdout, stderr=sys.stderr,
            )
        except Exception as e:
            print(f"⚠️  Teardown error for {info.volume_name}: {e}", file=sys.stderr)

    def _preflight_vg_space_check(self) -> None:
        if self._dry_run:
            return

        by_vg: dict[str, list[BackupJob]] = {}
        for job in self._lv_jobs:
            vg = job.config["vg_name"]
            by_vg.setdefault(vg, []).append(job)

        margin_bytes = _parse_size_bytes(self._min_free)

        for vg_name, jobs in by_vg.items():
            vg_free = self._query_vg_free(vg_name)
            total_snap = sum(
                _parse_size_bytes(str(j.config["snapshot_size"])) for j in jobs
            )
            required = total_snap + margin_bytes

            if vg_free < required:
                snap_str = self._format_bytes(total_snap)
                free_str = self._format_bytes(vg_free)
                margin_str = self._min_free
                shortfall_str = self._format_bytes(required - vg_free)
                raise RuntimeError(
                    f"Insufficient free space in VG '{vg_name}' for batch snapshots.\n"
                    f"  VG free:              {free_str}\n"
                    f"  Total snapshot alloc:  {snap_str}\n"
                    f"  Safety margin:         {margin_str}\n"
                    f"  Shortfall:             {shortfall_str}\n"
                    f"  → Free up space in the VG or reduce snapshot_size values."
                )

    def _query_vg_free(self, vg_name: str) -> int:
        result = subprocess.run(
            ["vgs", "--noheadings", "--nosuffix", "--units", "b",
             "-o", "vg_free", vg_name],
            check=True, capture_output=True, text=True,
        )
        return int(result.stdout.strip())

    def _query_cow_percent(self, info: SnapshotInfo) -> float | None:
        try:
            result = subprocess.run(
                ["lvs", "--noheadings", "--nosuffix",
                 "-o", "snap_percent",
                 f"/dev/{info.vg_name}/{info.snap_name}"],
                check=True, capture_output=True, text=True,
            )
            val = result.stdout.strip()
            if not val:
                return None
            return float(val)
        except (subprocess.CalledProcessError, ValueError):
            return None

    def _install_signal_handlers(self) -> None:
        self._original_sigint = signal.getsignal(signal.SIGINT)
        self._original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _restore_signal_handlers(self) -> None:
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)

    def _signal_handler(self, signum, frame):
        sig_name = signal.Signals(signum).name
        print(
            f"\n⚠️  Received {sig_name} — tearing down all snapshots…",
            file=sys.stderr,
        )
        self.teardown_all()
        self._restore_signal_handlers()
        signal.raise_signal(signum)

    @staticmethod
    def _format_bytes(n: int) -> str:
        for unit in ("B", "K", "M", "G", "T"):
            if abs(n) < 1024:
                return f"{n:.1f}{unit}" if n != int(n) else f"{n}{unit}"
            n /= 1024
        return f"{n:.1f}P"
