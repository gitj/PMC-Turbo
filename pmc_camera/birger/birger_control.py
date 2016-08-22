import serial
import time
import re

class Birger(object):

    def __init__(self, port='/dev/ttyUSB0', debug=False):
        self.debug = debug
        self.initialize(port)
        return

    def initialize(self, port):
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.5
        self.s.bytesize = 8
        self.stopbits = 1
        self.setup_regex()
        check = self.flush_buffer()
        protocol_check = self.set_protocol()
        if not protocol_check:
            print "Protocol set error. Cannot procede."
            return
        initialize_check = self.initialize_aperture()
        if not initialize_check:
            print "Initialization error."
            return
        self.apmin, self.apmax = (0, self.find_aperture_range())
        self.appos = int(self.apmax)
        # When we find the aprange we set the appos to max (fully closed)
        self.update_focus()


    def setup_regex(self):
        self.aperture_response = re.compile('DONE-*[0-9]*,f[0-9]*')
        self.focus_response = re.compile('DONE-*[0-9]*,[0-9]*')
        self.pa_response = re.compile('-*[0-9]*,f[0-9]*')
        self.focus_range_response = re.compile('fmin:-*[0-9]*  fmax:-*[0-9]*  current:-*[0-9]*')
        self.in_response = re.compile('DONE')
        self.protocol_response = re.compile('OK')

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
                if not self.debug:
                    if resp[-1] == terminator:
                        break
        self.s.close()
        if self.debug:
            print 'Message: %s' % (msg)
            print 'Response: %s' % (resp)
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

    def set_protocol(self, tries=0):
        # This should raise an error after n tries.
        tries += 1
        response = self.sendget('rm0,1')
        if not self.protocol_response.match(response):
            if tries > 3:
            # Try 3 times before it gives up.
                return False
            self.flush_buffer()
            self.set_protocol(tries)
        return True

    def initialize_aperture(self):
        # Required when the aperature hasn't been initialized.
        response = self.sendget('in')
        if not self.in_response.match(response):
            return False
        return True

    def find_aperture_range(self):
        # Closes aperture fully, gets info to find what absolute step it is at.
        # Slices string and returns max.
        response = self.sendget('mc')
        if not self.aperture_response.match(response):
            return False
        response = self.sendget('pa')
        if not self.pa_response.match(response):
            return False
        return int(response.split(',')[0].strip('DONE'))
        # Should clean this up

    def move_aperture(self, steps):
        # Moves aperture incremental steps.
        # Negative for open, positive for close.
        # This should return something for reaching limit.
        response = self.sendget('mn' + str(steps))
        if not self.aperture_response.match(response):
            return False
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.appos += steps_taken
        return True

    def aperture_full_open(self):
        response = self.sendget("mo")
        if not self.aperture_response.match(response):
            return False
        self.appos = 0
        return True

    def aperture_full_close(self):
        response = self.sendget("mc")
        if not self.aperture_response.match(response):
            return False
        self.appos = self.apmax
        return True

    def focus_infinity(self):
        # Problem: the sendget command returns an empty string when moving from infinity to zero.
        # This even happens with a really large timeout - something is up in sendget or birger.
        # After sending this command once, a second call will properly operate.
        response = self.sendget("mi")
        if not self.focus_response.match(response):
            return False
        self.update_focus()
        return True

    def focus_zero(self):
        response = self.sendget("mz")
        if not self.focus_response.match(response):
            return False
        self.update_focus()
        return True


    def find_focus_and_range(self):
        #self.s.timeout = 3
        # la takes some time
        #response = self.sendget('la0')
        #self.s.timeout = 0.5
        focus_range_string = self.sendget('fp')
        if not self.focus_range_response.match(focus_range_string):
            return False
        raw = focus_range_string.split(':')
        return (int(raw[1].strip('fmax')), int(raw[2].strip('current')), int(raw[3].strip('\r')))
        # min, max, current
        # We should discuss how often to redo the la command.
        # Seems like we shouldn't do it every time, however.

    def move_focus(self, steps):
        response = self.sendget('mf'+str(steps))
        if not self.focus_response.match(response):
            return False
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.fpos += steps_taken
        return True

    def print_status(self):
        print 'Ap min: %d, Ap max: %d, Current ap: %d' % (self.apmin, self.apmax, self.appos)
        print 'f min: %d, f max: %d, Current f: %d' % (self.fmin, self.fmax, self.fpos)
