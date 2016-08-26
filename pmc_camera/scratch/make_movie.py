import matplotlib.animation as animation
import numpy as np
from pylab import *
import scipy.ndimage
import cv2
import time
import sys

import glob

from pmc_camera.star_finding.blobs import BlobFinder
#files = glob.glob('/data1/2016-08-24_50mm_star_focus_test_100ms/*step_0005.npz')
files = glob.glob('/data1/2016-08-07_sunrise/*step_0010.npz')
files.sort()
#files = files[::10]

imd = np.load(files[0])['image']
dpi = 100

def ani_frame(frames=10):

    fig = plt.figure()
    ax = fig.add_subplot(111)
    #ax.set_aspect('equal')
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)

    im = ax.imshow(scipy.ndimage.gaussian_filter(imd,2)[::4,::4],cmap='gray',interpolation='nearest')
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
        npz = np.load(files[n])
        imd = npz['image']
        bf = BlobFinder(imd,cell_size=64,kernel_sigma=1,kernel_size=8,fit_blobs=False)
        #data = scipy.ndimage.gaussian_filter(imd,2)[::4,::4]
        data = cv2.GaussianBlur(imd,(3,3),0)[::4,::4]
        im.set_data(data)
        mn = data.mean(dtype='float64')
        if mn < 1000:
            mx = 1000
        else:
            mx = data.max()
        im.set_clim(0,mx)
        txt.set_text(time.ctime(npz['state'][()]['time']))
        for blob in bf.blobs[:20]:
            ax.add_artist(Circle((blob.y/4.,blob.x/4.),linewidth=1,facecolor='none',edgecolor='y',radius=2))
        print ("\r%d of %d %.1f minutes elapsed, %.1f minutes remaining, %d blobs" % (n,len(files), elapsed/60,
                                                                            (len(files)-n)*time_per_frame/60.,
                                                                            len(bf.blobs))),

        return im,txt

    #legend(loc=0)
    ani = animation.FuncAnimation(fig,update_img,frames,interval=50)
    writer = animation.writers['ffmpeg'](fps=20, codec='h264')#, bitrate=2**20)

    ani.save('/home/pmc/pmchome/2016-08-07_sunrise_blobs.mp4',writer=writer,dpi=dpi)
    return ani

ani_frame(frames=len(files))