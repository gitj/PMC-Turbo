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
    def __init__(self, camera_id, infobar, *args, **kwargs):
        # GroundConfiguration.__init__(**kwargs)
        super(MyImageView, self).__init__(*args, **kwargs)
        self.root_data_path = '/data/gse_data'
        self.camera_id = camera_id
        data_dirs = glob.glob(os.path.join(self.root_data_path, '2*'))
        data_dirs.sort()
        print data_dirs[-1]
        self.mi = MergedIndex('*', data_dirs=[data_dirs[-1]], index_filename='file_index.csv', sort_on=None)
        self.last_index = 0

        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.addItem(self.vLine, ignoreBounds=True)
        self.addItem(self.hLine, ignoreBounds=True)

        self.infobar = infobar
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
        self.infobar.update(image_file, latest)
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

    def mouseMoved(self, evt):
        vb = self.getView()
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.imageItem.sceneBoundingRect().contains(pos):
            mousePoint = vb.mapSceneToView(pos)
            index = int(mousePoint.x())
            # label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>" % (mousePoint.x(), data1[index], data2[index]))
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            # print mousePoint.x(), mousePoint.y()
            self.infobar.x_value.setText('%.0f' % mousePoint.x())
            self.infobar.y_value.setText('%.0f' % mousePoint.y())


class InfoBar(QtGui.QDockWidget):
    def __init__(self, *args, **kwargs):
        super(InfoBar, self).__init__(*args, **kwargs)
        self.setWindowTitle("Info")
        self.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures | QtGui.QDockWidget.DockWidgetVerticalTitleBar)
        self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        mywidget = QtGui.QWidget()
        nested_widget = QtGui.QWidget()
        vlayout = QtGui.QVBoxLayout()
        grid_layout = QtGui.QGridLayout()

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

        grid_layout.addWidget(frame_status_label, 0, 0)
        grid_layout.addWidget(frame_id_label, 1, 0)
        grid_layout.addWidget(frame_timestamp_ns, 2, 0)
        grid_layout.addWidget(focus_step_label, 3, 0)

        grid_layout.addWidget(aperture_stop_label, 0, 2)
        grid_layout.addWidget(exposure_us_label, 1, 2)
        grid_layout.addWidget(file_index_label, 2, 2)
        grid_layout.addWidget(write_timestamp_label, 3, 2)

        grid_layout.addWidget(acquisition_count_label, 0, 4)
        grid_layout.addWidget(lens_status_label, 1, 4)
        grid_layout.addWidget(gain_db_label, 2, 4)
        grid_layout.addWidget(focal_length_mm_label, 3, 4)

        grid_layout.addWidget(row_offset_label, 0, 6)
        grid_layout.addWidget(column_offset_label, 1, 6)
        grid_layout.addWidget(num_rows_label, 2, 6)
        grid_layout.addWidget(num_columns_label, 3, 6)

        grid_layout.addWidget(scale_by_label, 0, 8)
        grid_layout.addWidget(pixel_offset_label, 1, 8)
        grid_layout.addWidget(pixel_scale_label, 2, 8)
        grid_layout.addWidget(quality_label, 3, 8)

        self.frame_status_value = QtGui.QLabel('---')
        self.frame_id_value = QtGui.QLabel('---')
        self.frame_timestamp_ns = QtGui.QLabel('---')
        self.focus_step_value = QtGui.QLabel('---')

        self.aperture_stop_value = QtGui.QLabel('---')
        self.exposure_us_value = QtGui.QLabel('---')
        self.file_index_value = QtGui.QLabel('---')
        self.write_timestamp_value = QtGui.QLabel('---')

        self.acquisition_count_value = QtGui.QLabel('---')
        self.lens_status_value = QtGui.QLabel('---')
        self.gain_db_value = QtGui.QLabel('---')
        self.focal_length_mm_value = QtGui.QLabel('---')

        self.row_offset_value = QtGui.QLabel('---')
        self.column_offset_value = QtGui.QLabel('---')
        self.num_rows_value = QtGui.QLabel('---')
        self.num_columns_value = QtGui.QLabel('---')

        self.scale_by_value = QtGui.QLabel('---')
        self.pixel_offset_value = QtGui.QLabel('---')
        self.pixel_scale_value = QtGui.QLabel('---')
        self.quality_value = QtGui.QLabel('---')

        self.frame_status_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.frame_id_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.frame_timestamp_ns.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.focus_step_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.aperture_stop_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.exposure_us_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.file_index_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.write_timestamp_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.acquisition_count_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lens_status_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.gain_db_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.focal_length_mm_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.row_offset_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.column_offset_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.num_rows_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.num_columns_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.scale_by_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.pixel_offset_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.pixel_scale_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.quality_value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        grid_layout.addWidget(self.frame_status_value, 0, 1)
        grid_layout.addWidget(self.frame_id_value, 1, 1)
        grid_layout.addWidget(self.frame_timestamp_ns, 2, 1)
        grid_layout.addWidget(self.focus_step_value, 3, 1)

        grid_layout.addWidget(self.aperture_stop_value, 0, 3)
        grid_layout.addWidget(self.exposure_us_value, 1, 3)
        grid_layout.addWidget(self.file_index_value, 2, 3)
        grid_layout.addWidget(self.write_timestamp_value, 3, 3)

        grid_layout.addWidget(self.acquisition_count_value, 0, 5)
        grid_layout.addWidget(self.lens_status_value, 1, 5)
        grid_layout.addWidget(self.gain_db_value, 2, 5)
        grid_layout.addWidget(self.focal_length_mm_value, 3, 5)

        grid_layout.addWidget(self.row_offset_value, 0, 7)
        grid_layout.addWidget(self.column_offset_value, 1, 7)
        grid_layout.addWidget(self.num_rows_value, 2, 7)
        grid_layout.addWidget(self.num_columns_value, 3, 7)

        grid_layout.addWidget(self.scale_by_value, 0, 9)
        grid_layout.addWidget(self.pixel_offset_value, 1, 9)
        grid_layout.addWidget(self.pixel_scale_value, 2, 9)
        grid_layout.addWidget(self.quality_value, 3, 9)

        self.filename_label = QtGui.QLabel('---')
        self.filename_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        x_label = QtGui.QLabel('X: ')
        y_label = QtGui.QLabel('Y: ')
        self.x_value = QtGui.QLabel('---')
        self.y_value = QtGui.QLabel('---')

        crosshair_widget = QtGui.QWidget()
        crosshair_layout = QtGui.QHBoxLayout()
        crosshair_layout.addWidget(x_label)
        crosshair_layout.addWidget(self.x_value)
        crosshair_layout.addWidget(y_label)
        crosshair_layout.addWidget(self.y_value)
        crosshair_widget.setLayout(crosshair_layout)

        nested_widget.setLayout(grid_layout)
        vlayout.addWidget(self.filename_label)
        vlayout.addWidget(crosshair_widget)
        vlayout.addWidget(nested_widget)

        mywidget.setLayout(vlayout)

        self.setWidget(mywidget)

    def update(self, jpeg_file, data_row):
        self.frame_status_value.setText(str(jpeg_file.frame_status))
        self.frame_id_value.setText(str(jpeg_file.frame_id))
        self.frame_timestamp_ns.setText(str(jpeg_file.frame_timestamp_ns)[:3] + '...')
        self.frame_timestamp_ns.setToolTip(
            'frame_timestamp_ns: ' + str(jpeg_file.frame_timestamp_ns) + '\n' + 'human readable: ')
        self.focus_step_value.setText(str(jpeg_file.focus_step))

        self.aperture_stop_value.setText(str(jpeg_file.aperture_stop))
        self.exposure_us_value.setText(str(jpeg_file.exposure_us))
        self.file_index_value.setText(str(jpeg_file.file_index))
        self.write_timestamp_value.setText(str(jpeg_file.write_timestamp))
        self.write_timestamp_value.setText(str(jpeg_file.write_timestamp)[:3] + '...')
        self.write_timestamp_value.setToolTip(
            'write_timestamp: ' + str(jpeg_file.write_timestamp) + '\n' + 'human readable: ')

        self.acquisition_count_value.setText(str(jpeg_file.acquisition_count))
        self.lens_status_value.setText(str(jpeg_file.lens_status))
        self.gain_db_value.setText(str(jpeg_file.gain_db))
        self.focal_length_mm_value.setText(str(jpeg_file.focal_length_mm))

        self.row_offset_value.setText(str(jpeg_file.row_offset))
        self.column_offset_value.setText(str(jpeg_file.column_offset))
        self.num_rows_value.setText(str(jpeg_file.num_rows))
        self.num_columns_value.setText(str(jpeg_file.num_columns))

        self.scale_by_value.setText(str(jpeg_file.scale_by))
        self.pixel_offset_value.setText(str(jpeg_file.pixel_offset))
        self.pixel_scale_value.setText('%.3f' % jpeg_file.pixel_scale)
        self.quality_value.setText(str(jpeg_file.quality))

        self.filename_label.setText(str(data_row['filename']))


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
    imv = MyImageView(camera_id, iw)
    proxy = pg.SignalProxy(imv.imageItem.scene().sigMouseMoved, rateLimit=60, slot=imv.mouseMoved)
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
