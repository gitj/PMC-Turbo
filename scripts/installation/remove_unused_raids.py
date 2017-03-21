import os

from subprocess import check_output,CalledProcessError, STDOUT
import logging
import glob
import time
import tempfile

logging.basicConfig(format='%(levelname)-4.4s %(asctime)s - remove_unused_raids:%(lineno)d  %(message)s',
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

root_device = None
var_device =None
lines = run_command('df -h')
for line in lines.splitlines():
    parts = line.split()
    last_column = parts[-1].strip()
    if last_column == '/':
        root_device = parts[0].strip()
    if last_column == '/var':
        var_device = parts[0].strip()

if root_device is None:
    raise RuntimeError("could not find root device")
if var_device is None:
    raise RuntimeError("could not find var device")

result = run_command('cat /proc/mdstat | grep %s' % os.path.split(root_device)[1])
root_partitions = [part[:4] for part in result.split() if part.startswith('sd')]

result = run_command('cat /proc/mdstat | grep md')
logger.info('root device is %s, var device is %s' % (root_device,var_device))
logger.info('root partitions are %r' % root_partitions)
for line in result.splitlines():
    parts = line.split()
    md_device = parts[0]
    if md_device in [os.path.split(root_device)[1], os.path.split(var_device)[1]]:
        logger.info('Skipping %s' % md_device)
        continue
    partitions = [part[:4] for part in parts if part.startswith('sd')]
    logger.info("found device %s, with partitions %r" %(md_device,partitions))
    if raw_input("Stop and delete this device? (y/n)") == 'y':
        run_command('sudo mdadm --stop /dev/%s' % md_device)
        for part in partitions:
            run_command("sudo mdadm --zero-superblock /dev/%s" % part)
        run_command('sudo mdadm --remove /dev/%s' % md_device)
    else:
        logger.info('Skipping %s' % md_device)

run_command("cat /proc/mdstat")
    #run_command("")
