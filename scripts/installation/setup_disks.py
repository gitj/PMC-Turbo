import os
from subprocess import check_output,CalledProcessError, STDOUT
import logging
import glob
import time
import tempfile

BIG_DISK_PREFIX = '/dev/disk/by-id/ata-WDC_WD80EFZX'
SSD_PREFIX = '/dev/disk/by-id/ata-ADATA_ISMS312'
ROOT_PARTITION=1
VAR_PARTITION=2
DATA_PARTITION=3

BIG_DISKS_TO_RAID = ['sda','sdb']

SSD_DEVICES = ['sdc','sdd']

logging.basicConfig(format='%(levelname)-4.4s %(asctime)s - setup_all:%(lineno)d  %(message)s',
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

can_sudo = False
try:
    result = check_output('sudo -n -l | grep NOPASSWD',shell=True)
    if result.find('NOPASSWD') >=0:
        can_sudo=True
except Exception:
    pass
if not can_sudo:
    logger.error("Cannot sudo without password")

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
for partition in root_partitions:
    if partition[:3] in BIG_DISKS_TO_RAID:
        logger.warning("%s is part of the root raid %s, removing it in 5 seconds" % (partition, root_device ))
        time.sleep(5)
        run_command("sudo mdadm --fail %s /dev/%s" % (root_device,partition))
        run_command("sudo mdadm --remove %s /dev/%s" % (root_device,partition))

result = run_command('cat /proc/mdstat | grep %s' % os.path.split(var_device)[1])
var_partitions = [part[:4] for part in result.split() if part.startswith('sd')]
for partition in var_partitions:
    if partition[:3] in BIG_DISKS_TO_RAID:
        logger.warning("%s is part of the /var raid %s, removing it in 5 seconds" % (partition, var_device ))
        time.sleep(5)
        run_command("sudo mdadm --fail %s /dev/%s" % (var_device,partition))
        run_command("sudo mdadm --remove %s /dev/%s" % (var_device,partition))

logger.info("getting partition table information")
result = run_command('sudo parted -m /dev/%s unit s print' % root_partitions[0][:3])
root_partition_params = []
var_partition_params = []
for line in result.splitlines():
    parts = line.split(':')
    try:
        partition_num = int(parts[0])
    except ValueError:
        continue
    if partition_num == ROOT_PARTITION:
        root_partition_params = [parts[1][:-1], parts[2][:-1]] # start and end as strings, strip off trailing 's'
    if partition_num == VAR_PARTITION:
        var_partition_params = [parts[1][:-1], parts[2][:-1]] # start and end as strings, strip off trailing 's'

for dirname in ['/data1','/data2','/data3','/data4']:

    if os.path.exists(dirname):
        logger.warning("%s exists, trying to unmount it" % dirname)
        run_command("sudo umount %s" % dirname)
    else:
        run_command('sudo mkdir %s' % dirname)
    run_command('sudo chmod a+rwx %s' % dirname)
    run_command('sudo chattr +i %s' % dirname)

big_disks = glob.glob(BIG_DISK_PREFIX+'*')
big_disk_partitions = [disk for disk in big_disks if disk[:-1].endswith('part')]
big_disk_devices = [disk for disk in big_disks if not disk[:-1].endswith('part')]
real_device_to_by_id = {}
for big_disk_device in big_disk_devices:
    partitions = [partition for partition in big_disk_partitions if partition.startswith(big_disk_device)]
    partitions.sort()
    if partitions:
        result = run_command('sudo parted %s print' % big_disk_device)
        logger.warning("Found existing partitions on %s:\n%s" % (big_disk_device,result))
        logger.warning("**** These will be deleted unless the script is aborted in 5 seconds")
        time.sleep(5)
        logger.warning("proceeding...")

    real_device = os.path.split(os.path.realpath(big_disk_device))[1]
    real_device_to_by_id[real_device] = big_disk_device

    logger.info("creating new partition table")
    run_command("sudo parted -s /dev/%s mklabel gpt" %real_device)
    if real_device in BIG_DISKS_TO_RAID:
        logger.info("preparing partitions on %s to incorporate into raids" % (real_device))
        run_command("sudo parted -s /dev/%s unit s mkpart primary %s %s" % (real_device, root_partition_params[0], root_partition_params[1]))
        run_command("sudo parted /dev/%s set 1 raid on" % real_device)

#        run_command("sudo parted /dev/%s set 1 boot on" % real_device)  # sounds like this shouldn't be needed

        run_command("sudo parted -s /dev/%s unit s mkpart primary %s %s" % (real_device, var_partition_params[0], var_partition_params[1]))
        run_command("sudo parted /dev/%s set 2 raid on" % real_device)

        run_command("sudo parted /dev/%s unit s print" % real_device)

        logger.info("attempting to add partions to raids")
        run_command("sudo mdadm --add %s --write-mostly /dev/%s1" % (root_device, real_device))
        run_command("sudo mdadm --add %s --write-mostly /dev/%s2" % (var_device, real_device))


        start_data_partition = var_partition_params[1] + 's'
        data_partition = 3
    else:
        start_data_partition = '2048s'
        data_partition = 1
    logger.info("creating data partition")
    run_command("sudo parted /dev/%s mkpart primary ext4 %s 100%%" % (real_device,start_data_partition))
    logger.info("resulting partition table:")
    run_command("sudo parted /dev/%s unit s print" % real_device)

    logger.info("creating filesystem on data partition")
    run_command("sudo mkfs.ext4 -v /dev/%s%d" % (real_device, data_partition))



logger.info("Mirroring the raid onto all disks")
result = run_command('cat /proc/mdstat | grep %s' % os.path.split(root_device)[1])
root_partitions = [part[:4] for part in result.split() if part.startswith('sd')]
run_command("sudo mdadm --grow %s --raid-devices=%d" % (root_device, len(root_partitions)))

result = run_command('cat /proc/mdstat | grep %s' % os.path.split(var_device)[1])
var_partitions = [part[:4] for part in result.split() if part.startswith('sd')]
run_command("sudo mdadm --grow %s --raid-devices=%d" % (var_device, len(var_partitions)))

time.sleep(1)
run_command("cat /proc/mdstat")

logger.info("creating /etc/mdadm/mdadm.conf")
tempdir = tempfile.mkdtemp()
scan_file = os.path.join(tempdir,'scan.conf')
old_mdadm_conf_lines = open('/etc/mdadm/mdadm.conf').read().splitlines()
mdadm_conf_lines = [line for line in old_mdadm_conf_lines if not line.startswith('ARRAY')]
mdadm_conf_lines += ['\n# ARRAY information created at %s' % time.ctime()]
with open(scan_file,'w') as fh:
    fh.write('\n'.join(mdadm_conf_lines))

run_command("sudo mdadm --detail --scan >> %s" % scan_file)
run_command("cp %s /etc/mdadm/mdadm.conf" % scan_file)


new_fstab_lines = []
big_disk_real_devices = real_device_to_by_id.keys()
big_disk_real_devices.sort()
for device_number,real_device in enumerate(big_disk_real_devices):

    if real_device in BIG_DISKS_TO_RAID:
        data_partition = 3
    else:
        data_partition = 1
    fstab_line = "%s-part%d /data%d ext4 nofail 0 2" % (real_device_to_by_id[real_device],
                                                    data_partition,
                                                    device_number+1)
    new_fstab_lines.append(fstab_line)

original_fstab_lines = open('/etc/fstab','r').read().splitlines()
logger.info("original fstab:\n\n%s\n" % ('\n'.join(original_fstab_lines)))
fstab_lines = []
for line in original_fstab_lines:
    if line.startswith('/dev/disk/by-id'):
        logger.info("found old line to be replaced:\n%s" % line)
    else:
        fstab_lines.append(line)
new_fstab = '\n'.join(fstab_lines +['# The following were automatically generated by setup_disks.py'] + new_fstab_lines)
tmpfile = tempfile.NamedTemporaryFile(delete=False)
tmpfile.write(new_fstab)
tmpfile.close()
run_command('sudo cp %s /etc/fstab' % tmpfile.name)
logger.info("fstab is now:\n\n%s\n" % (open('/etc/fstab').read()))


logger.info("installing grub")
for partition in root_partitions:
    if partition[:3] in BIG_DISKS_TO_RAID:
        run_command("sudo grub-install /dev/%s" % partition[:3])



logger.info("Creating logging directory")
if not os.path.exists('/var/pmclogs'):
    run_command('sudo mkdir /var/pmclogs')
run_command('sudo chmod a+rwx /var/pmclogs')

