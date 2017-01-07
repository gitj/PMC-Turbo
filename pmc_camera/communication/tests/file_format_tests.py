import unittest
import tempfile
import os
import copy
import shutil
import inspect
from pmc_camera.communication import file_format_classes

def test_unique_file_types():
    file_types = [eval('file_format_classes.'+k+'.file_type') for k in dir(file_format_classes) if k.endswith('File')]
    print "found these file types:", file_types
    assert len(file_types) == len(set(file_types))

class TestGeneralFile(unittest.TestCase):
    def test_basic(self):
        file_format_classes.GeneralFile(payload='blah',filename='hello.txt',timestamp=123.1,request_id=535)

    def test_argument_errors(self):
        with self.assertRaises(ValueError):
            file_format_classes.GeneralFile(payload='blah',filename='hello.txt',timestamp=123.1)
        with self.assertRaises(ValueError):
            file_format_classes.GeneralFile(payload='blah',filename='hello.txt',timestamp=123.1,request_id=535,
                                            extra_arg='???')
        with self.assertRaises(ValueError):
            file_format_classes.GeneralFile(buffer='')

def check_file_round_trip(instance,from_file_method):
    tempdir = tempfile.mkdtemp()
    filename = os.path.join(tempdir,'blah')
    instance.write_buffer_to_file(filename)
    output = from_file_method(filename)
    for attr in instance._metadata_parameter_names:
        assert file_format_classes.equal_or_close(getattr(instance,attr), getattr(output,attr))
    assert instance.payload == output.payload
    shutil.rmtree(tempdir,ignore_errors=True)

def test_file_round_trips():
    general_file = file_format_classes.GeneralFile(payload='blah',filename='hello.txt',timestamp=123.1,request_id=535)
    jpeg_file = file_format_classes.JPEGFile(payload='d'*1000,frame_status=2**31,frame_id=100,frame_timestamp_ns=2**38,
                                             focus_step=987,aperture_stop=789,exposure_us=int(100e3),file_index=12345,
                                             write_timestamp=1233.3333,acquisition_count=2,lens_status=0x6523,
                                             gain_db=300,focal_length_mm=135,row_offset=1,column_offset=2,
                                             num_rows=3232,num_columns=4864,scale_by=1/8.,quality=75,request_id=7766)
    for instance,from_file_method in [(general_file,file_format_classes.GeneralFile.from_file),
                                      (jpeg_file,file_format_classes.JPEGFile.from_file)]:
        yield check_file_round_trip, instance, from_file_method

def check_same_attributes(c1):
    c2 = copy.deepcopy(c1)
    dir1 = dir(c1)
    _ = c1.to_buffer()
    dir2 = dir(c1)
    assert dir1 == dir2
    public_attributes = [x for x in dir1 if not x.startswith('__')]
    for attr in public_attributes:
        if inspect.ismethod(getattr(c1,attr)):
            continue
        assert getattr(c1,attr) == getattr(c2,attr)

def test_to_buffer_idempotent():
    general_file = file_format_classes.GeneralFile(payload='blah',filename='hello.txt',timestamp=123.1,request_id=535)
    jpeg_file = file_format_classes.JPEGFile(payload='d'*1000,frame_status=2**31,frame_id=100,frame_timestamp_ns=2**38,
                                             focus_step=987,aperture_stop=789,exposure_us=int(100e3),file_index=12345,
                                             write_timestamp=1233.3333,acquisition_count=2,lens_status=0x6523,
                                             gain_db=300,focal_length_mm=135,row_offset=1,column_offset=2,
                                             num_rows=3232,num_columns=4864,scale_by=1/8.,quality=75,request_id=7766)
    for instance in [general_file,jpeg_file]:
        yield check_same_attributes, instance