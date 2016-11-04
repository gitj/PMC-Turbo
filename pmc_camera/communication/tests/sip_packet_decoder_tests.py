from pmc_camera.communication import generate_bad_packets, sip_packet_decoder


def simple_test():
    u = sip_packet_decoder.SIPPacketDecoder()
    u.put_bytes_in_buffer('\x10\x13\x03')
    u.process_buffer()
    assert (u.buffer == '\x10\x13\x03')
    assert (u.candidate_packets == ['\x10\x13\x03'])


def junk_before_test():
    u = sip_packet_decoder.SIPPacketDecoder()
    bytes = generate_bad_packets.generate_random_bytes(100) + '\x10\x13\x03'
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03'])


def junk_after_test():
    u = sip_packet_decoder.SIPPacketDecoder()
    bytes = '\x10\x13\x03' + generate_bad_packets.generate_random_bytes(100)
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03'])


def two_packets_test():
    u = sip_packet_decoder.SIPPacketDecoder()
    bytes = '\x10\x13\x03' + '\x10\x13\x03'
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03', '\x10\x13\x03\x10\x13\x03', '\x10\x13\x03'])
