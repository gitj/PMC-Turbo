import serial
import time

class birger():

    def __init__(self, port='/dev/ttyUSB0'):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.01
        self.s.bytesize = 8
        self.stopbits = 1

    def sendget(self, msg, wait=2):
        self.s.open()	
        self.s.write(msg)
        #tic = time.time()
        resp = ''
        while self.s.inWaiting()>0:
             resp += self.s.read(1)
        #while time.time()-tic < wait:
        #    resp += self.s.read()
        #    time.sleep(0.001)
        # Tried using a timeout - also didn't work
        print resp
        self.s.close()
        return resp
