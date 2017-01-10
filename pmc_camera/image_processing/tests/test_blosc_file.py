import numpy as np
import tempfile
import shutil
import os
from pmc_camera.image_processing import blosc_file
from pmc_camera.pycamera import dtypes


class TestBloscFiles(object):
    def setup(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.temp_dir)

    def test_blosc_file_round_trip(self):
        filename = os.path.join(self.temp_dir,'blah.blosc')
        data = np.random.random_integers(0,255,2**20).astype('uint8').tostring()
        blosc_file.write_image_blosc(filename=filename,data=data)
        data2 = blosc_file.load_blosc_file(filename)
        assert data == data2

    def test_blosc_image_round_trip(self):
        filename = os.path.join(self.temp_dir,'blah2.blosc')
        image = np.zeros(dtypes.image_dimensions,dtype='uint16')
        chunk = np.zeros((1,),dtype=dtypes.chunk_dtype)
        data = image.tostring() + chunk.tostring()
        blosc_file.write_image_blosc(filename,data)
        image2,chunk2 = blosc_file.load_blosc_image(filename)
        assert np.all(image == image2)
        assert np.all(chunk2 == chunk)
        assert image.dtype == image2.dtype

    def test_blosc_image_write(self):
        filename = os.path.join(self.temp_dir,'blah3.blosc')
        image = np.random.random_integers(0,2**14-1,size=(31440952//2,)).astype('uint16')
        blosc_file.write_image_blosc(filename,image)
        image2,chunk2 = blosc_file.load_blosc_image(filename)
