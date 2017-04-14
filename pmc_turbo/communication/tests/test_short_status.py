from nose.tools import assert_raises, assert_almost_equal

from pmc_turbo.communication.short_status import ShortStatusCamera, ShortStatusLeader, decode_one_byte_summary,encode_one_byte_summary

def test_incomplete_status():
    ss = ShortStatusCamera()
    with assert_raises(RuntimeError):
        ss.encode()

def test_camera_encode():
    ss = ShortStatusCamera()
    ss.message_id =0
    ss.timestamp = 123.133
    ss.leader_id =0
    ss.free_disk_root_mb = 123000
    ss.free_disk_var_mb = 127000
    ss.free_disk_data_1_mb = 123000
    ss.free_disk_data_2_mb = 123000
    ss.free_disk_data_3_mb = 123000
    ss.free_disk_data_4_mb = 123000
    ss.total_images_captured = 49494
    ss.camera_packet_resent = 0
    ss.camera_packet_missed =0
    ss.camera_frames_dropped = 0
    ss.camera_timestamp_offset_us = 65
    ss.exposure_us = 4774
    ss.focus_step = 2000
    ss.aperture_times_100 = 123
    ss.pressure = 101033.3
    ss.lens_wall_temp = 30
    ss.dcdc_wall_temp = 25
    ss.labjack_temp = 28
    ss.camera_temp = 50
    ss.ccd_temp = 53
    ss.rail_12_mv = 12000
    ss.cpu_temp = 70
    ss.sda_temp = 55
    ss.sdb_temp = 45
    ss.sdc_temp = 48
    ss.sdd_temp = 47
    ss.sde_temp = 46
    ss.sdf_temp = 77
    original_values = ss._values.copy()
    result = ss.encode()
    ss = ShortStatusCamera(result)
    for key in original_values.keys():
        assert_almost_equal(original_values[key], ss._values[key],places=1)


def test_coerce():
    ss = ShortStatusCamera()
    ss.message_id =0
    ss.timestamp = 123.133
    ss.leader_id =0
    ss.free_disk_root_mb = 12300000000 # intentionally > 2^32 to check clipping
    ss.free_disk_var_mb = 16400
    ss.free_disk_data_1_mb = 123000
    ss.free_disk_data_2_mb = 123000
    ss.free_disk_data_3_mb = 123000
    ss.free_disk_data_4_mb = 123000
    ss.total_images_captured = 49494
    ss.camera_packet_resent = 0
    ss.camera_packet_missed =0
    ss.camera_frames_dropped = 0
    ss.camera_timestamp_offset_us = 65
    ss.exposure_us = 4774
    ss.focus_step = 200000
    ss.aperture_times_100 = 123
    ss.pressure = 101033.3
    ss.lens_wall_temp = 300
    ss.dcdc_wall_temp = -225
    ss.labjack_temp = 28
    ss.camera_temp = 50
    ss.ccd_temp = 53
    ss.rail_12_mv = 12000
    ss.cpu_temp = 70
    ss.sda_temp = 55
    ss.sdb_temp = 45
    ss.sdc_temp = 48
    ss.sdd_temp = 47
    ss.sde_temp = 46
    ss.sdf_temp = 77
    values = ss._values.copy()
    ss2 = ShortStatusCamera(ss.encode())
    assert ss2.free_disk_root_mb == 2**32-2
    assert ss2.focus_step == 2**16-2
    assert ss2.lens_wall_temp == 126
    assert ss2.dcdc_wall_temp == -128

    ss._values = values
    ss.timestamp = "hello"
    result = ss.decode(ss.encode())
    assert result['timestamp'] == 0

def test_sizes():
    ss = ShortStatusCamera()
    print "camera status size:", ss.encoded_size
    assert ss.encoded_size <= 255
    ss = ShortStatusLeader()
    print "leader status size:", ss.encoded_size
    assert ss.encoded_size <= 255

def test_dir():
    ss = ShortStatusCamera()
    dir(ss)

def test_non_existant_attribute():
    ss = ShortStatusCamera()
    with assert_raises(AttributeError):
        ss.asdfb = 45


def test_one_byte():
    for value in range(255):
        result = decode_one_byte_summary(value)
        new_byte = encode_one_byte_summary(**result)
        assert value == new_byte
    with assert_raises(ValueError):
        decode_one_byte_summary(1000)