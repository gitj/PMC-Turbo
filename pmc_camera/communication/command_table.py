import struct
import logging
logger = logging.getLogger(__name__)
from pmc_camera.communication.command_classes import Command, ListArgumentCommand, COMMAND_FORMAT_PREFIX

DESTINATION_ALL_CAMERAS = 255
DESTINATION_WIDEFIELD_CAMERAS = 254
DESTINATION_NARROWFIELD_CAMERAS = 253
DESTINATION_LIDAR = 252

class CommandStatus():
    command_ok = 0
    failed_to_ping_destination = 1
    command_error = 2

command_list = [Command("set_focus",[("focus_step", '1H')]),
                Command("set_exposure",[("exposure_time_us", '1L')]),
                ListArgumentCommand("set_peer_polling_order",'1B')]

command_dict = {}
for number,command in enumerate(command_list):
    command._command_number = number
    command_dict[number] = command

logger.debug("Built command table with total of %d commands" % len(command_list))

def decode_commands_from_string(data):
    remainder = data
    commands = []
    while remainder:
        command_number = struct.unpack(COMMAND_FORMAT_PREFIX,data[:1])
        command = command_dict[command_number]
        kwargs, remainder = command.decode_command_and_arguments(data)
        commands.append((command.name,kwargs))
    return commands