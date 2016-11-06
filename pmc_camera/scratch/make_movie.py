import matplotlib.animation as animation
import numpy as np
from pylab import *
import scipy.ndimage
import cv2
import time
import sys
import os
import glob

from pmc_camera.star_finding.blobs import BlobFinder
#files = glob.glob('/data1/2016-08-24_50mm_star_focus_test_100ms/*step_0005.npz')
#files = glob.glob('/data1/2016-08-24_50mm_star_focus_test_100ms/*step_0005.npz')
#files.sort()
#files = files[::10]

#imd = np.load(files[0])['image']
imd = np.zeros((3232,4864))
dpi = 100

def ani_frame(files,output_name):
    frames = len(files)
    fig = plt.figure()
    ax = fig.add_subplot(111)
    #ax.set_aspect('equal')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    im = ax.imshow(scipy.ndimage.gaussian_filter(imd,2)[::4,::4],cmap=cm.gray,interpolation='nearest')
    fig.set_size_inches([12,8])
    txt = ax.text(0.1,0.9,'time:',ha='left',va='top',color='yellow')


    tight_layout()
    start_at = time.time()
    ax = gca()

    def update_img(n):
        elapsed = time.time()-start_at
        if n:
            time_per_frame = elapsed/(n)
        else:
            time_per_frame = 1
        sys.stdout.flush()
        try:
            npz = np.load(files[n])

            imall = npz['image']
        except Exception:
            return
        nblobs=0
        if False:
            for imd in [imall[:1616,:2432],imall[-1616:,:2432],imall[:1616,-2432:],imall[-1616:,-2432:]]:
                bf = BlobFinder(imd,blob_threshold=8,cell_size=64,kernel_sigma=1,kernel_size=8,fit_blobs=False)
                for blob in bf.blobs[:20]:
                    ax.add_artist(Circle((blob.y/4.,blob.x/4.),linewidth=1,facecolor='none',edgecolor='y',radius=2))
                nblobs = len(bf.blobs)
        #data = scipy.ndimage.gaussian_filter(imd,2)[::4,::4]
        data = cv2.GaussianBlur(imall,(3,3),0)[::4,::4]
        im.set_data(data)
        mn = data.mean(dtype='float64')
        if mn < 1000:
            mx = 1000
        else:
            mx = data.max()+1000
        #mx = 14000
#        im.set_clim(mn-200,mn+200)
        im.set_clim(0,mx)
        try:
            txt.set_text(time.ctime(npz['state'][()]['time']))
        except Exception:
            pass
        print ("\r%d of %d %.1f minutes elapsed, %.1f minutes remaining, %d blobs" % (n,len(files), elapsed/60,
                                                                            (len(files)-n)*time_per_frame/60.,
                                                                            nblobs)),

        return im,txt

    #legend(loc=0)
    ani = animation.FuncAnimation(fig,update_img,frames,interval=50)
    writer = animation.writers['ffmpeg'](fps=20, codec='h264')#, bitrate=2**20)

    ani.save(output_name,writer=writer,dpi=dpi)
    return ani

listing = """
2016-10-26_135mm_trying_to_capture_PMClike_clouds_for_dave
2016-10-26_135mm_trying_to_capture_PMClike_clouds_for_dave_.8ms
2016-10-26_50mm_trying_to_capture_PMClike_clouds_for_dave_1ms_NDF
"""
dirs = listing.splitlines()
import joblib
p = joblib.Parallel(n_jobs=3)
def process_dir(dirname):
    files = glob.glob(os.path.join('/data3',dirname,'*step*.npz'))
    files.sort()
    if len(files):
        print len(files[1::1]),files[14]
        output_name = '/home/pmc/pmchome/%s_noblobs.mp4' % os.path.split(dirname)[1]
        ani_frame(files[1::1],output_name)

p([joblib.delayed(process_dir)(x) for x in dirs])