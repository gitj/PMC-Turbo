import collections
import time
from pyqtgraph.Qt import QtCore,QtGui
from pmc_turbo.ground.lowrate_monitor import LowrateMonitor
from pmc_turbo.communication.short_status import (ShortStatusLeader, one_byte_summary_bit_definitions,
                                                  decode_one_byte_summary)
import logging
logger = logging.getLogger(__name__)

class SingleByteSummaryWidget(QtGui.QWidget):
    def __init__(self,parent=None):
        super(SingleByteSummaryWidget,self).__init__(parent=parent)
        self.labels = collections.OrderedDict([(text, QtGui.QLabel(text)) for text in one_byte_summary_bit_definitions])
        self.top_layout = QtGui.QGridLayout()
        self.setLayout(self.top_layout)
        for k,label in enumerate(self.labels.values()):
            self.top_layout.addWidget(label,k+1,0)
        self.checks = [collections.OrderedDict([(text, QtGui.QCheckBox()) for text in one_byte_summary_bit_definitions])
                       for k in range(8)]
        for k in range(8):
            self.top_layout.addWidget(QtGui.QLabel("%d" %k), 0,k+1)
            for row,check in enumerate(self.checks[k].values()):
                self.top_layout.addWidget(check,row+1,k+1)
                check.setEnabled(False)

    def set_values(self,values):
        for camera_id in range(8):
            bit_values = decode_one_byte_summary(values['status_byte_camera_%d' % camera_id])
            for name,bit in bit_values.items():
                if bit:
                    self.checks[camera_id][name].setCheckState(QtCore.Qt.Checked)
                else:
                    self.checks[camera_id][name].setCheckState(QtCore.Qt.Unchecked)


class LowrateMonitorWidget(QtGui.QLabel):
    def __init__(self,lowrate_monitor,message_id,num_columns = 3, parent=None):
        super(LowrateMonitorWidget,self).__init__(parent)
        self.lowrate_monitor = lowrate_monitor
        self.message_id = message_id
        self.num_columns=num_columns
        self.setFrameStyle(QtGui.QFrame.Box)
        self.update_display()
    def update_display(self):
        #self.lowrate_monitor.update()
        try:
            values = self.lowrate_monitor.latest(self.message_id)
        except KeyError:
            logger.debug("No info for %d" % self.message_id)
            return
        if (time.time() - values['timestamp']) < 60:
            logger.debug("data for %d is fresh" % self.message_id)
            result = '<b>'
            end = '</b>'
        else:
            result = ''
            end = ''
        result = result + '<table cellspacing=5>'
        end =  '</table>' +end
        items = values.items()
        while items:
            row = ''.join([('<td>%s</td><td align="right">%s</td>' % item) for item in items[:self.num_columns]])
            row = '<tr>'+ row + '</tr>'
            result = result + row
            items = items[self.num_columns:]
        self.setText(result+end)
        font = self.font()
        font.setPointSize(6)
        self.setFont(font)
        logger.debug("Updated %d" % self.message_id)

if __name__ == "__main__":
    from pmc_turbo.utils import log
    log.setup_stream_handler(log.logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(log.default_handler)
    app  = QtGui.QApplication([])
    widget = QtGui.QWidget()
    layout = QtGui.QGridLayout()
    widget.setLayout(layout)
    lrm = LowrateMonitor()
    leader = LowrateMonitorWidget(lrm,ShortStatusLeader.LEADER_MESSAGE_ID,parent=widget)
    layout.addWidget(leader,0,0)
    sbs = SingleByteSummaryWidget()
    layout.addWidget(sbs,0,1)
    widgets = [leader]
    for row in range(4):
        for column in range(2):
            if row*2+column < 8:
                w = LowrateMonitorWidget(lrm,row*2+column,parent=widget)
                layout.addWidget(w,row+1,column)
                widgets.append(w)
    def update():
        lrm.update()
        for w in widgets:
            w.update_display()
        try:
            sbs.set_values(lrm.latest(ShortStatusLeader.LEADER_MESSAGE_ID))
        except KeyError:
            pass
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(1000)
    widget.show()
    app.exec_()