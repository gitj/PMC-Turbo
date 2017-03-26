import logging

logger = logging.getLogger(__name__)
from pmc_turbo.communication.command_classes import Command, ListArgumentCommand, CommandManager, StringArgumentCommand

DESTINATION_ALL_CAMERAS = 255
DESTINATION_WIDEFIELD_CAMERAS = 254
DESTINATION_NARROWFIELD_CAMERAS = 253
DESTINATION_LIDAR = 252
DESTINATION_SUPER_COMMAND = 251 # use for sending commands to anyone listening, i.e for manually assigning leader
DESTINATION_LEADER = 250

USE_BULLY_ELECTION = 254

command_manager = CommandManager()
command_manager.add_command(Command("set_focus", [("focus_step", 'H')]))
command_manager.add_command(Command("set_exposure", [("exposure_time_us", 'I')]))
command_manager.add_command(Command("set_fstop", [("fstop", 'f')]))
command_manager.add_command(Command("run_focus_sweep", [('request_id', 'I'),
                                                        ('row_offset', 'H'),
                                                        ('column_offset', 'H'),
                                                        ('num_rows', 'H'),
                                                        ('num_columns', 'H'),
                                                        ('scale_by', 'f'),
                                                        ('quality', 'B'),
                                                        ('start', 'H'),
                                                        ('stop', 'H'),
                                                        ('step', 'h')]))
command_manager.add_command(StringArgumentCommand("send_arbitrary_camera_command",[("command", "s")],
                                                  docstring="Set an arbitrary camera parameter or execute a camera command.\n"
                                                            "The `command` string must be of the format <parameter name>:<parameter value> (colon delimeter)\n"
                                                            "Or, to execute a command, use the format <command name>:None"))
command_manager.add_command(Command("set_standard_image_parameters", [("row_offset", "H"),
                                                                      ("column_offset", "H"),
                                                                      ("num_rows", "H"),
                                                                      ("num_columns", "H"),
                                                                      ("scale_by", "f"),
                                                                      ("quality", "B")]))
command_manager.add_command(Command("request_specific_images", [("timestamp", "d"),
                                                                ("request_id", "I"),
                                                                ("num_images", "H"),
                                                                ("step", "i"),
                                                                ("row_offset", "H"),
                                                                ("column_offset", "H"),
                                                                ("num_rows", "H"),
                                                                ("num_columns", "H"),
                                                                ("scale_by", "f"),
                                                                ("quality", "B")]))
command_manager.add_command(ListArgumentCommand("set_peer_polling_order", 'B',
                                                docstring="Argument is list of uint8 indicating order"))
command_manager.add_command(StringArgumentCommand("request_specific_file", [("max_num_bytes", 'i'),
                                                                            ("request_id", 'I'),
                                                                            ("filename", "s")]))
command_manager.add_command(StringArgumentCommand("run_shell_command", [("max_num_bytes_returned", 'I'),
                                                                        ("request_id", 'I'),
                                                                        ("timeout", "f"),
                                                                        ("command_line", "s")],
                                                  docstring="`timeout` is maximum number of seconds command will be allowed to run.\n"
                                                            "`command_line` is shell command to execute"))
command_manager.add_command(Command("get_status_report", [("compress", "B"),
                                                          ("request_id", 'I')],
                                    docstring="if `compress` is non-zero, result will be compressed for downlink"))
command_manager.add_command(Command("flush_downlink_queues", []))
command_manager.add_command(Command("use_synchronized_images", [("synchronize", "B")],
                                    docstring="non-zero argument means images should be synchronized"))
command_manager.add_command(Command("set_downlink_bandwidth", [("openport", "I"),
                                                               ("highrate", "I"),
                                                               ("los", "I")],
                                    docstring="bandwidths are specified in bytes per second"))
command_manager.add_command(Command("set_leader", [("leader_id", "B")],
                                    docstring="Set leader or election directly.\n"
                                    "Typically used with destination SUPER_COMMAND to override"
                                    ))

# add command to set pyro comm timeout?

logger.debug("Built command manager with %d total commands" % (command_manager.total_commands))


