import serial
import time

class birger():

    def __init__(self, port='/dev/ttyUSB0'):
        self.initialize(port)
        return

    def initialize(self, port):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.5
        self.s.bytesize = 8
        self.stopbits = 1
        self.state_dict = {'focus', 'aperture'}
        check = self.flush_buffer()
        check = self.set_protocol
        self.initialize_aperture()
        self.ap_min, self.ap_max = (0, self.find_aperture_range())
        self.ap_pos = int(self.ap_max)
        # When we find the ap_range we set the ap_pos to max (fully closed)
        self.fmin, self.fmax, self.f_pos = self.find_focus_and_range() 

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

    def initialize_aperture(self):
        # Required when the aperature hasn't been initialized.
        return self.sendget('in')

    def find_aperture_range(self):
        # Closes aperture fully, gets info to find what absolute step it is at.
        # Slices string and returns max.
        response = self.sendget('mc')
        return int(self.sendget('pa').split(',')[0])

    def move_aperture(self, steps):
        # Moves aperture incremental steps.
        # Negative for open, positive for close.
        # This should return something for reaching limit.
        response = self.sendget('mn' + str(steps))
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.ap_pos += steps_taken
        return

    def find_focus_and_range(self):
        #self.s.timeout = 3
        # la takes some time
        #response = self.sendget('la0')
        #self.s.timeout = 0.5
        focus_range_string = self.sendget('fp')
        raw = focus_range_string.split(':')
        return (int(raw[1].strip('fmax')), int(raw[2].strip('current')), int(raw[3].strip('\r')))
        # min, max, current
        # We should discuss how often to redo the la command.
        # Seems like we shouldn't do it every time, however.

    def move_focus(self, steps):
        response = self.sendget('mf'+str(steps))
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.f_pos += steps_taken
        return

    def print_status(self):
        print 'Ap min: %d, Ap max: %d, Current ap: %d' % (self.ap_min, self.ap_max, self.ap_pos)
        print 'f min: %d, f max: %d, Current f: %d' % (self.fmin, self.fmax, self.f_pos)
    
