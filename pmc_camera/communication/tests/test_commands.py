from pmc_camera.communication.command_classes import Command,ListArgumentCommand

def test_list_argument_command_round_trip():
    c = ListArgumentCommand("some_command",'1H')
    c._command_number=45

    list_argument = range(10)
    encoded = c.encode_command(list_argument)
    kwargs,remainder = c.decode_command_and_arguments(encoded)
    for a,b in  zip(kwargs['list_argument'],list_argument):
        assert a==b