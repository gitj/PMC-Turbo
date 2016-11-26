import serial

USB_PORT_ADDRESS = '/dev/ttyUSB1'
BAUDRATE = 2400

ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)

msg = '\x10\x01\x09\x02\x00\x00\x03'

ser.write(msg)
ser.close()
'''
import struct


def construct_request_to_send_packet(link_routing, routing_address, data):
    # link_routing is 0x00, 0x01, or 0x02
    # 0x00 is LOS, 0x01 is TDRSS, 0x02 is Iridium
    # Routing address is 0x09 or 0x0c
    # 0x09 selects science interface COMM1
    # 0x0c selects science interface COMM2
    # Length below 20 must be even, above 20 does not require even.
    # Below 20 packs of 2 bytes will be sent, above 20 one packet will be sent.

    # LOS can communicate with COMM1 or COMM2
    # TDRSS only COMM1
    # Iridium only COMM2

    format_string = '<4B%ds1B' % len(data)
    return struct.pack(format_string, 0x10, link_routing, routing_address, len(data), data, 0x03)
    '''
