from traitlets import (Int, Unicode, Bytes, List, Float, Enum, TCPAddress, Dict)
from traitlets.config import Configurable

standard_baudrates = (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000, 576000, 921600, 1000000)

class GroundConfiguration(Configurable):
    openport_uplink_address = TCPAddress(('pmc-camera-0',4501), help="(IP,port) tuple to send OpenPort commands to").tag(config=True)
    command_port = Bytes('/dev/ttyUSB1', help="Serial device connected to GSE uplink").tag(config=True)

    downlink_parameters = Dict(default_value=dict(openport=dict(port=4501,baudrate=None,loop_interval=1.0),
                                                  gse_sip=dict(port='/dev/ttyUSB0',baudrate=115200, loop_interval=1.0),
                                                  los=dict(port='/dev/ttyS0',baudrate=115200, loop_interval=1.0),
                                                  tdrss_direct=dict(port='/dev/ttyUSB2',baudrate=115200,loop_interval=1.0)))

