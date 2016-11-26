import serial
import struct

USB_PORT_ADDRESS = '/dev/ttyUSB0'
BAUDRATE = 115200

ser = serial.Serial(USB_PORT_ADDRESS, baudrate=BAUDRATE)
ser.timeout = 5
while True:
    data = ser.read(255)

    format_string = '%dB' % len(data)
    d = struct.unpack(format_string, data)
    print d
ser.close()