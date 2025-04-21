import os
from pathlib import Path
from resticlvm.logical_volume import LogicalVolume, LVMSnapshot


def test_logical_volume_init():
    lv = LogicalVolume(vg_name="vg_test", lv_name="lv_test")
    assert lv.vg_name == "vg_test"
    assert lv.lv_name == "lv_test"
    assert lv.device_path == Path("/dev/vg_test/lv_test")


def test_real_logical_volume():
    # This test requires a real logical volume to be present
    # and may not be suitable for all environments.
    lv = LogicalVolume(vg_name="vg0", lv_name="lv0")
    assert lv.device_path.exists()
    assert lv.device_path.is_block_device()


def test_real_snapshot_init_and_destroy():
    # This test requires a real logical volume to be present
    # and may not be suitable for all environments.
    lv = LogicalVolume(vg_name="vg0", lv_name="lv0")
    snapshot = LVMSnapshot(
        origin=lv,
        size=1,
        size_unit="G",
        mount_point=Path("/mnt/snapshot"),
        dry_run=False,
    )
    assert snapshot.device_path.exists()
    assert snapshot.device_path.is_block_device()
    snapshot.destroy()
    assert not snapshot.device_path.exists()


def test_create_and_remove_mount_point():
    lv = LogicalVolume(vg_name="vg0", lv_name="lv0")
    snapshot = LVMSnapshot(
        origin=lv,
        size=1,
        size_unit="G",
        mount_point=Path("/mnt/snapshot"),
        dry_run=False,
    )
    snapshot.create_mount_point()
    assert snapshot.mount_point.exists()
    snapshot.delete_mount_point()
    assert not snapshot.mount_point.exists()
    snapshot.destroy()


def test_mount_and_unmount():
    lv = LogicalVolume(vg_name="vg0", lv_name="lv0")
    snapshot = LVMSnapshot(
        origin=lv,
        size=1,
        size_unit="G",
        mount_point=Path("/mnt/snapshot"),
        dry_run=False,
    )
    snapshot.create_mount_point()
    snapshot.mount()
    assert os.path.ismount(snapshot.mount_point)
    snapshot.unmount()
    assert not os.path.ismount(snapshot.mount_point)
    snapshot.destroy()


def test_real_snapshot_backup_prepare_and_cleanup():
    lv = LogicalVolume(vg_name="vg0", lv_name="lv0")
    snapshot = LVMSnapshot(
        origin=lv,
        size=1,
        size_unit="G",
        mount_point=Path("/mnt/snapshot"),
        dry_run=False,
    )
    assert snapshot.device_path.exists()
    snapshot.prepare_for_backup()
    assert snapshot.mount_point.exists()
    assert os.path.ismount(path=snapshot.mount_point)
    snapshot.post_backup_cleanup()
    assert not snapshot.mount_point.exists()
    assert not snapshot.device_path.exists()
