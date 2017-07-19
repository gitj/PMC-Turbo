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
from pmc_turbo.camera.pycamera import dtypes


def get_roi_coordinates(roi_pos, roi_size, scale_by, row_offset, column_offset, portrait_mode):
    if portrait_mode:
        x_idx = 1
        y_idx = 0
    else:
        x_idx = 0
        y_idx = 1
    xmin = np.floor(roi_pos[x_idx] / scale_by) + row_offset
    xmax = np.ceil((roi_pos[x_idx] + roi_size[x_idx]) / scale_by) + row_offset
    ymin = np.floor(roi_pos[y_idx] / scale_by) + column_offset
    ymax = np.ceil((roi_pos[y_idx] + roi_size[y_idx]) / scale_by) + column_offset
    return xmin, xmax, ymin, ymax


class MyImageView(pg.ImageView):
    def __init__(self, camera_id, infobar, commandbar, window, portrait_mode, *args, **kwargs):
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
        self.prev_shape = None
        #
        # self.vLine = pg.InfiniteLine(angle=90, movable=False)
        # self.hLine = pg.InfiniteLine(angle=0, movable=False)
        # self.addItem(self.vLine, ignoreBounds=True)
        # self.addItem(self.hLine, ignoreBounds=True)

        self.selection_roi = pg.RectROI((0, 0), size=(20, 20), scaleSnap=True, translateSnap=True)
        self.selection_roi.sigRegionChangeFinished.connect(self.roi_update)

        self.addItem(self.selection_roi)

        self.infobar = infobar
        self.commandbar = commandbar

        self.update(-1, autoLevels=True, autoRange=True)

    def roi_update(self):
        xmin, xmax, ymin, ymax = get_roi_coordinates(self.selection_roi.pos(), self.selection_roi.size(), self.scale_by,
                                                     self.row_offset, self.column_offset, self.portrait_mode)
        if self.portrait_mode:
            x_idx = 1
            y_idx = 0
        else:
            x_idx = 0
            y_idx = 1
        self.infobar.roi_x_value.setText('%.0f:%.0f' % (
            self.selection_roi.pos()[x_idx], self.selection_roi.pos()[x_idx] + self.selection_roi.size()[x_idx]))
        self.infobar.roi_y_value.setText('%.0f:%.0f' % (
            self.selection_roi.pos()[y_idx], self.selection_roi.pos()[y_idx] + self.selection_roi.size()[y_idx]))
        self.infobar.roi_column_offset.setText('%.0f' % xmin)
        self.infobar.roi_row_offset.setText('%.0f' % ymin)
        self.infobar.roi_num_columns.setText('%.0f' % (xmax - xmin))
        self.infobar.roi_num_rows.setText('%.0f' % (ymax - ymin))
        self.commandbar.dynamic_command.setText(
            'request_specific_images(timestamp=%f, row_offset=%d, column_offset=%d, num_rows=%d, num_columns=%d, num_images=1, scale_by=1, quality=75, step=-1)'
            % (self.timestamp, ymin, xmin, (ymax - ymin), (xmax - xmin)))
        self.commandbar.dynamic_command.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

    def update(self, index=-1, autoLevels=True, autoRange=True):
        self.mi.update()
        if self.camera_id is not None:
            df = self.mi.df[self.mi.df.camera_id == self.camera_id]
        else:
            df = self.mi.df
        df = df[df.file_type == JPEGFile.file_type].reset_index(drop=True)
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
        self.infobar.update(image_file, latest, file_size, index, df.index.max())
        self.timestamp = image_file.frame_timestamp_ns / 1e9
        self.scale_by = image_file.scale_by
        self.row_offset = image_file.row_offset
        self.column_offset = image_file.column_offset
        image_data = image_file.image_array() / image_file.pixel_scale + image_file.pixel_offset
        self.setImage(image_data, autoLevels=autoLevels, autoRange=autoRange)

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

        if image_data.shape != self.prev_shape:
            self.selection_roi.setSize([10, 10])
            self.selection_roi.setPos([0, 0, ])
            self.prev_shape = image_data.shape
        else:
            if xmax > xlim:
                self.selection_roi.setSize(
                    [xlim - self.selection_roi.pos()[0], self.selection_roi.size()[1]])

            if ymax > ylim:
                self.selection_roi.setSize(
                    [self.selection_roi.size()[0], ylim - self.selection_roi.pos()[1]])
        self.roi_update()

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
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())
            self.infobar.x_value.setText('%.0f' % mousePoint.x())
            self.infobar.y_value.setText('%.0f' % mousePoint.y())

    def update_from_index_edit(self):
        idx = int(self.infobar.go_to_index_edit.text())
        self.update(idx)


class InfoBar(QtGui.QDockWidget):
    def __init__(self, *args, **kwargs):
        super(InfoBar, self).__init__(*args, **kwargs)
        self.image_viewer = None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QtGui.QWidget(None))
        mywidget = QtGui.QWidget()
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

        roi_x_label = QtGui.QLabel('ROI x lims')
        roi_y_label = QtGui.QLabel('ROI y lims')
        roi_row_offset_label = QtGui.QLabel('Row offset')
        roi_col_offset_label = QtGui.QLabel('Column offset')
        roi_num_rows_label = QtGui.QLabel('Num rows')
        roi_num_cols_label = QtGui.QLabel('Num columns')

        last_error_message_label = QtGui.QLabel('last error msg')
        auto_focus_label = QtGui.QLabel('auto focus')
        last_error_label = QtGui.QLabel('last error')
        lens_attached_label = QtGui.QLabel('lens attached')
        lens_error_label = QtGui.QLabel('error')

        ground_index_label = QtGui.QLabel('Index:')
        total_index_label = QtGui.QLabel('Length:')
        go_to_index_label = QtGui.QLabel('Go to:')

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
            roi_row_offset_label,
            roi_col_offset_label,
            roi_num_rows_label,
            roi_num_cols_label,
            last_error_message_label,
            auto_focus_label,
            last_error_label,
            lens_attached_label,
            lens_error_label,
            ground_index_label,
            total_index_label,
            go_to_index_label
        ]

        labelfont = frame_status_label.font()
        labelfont.setPointSize(5)
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

        self.last_error_message_value = QtGui.QLabel('---')
        self.auto_focus_value = QtGui.QLabel('---')
        self.last_error_value = QtGui.QLabel('---')
        self.lens_attached_value = QtGui.QLabel('---')
        self.lens_error_value = QtGui.QLabel('---')

        self.ground_index_value = QtGui.QLabel('---')
        self.total_index_value = QtGui.QLabel('---')

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
            self.roi_row_offset,
            self.roi_column_offset,
            self.roi_num_rows,
            self.roi_num_columns,

            self.last_error_message_value,
            self.auto_focus_value,
            self.last_error_value,
            self.lens_attached_value,
            self.lens_error_value,
            self.ground_index_value,
            self.total_index_value
        ]

        valuefont = self.frame_status_value.font()
        valuefont.setPointSize(5)
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
        camera_layout.addWidget(self.gain_db_value, 10, 1)
        camera_layout.addWidget(self.focal_length_mm_value, 11, 1)
        camera_layout.addWidget(self.frame_id_value, 1, 1)
        camera_layout.addWidget(self.file_index_value, 6, 1)
        camera_layout.addWidget(self.acquisition_count_value, 8, 1)

        lens_status_widget = QtGui.QWidget()
        lens_status_layout = QtGui.QGridLayout()

        lens_status_layout.addWidget(last_error_message_label, 0, 0)
        lens_status_layout.addWidget(auto_focus_label, 1, 0)
        lens_status_layout.addWidget(last_error_label, 2, 0)
        lens_status_layout.addWidget(lens_attached_label, 3, 0)
        lens_status_layout.addWidget(lens_error_label, 4, 0)
        lens_status_layout.addWidget(self.last_error_message_value, 0, 1)
        lens_status_layout.addWidget(self.auto_focus_value, 1, 1)
        lens_status_layout.addWidget(self.last_error_value, 2, 1)
        lens_status_layout.addWidget(self.lens_attached_value, 3, 1)
        lens_status_layout.addWidget(self.lens_error_value, 4, 1)
        lens_status_widget.setLayout(lens_status_layout)

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

        # x_label = QtGui.QLabel('X')
        # y_label = QtGui.QLabel('Y')
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

        index_widget = QtGui.QWidget()
        index_layout = QtGui.QGridLayout()
        index_widget.setLayout(index_layout)
        index_layout.addWidget(ground_index_label, 0, 0)
        index_layout.addWidget(total_index_label, 1, 0)
        index_layout.addWidget(go_to_index_label, 2, 0)
        index_layout.addWidget(self.ground_index_value, 0, 1)
        index_layout.addWidget(self.total_index_value, 1, 1)

        self.go_to_index_edit = QtGui.QLineEdit()
        self.go_to_index_edit.setValidator(QtGui.QIntValidator())
        f = self.go_to_index_edit.font()
        f.setPointSize(5)
        self.go_to_index_edit.setFont(f)
        self.go_to_index_edit.setFixedWidth(25)
        self.go_to_index_edit.setFixedHeight(13)
        #self.go_to_index_edit.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        self.go_to_index_edit.returnPressed.connect(self.update_from_index_edit)

        index_layout.addWidget(self.go_to_index_edit, 2, 1)

        vertical_spacer = QtGui.QSpacerItem(10, 10, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)

        headers = [
            QtGui.QLabel('ROI Coordinates'),
            QtGui.QLabel('Timestamps'),
            QtGui.QLabel('Camera'),
            QtGui.QLabel('Lens Status'),
            QtGui.QLabel('Lens Status'),
            QtGui.QLabel('Image')
        ]

        # vlayout.addWidget()
        vlayout.addWidget(roi_widget)
        # vlayout.addWidget()
        vlayout.addWidget(time_widget)
        # vlayout.addWidget()
        vlayout.addWidget(camera_widget)
        # vlayout.addWidget()
        vlayout.addWidget(lens_status_widget)
        # vlayout.addWidget()
        vlayout.addWidget(image_widget)
        vlayout.addWidget(index_widget)
        vlayout.addItem(vertical_spacer)
        mywidget.setLayout(vlayout)
        self.setWidget(mywidget)

    def update(self, jpeg_file, data_row, file_size, index, max_index):
        self.frame_status_value.setText(str(jpeg_file.frame_status))
        self.frame_id_value.setText(str(jpeg_file.frame_id))
        time_s = jpeg_file.frame_timestamp_ns / 1e9
        self.frame_timestamp_s.setText('%.0f' % time_s)
        self.frame_timestamp_s.setToolTip(time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(time_s)))
        self.focus_step_value.setText(str(jpeg_file.focus_step))

        self.aperture_stop_value.setText(str(dtypes.decode_aperture_chunk_data(jpeg_file.aperture_stop)))
        self.exposure_us_value.setText(str(jpeg_file.exposure_us))
        self.file_index_value.setText(str(jpeg_file.file_index))
        self.write_timestamp_value.setText('%.0f' % jpeg_file.write_timestamp)
        self.write_timestamp_value.setToolTip(
            time.strftime("%Y.%m.%d_%H:%M:%S", time.localtime(jpeg_file.write_timestamp)))

        self.acquisition_count_value.setText(str(jpeg_file.acquisition_count))
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

        lens_status_dict = dtypes.decode_lens_status_chunk_data(jpeg_file.lens_status)
        self.last_error_message_value.setText(str(lens_status_dict['last_error_message']))
        self.auto_focus_value.setText(str(lens_status_dict['auto_focus']))
        self.last_error_value.setText(str(lens_status_dict['last_error']))
        self.lens_attached_value.setText(str(lens_status_dict['lens_attached']))
        self.lens_error_value.setText(str(lens_status_dict['error']))

        self.ground_index_value.setText(str(index))
        self.total_index_value.setText(str(max_index))

    def update_from_index_edit(self):
        if self.image_viewer:
            self.image_viewer.update_from_index_edit()


class CommandBar(QtGui.QDockWidget):
    def __init__(self, *args, **kwargs):
        super(CommandBar, self).__init__(*args, **kwargs)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QtGui.QWidget(None))
        mywidget = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        label = QtGui.QLabel('Command:')

        self.dynamic_command = QtGui.QLabel('---')
        dfont = self.dynamic_command.font()
        dfont.setPointSize(5)
        label.setFont(dfont)
        dfont.setBold(True)
        self.dynamic_command.setFont(dfont)
        layout.addWidget(label)
        layout.addWidget(self.dynamic_command)
        # horizontal_spacer = QtGui.QSpacerItem(5, 5, hPolicy=QtGui.QSizePolicy.Expanding,
        #                                       vPolicy=QtGui.QSizePolicy.Minimum)
        # layout.addItem(horizontal_spacer)
        mywidget.setLayout(layout)
        self.setWidget(mywidget)


if __name__ == "__main__":
    from pmc_turbo.utils import log
    import sys

    camera_id = None
    portrait_mode = False
    if len(sys.argv) > 1:
        portrait_mode = int(sys.argv[1])
    if len(sys.argv) > 2:
        camera_id = int(sys.argv[1])
    if not portrait_mode:
        pg.setConfigOptions(imageAxisOrder='row-major')
    else:
        pg.setConfigOptions(imageAxisOrder='col-major')
    log.setup_stream_handler(log.logging.DEBUG)
    app = QtGui.QApplication([])
    dw = QtGui.QDesktopWidget()
    iw = InfoBar()
    cb = CommandBar()
    win = QtGui.QMainWindow()

    imv = MyImageView(camera_id, iw, cb, win, portrait_mode=portrait_mode)
    iw.image_viewer = imv
    # proxy = pg.SignalProxy(imv.imageItem.scene().sigMouseMoved, rateLimit=60, slot=imv.mouseMoved)
    win.setCentralWidget(imv)
    win.addDockWidget(QtCore.Qt.LeftDockWidgetArea, iw)
    win.addDockWidget(QtCore.Qt.BottomDockWidgetArea, cb)
    win.resize(600, 600)
    win.show()
    print "main window width x height", win.frameGeometry().width(), win.frameGeometry().height()
    if win.frameGeometry().height() > 870:
        raise Exception("Window is too high, rearrange widgets to reduce height")
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
