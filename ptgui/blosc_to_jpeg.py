import sys
from pmc_turbo.camera.image_processing import blosc_file
from pmc_turbo.camera.image_processing import jpeg

def make_jpeg_from_blosc(filename):
    img, chunk = blosc_file.load_blosc_image(filename)
    img_jpeg = jpeg.simple_jpeg(img, scale_by=1, quality=100)
    with open('/home/pmc/myimg.jpeg', 'wb') as f:
        f.write(img_jpeg)


if __name__ =="__main__":
    filename = sys.argv()
    make_jpeg_from_blosc(filename)
