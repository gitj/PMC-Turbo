import serial
import time
import re

class Birger(object):

    def __init__(self, port='/dev/ttyUSB0', debug=False):
        self.debug = debug
        self.initialize(port)
        return

    def initialize(self, port):
        self.log = self.setup_log()
        self.s = serial.Serial()
        self.s.port = port
        self.s.baudrate = 115200
        self.s.timeout = 0.0
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
        apmax = self.find_aperture_range()
        if not apmax:
            print 'Error finding aperture'
            return
        self.apmin, self.apmax = (0, apmax)
        self.appos = apmax
        focus_check = self.update_focus()
        if not focus_check:
            print 'Error updating focus'
            return False
        return True

    def setup_regex(self):
        self.aperture_response = re.compile('DONE-*[0-9]*,f[0-9]*')
        self.focus_response = re.compile('DONE-*[0-9]*,[0-9]*')
        self.pa_response = re.compile('-*[0-9]*,f[0-9]*')
        self.focus_range_response = re.compile('fmin:-*[0-9]*  fmax:-*[0-9]*  current:-*[0-9]*')
        self.in_response = re.compile('DONE')
        self.protocol_response = re.compile('OK')

    def setup_log(self):
        # Creates dictionary of lists
        return dict(start=[], end=[], cmd=[], resp=[],
                    fmin=[], fmax=[], fnow=[],
                    apmin=[], apmax=[], apnow=[])

    def update_log(self, param_dict):
        # Updates all keys with new info, copies entries which have not changed.
        for key in self.log.keys():
            if key in param_dict.keys():
                a[key].append(b[key])
            else:
                a[key].append(a[key][-1])

    @property
    def state_dict(self):
        # Returns dictionary of last entries in log.
        state_dict = dict()
        for key in self.log.keys():
            state_dict[key]=log[key][-1]
        return state_dict

    def sendget(self, msg, wait=0.5, terminator='\r'):
        self.s.open()	
        start = time.time()
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
        end = time.time()
        self.s.close()
        if self.debug:
            print 'Message: %s' % (msg)
            print 'Response: %s' % (resp)
        return dict(start=start, end=end, cmd=msg, resp=resp)

    def general_command(self, command, expected_response):
        response = self.sendget(command)
        if not expected_response.match(response['resp']):
            raise RuntimeError("Response doesn't match expected response")
        return response

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
        response = self.general_command('rm0,1', self.protocol_response)
        if not response:
            if tries > 3:
            # Try 3 times before it gives up.
                return False
            self.flush_buffer()
            self.set_protocol(tries)
        self.update_log(response)
        return response

    def initialize_aperture(self):
        # Required when the aperature hasn't been initialized.
        response = self.general_command('in', self.in_response)
        self.update_log(response)
        return True

    def find_aperture_range(self):
        # There must be a better way to do this.
        response = self.general_command('mc', self.aperture_response)
        self.update_log(response)
        response = self.general_command('pa', self.pa_response)
        self.update_log(response)
        return int(response.split(',')[0].strip('DONE'))

    def move_aperture(self, steps):
        command = 'mn' + str(steps)
        response = self.general_command(command, self.aperture_response)
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.appos += steps_taken
        response['apnow'] = self.state_dict['apnow'] + steps_taken
        self.update_log(response)
        return True

    def aperture_full_open(self):
        response = self.general_command('mo', self.aperture_response)
        if not response:
            return False
        self.appos = 0
        return True


    def aperture_full_close(self):
        response = self.general_command('mc', self.aperture_response)
        if not response:
            return False
        self.appos = self.apmax
        return True

    def focus_infinity(self):
        # Problem: the sendget command returns an empty string when moving from infinity to zero.
        # This even happens with a really large timeout - something is up in sendget or birger.
        # After sending this command once, a second call will properly operate.
        response = self.general_command('mi', self.focus_response)
        if not response:
            return False
        response = self.update_focus()
        if not response:
            return False
        return True


    def focus_zero(self):
        response = self.general_command('mz', self.focus_response)
        if not response:
            return False
        response = self.update_focus()
        if not response:
            return False
        return True

    def find_focus_and_range(self):
        response = self.general_command('fp', self.focus_range_response)
        if not response:
            return False
        raw = response.split(':')
        return (int(raw[1].strip('fmax')), int(raw[2].strip('current')), int(raw[3].strip('\r')))


    def move_focus(self, steps):
        command = 'mf'+str(steps)
        response = self.general_command(command, self.focus_response)
        if not response:
            return False
        steps_taken = int(response.split(',')[0].strip('DONE'))
        self.fpos += steps_taken
        return True
        

    def print_status(self):
        print 'Ap min: %d, Ap max: %d, Current ap: %d' % (self.apmin, self.apmax, self.appos)
        print 'f min: %d, f max: %d, Current f: %d' % (self.fmin, self.fmax, self.fpos)
