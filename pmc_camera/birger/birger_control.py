import serial
import time

class Birger(object):

    def __init__(self, port='/dev/ttyUSB0'):
        #self.initialize(port)
        return

    def initialize(self, port):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.5
        self.s.bytesize = 8
        self.stopbits = 1
        check = self.flush_buffer()
        check = self.set_protocol()
        self.initialize_aperture()
        self.apmin, self.apmax = (0, self.find_aperture_range())
        self.appos = int(self.apmax)
        # When we find the aprange we set the appos to max (fully closed)
        self.update_focus()

    def update_focus(self):
        self.fmin, self.fmax, self.fpos = self.find_focus_and_range() 

    @property
    def state_dict(self):
        return dict(apmin=self.apmin, apmax=self.apmax, appos=self.appos,
                    fmin=self.fmin, fmax=self.fmax, fpos=self.fpos)

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
        return int(self.sendget('pa').split(',')[0].strip('DONE'))

    def move_aperture(self, steps):
        # Moves aperture incremental steps.
        # Negative for open, positive for close.
        # This should return something for reaching limit.
        response = self.sendget('mn' + str(steps))
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.appos += steps_taken
        return

    def aperture_full_open(self):
        response = self.sendget("mo")
        self.appos = 0

    def aperture_full_close(self):
        response = self.sendget("mc")
        self.appos = self.apmax

    def focus_infinity(self):
        response = self.sendget("mi")
        self.update_focus()

    def focus_zero(self):
        response = self.sendget("mz")
        self.update_focus()


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
        self.fpos += steps_taken
        return

    def print_status(self):
        print 'Ap min: %d, Ap max: %d, Current ap: %d' % (self.apmin, self.apmax, self.appos)
        print 'f min: %d, f max: %d, Current f: %d' % (self.fmin, self.fmax, self.fpos)
    
