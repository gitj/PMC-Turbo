from pmc_camera.communication import file_format_classes

def test_unique_file_types():
    file_types = [eval('file_format_classes.'+k+'.file_type') for k in dir(file_format_classes) if k.endswith('File')]
    print "found these file types:", file_types
    assert len(file_types) == len(set(file_types))