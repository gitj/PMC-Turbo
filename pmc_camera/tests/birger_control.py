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

    def sendget(self, msg, wait=2):
        self.s.open()	
        self.s.write(msg)
        tic = time.time()
        resp = self.s.read()
#        while self.s.inWaiting()>0:
#             resp += self.s.read(1)
        while resp and (time.time()-tic < wait):
            last = self.s.read()
            resp += last
        #    time.sleep(0.001)
        # Tried using a timeout - also didn't work
        print resp
        self.s.close()
        return resp
