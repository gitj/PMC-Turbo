import science_communication


class SIPPacketDecoder():
    def __init__(self, max_buffer_len=260):
        # Currently use ip='192.168.1.137', port=4001
        self.buffer = ''
        self.max_buffer_len = max_buffer_len
        self.candidate_packets = []
        self.confirmed_packets = []

    def find_interesting_byte(self, buffer, byte_of_interest):
        idxs = []
        for idx, byte in enumerate(buffer):
            if byte == byte_of_interest:
                idxs.append(idx)
        return idxs

    def find_candidate_packets(self):
        idxs = self.find_interesting_byte(self.buffer, '\x10')
        end_idxs = self.find_interesting_byte(self.buffer, '\x03')
        for idx in idxs:
            for end_idx in end_idxs:
                if end_idx > idx:
                    self.candidate_packets.append(self.buffer[idx:end_idx + 1])

    def put_bytes_in_buffer(self, bytes):
        self.buffer += bytes

    def process_buffer(self):
        self.find_candidate_packets()
        if len(self.buffer) > self.max_buffer_len:
            self.buffer = self.buffer[-self.max_buffer_len]
            # Find potential packets, cut the buffer to the most recent bytes.

    def process_candidate_packets(self):
        for packet in self.candidate_packets:
            self.confirmed_packets.append([packet for packet in self.candidate_packets if self.test_packet(packet)])
        self.candidate_packets = []
        # Grab the good packets, empty the candidate_packets

    def test_packet(self, potential_packet):
        try:
            packet = science_communication.decode_packet(potential_packet)
            return True
        except:
            return False
