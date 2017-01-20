import struct
import logging
logger = logging.getLogger(__name__)
from pmc_camera.communication.command_classes import Command, ListArgumentCommand, COMMAND_FORMAT_PREFIX, CommandManager

DESTINATION_ALL_CAMERAS = 255
DESTINATION_WIDEFIELD_CAMERAS = 254
DESTINATION_NARROWFIELD_CAMERAS = 253
DESTINATION_LIDAR = 252

command_manager = CommandManager()
command_manager.add_command(Command("set_focus",[("focus_step", '1H')]))
command_manager.add_command(Command("set_exposure",[("exposure_time_us", '1L')]))
command_manager.add_command(ListArgumentCommand("set_peer_polling_order",'1B'))

logger.debug("Built command manager with %d total commands" % (command_manager.total_commands))

class CommandStatus():
    command_ok = 0
    failed_to_ping_destination = 1
    command_error = 2
