from pmc_turbo.communication import downlink_classes
import time

class TestHighrateDownlinks():
    def setup(self):
        self.downlink = downlink_classes.HirateDownlink('localhost',9999,speed_bytes_per_sec=0,name="test")

    def test_set_bandwidth(self):
        self.downlink.set_bandwidth(1000)
        assert self.downlink.downlink_speed_bytes_per_sec == 1000

    def test_send(self):
        assert not self.downlink.enabled
        assert not self.downlink.packets_to_send # should be empty to start
        self.downlink.send_data() # should do nothing
        self.downlink.put_data_into_queue('a'*1000*10,file_id=1,packet_size=1000)
        assert len(self.downlink.packets_to_send) == 10
        self.downlink.send_data() # should do nothing because speed is still set to 0
        assert len(self.downlink.packets_to_send) == 10 # nothing should have been sent yet
        self.downlink.set_bandwidth(10000)
        assert not self.downlink.has_bandwidth()
        tic = time.time()
        while self.downlink.packets_to_send and (time.time()-tic < 10):  # timeout after 10 seconds
            self.downlink.send_data()
            time.sleep(0.1)
        print time.time()-tic
        assert time.time()-tic < 3
        assert self.downlink.has_bandwidth()

    def test_flush(self):
        self.downlink.put_data_into_queue('a'*1000*10,file_id=1,packet_size=1000)
        assert len(self.downlink.packets_to_send) == 10
        self.downlink.flush_packet_queue()
        assert len(self.downlink.packets_to_send) == 0
