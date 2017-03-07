import shutil
import tempfile
import copy

import Pyro4
import time
from nose.tools import timed
from pmc_turbo.communication import command_table
from pmc_turbo.communication import packet_classes

from pmc_turbo.camera.pipeline import controller, basic_pipeline
from pmc_turbo.communication import camera_communicator
from pmc_turbo.utils.tests.test_config import BasicTestHarness
from copy import deepcopy

counter_dir = ''

FAKE_BASE_PORT = 56654


def setup():
    global counter_dir
    counter_dir = tempfile.mkdtemp()


def teardown():
    global counter_dir
    shutil.rmtree(counter_dir)


class TestCommunicator(BasicTestHarness):
    def test_valid_command_table(self):
        config = deepcopy(self.basic_config)
        config.Communicator.lowrate_link_parameters = [(('localhost', 6501), 6501)]
        cc = camera_communicator.Communicator(cam_id=0, peers=[], controller=None, leader=True, start_pyro=False,
                                              base_port=FAKE_BASE_PORT, config=config)
        cc.validate_command_table()
        cc.close()

    def test_basic_command_path(self):
        config = copy.deepcopy(self.basic_config)
        config.BasicPipeline.default_write_enable = 0
        bpl = basic_pipeline.BasicPipeline(config=config)

        bpl.initialize()
        cont = controller.Controller(pipeline=bpl, config=self.basic_config)
        config1 = deepcopy(self.basic_config)
        config1.Communicator.lowrate_link_parameters = [(('localhost', 6501), 6501)]
        cc1 = camera_communicator.Communicator(cam_id=0, peers=[], controller=None, leader=True, start_pyro=False,
                                               base_port=FAKE_BASE_PORT, config=config1)

        config2 = deepcopy(self.basic_config)
        config2.Communicator.lowrate_link_parameters = [(('localhost', 6601), 6601)]
        cc2 = camera_communicator.Communicator(cam_id=1, peers=[], controller=None, leader=True, start_pyro=False,
                                               base_port=FAKE_BASE_PORT, config=config2)
        cc1.controller = cont
        cc2.controller = cont
        cc1.peers = [cc1, cc2]
        cc1.destination_lists = {0: [cc1], 1: [cc2]}
        command = command_table.command_manager.set_focus(focus_step=1000)
        command_packet = packet_classes.CommandPacket(payload=command, sequence_number=1, destination=1)
        cc1.execute_packet(command_packet.to_buffer())

        bad_buffer = command_packet.to_buffer()[:-2] + 'AA'
        cc1.execute_packet(bad_buffer)

        bad_crc_buffer = command_packet.to_buffer()[:-2] + 'A\x03'
        cc1.execute_packet(bad_crc_buffer)

        cc1.execute_packet('bad packet')

        non_existant_command = '\xfe' + command
        cc1.execute_packet(packet_classes.CommandPacket(payload=non_existant_command, sequence_number=1,
                                                        destination=1).to_buffer())

        cm = command_table.command_manager
        commands = [cm.set_exposure(exposure_time_us=1000),
                    cm.run_focus_sweep(request_id=333,row_offset=1000, column_offset=1000, num_rows=256,num_columns=256,
                                       scale_by = 1.0, quality=90,start=4400,stop=4900,step=10),
                    cm.send_arbitrary_camera_command(command="TriggerSource:FixedRate"),
                    cm.send_arbitrary_camera_command(command="TriggerSource:None"),
                    cm.send_arbitrary_camera_command(command="TriggerSource:FixedRate:"),
                    cm.send_arbitrary_camera_command(command="TriggerSource"),
                    cm.set_standard_image_parameters(row_offset=1000, column_offset=1000, num_rows=256,num_columns=256,
                                       scale_by = 1.0, quality=90),
                    cm.request_specific_images(timestamp=123456789.123,request_id=1223,num_images=2,step=1,row_offset=1000,
                                               column_offset=1000, num_rows=256,num_columns=256,
                                       scale_by = 1.0, quality=90),
                    cm.set_peer_polling_order([0,1,2,3,4,5,6]),
                    cm.request_specific_file(max_num_bytes=2**20,request_id=123,filename='/data1/index.csv'),
                    cm.run_shell_command(max_num_bytes_returned=2**20,request_id=3488,timeout=30.0,command_line="ls -lhtr"),
                    cm.get_status_report(compress=1,request_id=344),
                    cm.flush_downlink_queues(),
                    cm.use_synchronized_images(synchronize=1),
                    cm.set_downlink_bandwidth(openport=10000,highrate=100,los=0),
                    ]
        for command in commands:
            print cm.decode_commands(command)
            cc1.execute_packet(packet_classes.CommandPacket(payload=command, sequence_number=1,
                                                        destination=1).to_buffer())
        cc1.close()
        cc2.close()
        bpl.close()
        time.sleep(1)

        # command = command_table.command_manager.


class FakeLowrateUplink():
    def __init__(self):
        self.bytes = ''

    def assign_bytes_to_get(self, bytes):
        self.bytes = bytes

    def get_sip_packets(self):
        return [self.bytes]


class FakeLowrateDownlink():
    def __init__(self):
        self.buffer = '\xff'*255

    def send(self, msg):
        self.buffer = msg

    def retrieve_msg(self):
        return self.buffer


class FakeHirateDownlink():
    def __init__(self):
        self.queue = None

    def has_bandwidth(self):
        return True

    def put_data_into_queue(self, data, file_id):
        self.queue = data


class FakeController():
    def get_latest_fileinfo(self):
        return [0] * 20

    def get_next_data_for_downlink(self):
        return '\x00' * 1024

    def get_status_summary(self):
        return (1, ['array_voltage', 'battery_voltage'])


class FakeStatusGroup():
    def update(self):
        return

    def get_status(self):
        return


class TestNoPeers(BasicTestHarness):
    def setup(self):
        super(TestNoPeers, self).setup()
        config = self.basic_config.copy()
        config.Communicator.lowrate_link_parameters = [(('pmc-serial-1', 6501), 6501)]
        self.base_port = FAKE_BASE_PORT
        self.c = camera_communicator.Communicator(cam_id=0, peers=[], controller=None, leader=True,
                                                  base_port=self.base_port, config=config)

    def teardown(self):
        super(TestNoPeers, self).teardown()
        self.c.close()

    def get_bytes_test(self):
        self.c.lowrate_uplink = FakeLowrateUplink()
        self.c.lowrate_uplink.assign_bytes_to_get('\x10\x13\x03')
        valid_packets = self.c.lowrate_uplink.get_sip_packets()
        assert (valid_packets == ['\x10\x13\x03'])

    def get_and_process_bytes_test(self):
        self.c.lowrate_uplink = FakeLowrateUplink()
        self.c.add_status_group(FakeStatusGroup())
        self.c.lowrate_uplink.assign_bytes_to_get('\x10\x13\x03')
        self.c.controller = FakeController()
        self.c.lowrate_downlink = FakeLowrateDownlink()

        self.c.get_and_process_sip_bytes()

        msg = self.c.lowrate_downlink.retrieve_msg()
        # this is temporary until the status message is defined
        assert (msg == ('\xff' * 255))


class TestPeers(BasicTestHarness):
    def setup(self):
        super(TestPeers, self).setup()
        # Set up port manually.
        config = self.basic_config.copy()
        config.Communicator.lowrate_link_parameters = [(("pmc-serial-1", 6501), 6501)]
        self.base_port = FAKE_BASE_PORT
        proxy = Pyro4.Proxy('PYRO:communicator@0.0.0.0:%d' % (self.base_port + 1))
        self.c = camera_communicator.Communicator(cam_id=0, peers=[proxy], controller=None, leader=True,
                                                  base_port=self.base_port, config=config)
        self.c.setup_pyro_daemon()

        self.c.file_id = 0
        config.Communicator.lowrate_link_parameters = [(("pmc-serial-1", 6601), 6601)]
        self.peer = camera_communicator.Communicator(cam_id=1, peers=[], controller=None, leader=True,
                                                     base_port=(self.base_port + 1), config=config)
        self.peer.setup_pyro_daemon()
        self.peer.start_pyro_thread()

    def teardown(self):
        super(TestPeers, self).teardown()
        self.c.close()
        self.peer.close()

    @timed(20)
    def ping_peer_test(self):
        result = self.c.peers[0].ping()
        assert (result == True)

    @timed(20)
    def send_data_on_downlinks_test(self):
        self.c.peer_polling_order = [0] # This is manually set
        self.peer.controller = FakeController()
        print 'Peers are:', self.c.peers
        print 'Peer polling order is:', self.c.peer_polling_order
        self.hirate_downlink = FakeHirateDownlink()
        self.c.downlinks = [self.hirate_downlink]
        self.c.send_data_on_downlinks()
        print '%r' % self.hirate_downlink.queue[0]
        assert (self.hirate_downlink.queue == ('\x00' * 1024))
