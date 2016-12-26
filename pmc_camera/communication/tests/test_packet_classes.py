from pmc_camera.communication import packet_classes

def test_gse_packet_roundtrip():
    packet = packet_classes.GSEPacket(sync2_byte=0xFA,origin=1,payload='hi there!')
    packet2 = packet_classes.GSEPacket(buffer=packet.to_buffer())
    assert packet.sync2_byte == packet2.sync2_byte
    assert packet.origin == packet2.origin
    assert packet.payload_length == packet2.payload_length
    assert packet.checksum == packet2.checksum
    assert packet.payload == packet2.payload

def test_hirate_packet_roundtrip():
    packet = packet_classes.HiratePacket(file_id=99,file_type=89,packet_number=1,total_packet_number=10,
                                         payload="the payload is long")
    packet2 = packet_classes.HiratePacket(buffer=packet.to_buffer())
    assert packet.file_type == packet2.file_type
    assert packet.file_id == packet2.file_id
    assert packet.payload_crc == packet2.payload_crc
    assert packet.payload_length == packet2.payload_length
    assert packet.payload == packet2.payload
    assert packet.packet_number == packet2.packet_number
    assert packet.total_packet_number == packet2.total_packet_number