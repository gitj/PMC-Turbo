import os
import shutil
import tempfile
import threading
import time
import numpy as np

import pmc_camera.pipeline.indexer
from pmc_camera.pipeline import controller
from pmc_camera.pipeline import basic_pipeline
from pmc_camera.communication.file_format_classes import decode_file_from_buffer, GeneralFile

test_data_path = os.path.join(os.path.split(os.path.abspath(__file__))[0],'test_data')
test_pipeline_port = 47563

class TestMultiIndex(object):
    @classmethod
    def setup(cls):
        cls.top_dir = tempfile.mkdtemp('server_test')
        cls.data_dirs = [os.path.join(cls.top_dir,'data%d' %k) for k in range(1,5)]
        for data_dir in cls.data_dirs:
            os.mkdir(data_dir)
        cls.all_subdirs = ['lost+found','2016-10-25_195422',
                           '2016-11-29_112233',
                           '2016-12-08_231459','2016-12-20_100727']
        for data_dir in cls.data_dirs:
            for subdir in cls.all_subdirs:
                subdir_path = os.path.join(data_dir,subdir)
                os.mkdir(subdir_path)
                if subdir_path.startswith('20'):
                    open(os.path.join(subdir_path,'index.csv'),'w').close()

        cls.subdir = '2016-12-20_100727'
        cls.general_filename = os.path.join(cls.top_dir,'a_file.txt')
        cls.general_file_contents = np.random.random_sample((1024,)).tostring()
        with open(cls.general_filename,'w') as fh:
            fh.write(cls.general_file_contents)
            
        cls.controller_no_pipeline = controller.Controller(pipeline=None,data_dirs=cls.data_dirs)

        

    @classmethod
    def teardown(cls):
        shutil.rmtree(cls.top_dir,ignore_errors=True)

    def test_all_data(self):
        for k,data_dir in enumerate(self.data_dirs):
            shutil.copy(os.path.join(test_data_path,('index_%d.csv' % (k+1))),
                        os.path.join(data_dir,self.subdir,'index.csv'))
        mi = pmc_camera.pipeline.indexer.MergedIndex(subdirectory_name=self.subdir, data_dirs=self.data_dirs)
        result = mi.get_latest(update=True)
        assert result['frame_id'] == 422
        assert mi.get_index_of_timestamp(1482246746.160007500) == 416
        for k,data_dir in enumerate(self.data_dirs):
            open(os.path.join(data_dir,self.subdir,'index.csv'),'w').close()

    def test_image_server(self):
        bpl = basic_pipeline.BasicPipeline(disks_to_use=self.data_dirs,use_simulated_camera=True,
                                           default_write_enable=0,pipeline_port=test_pipeline_port)
        thread = threading.Thread(target=bpl.run_pyro_loop)
        thread.daemon=True
        thread.start()
        time.sleep(1)
        sis = controller.Controller(pipeline=bpl, data_dirs=self.data_dirs)
        sis.run_focus_sweep(request_params=dict())
        time.sleep(1)
        sis.check_for_completed_commands()
        bpl.close()

    def test_full_file_access(self):
        
        self.controller_no_pipeline.request_specific_file(self.general_filename,2**20,123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents
        assert fileobj.request_id == 123

    def test_partial_file_access(self):
        
        self.controller_no_pipeline.request_specific_file(self.general_filename,16,123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents[:16]
        assert fileobj.request_id == 123
        
    def test_partial_file_access_from_end(self):

        self.controller_no_pipeline.request_specific_file(self.general_filename,-16,123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents[-16:]
        assert fileobj.request_id == 123

    def test_access_non_existant_file(self):
        self.controller_no_pipeline.request_specific_file(filename="doesnt_exist",max_num_bytes=2**20,request_id=123)

