import time
from pyqtgraph.Qt import QtCore,QtGui
from pmc_turbo.ground.lowrate_monitor import LowrateMonitor
from pmc_turbo.communication.short_status import ShortStatusLeader
import logging
logger = logging.getLogger(__name__)

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
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(1000)
    widget.show()
    app.exec_()