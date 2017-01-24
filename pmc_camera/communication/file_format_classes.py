import logging
import struct

from pmc_camera.utils.comparisons import equal_or_close

logger = logging.getLogger(__name__)


class FileBase(object):
    _metadata_table = [('1I','request_id'),
                       ('1B','camera_id')]

    def __init__(self,buffer=None,payload=None,**kwargs):
        self._metadata_format_string = '>' + ''.join([format_ for format_,name in self._metadata_table])
        self._metadata_length = struct.calcsize(self._metadata_format_string)
        self._metadata_name_to_format = dict([(name,format_) for format_,name in self._metadata_table])
        self._metadata_parameter_names = [name for (format_,name) in self._metadata_table]
        if buffer is not None:
            self._from_buffer(buffer)
        else:
            self.from_values(payload,**kwargs)

    @classmethod
    def from_file(cls,filename):
        with open(filename,'r') as fh:
            buffer = fh.read()
        file_type, = struct.unpack('>1B',buffer[0])
        buffer = buffer[1:]
        if file_type != cls.file_type:
            raise RuntimeError("File %s contains file type code %d, which does not match type code %d ofthe class you "
                               "are trying to read with. try using load_load_and_decode_file instead"
                               % (filename, file_type, cls.file_type))
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
                if not equal_or_close(value, formatted_value):
                    logger.critical("Formatting parameter %s as '%s' results in loss of information!\nOriginal value "
                                    "%r   Formatted value %r" % (key,format_,value,formatted_value))
                setattr(self,key,value)
            else:
                raise ValueError("Received parameter %s that is not expected for this file type" % key)

    def _from_buffer(self, buffer):
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
        header = struct.pack('>1B',self.file_type) + struct.pack(self._metadata_format_string,*values)
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
    _metadata_table = (FileBase._metadata_table+[('1H','filename_length'),
                       ('1f','timestamp')])
    file_type = 2
    def from_values(self,payload,**kwargs):
        try:
            filename = kwargs.pop('filename')
        except KeyError:
            raise ValueError("filename must be specified")
        kwargs['filename_length'] = len(filename)
        super(GeneralFile,self).from_values(payload,**kwargs)
        self.filename = filename

    def _from_buffer(self, buffer):
        super(GeneralFile,self)._from_buffer(buffer)
        payload_with_filename = self.payload
        if len(payload_with_filename) < self.filename_length:
            raise ValueError("Error decoding file, payload length %d is not long enough to contain filename of length %d"
                             % (len(payload_with_filename),self.filename_length))
        self.filename = payload_with_filename[:self.filename_length]
        self.payload = payload_with_filename[self.filename_length:]

    def to_buffer(self):
        original_payload = self.payload
        self.payload = self.filename + original_payload
        try:
            result = super(GeneralFile,self).to_buffer()
        finally:
            self.payload = original_payload
        return result


class ShellCommandFile(FileBase):
    _metadata_table = (FileBase._metadata_table +
                       [('1f', 'timestamp'),
                        ('1B', 'timed_out'),
                        ('1i', 'returncode')])
    file_type = 3


try:
    file_classes = [eval(k) for k in dir() if k.endswith('File')]
    file_type_to_class = dict([(k.file_type, k) for k in file_classes])
except Exception as e:
    raise RuntimeError("Problem in file_format_classes.py: couldn't extract file_types from all file_classes %r" % e)


def decode_file_from_buffer(buffer):
    file_type, = struct.unpack('>1B', buffer[0])
    buffer = buffer[1:]
    try:
        file_class = file_type_to_class[file_type]
    except KeyError:
        raise RuntimeError("This buffer claims to be file_type %d, which doesn't exist. Known file_types: %r. Next "
                           "few bytes of offending buffer %r" % (file_type, file_type_to_class, buffer[:10]))
    return file_class(buffer=buffer)


def load_and_decode_file(filename):
    with open(filename, 'r') as fh:
        buffer = fh.read()
    return decode_file_from_buffer(buffer)
