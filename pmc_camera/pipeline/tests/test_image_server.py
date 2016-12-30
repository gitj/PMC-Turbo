import os
import shutil
import tempfile

from pmc_camera.pipeline import simple_image_server

test_data_path = os.path.join(os.path.split(os.path.abspath(__file__))[0],'test_data')

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
                    open(os.path.join(subdir_path,'index.csv'),'w')

        cls.subdir = '2016-12-20_100727'

        

    @classmethod
    def teardown(cls):
        shutil.rmtree(cls.top_dir,ignore_errors=True)

    def test_all_data(self):
        for k,data_dir in enumerate(self.data_dirs):
            shutil.copy(os.path.join(test_data_path,('index_%d.csv' % (k+1))),
                        os.path.join(data_dir,self.subdir,'index.csv'))
        mi = simple_image_server.MergedIndex(subdirectory_name=self.subdir,data_dirs=self.data_dirs)
        result = mi.get_latest(update=True)
        assert result['frame_id'] == 422
        assert mi.get_index_of_timestamp(1482246746.160007500) == 416