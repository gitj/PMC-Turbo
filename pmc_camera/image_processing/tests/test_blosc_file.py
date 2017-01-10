import numpy as np
import tempfile
import shutil
import multiprocessing as mp
import os
import blosc
print blosc.set_nthreads(1)
from pmc_camera.image_processing import blosc_file
from pmc_camera.pycamera import dtypes
print blosc.set_nthreads(1)


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


    def test_blosc_multiprocessing(self):
        filename = os.path.join(self.temp_dir,'blah3.blosc')
        data = np.random.random_integers(0,2**14-1,size=(31440952//2,)).astype('uint16')
        p = mp.Process(target=blosc_file.write_image_blosc,args=(filename,data))
        p.start()
        p.join(10)
        print "one process, ok"

        filename = os.path.join(self.temp_dir,'blah4.blosc')
        p = mp.Process(target=write_random_blosc_file, args=(filename,))
        p.start()
        p.join(10)
        print "one process, type 2 ok"

        filename = os.path.join(self.temp_dir,'blah5.blosc')
        p = mp.Process(target=write_random_blosc_file, args=(filename,))
        filename2 = os.path.join(self.temp_dir,'blah6.blosc')
        p2 = mp.Process(target=write_random_blosc_file, args=(filename2,))
        p.start()
        p2.start()
        p.join(10)
        p2.join(10)
        print "two process, type 2 ok"

def write_random_blosc_file(filename):
    data = np.random.random_integers(0,2**14-1,size=(31440952//2,)).astype('uint16')
    blosc_file.write_image_blosc(filename,data)