from pmc_camera.communication import generate_bad_packets, udp_receiver


def simple_test():
    u = udp_receiver.UDPReceiver(ip='localhost', port=4001)
    u.put_bytes_in_buffer('\x10\x13\x03')
    u.process_buffer()
    assert (u.buffer == '\x10\x13\x03')
    assert (u.candidate_packets == ['\x10\x13\x03'])


def junk_before_test():
    u = udp_receiver.UDPReceiver(ip='localhost', port=4001)
    bytes = generate_bad_packets.generate_random_bytes(100) + '\x10\x13\x03'
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03'])


def junk_after_test():
    u = udp_receiver.UDPReceiver(ip='localhost', port=4001)
    bytes = '\x10\x13\x03' + generate_bad_packets.generate_random_bytes(100)
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03'])


def two_packets_test():
    u = udp_receiver.UDPReceiver(ip='localhost', port=4001)
    bytes = '\x10\x13\x03' + '\x10\x13\x03'
    u.put_bytes_in_buffer(bytes)
    u.process_buffer()
    assert (u.buffer == bytes)
    assert (u.candidate_packets == ['\x10\x13\x03', '\x10\x13\x03\x10\x13\x03', '\x10\x13\x03'])
