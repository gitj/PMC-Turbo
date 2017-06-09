import sys
import Pyro4
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

pg.setConfigOptions(imageAxisOrder='row-major')
import pgview

root_path = '/'
proxy = Pyro4.Proxy('PYRO:controller@0.0.0.0:50001')


class GUIWrapper():
    def __init__(self, proxy=True):
        self.app = QtGui.QApplication([])

        if proxy:
            self.proxy = Pyro4.Proxy('PYRO:controller@0.0.0.0:50001')
            initial_status = self.proxy.get_pipeline_status()
            current_focus = initial_status['all_camera_parameters']['EFLensFocusCurrent']
            # min_focus = initial_status['all_camera_parameters']['EFLensFocusMin']
            max_focus = initial_status['all_camera_parameters']['EFLensFocusMax']
            exposure = initial_status['all_camera_parameters']['ExposureTimeAbs']
        else:
            self.proxy = None
            current_focus = '---'
            max_focus = '---'
            exposure = '---'
        self.real_time_values = RealTimeValues(current_focus, max_focus, exposure)
        self.window = QtGui.QMainWindow()
        self.window.resize(800, 800)

        self.window.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.real_time_values)

        self.imv = pgview.MyImageView(real_time_values=self.real_time_values)
        self.window.setCentralWidget(self.imv)

        self.toolbar = MyToolBar(guiwrapper=self)
        self.window.addToolBar(QtCore.Qt.BottomToolBarArea, self.toolbar)

        self.focus_step = 10
        self.exposure_step = 10e3
        self.focus = 2000
        self.exposure = 100e3

    def increase_focus_button_press(self):
        focus_step = self.focus + self.focus_step
        try:
            if self.proxy:
                self.proxy.set_focus(focus_step)
            self.focus = focus_step
            print 'Increased focus to %d' % self.focus
            self.real_time_values.update_focus(self.focus)
        except Exception as e:
            print e

    def decrease_focus_button_press(self):
        focus_step = self.focus - self.focus_step
        try:
            if self.proxy:
                self.proxy.set_focus(focus_step)
            self.focus = focus_step
            print 'Decreased focus to %d' % self.focus
            self.real_time_values.update_focus(self.focus)
        except Exception as e:
            print e

    def increase_exposure_button_press(self):
        exposure_us = self.exposure + self.exposure_step
        try:
            if self.proxy:
                self.proxy.set_exposure(exposure_us)
            self.exposure = exposure_us
            print 'Increased exposure to %d' % self.exposure
            self.real_time_values.update_exposure(self.exposure)
        except Exception as e:
            print e

    def decrease_exposure_button_press(self):
        exposure_us = self.exposure - self.exposure_step
        try:
            if self.proxy:
                self.proxy.set_exposure(exposure_us)
            self.exposure = exposure_us
            print 'Increased exposure to %d' % self.exposure
            self.real_time_values.update_exposure(self.exposure)
        except Exception as e:
            print e

    def change_focus_step(self, focus_step):
        focus_step = int(focus_step)
        self.focus_step = focus_step
        print 'Changed focus step to %d' % self.focus_step

    def change_exposure_step(self, exposure_step):
        exposure_step = int(exposure_step)
        self.exposure_step = exposure_step
        print 'Changed exposure step to %d' % self.exposure_step

    def change_focus(self, focus):
        focus = int(focus)
        try:
            if self.proxy:
                self.proxy.set_focus(focus)
            self.focus = focus
            print 'Changed focus to %d' % self.focus
            self.real_time_values.update_focus(self.focus)
        except Exception as e:
            print e

    def change_exposure(self, exposure):
        exposure = int(exposure)
        try:
            if self.proxy:
                self.proxy.set_exposure(exposure)
            self.exposure = exposure
            print 'Changed exposure to %d' % self.exposure
            self.real_time_values.update_exposure(self.exposure)
        except Exception as e:
            print e


class MyToolBar(QtGui.QToolBar):
    def __init__(self, guiwrapper, *args, **kwargs):
        super(MyToolBar, self).__init__(*args, **kwargs)
        self.guiwrapper = guiwrapper
        print self.guiwrapper
        self.setup_layout()

    def setup_layout(self):
        increase_focus = QtGui.QPushButton("Increase Focus", self.guiwrapper.window)
        decrease_focus = QtGui.QPushButton("Decrease Focus", self.guiwrapper.window)
        increase_exposure_time = QtGui.QPushButton("Increase Exposure Time", self.guiwrapper.window)
        decrease_exposure_time = QtGui.QPushButton("Decrease Exposure Time", self.guiwrapper.window)

        increase_focus.clicked.connect(self.guiwrapper.increase_focus_button_press)
        decrease_focus.clicked.connect(self.guiwrapper.decrease_focus_button_press)
        increase_exposure_time.clicked.connect(self.guiwrapper.increase_exposure_button_press)
        decrease_exposure_time.clicked.connect(self.guiwrapper.decrease_exposure_button_press)

        self.focus_step_edit = QtGui.QLineEdit()
        self.focus_step_edit.returnPressed.connect(self.change_focus_step)

        self.exposure_step_edit = QtGui.QLineEdit()
        self.exposure_step_edit.returnPressed.connect(self.change_exposure_step)

        increase_decrease_focus_widget = QtGui.QWidget()
        increase_decrease_focus_layout = QtGui.QGridLayout()
        increase_decrease_focus_layout.addWidget(increase_focus, 0, 0)
        increase_decrease_focus_layout.addWidget(decrease_focus, 1, 0)
        increase_decrease_focus_widget.setLayout(increase_decrease_focus_layout)

        increase_decrease_exposure_widget = QtGui.QWidget()
        increase_decrease_exposure_layout = QtGui.QGridLayout()
        increase_decrease_exposure_layout.addWidget(increase_exposure_time, 0, 0)
        increase_decrease_exposure_layout.addWidget(decrease_exposure_time, 1, 0)
        increase_decrease_exposure_widget.setLayout(increase_decrease_exposure_layout)

        step_increment_widget = QtGui.QWidget()
        step_increment_layout = QtGui.QGridLayout()

        focus_step_label = QtGui.QLabel()
        focus_step_label.setText('Focus Step: ')
        step_increment_layout.addWidget(focus_step_label, 0, 0)
        step_increment_layout.addWidget(self.focus_step_edit, 0, 1)

        exposure_step_label = QtGui.QLabel()
        exposure_step_label.setText('Exposure Step: ')
        step_increment_layout.addWidget(exposure_step_label, 1, 0)
        step_increment_layout.addWidget(self.exposure_step_edit, 1, 1)
        step_increment_widget.setLayout(step_increment_layout)

        absolute_widget = QtGui.QWidget()
        absolute_layout = QtGui.QGridLayout()

        self.focus_edit = QtGui.QLineEdit()
        self.focus_edit.returnPressed.connect(self.change_focus)
        self.exposure_edit = QtGui.QLineEdit()
        self.exposure_edit.returnPressed.connect(self.change_exposure)

        focus_label = QtGui.QLabel()
        focus_label.setText('Set Focus: ')
        absolute_layout.addWidget(focus_label, 0, 0)
        absolute_layout.addWidget(self.focus_edit, 0, 1)

        exposure_label = QtGui.QLabel()
        exposure_label.setText('Set Exposure: ')
        absolute_layout.addWidget(exposure_label, 1, 0)
        absolute_layout.addWidget(self.exposure_edit, 1, 1)
        absolute_widget.setLayout(absolute_layout)

        self.addWidget(increase_decrease_focus_widget)
        self.addWidget(increase_decrease_exposure_widget)
        self.addWidget(step_increment_widget)
        self.addWidget(absolute_widget)

    def change_focus_step(self):
        self.guiwrapper.change_focus_step(self.focus_step_edit.text())
        print self.focus_step_edit.text()

    def change_exposure_step(self):
        self.guiwrapper.change_exposure_step(self.exposure_step_edit.text())
        print self.exposure_step_edit.text()

    def change_focus(self):
        self.guiwrapper.change_focus(self.focus_edit.text())
        print self.focus_edit.text()

    def change_exposure(self):
        self.guiwrapper.change_exposure(self.exposure_edit.text())
        print self.exposure_edit.text()


class RealTimeValues(QtGui.QDockWidget):
    def __init__(self, current_focus, max_focus, exposure, *args, **kwargs):
        # super(RealTimeValues,self).__init__("Status", *args,**kwargs)
        super(RealTimeValues, self).__init__(*args, **kwargs)
        multiwidget = QtGui.QWidget()
        layout = QtGui.QGridLayout()

        filename_title = QtGui.QLabel()
        layout.addWidget(filename_title, 0, 0)
        filename_title.setText('Filename:')

        self.filename_value = QtGui.QLabel()
        layout.addWidget(self.filename_value, 0, 1)
        self.filename_value.setText('---')

        focus_title = QtGui.QLabel()
        layout.addWidget(focus_title, 1, 0)
        focus_title.setText('Focus (max %s):' % max_focus)

        exposure_title = QtGui.QLabel()
        layout.addWidget(exposure_title, 2, 0)
        exposure_title.setText('Exposure: ')

        self.focus_value = QtGui.QLabel()
        layout.addWidget(self.focus_value, 1, 1)

        self.exposure_value = QtGui.QLabel()
        layout.addWidget(self.exposure_value, 2, 1)

        multiwidget.setLayout(layout)
        self.setWidget(multiwidget)

        self.update_focus(current_focus)
        self.update_exposure(exposure)

    def update_filename(self, filename):
        filename = (filename.split('/')[-1]).split('f')[0][:-1]
        self.filename_value.setText(str(filename))

    def update_focus(self, focus):
        self.focus_value.setText(str(focus))

    def update_exposure(self, exposure):
        self.exposure_value.setText(str(exposure))


if __name__ == "__main__":
    gw = GUIWrapper(proxy=True)
    gw.window.show()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
