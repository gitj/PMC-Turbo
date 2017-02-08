import logging

logger = logging.getLogger(__name__)
from pmc_turbo.camera.communication.command_classes import Command, ListArgumentCommand, CommandManager, StringArgumentCommand

DESTINATION_ALL_CAMERAS = 255
DESTINATION_WIDEFIELD_CAMERAS = 254
DESTINATION_NARROWFIELD_CAMERAS = 253
DESTINATION_LIDAR = 252

command_manager = CommandManager()
command_manager.add_command(Command("set_focus", [("focus_step", '1H')]))
command_manager.add_command(Command("set_exposure", [("exposure_time_us", '1I')]))
command_manager.add_command(ListArgumentCommand("set_peer_polling_order", '1B'))
command_manager.add_command(StringArgumentCommand("request_specific_file", [("max_num_bytes", '1i'),
                                                                            ("request_id", '1I'),
                                                                            ("filename", "s")]))
command_manager.add_command(StringArgumentCommand("run_shell_command", [("max_num_bytes_returned", '1I'),
                                                                        ("request_id", '1I'), ("timeout", "1f"),
                                                                        ("command_line", "s")]))
command_manager.add_command(Command("get_status_report", []))

logger.debug("Built command manager with %d total commands" % (command_manager.total_commands))


class CommandStatus():
    command_ok = 0
    failed_to_ping_destination = 1
    command_error = 2
