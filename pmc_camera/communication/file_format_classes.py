import logging
import struct
import numpy as np
logger = logging.getLogger(__name__)

def equal_or_close(value1,value2):
    if type(value1) is float:
        return np.allclose(value1,value2)
    if type(value1) is str:
        return value1 == value2[:value2.find('\x00')]
    else:
        return value1 == value2

class FileBase(object):
    _metadata_table = [('1I','request_id')]

    def __init__(self,buffer=None,payload=None,**kwargs):
        self._metadata_format_string = '>' + ''.join([format_ for format_,name in self._metadata_table])
        self._metadata_length = struct.calcsize(self._metadata_format_string)
        self._metadata_name_to_format = dict([(name,format_) for format_,name in self._metadata_table])
        self._metadata_parameter_names = [name for (format_,name) in self._metadata_table]
        if buffer is not None:
            self.from_buffer(buffer)
        else:
            self.from_values(payload,**kwargs)

    @classmethod
    def from_file(cls,filename):
        with open(filename,'r') as fh:
            buffer = fh.read()
        return cls(buffer=buffer)

    def from_values(self,payload,**kwargs):
        self.payload = payload
        for key in self._metadata_parameter_names:
            if not key in kwargs:
                raise ValueError("Parameter %s missing when creating %s" % (key,self.__class__.__name__))
        for key,value in kwargs.items():
            if key in self._metadata_name_to_format:
                format_ = self._metadata_name_to_format[key]
                formatted_value, = struct.unpack('>'+format_,struct.pack('>'+format_,value))
                if type(value) is str:
                    formatted_value = formatted_value[:formatted_value.find('\x00')]
                if not equal_or_close(value,formatted_value):
                    logger.critical("Formatting parameter %s as '%s' results in loss of information!\nOriginal value "
                                    "%r   Formatted value %r" % (key,format_,value,formatted_value))
                    if type(value) is str:
                        value = value[-256:]

                setattr(self,key,value)
            else:
                raise ValueError("Received parameter %s that is not expected for this file type" % key)

    def from_buffer(self,buffer):
        if len(buffer) <= self._metadata_length:
            raise ValueError("Cannot decode this buffer; the buffer length %d is not long enough. The metadata length is %d" %
                             (len(buffer), self._metadata_length))
        header = buffer[:self._metadata_length]
        self.payload = buffer[self._metadata_length:]
        parameters = struct.unpack(self._metadata_format_string,header)
        for name,value in zip(self._metadata_parameter_names,parameters):
            setattr(self,name,value)

    def to_buffer(self):
        values = []
        for name in self._metadata_parameter_names:
            values.append(getattr(self,name))
        header = struct.pack(self._metadata_format_string,*values)
        if self.payload is not None:
            result = header + self.payload
        else:
            result = header
        return result

    def write_payload_to_file(self,filename):
        if self.payload is None:
            raise ValueError("This file has no payload.")
        with open(filename,'w') as fh:
            fh.write(self.payload)

    def write_buffer_to_file(self,filename):
        with open(filename,'w') as fh:
            fh.write(self.to_buffer())


class ImageFileBase(FileBase):
    _metadata_table = (FileBase._metadata_table +
                       [('1L','frame_status'),
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
                       ('1H','row_offset'),
                       ('1H','column_offset'),
                       ('1H','num_rows'),
                       ('1H','num_columns'),
                       ('1f','scale_by'),
                       ])


class JPEGFile(ImageFileBase):
    _metadata_table = (ImageFileBase._metadata_table +
                       [('1f', 'quality')])
    file_type = 1

class GeneralFile(FileBase):
    _metadata_table = (FileBase._metadata_table+[('256s','filename'),
                       ('1f','timestamp')])
    file_type = 2

class UnixCommandFile(FileBase):
    _metadata_table = (FileBase._metadata_table +
                       [('1f','timestamp'),
                       ('1f','walltime'),
                       ('1i','exit_status')])
    file_type=3

class OldJPEGFile():
    _metadata_format_string = '>1L1L1H1H1L'
    file_type = 99

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



try:
    file_classes = [eval(k) for k in dir() if k.endswith('File')]
    file_type_to_class = dict([(k.file_type,k) for k in file_classes])
except Exception as e:
    raise RuntimeError("Problem in file_format_classes.py: couldn't extract file_types from all file_classes %r" % e)

def decode_file_from_buffer(buffer):
    file_type = struct.unpack('>1B',buffer[0])
    buffer = buffer[1:]
    file_class = file_type_to_class[file_type]
    return file_class(buffer=buffer)