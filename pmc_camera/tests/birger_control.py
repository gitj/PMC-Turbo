import serial
import time

class birger():

    def __init__(self, port='/dev/ttyUSB0'):
        self.initialize(port)

    def initialize(self, port):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.5
        self.s.bytesize = 8
        self.stopbits = 1
        self.state_dict = {'focus', 'aperature'}
        self.flush_buffer()
        self.set_protocol

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

    def flush_buffer(self):
        self.s.open()
        self.s.timeout = 0
        char_read = True
        while char_read:
            char_read = self.s.read() 
            print char_read
        self.s.close()
        self.s.timeout = 0.5
        return

    def set_protocol(self):
        # This should raise an error after n tries.
        set_birger_protocol = self.sendget('rm0,1')
        if set_birger_protocol != 'OK\r':
            self.flush_buffer()
            self.set_protocol()
        return

    def set_aperature(self, aperature):
        return

    def set_focus(self, focus):
        return

    def learn_focus(self, focus):
        return
