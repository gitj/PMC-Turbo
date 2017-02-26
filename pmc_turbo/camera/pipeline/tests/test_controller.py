import inspect
import os
import shutil
import tempfile
import threading
import time
import copy

import numpy as np

from traitlets.config.loader import load_pyconfig_files

import pmc_turbo.camera.pipeline.indexer
from pmc_turbo.camera.pipeline import basic_pipeline
from pmc_turbo.camera.pipeline import controller
from pmc_turbo.communication.file_format_classes import decode_file_from_buffer, GeneralFile, JPEGFile, ShellCommandFile

from pmc_turbo.utils.tests.test_config import BasicTestHarness

test_data_path = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'test_data')
test_pipeline_port = 47563


class TestMultiIndex(BasicTestHarness):
    def setup(self):
        super(TestMultiIndex, self).setup()
        self.top_dir = tempfile.mkdtemp('server_test')
        self.all_subdirs = ['lost+found', '2016-10-25_195422',
                            '2016-11-29_112233',
                            '2016-12-08_231459', '2016-12-20_100727']
        for data_dir in self.basic_config.GlobalConfiguration.data_directories:
            for subdir in self.all_subdirs:
                subdir_path = os.path.join(data_dir, subdir)
                os.mkdir(subdir_path)
                if subdir_path.startswith('20'):
                    open(os.path.join(subdir_path, 'index.csv'), 'w').close()

        self.subdir = '2016-12-20_100727'

        self.general_filename = os.path.join(self.top_dir, 'a_file.txt')
        self.general_file_contents = np.random.random_sample((1024,)).tostring()
        with open(self.general_filename, 'w') as fh:
            fh.write(self.general_file_contents)

        self.controller_no_pipeline = controller.Controller(pipeline=None, config=self.basic_config)

    def teardown(self):
        shutil.rmtree(self.top_dir, ignore_errors=True)

    def test_all_data(self):
        for k, data_dir in enumerate(self.basic_config.GlobalConfiguration.data_directories):
            shutil.copy(os.path.join(test_data_path, ('index_%d.csv' % (k + 1))),
                        os.path.join(data_dir, self.subdir, 'index.csv'))
        mi = pmc_turbo.camera.pipeline.indexer.MergedIndex(subdirectory_name=self.subdir,
                                                           data_dirs=self.basic_config.GlobalConfiguration.data_directories)
        result = mi.get_latest(update=True)
        assert result['frame_id'] == 422
        assert mi.get_index_of_timestamp(1482246746.160007500) == 416
        for k, data_dir in enumerate(self.basic_config.GlobalConfiguration.data_directories):
            open(os.path.join(data_dir, self.subdir, 'index.csv'), 'w').close()

    def test_controller_basic_function(self):
        config = copy.deepcopy(self.basic_config)
        config.BasicPipeline.default_write_enable = 1
        bpl = basic_pipeline.BasicPipeline(config=config)

        bpl.initialize()
        thread = threading.Thread(target=bpl.run_pyro_loop)
        thread.daemon = True
        thread.start()
        time.sleep(1)
        sis = controller.Controller(pipeline=bpl, config=config)
        sis.run_focus_sweep(request_params=dict())
        time.sleep(1)
        sis.check_for_completed_commands()
        bpl.close()

    def test_controller_get_image(self):
        config = copy.deepcopy(self.basic_config)
        config.BasicPipeline.default_write_enable = 1
        config.BasicPipeline.disks_to_use = self.basic_config.GlobalConfiguration.data_directories
        bpl = basic_pipeline.BasicPipeline(config=config)

        bpl.initialize()
        thread = threading.Thread(target=bpl.run_pyro_loop)
        thread.daemon = True
        thread.start()
        time.sleep(1)
        #        for dd in self.basic_config.GlobalConfiguration.data_directories:
        #            print subprocess.check_output(("ls -Rhl %s" % dd),shell=True)
        sis = controller.Controller(pipeline=bpl, config=config)
        if sis.merged_index.df is None:
            bpl.close()
            raise Exception("No index!!!")
        result = sis.get_next_data_for_downlink()
        result = decode_file_from_buffer(result)
        assert result.file_type == JPEGFile.file_type
        assert result.request_id == controller.DEFAULT_REQUEST_ID
        time.sleep(1)
        sis.request_image_by_index(2, request_id=128)
        result = sis.get_next_data_for_downlink()
        result = decode_file_from_buffer(result)
        assert result.request_id == 128

        sis.request_image_by_index(2, request_id=129)
        result2 = sis.get_next_data_for_downlink()
        result2 = decode_file_from_buffer(result2)
        for attr in dir(result):
            if attr[:2] == '__' or inspect.ismethod(getattr(result, attr)):
                continue
            if attr == 'request_id':
                assert result.request_id == 128
                assert result2.request_id == 129
            elif getattr(result, attr) != getattr(result2, attr):
                print attr, getattr(result, attr), getattr(result2, attr)
                assert False

        result = sis.get_latest_jpeg(request_id=999)

        bpl.close()
        time.sleep(1)

    def test_full_file_access(self):

        self.controller_no_pipeline.request_specific_file(self.general_filename, 2 ** 20, 123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents
        assert fileobj.request_id == 123

    def test_partial_file_access(self):

        self.controller_no_pipeline.request_specific_file(self.general_filename, 16, 123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents[:16]
        assert fileobj.request_id == 123

    def test_partial_file_access_from_end(self):

        self.controller_no_pipeline.request_specific_file(self.general_filename, -16, 123)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == GeneralFile.file_type
        assert fileobj.filename == self.general_filename
        assert fileobj.payload == self.general_file_contents[-16:]
        assert fileobj.request_id == 123

    def test_access_non_existant_file(self):
        self.controller_no_pipeline.request_specific_file(filename="doesnt_exist", max_num_bytes=2 ** 20,
                                                          request_id=123)

    def test_simple_shell_command(self):
        self.controller_no_pipeline.run_shell_command(command_line="ls -lhtr", max_num_bytes_returned=int(1e6),
                                                      request_id=124, timeout=10.0)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        assert fileobj.file_type == ShellCommandFile.file_type
        assert fileobj.returncode == 0
        assert fileobj.timed_out == 0
        assert fileobj.request_id == 124

    def test_shell_command_size_limit(self):
        self.controller_no_pipeline.run_shell_command(command_line="ls -lhtr", max_num_bytes_returned=2,
                                                      request_id=124, timeout=10.0)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        print fileobj.payload
        assert fileobj.file_type == ShellCommandFile.file_type
        assert fileobj.returncode == 0
        assert fileobj.timed_out == 0
        assert fileobj.request_id == 124
        assert len(fileobj.payload) < 50

    def test_shell_command_timeout(self):
        self.controller_no_pipeline.run_shell_command(command_line="sleep 10", max_num_bytes_returned=int(1e6),
                                                      request_id=124, timeout=1.0)
        buffer = self.controller_no_pipeline.get_next_data_for_downlink()
        fileobj = decode_file_from_buffer(buffer)
        print fileobj.payload
        assert fileobj.file_type == ShellCommandFile.file_type
        assert fileobj.returncode == -9
        assert fileobj.timed_out == 1
        assert fileobj.request_id == 124
