import Pyro4, Pyro4.socketutil
import time
import os
try:
    import u3
except ImportError:
    pass
import select

Pyro4.config.SERVERTYPE = 'multiplex'
Pyro4.config.SERIALIZERS_ACCEPTED = {'pickle','json'}
Pyro4.config.SERIALIZER = 'pickle'

LOG_DIR = '/home/pmc/logs/labjack'

@Pyro4.expose
class LabJackLogger():
    def __init__(self,measurement_interval = 10,debug = False, autoOpen = True, **openArgs):
        self.u3 = u3.U3(debug=debug, autoOpen=autoOpen, **openArgs)
        self.u3.configIO(FIOAnalog=0xFF)
        try:
            os.mkdir(LOG_DIR)
        except OSError:
            pass
        self.filename = None
        self.file = None
        self.last_measurement = {}
        self.measurement_interval = measurement_interval
        ip = Pyro4.socketutil.getInterfaceAddress('192.168.1.1')
        self.daemon = Pyro4.Daemon(host=ip,port=51000)
        print self.daemon.register(self,objectId='labjack')

    def create_file(self,log_dir=LOG_DIR):
        self.filename = os.path.join(log_dir,(time.strftime('%Y-%m-%d_%H%M%S.csv')))
        self.file = open(self.filename,'a')
        header = ('# %s Serial No %d Bootloader %s Firmware %s Hardware %s\n'% (self.u3.deviceName,self.u3.serialNumber,
                                                                  self.u3.bootloaderVersion,self.u3.firmwareVersion,
                                                                              self.u3.hardwareVersion))
        self.file.write(header)
        columns = ['epoch','temperature',] + [('ain%d' %x) for x in range(8)]
        self.file.write(','.join(columns) + '\n')
        self.file.flush()

    def measure(self):
        self.u3.toggleLED()
        epoch = time.time()
        temperature = self.u3.getTemperature()
        voltages = [self.u3.getAIN(x) for x in range(8)]
        result = dict(epoch=epoch,temperature=temperature)
        for x in range(8):
            result['ain%d'%x] = voltages[x]
        return result

    def run(self):
        while True:
            self.last_measurement = self.measure()
            if self.file is None:
                self.create_file()
            values = ([self.last_measurement['epoch'],self.last_measurement['temperature']]
            + [self.last_measurement['ain%d' %x] for x in range(8)])
            self.file.write((','.join([('%f' %x) for x in values])) + '\n')
            self.file.flush()
            while time.time() - self.last_measurement['epoch'] < self.measurement_interval:
                events,_,_ = select.select(self.daemon.sockets,[],[],0.1)
                if events:
                    self.daemon.events(events)

if __name__ == "__main__":
    lj = LabJackLogger()
    lj.run()