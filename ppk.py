import platform
if(platform.architecture()[0] != "32bit" and platform.system() == "Windows"):
    print("Wrong Python architecture, please install 32bit version of Python")
    eval(input("Press any key to exit..."))
    exit()
import pynrfjprog
import libs.rtt as rtt
import sys
import PyQt5 as Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
# from ui import ppk_ui
from ui.ppk_plotter import ppk_plotter
import numpy as np
# from ui.ppk_plotter import PlotData
import time


VERSION = "1.1.0"
FIRMWARE = ".\ppk_110.hex"
GLOBAL_OFFSET = 0.0e-6

sd_versions = ['130', '132', '212', '332', '110', '210', '310']
# Start Qt event loop unless running in interactive mode or using pyside.

app = pg.QtGui.QApplication([])

if __name__ == '__main__':
    print("Power Profiler Kit initializing...")
    plotter = ppk_plotter()

    ''' Create a temporary qapp for showing post setup error messages '''
    tempapp = QtGui.QApplication(sys.argv)
    nonwindow = QtGui.QWidget()

    ''' Check that packages are up to date '''
    print("\r\nPython version in use: %d.%d.%d\r\n" % (sys.version_info[0], sys.version_info[1], sys.version_info[2]))
    print("Checking installed packages")
    print(("pyqtgraph:\t %s" % pg.__version__))
    print(("numpy:\t\t %s" % np.__version__))
    print(("pynrfjprog:\t %s" % pynrfjprog.__version__))

    ''' Connect and read all initialization data '''

    try:
        rtt = rtt.rtt(plotter.rtt_handler)
    except Exception as e:
        print("Unable to connect to the PPK, check debugger connection and make sure the ppk is flashed.")
        print((str(e)))
        ret = QtGui.QMessageBox.critical(None,
                                         "Unable to connect to the PPK",
                                         "No response from the PPK. \
                                         \r\nCheck power, debugger connection and make sure the \
                                         \r\nfirmware is flashed on the PPK.",
                                         QtGui.QMessageBox.Ok,
                                         QtGui.QMessageBox.NoButton)
        exit()

    try:
        supported_fw = ['1.0.0', 'ED R1', '1.1.0']
        data = rtt.nrfjprog.rtt_read(0, 200)
        version = data[8:13]
        print(("FW version:\t %s" % version))
        if(version != VERSION):
            print(("Wrong firmware on board, please flash to v%s" % VERSION))
            # ED R1 is what is in the version place for the older board,
            # let's just pretend it says 1.0.0 :)
            if(version == "ED R1"):
                version = "1.0.0"
            flashbox = QtGui.QMessageBox()
            flashbox.setWindowTitle("Wrong firmware version")
            flashbox.setWindowIcon(QtGui.QIcon('images\icon.ico'))
            flashButton = flashbox.addButton("Flash new version", QtGui.QMessageBox.ActionRole)
            flashbox.addButton(QtGui.QMessageBox.Ignore)
            if(version not in supported_fw):
                print("Couldn't find any valid PPK firmware on board")
                flashbox.setText("<b>No PPK firmware found on board!</b><br><br>Are your sure you want to flash<br>PPK firmware to the connected board?")
            else:
                flashbox.setText("Please flash PPK with version %s.\r\nCurrent version on board is %s" % (VERSION, version))
            ret = flashbox.exec_()
            if(flashbox.clickedButton() == flashButton):
                print(("Upgrading to %s..." % VERSION))
                try:
                    rtt.nrfjprog.erase_all()
                except Exception as e:
                    print((str(e)))
                    print ("Failed to erase device")
                result = rtt.flash_application(FIRMWARE)
                if(type(result) == str):
                    print(result)
                elif(type(result) == bool):
                    try:
                        print ("Successfully upgraded ppk, resetting")
                        time.sleep(0.5)
                        rtt.nrfjprog.sys_reset()
                        time.sleep(0.5)
                        rtt.nrfjprog.go()
                        time.sleep(0.5)
                        print ("Reset done")
                    except Exception as e:
                        print((str(e)))
                        ret = QtGui.QMessageBox.critical(None,
                                                         "Failed to reset",
                                                         "PPK was flashed successfully but the board did not reset. \
                                                         \r\nRestart the software to continue using the upgraded board.",
                                                         QtGui.QMessageBox.Ok,
                                                         QtGui.QMessageBox.NoButton)
                        exit()

            else:
                print ("Ignoring")

        prod_data = data.split("USER SET ")[0]
        plotter.plotdata.MEAS_RES_LO  = float(prod_data.split("R1:")[1].split(" R2")[0])
        plotter.plotdata.MEAS_RES_MID = float(prod_data.split("R2:")[1].split(" R3")[0])
        plotter.plotdata.MEAS_RES_HI = float(prod_data.split("R3:")[1].split("Board ID ")[0])
        plotter.plotdata.board_id = str(prod_data.split("Board ID ")[1].split("Refs")[0])
        plotter.plotdata.CAL_MEAS_RES_LO = plotter.plotdata.MEAS_RES_LO
        plotter.plotdata.CAL_MEAS_RES_MID = plotter.plotdata.MEAS_RES_MID
        plotter.plotdata.CAL_MEAS_RES_HI = plotter.plotdata.MEAS_RES_HI
    except Exception as e:
        sd_version = rtt.nrfjprog.read_u32(int(0x3010))
        if str(sd_version) in sd_versions:
            print(("Found SoftDevice s%s on board" % (str(sd_version))))
            print("Initialization failed, wrong board connected?")
            print((str(e)))
            ret = QtGui.QMessageBox.critical(None,
                                             "Initialization failed",
                                             "Found SoftDevice on board. \
                                             \r\n\r\nA SoftDevice should not be present on the PPK.\r\nCorrect connection or flash the PPK.",
                                             QtGui.QMessageBox.Ok,
                                             QtGui.QMessageBox.NoButton)
            exit()
        else:

            print("Initialization failed, could not read calibration values.")
            ret = QtGui.QMessageBox.critical(None,
                                             "Initialization failed",
                                             "Could not read calibration values. \
                                             \r\nCheck power, debugger connection and make sure \r\nthe firmware is flashed on the PPK.",
                                             QtGui.QMessageBox.Ok,
                                             QtGui.QMessageBox.NoButton)
            exit()

    if('USER SET' in data):
        user_data = data.split("USER SET ")[1].split("Refs")[0]
        plotter.plotdata.MEAS_RES_LO  = float(user_data.split("R1:")[1].split(" R2")[0])
        plotter.plotdata.MEAS_RES_MID = float(user_data.split("R2:")[1].split(" R3")[0])
        plotter.plotdata.MEAS_RES_HI = float(user_data.split("R3:")[1].split("Board ID ")[0])

    try:
        refs_data = data.split("Refs ")[1]
    except:
        ret = QtGui.QMessageBox.critical(None,
                                         "Corrupted data",
                                         "Corrupt data received from PPK. \
                                         \r\nReflash PPK firmware.",
                                         QtGui.QMessageBox.Ok,
                                         QtGui.QMessageBox.Close)
        print("Corrupted data received from PPK, please reflash the PPK.")
        print((str(e)))
        exit()
    plotter.plotdata.vref_hi = refs_data.split("HI: ")[1].split(" LO")[0]
    plotter.plotdata.vref_lo = refs_data.split("LO: ")[1]
    plotter.plotdata.vdd     = refs_data.split("VDD: ")[1].split(" HI")[0]

    tempapp.exit()
    tempapp = None
    nonwindow = None
    plotter.setup_graphics()
    plotter.set_rtt_instance(rtt)
    plotter.start()
    #plotter.start_log_thread()
    print("Power Profiler Kit running!")

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
