import glob
import os
import sys
import time

import cv2
import matplotlib.animation as animation
import scipy.ndimage
from pylab import *
from pmc_turbo.camera.image_processing import blosc_file

imd = np.zeros((3232, 4864))
dpi = 100


def ani_frame(files, output_name):
    frames = len(files)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    # ax.set_aspect('equal')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    im = ax.imshow(scipy.ndimage.gaussian_filter(imd, 2)[::4, ::4], cmap=cm.gray, interpolation='nearest')
    fig.set_size_inches([12, 8])
    txt = ax.text(0.1, 0.9, 'time:', ha='left', va='top', color='yellow')

    tight_layout()
    start_at = time.time()
    ax = gca()

    def update_img(n):
        elapsed = time.time() - start_at
        if n:
            time_per_frame = elapsed / (n)
        else:
            time_per_frame = 1
        sys.stdout.flush()
        try:
            # npz = np.load(files[n])
            # imall = npz['image']


            imall, chunk = blosc_file.load_blosc_image(files[n])

        except Exception:
            return
        nblobs = 0
        # data = scipy.ndimage.gaussian_filter(imd,2)[::4,::4]
        data = cv2.GaussianBlur(imall, (3, 3), 0)[::4, ::4]
        im.set_data(data)
        mn = data.mean(dtype='float64')
        if mn < 1000:
            mx = 1000
        else:
            mx = data.max() + 1000
            # mx = 14000
        #        im.set_clim(mn-200,mn+200)
        im.set_clim(0, mx)
        try:
             txt.set_text(files[n].split('/')[-1].split('_')[1])
        except Exception:
             pass
        print ("\r%d of %d %.1f minutes elapsed, %.1f minutes remaining, %d blobs" % (n, len(files), elapsed / 60,
                                                                                      (len(
                                                                                          files) - n) * time_per_frame / 60.,
                                                                                      nblobs)),

        return im, txt

    # legend(loc=0)
    ani = animation.FuncAnimation(fig, update_img, frames, interval=50)
    #writer = animation.writers['ffmpeg'](fps=20, codec='h264')  # , bitrate=2**20)
    # ffmpeg not installed on clouds

    writer = animation.writers['avconv'](fps=20, codec='h264')  # , bitrate=2**20)

    ani.save(output_name, writer=writer, dpi=dpi)
    return ani


# listing = """
# 2016-10-26_135mm_trying_to_capture_PMClike_clouds_for_dave
# 2016-10-26_135mm_trying_to_capture_PMClike_clouds_for_dave_.8ms
# 2016-10-26_50mm_trying_to_capture_PMClike_clouds_for_dave_1ms_NDF
# """
# dirs = listing.splitlines()
# import joblib
# p = joblib.Parallel(n_jobs=3)
def process_dir():
    # files = glob.glob(os.path.join('/data3',dirname,'*step*.npz'))
    files = glob.glob(os.path.join('/data/home/bjorn/alberta_data/raw_2017-07-01-camera-2/2017*'))
    files.sort()
    if len(files):
        print len(files[1::1]), files[14]
        output_name = '/data/home/bjorn/movie_2017-07-01.mp4'
        ani_frame(files[1::1], output_name)


process_dir()
# p([joblib.delayed(process_dir)(x) for x in dirs])
