import os
from subprocess import check_output,CalledProcessError, STDOUT
import logging
import glob
import time
import tempfile


logging.basicConfig(format='%(levelname)-4.4s %(asctime)s - finalize:%(lineno)d  %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger()

def run_command(command):
    logger.info("\n-->  %s" % command)
    try:
        result = check_output(command,shell=True)#,stderr=STDOUT)
        if result.strip():
            logger.debug("result -->\n%s" % result)
        return result
    except CalledProcessError as e:
        logger.exception("Command '%s' failed with returncode %d and output\n%s" % (command, e.returncode,
                                                                                   e.output))
        return None

def read_mac_table(filename='./etc/pmc_camera_motherboard_mac_addresses.txt'):
    filename = os.path.abspath(filename)
    mb_mac_table = {}
    ipmi_mac_table = {}
    with open(filename) as fh:
        for line in fh.readlines():
            if line.startswith('#'):
                continue
            try:
                number,mb_mac,ipmi_mac = line.split()
                number = int(number)
            except (TypeError, ValueError):
                raise ValueError("Failed to parse line in %s:\n%r" % (filename,line))
            mb_mac_table[number] = mb_mac
            mb_mac_table[mb_mac] = number
            ipmi_mac_table[number] = ipmi_mac
            ipmi_mac_table[ipmi_mac] = number
    return mb_mac_table,ipmi_mac_table

mb_mac_table,ipmi_mac_table = read_mac_table()

def read_hosts(filename = './etc/pmc-turbo-hosts'):
    filename = os.path.abspath(filename)
    hosts ={}
    with open(filename) as fh:
        for line in fh.readlines():
            if line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) == 2:
                ip, host = parts
                hosts[host] = ip
    return hosts

hosts = read_hosts()

def get_mac(interface='eth0'):
    try:
        mac = open('/sys/class/net/'+interface+'/address').readline()
    except:
        mac = "00:00:00:00:00:00"

    return mac[0:17]

mac = get_mac()

number = mb_mac_table[mac]

hostname = 'pmc-camera-%d' % number
ipmi_hostname = 'pmc-camera-ipmi-%d' % number

motherboard_ip = hosts[hostname]
ipmi_ip = hosts[ipmi_hostname]

try:
    gateway = hosts['pmc-ops']
except KeyError:
    logger.warning("Couldn't find pmc-ops in host table, defaulting to 192.168.1.1 for gateway")
    gateway = "192.168.1.1"

### FIXME: For now use 192.168.1.1 as gateway always
gateway = "192.168.1.1"

eth0_interface = r"""
auto eth0
allow-hotplug eth0
iface eth0 inet static
   address %s
   netmask 255.255.255.0
   gateway 192.168.1.1
""" % (motherboard_ip)

logger.info("Copying hosts file")
run_command("sudo cp etc/pmc-turbo-hosts /etc/hosts")
run_command("sudo chmod a+r /etc/hosts")
logger.info("Setting hostname %s" % hostname)
run_command('echo "%s" | sudo tee /etc/hostname' % hostname)
run_command("sudo chmod a+r /etc/hostname")

run_command('echo 8.8.8.8 | sudo tee /etc/resolv.conf')

interface_file = tempfile.NamedTemporaryFile(delete=False)
interface_file.write(eth0_interface)
interface_file.close()
run_command("sudo cp %s /etc/network/interfaces.d/eth0" % interface_file.name)
run_command("sudo chmod a+r /etc/network/interfaces.d/eth0")

logger.info("/etc/network/interfaces.d/eth0 is now:")
run_command("cat /etc/network/interfaces.d/eth0")

run_command("sudo ipmitool lan set 1 ipsrc static")
run_command("sudo ipmitool lan set 1 ipaddr %s" % ipmi_ip)
run_command("sudo ipmitool lan set 1 netmask 255.255.255.0")
run_command("sudo ipmitool lan set 1 defgw ipaddr %s" % gateway)
#run_command("sudo ipmitool lan set 1 arp respond on")
run_command("sudo ipmitool lan set 1 access on")

time.sleep(1)
logger.info("IPMI Lan settigns:")
run_command("sudo ipmitool lan print 1")








