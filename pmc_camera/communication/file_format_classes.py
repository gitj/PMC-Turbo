import struct
import logging

logger = logging.getLogger(__name__)

class ImageFile(object):
    _metadata_table = [('1L','frame_status'),
                       ('1L','frame_id'),
                       ('1Q','frame_timestamp_ns'),
                       ('1H','focus_step'),
                       ('1H','aperture_stop'),
                       ('1L','exposure_us'),
                       ('1L','file_index'),
                       ('1d','write_timestamp',),
                       ('1H','acquisition_count',),
                       ('1H','lens_status',),
                       ('1H','gain_db',),
                       ('1H','focal_length_mm',),
                       ]
    file_type = 3
    def __init__(self,buffer=None,**kwargs):
        self._metadata_format_string = '>' + ''.join([format_ for format_,name in self._metadata_table])
        self._metadata_length = struct.calcsize(self._metadata_format_string)
        self._metadata_name_to_format = dict([(name,format_) for format_,name in self._metadata_table])
        if buffer is not None:
            self.from_buffer(buffer)
        else:
            self.from_values(**kwargs)

    def from_values(self,**kwargs):
        for key,value in kwargs:
            if key in self._metadata_name_to_format:
                format_ = self._metadata_name_to_format[key]
                formatted_value = struct.unpack('>'+format_,struct.pack('>'+format_,value))
                if value != formatted_value:
                    logger.critical("Formatting parameter %s as '%s' results in loss of information!\nOriginal value "
                                    "%r   Formatted value %r" % (key,format_,value,formatted_value))
                setattr(self,key,value)
            else:
                raise ValueError("Received parameter %s that is not expected for this file type" % key)

    def from_buffer(self,buffer):
        pass

class JPEGFile():
    _metadata_format_string = '>1L1L1H1H1L'
    file_type = 1

    def __init__(self, buffer=None, payload=None, frame_status=None, frame_id=None,
                 focus_step=None, aperture_stop=None, exposure_ms=None):

        self._metadata_length = struct.calcsize(self._metadata_format_string)
        if buffer is not None:
            self.from_buffer(buffer)
        else:
            self.payload = payload
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
        self.frame_status, self.frame_id, self.focus_step, self.aperture_stop, self.exposure_ms = struct.unpack(
            self._metadata_format_string, buffer[:self._metadata_length])

    def to_buffer(self):
        metadata_buffer = struct.pack(self._metadata_format_string, self.frame_status,
                                      self.frame_id, self.focus_step,
                                      self.aperture_stop, self.exposure_ms)

        return metadata_buffer + self.payload

    def write(self, filename):
        with open(filename + '.jpg', 'wb') as f:
            f.write(self.payload)
        with open(filename + '.info', 'w') as f:
            msg = 'Frame status: %d\nFrame id: %d\nFocus Step: %d\nAperture Stop: %d\nExposure: %d' % (
                self.frame_status, self.frame_id, self.focus_step, self.aperture_stop,
                self.exposure_ms)
            f.write(msg)

class GeneralFile(object):
    file_type = 2
    _metadata_format_string = '>1B1L1L1H1H1L'
    def __init__(self):
        pass
