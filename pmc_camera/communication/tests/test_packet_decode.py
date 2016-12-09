import SIP_communication_simulator
import science_communication

def test_packet_construct_decode(packet_construct_method, packet_decode_method):
    # Problem, some packet_construct_methods take in arguments (for data they will send)
    packet = packet_construct_method()
    decoded_packet = packet_decode_method(packet)
    return decoded_packet


def test_junk_packet_decode(packet_decode_method):
    np.random.seed(0)
    random_array = np.random.randint(0, 255, 123)
    packet = struct.pack('<255s', random_array.tostring())
    packet_decode_method(packet)
# test decoder with junk packet
# packet with bad start, end bytes
# packet with junk in the middle

# packet with half data missing
# wrong-sized packet
