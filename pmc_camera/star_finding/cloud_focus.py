import numpy as np
from numpy.fft import fft2, ifft2, fftshift
import cv2
from matplotlib import pyplot as plt
import glob

def fft_translation(im0, im1):
    """Return translation vector to register images."""
    shape = im0.shape
    im0 = im0-im0.mean()
    im1 = im1-im1.mean()
    f0 = fft2(im0)
    f1 = fft2(im1)
    ir = abs(ifft2((f0 * f1.conjugate()) / (abs(f0) * abs(f1))))
    ir[0,0] = 0
    t0, t1 = np.unravel_index(np.argmax(ir), shape)

    if t0 > shape[0] // 2:
        t0 -= shape[0]
    if t1 > shape[1] // 2:
        t1 -= shape[1]
    return [t0, t1]

def cv2_translation(im0,im1):
    if np.prod(im0.shape) > np.prod(im1.shape):
        templ = im1
        im = im0
    else:
        templ = im0
        im = im1

    cc = cv2.matchTemplate(im,templ,cv2.TM_CCOEFF_NORMED)
    r,c = np.unravel_index(np.argmax(cc),cc.shape)
    return r,c

def get_stamp_bounds(center,size,shape):
    height,width = shape
    row,col = center
    b = row-size//2
    t = row+size//2
    l = col-size//2
    r = col+size//2
    if b < 0:
        b = 0
        t = size
    if l < 0:
        l = 0
        r = size
    if t >= height:
        t = height-1
        b = t-size
    if r >= width:
        r = width-1
        l = r-size
    return b,t,l,r

def get_image_from_npz(filename):
    return np.load(filename)['image']

def get_aligned_stamps_from_files(files,center=None,size=256, track=True):
    images = [np.load(fn)['image'].astype('float32') for fn in files]
    return get_aligned_stamps(images,center=center,size=size,track=track)

def get_aligned_stamps(images, center=None,size=256,track=True):
    if type(images[0]) is str:
        get_image = get_image_from_npz
    else:
        get_image = lambda x: x
    im0 = get_image(images[0])
    if center is None:
        im = im0
        center = np.unravel_index(np.argmax(im),im.shape)
    row,col = center
    b,t,l,r = get_stamp_bounds(center,size,im0.shape)
    stamps = [im0[b:t,l:r]]
    for k,im in enumerate(images[1:]):
        im = get_image(im)
        if track:
            r,c = cv2_translation(stamps[k],im)
            if np.sqrt((r-row)**2 + (c-col)**2) > np.sqrt(2)*size:
                print "Warning: offset larger than stamp size", r,c,row,col
            b,t,l,r = get_stamp_bounds((r+size//2,c+size//2),size,im.shape)
        stamps.append(im[b:t,l:r])
    return stamps

def plot_stamps(stamps,figsize=(18,18)):
    maxs = []
    mins = []
    for stamp in stamps:
        maxs.append(stamp.max())
        mins.append(stamp.min())
    max_ = np.max(maxs)
    min_ = np.min(mins)
    nc = np.floor(np.sqrt(len(stamps)))
    nr = len(stamps)/float(nc)
    nr = np.ceil(nr)
    fig,axs = plt.subplots(int(nr),int(nc),figsize=figsize)
    for k,ax in enumerate(axs.flatten()):
        if k >= len(stamps):
            break
        im = ax.imshow(stamps[k],aspect='auto',interpolation='nearest',cmap=plt.cm.coolwarm)
        im.set_clim(min_,max_)