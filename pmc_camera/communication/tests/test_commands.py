from pmc_camera.communication.command_classes import Command,ListArgumentCommand,StringArgumentCommand

def test_list_argument_command_round_trip():
    c = ListArgumentCommand("some_command",'1H')
    c._command_number=45

    list_argument = range(10)
    encoded = c.encode_command(list_argument)
    kwargs,remainder = c.decode_command_and_arguments(encoded)
    for a,b in  zip(kwargs['list_argument'],list_argument):
        assert a==b

def test_string_argument_command_round_trip():
    c = StringArgumentCommand("request_specific_file", [("max_num_bytes",'1i'), ("request_id",'1I'),
                                                                            ("filename", "s")])
    c._command_number = 46

    filename='/home/data/file.txt'
    request_id = 245333
    max_num_bytes=-453
    encoded = c.encode_command(filename=filename,request_id=request_id,max_num_bytes=max_num_bytes)
    kwargs,remainder = c.decode_command_and_arguments(encoded)
    assert kwargs['filename'] == filename
    assert kwargs['request_id'] == request_id
    assert kwargs['max_num_bytes'] == max_num_bytes
