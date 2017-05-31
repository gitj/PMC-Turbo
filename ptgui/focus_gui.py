import sys
import Pyro4
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

pg.setConfigOptions(imageAxisOrder='row-major')
import pgview

root_path = '/'
proxy = Pyro4.Proxy('PYRO:controller@0.0.0.0:50001')


def toolbtnpressed(a):
    print a.text()

    if a.text() == 'Increase_Focus':
        # proxy.increase_focus
        # for example
        proxy.send_arbitrary_camera_command("EFLensFocus", argument_string)


def increase_focus_button_press():
    # focus_step = self.current_focus + self.focus_increment
    # try
    # proxy.set_focus(self, focus_step)
    # self.current_focus =
    # except
    #
    #
    print 'Increase focus'


def decrease_focus_button_press():
    # focus_step = self.current_focus - self.focus_increment
    # try
    # proxy.set_focus(self, focus_step)
    # self.current_focus =
    # except
    #
    #
    print 'Decrease focus'


def increase_exposure_button_press():
    # exposure_time_us = self.current_exposure_time_us + self.exposure_increment
    # try
    # proxy.set_exposure(self, focus_step)
    # self.current_exposure =
    # except
    #
    #
    print 'Increase exposure'


def decrease_exposure_button_press():
    # exposure_time_us = self.current_exposure_time_us - self.exposure_increment
    # try
    # proxy.set_exposure(self, focus_step)
    # self.current_exposure =
    # except
    #
    #
    print 'Decrease exposure'


def update(window):
    # update both image viewer and realtimevalues.
    return


class MyToolBar(QtGui.QToolBar):
    def __init__(self, *args, **kwargs):
        super(MyToolBar, self).__init__(*args, **kwargs)
        increase_focus = QtGui.QAction("Increase Focus", win)
        decrease_focus = QtGui.QAction("Decrease Focus", win)
        increase_exposure_time = QtGui.QAction("Increase Exposure Time", win)
        decrease_exposure_time = QtGui.QAction("Decrease Exposure Time", win)

        increase_focus.triggered.connect(increase_focus_button_press)
        decrease_focus.triggered.connect(decrease_focus_button_press)
        increase_exposure_time.triggered.connect(increase_exposure_button_press)
        decrease_exposure_time.triggered.connect(decrease_exposure_button_press)

        self.addAction(increase_focus)
        self.addAction(decrease_focus)
        self.addAction(increase_exposure_time)
        self.addAction(decrease_exposure_time)

        # self.actionTriggered[QtGui.QAction].connect(toolbtnpressed)
        #self.actionTriggered[increase_focus].connect(increase_focus_button_press)


class RealTimeValues(QtGui.QDockWidget):
    def __init__(self, *args, **kwargs):
        # super(RealTimeValues,self).__init__("Status", *args,**kwargs)
        super(RealTimeValues, self).__init__(*args, **kwargs)
        multiwidget = QtGui.QWidget()
        layout = QtGui.QGridLayout()

        filename_title = QtGui.QLabel()
        layout.addWidget(filename_title, 0, 0)
        filename_title.setText('Filename:')

        filename_value = QtGui.QLabel()
        layout.addWidget(filename_value, 0, 1)
        filename_value.setText('this_is_the_filename')

        focus_title = QtGui.QLabel()
        layout.addWidget(focus_title, 1, 0)
        focus_title.setText('Focus:')

        exposure_title = QtGui.QLabel()
        layout.addWidget(exposure_title, 2, 0)
        exposure_title.setText('Exposure: ')

        focus_value = QtGui.QLabel()
        layout.addWidget(focus_value, 1, 1)
        focus_value.setText('4000')

        exposure_value = QtGui.QLabel()
        layout.addWidget(exposure_value, 2, 1)
        exposure_value.setText('%d ms' % 100)

        multiwidget.setLayout(layout)
        self.setWidget(multiwidget)

    def update_value(self, label_widget, new_text):
        label_widget.setText(new_text)

    def update(self):
        return


if __name__ == "__main__":
    app = QtGui.QApplication([])
    # proxy = Pyro4.Proxy('')
    win = QtGui.QMainWindow()
    win.resize(800, 800)
    imv = pgview.MyImageView()
    win.setCentralWidget(imv)

    tb = MyToolBar()
    win.addToolBar(QtCore.Qt.RightToolBarArea, tb)

    mywidget = RealTimeValues()
    win.addDockWidget(QtCore.Qt.TopDockWidgetArea, mywidget)

    win.show()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
