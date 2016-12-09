import socket
import struct

IP = '192.168.1.253'
# IP address of the NPort
PORT = 4001
# Port which the NPort listens to.

#msg = '\x10\x50\x03'
# Request GPS Position
#msg = '\x10\x53\x04\x01\x02\x04\x05\x03'
msg = '\x10\x53\x04\x01\x01\x01\x01\x03'
# Message with some data (1,2,4,5)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(msg, (IP, PORT))
