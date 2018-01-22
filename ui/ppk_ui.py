import PyQt5 as Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

class ShowInfoWindow(QtCore.QThread):
    show_calib_signal = QtCore.Signal(str, str)

    def __init__(self, title="PPK", info="Calibrating..."):
        QtCore.QThread.__init__(self)
        self.title = title
        self.info = info

    def __del__(self):
        self.wait()

    def run(self):
        self.show_calib_signal.emit(self.title, self.info)


class CloseInfoWindow(QtCore.QThread):
    close_calib_signal = QtCore.Signal()

    def __init__(self):
        QtCore.QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        self.close_calib_signal.emit()
