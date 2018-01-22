from matplotlib import pyplot as plt
from matplotlib import style
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

class LogViewer():
    def __init__(self):
        pass

    def open_file(self):
        fname = QtGui.QFileDialog.getOpenFileName()
        if(fname[0] != ''):
            return fname[0]
        return None

    def do_log(self,filename):
        x,y = np.loadtxt(filename,unpack = True, delimiter=',', skiprows=1)

        try:
            win = pg.GraphicsWindow(title="PPK Log")
            win.resize(1000,600)
            win.setWindowTitle('PPK Log viewer')

            # Enable antialiasing for prettier plots
            pg.setConfigOptions(antialias=True)

            p1 = win.addPlot(title="Logged data")

            p1.setLabel('left', 'Current', 'A')
            p1.setLabel('bottom', 'Time', 's')
            p1.showGrid(x=True, y=True)

            avg_curve = p1.plot(x, y)
        except:
            print("Failed to open the log, maybe the format is wrong.")

if __name__ == '__main__':
    import sys
    lv = LogViewer()
    app = QtGui.QApplication([])
    logfile = lv.open_file()
    lv.do_log(logfile)

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
