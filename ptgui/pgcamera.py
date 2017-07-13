import glob
import os, sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

pg.setConfigOptions(imageAxisOrder='row-major')
from pmc_turbo.camera.image_processing import blosc_file
from pmc_turbo.camera.pipeline.indexer import MergedIndex
from pmc_turbo.ground.ground_configuration import GroundConfiguration
from pmc_turbo.communication.file_format_classes import load_and_decode_file, JPEGFile


class MyImageView(pg.ImageView):
    def __init__(self, camera_id, *args, **kwargs):
        # GroundConfiguration.__init__(**kwargs)
        super(MyImageView, self).__init__(*args, **kwargs)
        self.root_data_path = '/data/gse_data'
        self.camera_id = camera_id
        data_dirs = glob.glob(os.path.join(self.root_data_path, '2*'))
        data_dirs.sort()
        print data_dirs[-1]
        self.mi = MergedIndex('*', data_dirs=[data_dirs[-1]], index_filename='file_index.csv', sort_on=None)
        self.last_index = 0
        self.update(-1, autoLevels=True, autoRange=True)

    def update(self, index=-1, autoLevels=True, autoRange=True):
        self.mi.update()
        if self.camera_id is not None:
            df = self.mi.df[self.mi.df.camera_id == self.camera_id]
        else:
            df = self.mi.df
        df = df[df.file_type == JPEGFile.file_type]
        if index == -1:
            index = df.index.max()
        try:
            latest = df.iloc[df.index.get_loc(index, method='pad')]
        except (IndexError, KeyError) as e:
            print "invalid index", index, e
            return
        if index == self.last_index:
            return
        self.last_index = index
        filename = latest['filename']
        print filename
        image_file = load_and_decode_file(filename)
        image_data = image_file.image_array() / image_file.pixel_scale + image_file.pixel_offset
        self.setImage(image_data, autoLevels=autoLevels, autoRange=autoRange, transform=QtGui.QTransform().rotate(-90))

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_N:
            self.update(self.last_index + 1)
            ev.accept()
        elif ev.key() == QtCore.Qt.Key_P:
            self.update(self.last_index - 1)
            ev.accept()
        elif ev.key() == QtCore.Qt.Key_L:
            self.update(-1)
            ev.accept()

        super(MyImageView, self).keyPressEvent(ev)


class InfoBar(QtGui.QDockWidget):
    def __init__(self, *args, **kwargs):
        super(InfoBar, self).__init__(*args, **kwargs)
        self.setWindowTitle("Info")
        # self.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self.setFeatures(QtGui.QDockWidget.DockWidgetVerticalTitleBar)
        nested_widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()

        frame_status_label = QtGui.QLabel('frame_status')
        frame_id_label = QtGui.QLabel('frame_id')
        frame_timestamp_ns = QtGui.QLabel('frame_timestamp_ns')
        focus_step_label = QtGui.QLabel('focus_step')

        aperture_stop_label = QtGui.QLabel('aperture_stop')
        exposure_us_label = QtGui.QLabel('exposure_us')
        file_index_label = QtGui.QLabel('file_index')
        write_timestamp_label = QtGui.QLabel('write_timestamp')

        acquisition_count_label = QtGui.QLabel('acquisition_count')
        lens_status_label = QtGui.QLabel('lens_status')
        gain_db_label = QtGui.QLabel('gain_db')
        focal_length_mm_label = QtGui.QLabel('focal_length_mm')

        row_offset_label = QtGui.QLabel('row_offset')
        column_offset_label = QtGui.QLabel('column_offset')
        num_rows_label = QtGui.QLabel('num_rows')
        num_columns_label = QtGui.QLabel('num_columns')

        scale_by_label = QtGui.QLabel('scale_by')
        pixel_offset_label = QtGui.QLabel('pixel_offset')
        pixel_scale_label = QtGui.QLabel('pixel_scale')
        quality_label = QtGui.QLabel('quality')

        layout.addWidget(frame_status_label, 0, 0)
        layout.addWidget(frame_id_label, 1, 0)
        layout.addWidget(frame_timestamp_ns, 2, 0)
        layout.addWidget(focus_step_label, 3, 0)

        layout.addWidget(aperture_stop_label, 0, 3)
        layout.addWidget(exposure_us_label, 1, 3)
        layout.addWidget(file_index_label, 2, 3)
        layout.addWidget(write_timestamp_label, 3, 3)

        layout.addWidget(acquisition_count_label, 0, 5)
        layout.addWidget(lens_status_label, 1, 5)
        layout.addWidget(gain_db_label, 2, 5)
        layout.addWidget(focal_length_mm_label, 3, 5)

        layout.addWidget(row_offset_label, 0, 7)
        layout.addWidget(column_offset_label, 1, 7)
        layout.addWidget(num_rows_label, 2, 7)
        layout.addWidget(num_columns_label, 3, 7)

        layout.addWidget(scale_by_label, 0, 5)
        layout.addWidget(pixel_offset_label, 1, 5)
        layout.addWidget(pixel_scale_label, 2, 5)
        layout.addWidget(quality_label, 3, 5)

        nested_widget.setLayout(layout)
        self.setWidget(nested_widget)


if __name__ == "__main__":
    from pmc_turbo.utils import log
    import sys

    camera_id = None
    if len(sys.argv) > 1:
        camera_id = int(sys.argv[1])
    log.setup_stream_handler(log.logging.DEBUG)
    app = QtGui.QApplication([])
    dw = QtGui.QDesktopWidget()
    iw = InfoBar()
    win = QtGui.QMainWindow()
    win.resize(800, 800)
    imv = MyImageView(camera_id)
    win.setCentralWidget(imv)
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, iw)
    win.show()
    if camera_id is not None:
        if dw.screenCount() > 1:
            pass
        else:
            pass
        if True:
            geom = dw.availableGeometry()
            h = geom.height()
            w = geom.width()
            h0 = h / 2. * (camera_id % 2) + geom.top()
            w0 = w / 4.0 * (camera_id // 2) + geom.left()
            win.setMaximumHeight(h / 2.0)
            win.setMaximumWidth(w / 4.0)
            win.move(h0, w0)

    # timer = QtCore.QTimer()
    # timer.timeout.connect(imv.update)
    ##timer.start(1000)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
