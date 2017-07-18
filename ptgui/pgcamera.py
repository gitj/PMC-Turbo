import glob
import os, sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import time

from pmc_turbo.camera.image_processing import blosc_file
from pmc_turbo.camera.pipeline.indexer import MergedIndex
from pmc_turbo.ground.ground_configuration import GroundConfiguration
from pmc_turbo.communication.file_format_classes import load_and_decode_file, JPEGFile


class MyImageView(pg.ImageView):
    def __init__(self, camera_id, infobar, window, portrait_mode, *args, **kwargs):
        # GroundConfiguration.__init__(**kwargs)
        super(MyImageView, self).__init__(*args, **kwargs)
        self.window = window
        self.portrait_mode = portrait_mode
        self.root_data_path = '/data/gse_data'
        self.camera_id = camera_id
        data_dirs = glob.glob(os.path.join(self.root_data_path, '2*'))
        data_dirs.sort()
        print data_dirs[-1]
        self.mi = MergedIndex('*', data_dirs=[data_dirs[-1]], index_filename='file_index.csv', sort_on=None)
        self.last_index = 0
        self.scale_by = 1
        #
        # self.vLine = pg.InfiniteLine(angle=90, movable=False)
        # self.hLine = pg.InfiniteLine(angle=0, movable=False)
        # self.addItem(self.vLine, ignoreBounds=True)
        # self.addItem(self.hLine, ignoreBounds=True)

        self.selection_roi = pg.RectROI((0, 0), size=(20, 20), scaleSnap=True, translateSnap=True)
        self.selection_roi.sigRegionChanged.connect(self.roi_update)

        self.addItem(self.selection_roi)

        self.infobar = infobar

        self.update(-1, autoLevels=True, autoRange=True)

    def roi_update(self):
        # print self.selection_roi.pos()
        # print self.selection_roi.size()
        xmin, xmax, ymin, ymax = self.get_roi_coordinates()
        self.infobar.roi_x_value.setText('%.0f:%.0f' % (xmin, xmax))
        self.infobar.roi_y_value.setText('%.0f:%.0f' % (ymin, ymax))
        self.infobar.roi_column_offset.setText('%.0f' % xmin)
        self.infobar.roi_row_offset.setText('%.0f' % ymin)
        self.infobar.roi_num_columns.setText('%.0f' % (xmax - xmin))
        self.infobar.roi_num_rows.setText('%.0f' % (ymax - ymin))
        self.infobar.command_to_send.setText('---')
        # Update command to send here

    def get_roi_coordinates(self):
        if self.portrait_mode:
            ymin = np.floor(self.selection_roi.pos()[0] / self.scale_by) + self.column_offset
            ymax = np.ceil(
                (self.selection_roi.pos()[0] + self.selection_roi.size()[0]) / self.scale_by) + self.column_offset
            xmin = np.floor(self.selection_roi.pos()[1] / self.scale_by) + self.row_offset
            xmax = np.ceil(
                (self.selection_roi.pos()[1] + self.selection_roi.size()[1]) / self.scale_by) + self.row_offset
        else:
            xmin = np.floor(self.selection_roi.pos()[0] / self.scale_by) + self.row_offset
            xmax = np.ceil(
                (self.selection_roi.pos()[0] + self.selection_roi.size()[0]) / self.scale_by) + self.row_offset
            ymin = np.floor(self.selection_roi.pos()[1] / self.scale_by) + self.column_offset
            ymax = np.ceil(
                (self.selection_roi.pos()[1] + self.selection_roi.size()[1]) / self.scale_by) + self.column_offset
        return xmin, xmax, ymin, ymax

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
            print latest.keys()
        except (IndexError, KeyError) as e:
            print "invalid index", index, e
            return
        if index == self.last_index:
            return
        self.last_index = index
        filename = latest['filename']
        self.window.setWindowTitle(filename)
        print filename
        file_size = os.path.getsize(filename)
        image_file = load_and_decode_file(filename)
        self.infobar.update(image_file, latest, file_size)
        self.scale_by = image_file.scale_by
        self.row_offset = image_file.row_offset
        self.column_offset = image_file.column_offset
        image_data = image_file.image_array() / image_file.pixel_scale + image_file.pixel_offset
        self.setImage(image_data, autoLevels=autoLevels, autoRange=autoRange)
        print image_data.shape
        print self.selection_roi.size()
        print self.selection_roi.pos()

        if (self.selection_roi.pos()[0] < 0) or (self.selection_roi.pos()[1] < 0):
            self.selection_roi.setPos((0, 0))

        xmax = self.selection_roi.pos()[0] + self.selection_roi.size()[0]
        ymax = self.selection_roi.pos()[1] + self.selection_roi.size()[1]

        if not self.portrait_mode:
            xlim = image_data.shape[1]
            ylim = image_data.shape[0]
        else:
            xlim = image_data.shape[0]
            ylim = image_data.shape[1]

        print xmax, ymax
        if xmax > xlim:
            self.selection_roi.setSize(
                [xlim - self.selection_roi.pos()[0], self.selection_roi.size()[1]])

        if ymax > ylim:
            self.selection_roi.setSize(
                [self.selection_roi.size()[0], ylim - self.selection_roi.pos()[1]])

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
        # self.setWindowTitle("Info: ---")
        # self.setFeatures(QtGui.QDockWidget.AllDockWidgetFeatures | QtGui.QDockWidget.DockWidgetVerticalTitleBar)
        # self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        mywidget = QtGui.QWidget()
        nested_widget = QtGui.QWidget()
        vlayout = QtGui.QVBoxLayout()

        frame_status_label = QtGui.QLabel('frame_status')
        frame_id_label = QtGui.QLabel('frame_id')
        frame_timestamp_s = QtGui.QLabel('frame (s)')
        focus_step_label = QtGui.QLabel('focus_step')

        aperture_stop_label = QtGui.QLabel('aperture_stop')
        exposure_us_label = QtGui.QLabel('exposure_us')
        file_index_label = QtGui.QLabel('file_index')
        write_timestamp_label = QtGui.QLabel('write')

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
        file_size_label = QtGui.QLabel('file size (bytes)')
        first_timestamp_label = QtGui.QLabel('first packet')
        last_timestamp_label = QtGui.QLabel('last packet')
        file_write_timestamp_label = QtGui.QLabel('file write')
        camera_id_label = QtGui.QLabel('camera id')

        roi_x_label = QtGui.QLabel('ROI x lims: ')
        roi_y_label = QtGui.QLabel('ROI y lims: ')
        command_to_send_label = QtGui.QLabel('Command to send: ')
        roi_row_offset_label = QtGui.QLabel('Row offset')
        roi_col_offset_label = QtGui.QLabel('Column offset')
        roi_num_rows_label = QtGui.QLabel('Num rows')
        roi_num_cols_label = QtGui.QLabel('Num columns')

        self.labels = [
            frame_status_label,
            frame_id_label,
            frame_timestamp_s,
            focus_step_label,

            aperture_stop_label,
            exposure_us_label,
            file_index_label,
            write_timestamp_label,

            acquisition_count_label,
            lens_status_label,
            gain_db_label,
            focal_length_mm_label,

            row_offset_label,
            column_offset_label,
            num_rows_label,
            num_columns_label,

            scale_by_label,
            pixel_offset_label,
            pixel_scale_label,
            quality_label,
            file_size_label,
            first_timestamp_label,
            last_timestamp_label,
            file_write_timestamp_label,
            camera_id_label,
            roi_x_label,
            roi_y_label,
            command_to_send_label,
            roi_row_offset_label,
            roi_col_offset_label,
            roi_num_rows_label,
            roi_num_cols_label,

        ]

        labelfont = frame_status_label.font()
        labelfont.setPointSize(6)
        # labelfont.setBold(True)
        for label in self.labels:
            label.setFont(labelfont)

        self.frame_status_value = QtGui.QLabel('---')
        self.frame_id_value = QtGui.QLabel('---')
        self.frame_timestamp_s = QtGui.QLabel('---')
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
        self.file_size_value = QtGui.QLabel('---')
        self.first_timestamp_value = QtGui.QLabel('---')
        self.last_timestamp_value = QtGui.QLabel('---')
        self.file_write_timestamp_value = QtGui.QLabel('---')
        self.camera_id_value = QtGui.QLabel('---')
        self.roi_row_offset = QtGui.QLabel('---')
        self.roi_column_offset = QtGui.QLabel('---')
        self.roi_num_rows = QtGui.QLabel('---')
        self.roi_num_columns = QtGui.QLabel('---')
        self.roi_x_value = QtGui.QLabel('---')
        self.roi_y_value = QtGui.QLabel('---')
        self.command_to_send = QtGui.QLabel('---')

        self.values = [
            self.frame_status_value,
            self.frame_id_value,
            self.frame_timestamp_s,
            self.focus_step_value,

            self.aperture_stop_value,
            self.exposure_us_value,
            self.file_index_value,
            self.write_timestamp_value,

            self.acquisition_count_value,
            self.lens_status_value,
            self.gain_db_value,
            self.focal_length_mm_value,

            self.row_offset_value,
            self.column_offset_value,
            self.num_rows_value,
            self.num_columns_value,

            self.scale_by_value,
            self.pixel_offset_value,
            self.pixel_scale_value,
            self.quality_value,
            self.file_size_value,
            self.first_timestamp_value,
            self.last_timestamp_value,
            self.file_write_timestamp_value,
            self.camera_id_value,
            self.roi_x_value,
            self.roi_y_value,
            self.command_to_send,
            self.roi_row_offset,
            self.roi_column_offset,
            self.roi_num_rows,
            self.roi_num_columns
        ]

        valuefont = self.frame_status_value.font()
        valuefont.setPointSize(6)
        for value in self.values:
            value.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            value.setFont(valuefont)

        time_widget = QtGui.QWidget()
        time_layout = QtGui.QGridLayout()
        time_widget.setLayout(time_layout)
        time_layout.addWidget(frame_timestamp_s, 2, 0)
        time_layout.addWidget(write_timestamp_label, 7, 0)
        time_layout.addWidget(first_timestamp_label, 8, 0)
        time_layout.addWidget(last_timestamp_label, 9, 0)
        time_layout.addWidget(file_write_timestamp_label, 10, 0)
        time_layout.addWidget(self.frame_timestamp_s, 2, 1)
        time_layout.addWidget(self.write_timestamp_value, 7, 1)
        time_layout.addWidget(self.first_timestamp_value, 8, 1)
        time_layout.addWidget(self.last_timestamp_value, 9, 1)
        time_layout.addWidget(self.file_write_timestamp_value, 10, 1)

        camera_widget = QtGui.QWidget()
        camera_layout = QtGui.QGridLayout()
        camera_widget.setLayout(camera_layout)
        camera_layout.addWidget(camera_id_label, 0, 0)
        camera_layout.addWidget(aperture_stop_label, 4, 0)
        camera_layout.addWidget(exposure_us_label, 5, 0)
        camera_layout.addWidget(frame_status_label, 2, 0)
        camera_layout.addWidget(focus_step_label, 3, 0)
        camera_layout.addWidget(lens_status_label, 9, 0)
        camera_layout.addWidget(gain_db_label, 10, 0)
        camera_layout.addWidget(focal_length_mm_label, 11, 0)
        camera_layout.addWidget(frame_id_label, 1, 0)
        camera_layout.addWidget(file_index_label, 6, 0)
        camera_layout.addWidget(acquisition_count_label, 8, 0)
        camera_layout.addWidget(self.camera_id_value, 0, 1)
        camera_layout.addWidget(self.aperture_stop_value, 4, 1)
        camera_layout.addWidget(self.exposure_us_value, 5, 1)
        camera_layout.addWidget(self.frame_status_value, 2, 1)
        camera_layout.addWidget(self.focus_step_value, 3, 1)
        camera_layout.addWidget(self.lens_status_value, 9, 1)
        camera_layout.addWidget(self.gain_db_value, 10, 1)
        camera_layout.addWidget(self.focal_length_mm_value, 11, 1)
        camera_layout.addWidget(self.frame_id_value, 1, 1)
        camera_layout.addWidget(self.file_index_value, 6, 1)
        camera_layout.addWidget(self.acquisition_count_value, 8, 1)

        image_widget = QtGui.QWidget()
        image_layout = QtGui.QGridLayout()
        image_widget.setLayout(image_layout)
        image_layout.addWidget(row_offset_label, 12, 0)
        image_layout.addWidget(column_offset_label, 13, 0)
        image_layout.addWidget(num_rows_label, 14, 0)
        image_layout.addWidget(num_columns_label, 15, 0)
        image_layout.addWidget(scale_by_label, 16, 0)
        image_layout.addWidget(pixel_offset_label, 17, 0)
        image_layout.addWidget(pixel_scale_label, 18, 0)
        image_layout.addWidget(quality_label, 19, 0)
        image_layout.addWidget(file_size_label, 20, 0)
        image_layout.addWidget(self.row_offset_value, 12, 1)
        image_layout.addWidget(self.column_offset_value, 13, 1)
        image_layout.addWidget(self.num_rows_value, 14, 1)
        image_layout.addWidget(self.num_columns_value, 15, 1)
        image_layout.addWidget(self.scale_by_value, 16, 1)
        image_layout.addWidget(self.pixel_offset_value, 17, 1)
        image_layout.addWidget(self.pixel_scale_value, 18, 1)
        image_layout.addWidget(self.quality_value, 19, 1)
        image_layout.addWidget(self.file_size_value, 20, 1)

        # x_label = QtGui.QLabel('X: ')
        # y_label = QtGui.QLabel('Y: ')
        # self.x_value = QtGui.QLabel('---')
        # self.y_value = QtGui.QLabel('---')
        #
        # crosshair_widget = QtGui.QWidget()
        # crosshair_layout = QtGui.QHBoxLayout()
        # crosshair_layout.addWidget(x_label)
        # crosshair_layout.addWidget(self.x_value)
        # crosshair_layout.addWidget(y_label)
        # crosshair_layout.addWidget(self.y_value)
        # crosshair_widget.setLayout(crosshair_layout)



        roi_widget = QtGui.QWidget()
        roi_layout = QtGui.QGridLayout()
        roi_widget.setLayout(roi_layout)
        roi_layout.addWidget(roi_x_label, 0, 0)
        roi_layout.addWidget(roi_y_label, 1, 0)
        roi_layout.addWidget(self.roi_x_value, 0, 1)
        roi_layout.addWidget(self.roi_y_value, 1, 1)
        roi_layout.addWidget(roi_row_offset_label, 2, 0)
        roi_layout.addWidget(self.roi_row_offset, 2, 1)
        roi_layout.addWidget(roi_col_offset_label, 3, 0)
        roi_layout.addWidget(self.roi_column_offset, 3, 1)
        roi_layout.addWidget(roi_num_rows_label, 4, 0)
        roi_layout.addWidget(self.roi_num_rows, 4, 1)
        roi_layout.addWidget(roi_num_cols_label, 5, 0)
        roi_layout.addWidget(self.roi_num_columns, 5, 1)
        roi_layout.addWidget(command_to_send_label, 6, 0)
        roi_layout.addWidget(self.command_to_send, 6, 1)

        vertical_spacer = QtGui.QSpacerItem(10, 10, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

        vlayout.addWidget(QtGui.QLabel('ROI Coordinates'))
        vlayout.addWidget(roi_widget)
        vlayout.addWidget(QtGui.QLabel('Timestamps'))
        vlayout.addWidget(time_widget)
        vlayout.addWidget(QtGui.QLabel('Camera'))
        vlayout.addWidget(camera_widget)
        vlayout.addWidget(QtGui.QLabel('Image'))
        vlayout.addWidget(image_widget)
        vlayout.addItem(vertical_spacer)

        mywidget.setLayout(vlayout)

        self.setWidget(mywidget)

    def update(self, jpeg_file, data_row, file_size):
        self.frame_status_value.setText(str(jpeg_file.frame_status))
        self.frame_id_value.setText(str(jpeg_file.frame_id))
        time_s = jpeg_file.frame_timestamp_ns / 1e9
        self.frame_timestamp_s.setText('%.0f' % time_s)
        self.frame_timestamp_s.setToolTip(time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(time_s)))
        self.focus_step_value.setText(str(jpeg_file.focus_step))

        self.aperture_stop_value.setText(str(jpeg_file.aperture_stop))
        self.exposure_us_value.setText(str(jpeg_file.exposure_us))
        self.file_index_value.setText(str(jpeg_file.file_index))
        self.write_timestamp_value.setText('%.0f' % jpeg_file.write_timestamp)
        self.write_timestamp_value.setToolTip(
            time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(jpeg_file.write_timestamp)))

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
        self.file_size_value.setText(str(file_size))

        self.first_timestamp_value.setText('%.0f' % data_row['first_timestamp'])
        self.first_timestamp_value.setToolTip(
            time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(float(data_row['first_timestamp']))))
        self.last_timestamp_value.setText('%.0f' % data_row['last_timestamp'])
        self.last_timestamp_value.setToolTip(
            time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(float(data_row['last_timestamp']))))
        self.file_write_timestamp_value.setText('%.0f' % data_row['file_write_timestamp'])
        self.file_write_timestamp_value.setToolTip(
            time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(float(data_row['file_write_timestamp']))))

        # self.filename_label.setText(str(data_row['filename']))

        self.camera_id_value.setText(str(data_row['camera_id']))


if __name__ == "__main__":
    from pmc_turbo.utils import log
    import sys

    camera_id = None
    portrait_mode = False
    if len(sys.argv) > 1:
        # camera_id = int(sys.argv[1])
        portrait_mode = int(sys.argv[1])

    if not portrait_mode:
        pg.setConfigOptions(imageAxisOrder='row-major')
    else:
        pg.setConfigOptions(imageAxisOrder='col-major')
    log.setup_stream_handler(log.logging.DEBUG)
    app = QtGui.QApplication([])
    dw = QtGui.QDesktopWidget()
    iw = InfoBar()
    win = QtGui.QMainWindow()
    win.resize(800, 800)
    imv = MyImageView(camera_id, iw, win, portrait_mode=portrait_mode)
    # proxy = pg.SignalProxy(imv.imageItem.scene().sigMouseMoved, rateLimit=60, slot=imv.mouseMoved)
    win.setCentralWidget(imv)
    win.addDockWidget(QtCore.Qt.LeftDockWidgetArea, iw)
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
