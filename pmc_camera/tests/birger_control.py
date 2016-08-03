import serial
import time

class birger():

    def __init__(self, port='/dev/ttyUSB0'):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.5
        self.s.bytesize = 8
        self.stopbits = 1
        set_birger_protocol = self.sendget('rm0,1')
        print set_birger_protocol
        # Sendget reads birger protocol in the rm0,1 mode.
        # We should write something that flushes the serial buffer.
        # And do error checking to make sure the protocol is as expected.

    def sendget(self, msg, wait=0.5, terminator='\r'):
        self.s.open()	
        self.s.write(msg+terminator)
        tic = time.time()
        resp = self.s.read()
        while resp and (time.time()-tic < wait):
            last = self.s.read()
            resp += last
            if len(resp) > 1:
                if resp[-1] == terminator:
                    break
        self.s.close()
        return resp
