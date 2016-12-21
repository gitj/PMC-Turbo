import struct


class JPEGFile():
    _metadata_format_string = '>1B1L1L1H1H1L'
    file_type = 1

    def __init__(self, buffer=None, payload=None, overall_status=None, frame_status=None, frame_id=None,
                 focus_step=None, aperture_stop=None, exposure_ms=None):

        self._metadata_length = struct.calcsize(self._metadata_format_string)
        if buffer is not None:
            self.from_buffer(buffer)
        else:
            self.payload = payload
            self.overall_status = overall_status
            self.frame_status = frame_status
            self.frame_id = frame_id
            self.focus_step = focus_step
            self.aperture_stop = aperture_stop
            self.exposure_ms = exposure_ms

    def from_buffer(self, buffer):
        """
        Decode and validate the given buffer and update the class attributes accordingly

        Parameters
        ----------
        buffer : str
            buffer to decode as a packet
        """

        self.payload = buffer[self._metadata_length:]
        self.overall_status, self.frame_status, self.frame_id, self.focus_step, self.aperture_stop, self.exposure_ms = struct.unpack(
            self._metadata_format_string, buffer[:self._metadata_length])

    def to_buffer(self):
        metadata_buffer = struct.pack(self._metadata_format_string, self.overall_status, self.frame_status,
                                      self.frame_id, self.focus_step,
                                      self.aperture_stop, self.exposure_ms)

        return metadata_buffer + self.payload

    def write(self, filename):
        with open(filename + '.jpg', 'wb') as f:
            f.write(self.payload)
        with open(filename + '.info', 'w') as f:
            msg = 'Overall status: %d\nFrame status: %d\nFrame id: %d\nFocus Step: %d\nAperture Stop: %d\nExposure: %d' % (
                self.overall_status, self.frame_status, self.frame_id, self.focus_step, self.aperture_stop,
                self.exposure_ms)
            f.write(msg)
