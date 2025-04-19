from resticlvm.local_classes import LogicalVolume


def test_logical_volume_init():
    lv = LogicalVolume(vg_name="vg_test", lv_name="lv_test")
    assert lv.vg_name == "vg_test"
    assert lv.lv_name == "lv_test"
