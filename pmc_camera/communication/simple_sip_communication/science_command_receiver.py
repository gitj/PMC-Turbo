import socket
import struct

IP = '192.168.1.137'

PORT = 4001


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, PORT))

    while True:
        data = sock.recv(1024)
        format_string = '%dB' % len(data)
        d = struct.unpack(format_string, data)
        print d

if __name__ == "__main__":
    main()