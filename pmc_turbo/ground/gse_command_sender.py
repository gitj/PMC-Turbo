import serial
import struct

USB_PORT_ADDRESS = '/dev/ttyUSB1'
BAUDRATE = 2400

HEADER = '\x10\x01\x09'
PACKET_LENGTH = '\x16'
FOOTER = '\x03'

def send_command(sequence, verify, which, command, args):
    padding_length = 22 - (4 + len(args))
    # Decided to pad the packet to 22 bytes so it is sent in one packet.
    padding = [0]*padding_length
    format_string = '<4B%dB' % (len(args) + padding_length)
    #msg = struct.pack(format_string, sequence, verify, which, command, *args, *padding)
    # Python only wants one unpacked list
    msg = struct.pack(format_string, sequence, verify, which, command, *(args+padding))
    print msg
    msg = HEADER+PACKET_LENGTH+msg+FOOTER
    print msg
    ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE, timeout=1)
    ser.write(msg)
    print '%r' % ser.read(100)
    ser.close()

# Example send_command(sequence=0,verify=0, which=4,command=1,args=[100,200,5])


'''
ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)

#msg = '\x10\x01\x09\x02\x00\x00\x03'
#msg = '\x10\x01\x09\x06\x11\x12\x13\x15\x16\x17\x03'
header = '\x10\x01\x09'
data = '\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01'
length = '\x1c'
footer = '\x03'
msg = header+length+data+footer
print msg

ser.write(msg)
ser.close()
'''

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
