from pyqtgraph.Qt import QtCore, QtGui
from libs.label import EditableLabel
from libs.rtt import RTT_COMMANDS
import sys
import numpy as np
import struct
from ui.ppk_ui import ShowInfoWindow
from ui.ppk_ui import CloseInfoWindow
from ui.log_viewer import LogViewer
import webbrowser
import warnings

str_uA = u'[\u03bcA]'
str_uC = u'[\u03bcC]'
str_delta = u'\u0394'


def rms_flat(a):
    """
    Return the root mean square of all the elements of *a*, flattened out.
    https://gist.github.com/endolith/1257010
    """
    return np.sqrt(np.mean(np.absolute(a)**2))


class SettingsMainWindow(QtGui.QMainWindow):
    ''' Custom class to overrride closevent '''
    def __init__(self, settingsgui):
        QtGui.QMainWindow.__init__(self)
        self.settingsw = settingsgui

    def closeEvent(self, event):
        self.settingsw.destroyedEvent()


class SettingsWindow(QtCore.QObject):
    def __init__(self, plotdata, plot_window):
        warnings.filterwarnings('ignore')
        QtCore.QObject.__init__(self)
        self.rtt = None
        self.rtt_handler = None
        self.curs_avg_enabled = True
        self.curs_trig_enabled = True
        self.external_trig_enabled = False
        self.plot_window = plot_window
        self.m_vdd = 3000
        self.plotdata = plotdata

        # Settings main window
        self.settings_mainw = SettingsMainWindow(self)

        self.tabWidget = QtGui.QTabWidget(self.settings_mainw)
        self.tabWidget.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.settings_mainw.setCentralWidget(self.tabWidget)

        self.tabMain = QtGui.QWidget()
        self.tabConfig = QtGui.QWidget()

        self.tabWidget.addTab(self.tabMain, "")
        self.tabWidget.addTab(self.tabConfig, "")

        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabMain), "Main")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabConfig), "Advanced")

        ico = QtGui.QIcon('images\icon.ico')
        self.settings_mainw.setWindowIcon(ico)

        self.settings_mainw.move(50, 50)

        self.msgBox = QtGui.QMessageBox()
        self.msgBox.setWindowTitle("Information")
        self.msgBox.setIconPixmap(QtGui.QPixmap('images\icon.ico'))

        self.settings_mainw.setWindowTitle('Settings - Power Profiler Kit')
        self.settings_mainw.setMinimumWidth(400)
        self.settings_mainw.setMaximumWidth(400)

        self.tabMain.setFixedWidth(400)

        self.main_settings_layout = QtGui.QVBoxLayout()  # Settings layout
        self.config_settings_layout = QtGui.QVBoxLayout()  # Settings layout

        self.main_settings_layout.addWidget(self.logo_label())
        self.main_settings_layout.addLayout(self.average_settings())
        self.main_settings_layout.addWidget(self.trigger_settings())
        self.main_settings_layout.addWidget(self.cursor_settings())

        self.config_settings_layout.addLayout(self.vrefs())
        self.config_settings_layout.addWidget(self.calibration_resistors())
        self.config_settings_layout.addWidget(self.edit_colors_button())
        self.config_settings_layout.addWidget(self.edit_bg_button())
        self.config_settings_layout.addSpacing(250)

        self.settings_mainw.setStatusBar(self.statusbar())

        self.tabMain.setLayout(self.main_settings_layout)
        self.tabConfig.setLayout(self.config_settings_layout)

        self.settings_mainw.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.settings_mainw.destroyed.connect(self.destroyedEvent)
        self.create_menu_bar()
        self.settings_mainw.show()

    def write_new_res(self, r1, r2, r3):
        r1_list = []
        r2_list = []
        r3_list = []

        # Pack the floats
        bufr1 = struct.pack('f', r1)
        bufr2 = struct.pack('f', r2)
        bufr3 = struct.pack('f', r3)

        # PPK receives byte packages, put them in a list
        for b in bufr1:
            r1_list.append(b)
        for b in bufr2:
            r2_list.append(b)
        for b in bufr3:
            r3_list.append(b)

        # Write the floats to PPK
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_SET_RES_USER,
                                ord(r1_list[0]), ord(r1_list[1]), ord(r1_list[2]), ord(r1_list[3]),
                                ord(r2_list[0]), ord(r2_list[1]), ord(r2_list[2]), ord(r2_list[3]),
                                ord(r3_list[0]), ord(r3_list[1]), ord(r3_list[2]), ord(r3_list[3])
                                ])

    def destroyedEvent(self):
        self.rtt.alive = False
        try:
            QtGui.QApplication.quit()
        except:
            pass
        QtGui.QApplication.quit()

    def logo_label(self):
        logo = QtGui.QPixmap('images\\NordicS_small.png')
        image_label = QtGui.QLabel()
        image_label.setPixmap(logo)
        return image_label

    def set_rtt_instance(self, rtt):
        self.rtt = rtt

    def create_menu_bar(self):

        self.settings_mainw.fileMenu = self.settings_mainw.menuBar().addMenu("&File")
        self.settings_mainw.helpMenu = self.settings_mainw.menuBar().addMenu("&Help")
        self.settings_mainw.LogMenu = self.settings_mainw.menuBar().addMenu("&Logging")
        self.settings_mainw.menuBar().setNativeMenuBar(False)

        ''' Add items to File menu '''
        exitAction = QtGui.QAction("Exit", self, shortcut="Ctrl+Q",
                                   triggered=self.destroyedEvent)

        self.settings_mainw.fileMenu.addAction(exitAction)

        ''' Add items to Help menu '''
        userGuideAction = QtGui.QAction("Open user guide...", self, shortcut="Ctrl+U",
                                        triggered=self.menuActionUserGuide)

        aboutAction = QtGui.QAction("About", self,
                                    triggered=self.menuActionAbout)

        aboutQtAction = QtGui.QAction("About &Qt", self)
        aboutQtAction.triggered.connect(QtGui.qApp.aboutQt)

        self.settings_mainw.helpMenu.addAction(userGuideAction)
        self.settings_mainw.helpMenu.addAction(aboutAction)
        self.settings_mainw.helpMenu.addAction(aboutQtAction)

        ''' Add items to Logging menu '''
        self.loggingAction = QtGui.QAction("Start logging", self, shortcut="Ctrl+L",
                                           triggered=self.startLog)
        self.stopLogAction = QtGui.QAction("Stop log", self, shortcut="Ctrl+V",
                                           triggered=self.stopLog)
        self.stopLogAction.setDisabled(True)
        viewLogAction = QtGui.QAction("View log", self, shortcut="Ctrl+V",
                                      triggered=self.viewLog)

        self.settings_mainw.LogMenu.addAction(self.loggingAction)
        self.settings_mainw.LogMenu.addAction(self.stopLogAction)
        self.settings_mainw.LogMenu.addAction(viewLogAction)

    def viewLog(self):
        lv = LogViewer()
        lfile = lv.open_file()
        if(lfile is not None):
            self.avg_run_button.setText('Start')
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_STOP])
            self.trigger_start_button.setText('Start')
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TRIG_STOP])
            lv.do_log(lfile)

    def stopLog(self):
        self.plot_window.started_log = False
        self.plot_window.update_log = False
        self.plot_window.enable_log = False
        self.plot_window.log_stopped = True
        self.loggingAction.setDisabled(False)
        self.stopLogAction.setDisabled(True)

    def startLog(self):
        self.stopLog()
        self.stopLogAction.setDisabled(False)
        filename = QtGui.QFileDialog.getSaveFileName(None, 'Dialog Title')
        try:
            self.plot_window.logfile_name = filename[0]
            self.plot_window.enable_log = True
            self.plot_window.log_stopped = False
            print("Started logging to %s" % filename[0])
            self.loggingAction.setDisabled(True)
            ret = QtGui.QMessageBox.information(None,
                                                "Logging started!",
                                                "Logging average data to %s started" % filename[0],
                                                QtGui.QMessageBox.NoButton)
        except Exception as e:
            print(str(e))
            if ("Errno 13" in str(e)):
                print(("Unable to write to logfile '" + filename[0] + "', write protected?"))
                ret = QtGui.QMessageBox.warning(None,
                                                "Unable to write to logfile!",
                                                "Seems like %s is write protected.\
                                                \r\nMS Excel does this, but notepad++ does not, so make sure \
                                                \r\nto close any program that may have locked the file." % filename[0],
                                                QtGui.QMessageBox.Ok,
                                                QtGui.QMessageBox.NoButton)

    def menuActionExit(self):
        print("pressed exit")

    def menuActionUserGuide(self):
        new = 2  # Open in new tab if possible
        url = "http://infocenter.nordicsemi.com/topic/com.nordic.infocenter.tools/dita/tools/power_profiler_kit/PPK_user_guide_Intro.html"
        webbrowser.open(url, new)

    def menuActionAbout(self):
        QtGui.QMessageBox.about(self.settings_mainw, "About PPK v 1.0.1",
                                "Power Profiler Kit <b>v1.1.0</b>\n "
                                "<hr>"
                                "Tested with: \
                                <style> \
                                    th, td { \
                                        padding: 0px 10px 0px 0px; \
                                    } \
                                    </style> \
                                <table style=\"width:1000\"> \
                                    <tr> \
                                        <td>Python</td> \
                                        <td>2.7.12 32bit</td> \
                                    </tr> \
                                    <tr> \
                                        <td>pyside</td> \
                                        <td>1.2.4</td> \
                                    </tr> \
                                    <tr> \
                                        <td>pyqtgraph</td> \
                                        <td>0.10.0</td> \
                                    </tr> \
                                    <tr> \
                                        <td>numpy</td> \
                                        <td>1.11.3</td> \
                                    </tr> \
                                    <tr> \
                                        <td>pynrfjprog</td> \
                                        <td>9.1.0</td> \
                                    </tr> \
                                </table> \
                                <p> \
                                    Build date 23.02.2017 \
                                </p>")

    def average_settings(self):
        top_layout              = QtGui.QHBoxLayout()   # Container and dut switch in same layout
        dut_button_layout       = QtGui.QVBoxLayout()
        gb_avg_layout           = QtGui.QHBoxLayout()   # Container
        gb_avg_layout_bottom1   = QtGui.QHBoxLayout()   # next row...
        gb_avg_layout_bottom2   = QtGui.QHBoxLayout()

        # Create items
        self.avg_window_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.avg_window_slider.setTracking = False
        self.avg_window_slider.setMinimum(1)
        self.avg_window_slider.setMaximum(200)    # val*100ms, i.e max = 5000ms = 5s
        self.avg_window_slider.setValue(20)
        self.avg_window_slider.sliderReleased.connect(self.AverageWindowSliderReleased)
        self.avg_window_slider.valueChanged.connect(self.AverageWindowSliderMoved)

        self.avg_interval_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.avg_interval_slider.setTracking = False
        self.avg_interval_slider.setMinimum(1)
        self.avg_interval_slider.setMaximum(1024)  # val*16 i.e max = 8192 samples
        self.avg_interval_slider.setValue(4)
        self.avg_interval_slider.sliderReleased.connect(self.AverageIntervalSliderReleased)
        self.avg_interval_slider.valueChanged.connect(self.AverageIntervalSliderMoved)

        self.avg_window_label = EditableLabel(gb_avg_layout_bottom1, 2)
        self.avg_window_label.setText('2.00 s')
        self.avg_window_label.valueChanged.connect(self.AverageWindowValueChanged)

        self.avg_sample_num_label = EditableLabel(gb_avg_layout_bottom2, 1)
        self.avg_sample_num_label.setText('10')
        # self.avg_sample_num_label.valueChanged.connect(AverageWindowValueChanged)

        self.avg_run_button = QtGui.QPushButton('Stop')
        self.avg_run_button.clicked.connect(self.AvgRunButtonClicked)

        self.dut_power_button = QtGui.QPushButton('DUT Off')
        self.dut_power_button.clicked.connect(self.DUTPowerButtonPressed)

        self.calibration_btn = QtGui.QPushButton('Offset calibration')
        self.calibration_btn.clicked.connect(self.offset_calibration)

        # Set up groupbox with layouts
        gb_avg = QtGui.QGroupBox("Average")
        gb_avg_layout_bottom1.addWidget(QtGui.QLabel('Window:'))
        gb_avg_layout_bottom1.addWidget(self.avg_window_slider)
        gb_avg_layout_bottom1.addWidget(self.avg_window_label)
        gb_avg_layout_bottom1.addWidget(self.avg_run_button)

        gb_avg_layout.addLayout(gb_avg_layout_bottom1)
        gb_avg_layout.addLayout(gb_avg_layout_bottom2)
        gb_avg.setLayout(gb_avg_layout)
        dut_button_layout.addWidget(self.dut_power_button)
        # If you want to clutter the GUI with an offset button as well, uncomment
        # dut_button_layout.addWidget(self.calibration_btn)
        dut_button_layout.addWidget(gb_avg)
        top_layout.addLayout(dut_button_layout)
        # Return the groupbox object
        return top_layout

    def offset_calibration(self):
        self.plot_window.global_offset = 0.0
        self.plot_window.calibrating = True
        self.plot_window.calibrating_done = False

    def trigger_settings(self):
        gb_trigger_layout           = QtGui.QVBoxLayout()   # Container
        gb_trigger_layout_top       = QtGui.QHBoxLayout()   # top row
        gb_trigger_layout_bottom   = QtGui.QHBoxLayout()   # next row
        gb_trigger_layout_bottom1   = QtGui.QHBoxLayout()   # next row
        gb_trigger_layout_bottom2   = QtGui.QHBoxLayout()   # next row
        gb_trigger_layout_bottom3   = QtGui.QHBoxLayout()   # next row

        # Create items
        self.triggerlevel_textbox = QtGui.QLineEdit()
        self.triggerlevel_textbox.returnPressed.connect(self.TriggerLevelPressedReturn)
        self.triggerlevel_textbox.setText(str(self.plotdata.trigger))

        self.trigger_single_button = QtGui.QPushButton('Single')
        self.trigger_single_button.clicked.connect(self.TriggerSingleButtonClicked)

        self.trigger_start_button = QtGui.QPushButton("Stop")
        self.trigger_start_button.clicked.connect(self.TriggerStartButtonClicked)

        self.trigger_window_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.trigger_window_slider.setTracking = False
        self.trigger_window_slider.setMinimum(370)
        self.trigger_window_slider.setMaximum(2048)
        self.trigger_window_slider.setValue(512)
        self.trigger_window_slider.sliderReleased.connect(self.TriggerWindowSliderReleased)
        self.trigger_window_slider.valueChanged.connect(self.TriggerWindowSliderMoved)
        self.trig_window_label = EditableLabel(gb_trigger_layout_bottom, 4)
        self.trig_window_label.setText('6.65 ms')
        self.trig_window_label.valueChanged.connect(self.TriggerWindowValueChanged)
        self.enable_ext_trigg_chkb = QtGui.QCheckBox()

        # Set up groupbox with layouts
        gb_trigger = QtGui.QGroupBox("Trigger")
        gb_trigger_layout_top.addWidget(self.trigger_single_button)
        gb_trigger_layout_top.addWidget(self.trigger_start_button)

        # Add window slider
        gb_trigger_layout_bottom.addWidget(QtGui.QLabel('Window:'))
        gb_trigger_layout_bottom.addWidget(self.trigger_window_slider)
        gb_trigger_layout_bottom.addWidget(self.trig_window_label)

        # Add trigger level box
        gb_trigger_layout_bottom1.addWidget(QtGui.QLabel('Trigger level:'))
        gb_trigger_layout_bottom1.addWidget(self.triggerlevel_textbox)
        gb_trigger_layout_bottom1.addWidget(QtGui.QLabel(str_uA))

        # Add trigger checkbox
        gb_trigger_layout_bottom2.addWidget(QtGui.QLabel('Enable external trigger'))
        gb_trigger_layout_bottom2.addWidget(self.enable_ext_trigg_chkb)
        self.enable_ext_trigg_chkb.setChecked(False)
        self.enable_ext_trigg_chkb.stateChanged.connect(self.external_trig_changed)

        gb_trigger_layout.addLayout(gb_trigger_layout_top)
        gb_trigger_layout.addLayout(gb_trigger_layout_bottom)
        gb_trigger_layout.addLayout(gb_trigger_layout_bottom1)
        gb_trigger_layout.addLayout(gb_trigger_layout_bottom2)
        gb_trigger_layout.addLayout(gb_trigger_layout_bottom3)

        gb_trigger.setLayout(gb_trigger_layout)

        # Return the groupbox object
        return gb_trigger

    def switch_filter_chk_changed(self, state):
        self.switch_filter_enabled = bool(state)

    def MedianFilterChanged(self, val):
        k_val = val + (val + 1)
        self.median_filter_value_label.setText(str(k_val))

    def range_settings(self):
        # Create items
        range_drop_down = QtGui.QComboBox()

        range_drop_down.addItem("15uA")
        range_drop_down.addItem("1.5mA")
        range_drop_down.addItem("150mA")
        range_drop_down.addItem("Auto")
        range_drop_down.setCurrentIndex(3)
        range_drop_down.currentIndexChanged.connect(self.rangeChanged)

        # Set up groupbox with layouts
        gb_range = QtGui.QGroupBox("Range")
        gb_range_layout = QtGui.QVBoxLayout()
        gb_range_layout.addWidget(range_drop_down)
        gb_range.setLayout(gb_range_layout)

        # Return the groupbox object
        return gb_range

    def cursor_settings(self):
        gb_cursors_layout = QtGui.QVBoxLayout()
        curs_avg_box_layout = QtGui.QHBoxLayout()
        curs_avg_box_text_layout = QtGui.QVBoxLayout()
        curs_trig_box_text_layout = QtGui.QVBoxLayout()
        curs_trig_layout = QtGui.QHBoxLayout()

        bold = QtGui.QFont()
        bold.setBold(True)
        gb_cursors = QtGui.QGroupBox("Cursors")
        # gb_cursors.setFont(bold)

        curs_avg_box = QtGui.QGroupBox("Average window")
        self.curs_avg_enabled_checkb = QtGui.QCheckBox("Enabled")
        self.curs_avg_enabled_checkb.setChecked(True)
        self.curs_avg_enabled_checkb.stateChanged.connect(self.curs_avg_en_changed)
        self.curs_avg_rms_label = QtGui.QLabel("RMS: <b>0.00</b> [nA]")
        self.curs_avg_avg_label = QtGui.QLabel("AVG: <b>0.00</b> [nA]")
        self.curs_avg_max_label = QtGui.QLabel("MAX: <b>0.00</b> [nA]")
        self.curs_avg_coloumb_label = QtGui.QLabel("Charge: <b>0.00</b> [C]")
        self.curs_avg_cursx_label = QtGui.QLabel("X1: <b>1.00</b> [s] X2: <b>1.20</b> [s]")
        self.curs_avg_cursy_label = QtGui.QLabel("Y1: <b>0.00</b> [nA] Y2: <b>0.00</b> [nA]")
        self.curs_avg_cursy_label.setFixedWidth(180)
        self.curs_avg_delta_label = QtGui.QLabel("Cursor %s: <b>400.00</b> [ms]" % (str_delta))

        curs_avg_box_layout.addWidget(self.curs_avg_enabled_checkb)
        curs_avg_box_text_layout.addWidget(self.curs_avg_rms_label)
        curs_avg_box_text_layout.addWidget(self.curs_avg_avg_label)
        curs_avg_box_text_layout.addWidget(self.curs_avg_max_label)
        curs_avg_box_text_layout.addWidget(self.curs_avg_coloumb_label)
        curs_avg_box_text_layout.addWidget(self.curs_avg_cursx_label)
        curs_avg_box_text_layout.addWidget(self.curs_avg_cursy_label)

        curs_avg_box_text_layout.addWidget(self.curs_avg_delta_label)
        curs_avg_box_layout.addLayout(curs_avg_box_text_layout)
        curs_avg_box.setLayout(curs_avg_box_layout)

        curs_trig_box = QtGui.QGroupBox("Trigger window")
        self.curs_trig_enabled_checkb = QtGui.QCheckBox("Enabled")
        self.curs_trig_enabled_checkb.stateChanged.connect(self.curs_trig_en_changed)
        self.curs_trig_enabled_checkb.setChecked(True)
        self.curs_trig_rms_label = QtGui.QLabel("RMS: <b>0.00</b> [nA]")
        self.curs_trig_max_label = QtGui.QLabel("MAX: <b>0.00</b> [nA]")
        self.curs_trig_coloumb_label = QtGui.QLabel("Charge: <b>0.00</b> [C]")
        self.curs_trig_avg_label = QtGui.QLabel("AVG: <b>0.00</b> [nA]")
        self.curs_trig_cursx_label = QtGui.QLabel("X1: <b>5.00</b> [ms] X2: <b>6.00</b> [ms]")
        self.curs_trig_cursy_label = QtGui.QLabel("Y1: <b>0.00</b> [nA] Y2: <b>0.00</b> [nA]")
        self.curs_trig_cursy_label.setFixedWidth(180)
        self.curs_trig_delta_label = QtGui.QLabel("Cursor %s: <b>3.00</b> [ms]" % (str_delta))

        curs_trig_layout.addWidget(self.curs_trig_enabled_checkb)
        curs_trig_box_text_layout.addWidget(self.curs_trig_rms_label)

        curs_trig_box_text_layout.addWidget(self.curs_trig_avg_label)
        curs_trig_box_text_layout.addWidget(self.curs_trig_max_label)
        curs_trig_box_text_layout.addWidget(self.curs_trig_coloumb_label)
        curs_trig_box_text_layout.addWidget(self.curs_trig_cursx_label)
        curs_trig_box_text_layout.addWidget(self.curs_trig_cursy_label)

        curs_trig_box_text_layout.addWidget(self.curs_trig_delta_label)
        curs_trig_layout.addLayout(curs_trig_box_text_layout)
        curs_trig_box.setLayout(curs_trig_layout)

        gb_cursors_layout.addWidget(curs_avg_box)
        gb_cursors_layout.addWidget(curs_trig_box)
        gb_cursors.setLayout(gb_cursors_layout)

        return gb_cursors

    def statusbar(self):
        # Create label
        self.statusbarLabel = QtGui.QLabel()
        self.statusbarLabel.setText("<b>max:</b> 0.00 <b>min:</b> 0.00 <b>rms:</b> 0.00 <b>avg:</b> 0.00")

        # Create the statusbar
        statusBar = QtGui.QStatusBar(self.settings_mainw)
        statusBar.addWidget(self.statusbarLabel)

        # Return the statusbar
        return statusBar

    def edit_colors_button(self):
        btn = QtGui.QPushButton("Change graph color")
        btn.clicked.connect(self.plot_window.edit_colors)
        return btn

    def edit_bg_button(self):
        btn = QtGui.QPushButton("Change background color")
        btn.clicked.connect(self.plot_window.edit_bg)
        return btn

    def calibrate_offset_button(self):
        btn = QtGui.QPushButton("Calibrate")
        btn.clicked.connect(self.calibrate_button_clicked)
        return btn

    def vrefs(self):
        adjustments_layout = QtGui.QVBoxLayout()    # main layout

        vdd_layout = QtGui.QHBoxLayout()               # Layout for vdd slider
        vdd_gb = QtGui.QGroupBox("Voltage regulator")  # Groupbox for vdd
        vdd_gb.setMaximumHeight(70)

        vref_slider_layout = QtGui.QVBoxLayout()    #
        switches_layout = QtGui.QVBoxLayout()

        vref_on_layout = QtGui.QHBoxLayout()          # sublayout for vrefs
        vref_on_sliders_layout = QtGui.QHBoxLayout()  # For slider and label
        vref_on_labels_layout = QtGui.QVBoxLayout()   # For values

        vref_off_layout = QtGui.QHBoxLayout()          # Sublayout for vrefs off
        reset_sw_points_layout = QtGui.QHBoxLayout()   # Button for resetting switch points
        switch_filter_layout = QtGui.QHBoxLayout()     # For adding switch filter checkbox
        vref_off_sliders_layout = QtGui.QHBoxLayout()  # For slider and label
        vref_off_labels_layout = QtGui.QVBoxLayout()   # For values
        switches_gb = QtGui.QGroupBox("Switching points")

        self.vref_on_label_1 = QtGui.QLabel(str(38) + "m1")
        self.vref_on_label_2 = QtGui.QLabel(str(38) + "m2")

        self.vref_off_label_1 = QtGui.QLabel(str(2.34))
        self.vref_off_label_2 = QtGui.QLabel(str(2.34))
        self.vdd_label = QtGui.QLabel('3000mV')

        self.vref_off_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.vref_off_slider.setMinimum(100)
        self.vref_off_slider.setMaximum(400)
        self.vref_off_slider.setValue(234)
        self.vref_off_slider.setInvertedAppearance(True)
        self.vref_off_slider.sliderReleased.connect(self.vref_off_set)
        self.vref_off_slider.valueChanged.connect(self.vref_off_changed)

        self.vref_on_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.vref_on_slider.setMinimum(38)
        self.vref_on_slider.setMaximum(175)
        self.vref_on_slider.setValue(40)
        self.vref_on_slider.sliderReleased.connect(self.vref_on_set)
        self.vref_on_slider.valueChanged.connect(self.vref_on_changed)

        self.vdd_slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.vdd_slider.setMinimum(1850)
        self.vdd_slider.setMaximum(3600)
        self.vdd_slider.setValue(3000)
        self.vdd_slider.sliderReleased.connect(self.vdd_set)
        self.vdd_slider.valueChanged.connect(self.vdd_changed)

        vdd_layout.addWidget(QtGui.QLabel("VDD:"))
        vdd_layout.addWidget(self.vdd_slider)
        vdd_layout.addWidget(self.vdd_label)

        vref_on_sliders_layout.addWidget(QtGui.QLabel("Switch up  "))
        vref_on_sliders_layout.addWidget(self.vref_on_slider)

        vref_on_labels_layout.addWidget(self.vref_on_label_2)
        vref_on_labels_layout.addSpacing(5)
        vref_on_labels_layout.addWidget(self.vref_on_label_1)

        vref_on_layout.addLayout(vref_on_sliders_layout)
        vref_on_layout.addLayout(vref_on_labels_layout)

        vref_off_sliders_layout.addWidget(QtGui.QLabel("Switch down"))
        vref_off_sliders_layout.addWidget(self.vref_off_slider)

        vref_off_labels_layout.addWidget(self.vref_off_label_1)
        vref_off_labels_layout.addSpacing(5)
        vref_off_labels_layout.addWidget(self.vref_off_label_2)

        vref_off_layout.addLayout(vref_off_sliders_layout)
        vref_off_layout.addLayout(vref_off_labels_layout)

        # Add spike filtering
        self.enable_switch_filter_chkb = QtGui.QCheckBox()
        self.enable_switch_filter_chkb.setChecked(True)
        self.enable_switch_filter_chkb.stateChanged.connect(self.switch_filter_chk_changed)
        self.enable_switch_filter_chkb.setToolTip("When this is turned on, the software will filter\r\n"
                                                  "data directly after an automatic range switch.\r\n"
                                                  "This will help against unwanted spikes due to \r\n"
                                                  "rapid switching, but may also remove short\r\n"
                                                  "current spikes that might be of significance.")
        self.switch_filter_enabled = True
        switch_filter_layout.addWidget(QtGui.QLabel('Enable switch filter'))
        switch_filter_layout.addWidget(self.enable_switch_filter_chkb)

        reset_sw_button = QtGui.QPushButton("Reset switching points")
        reset_sw_button.setToolTip("Resets switching points to what was set at start-up")
        reset_sw_button.clicked.connect(self.reset_vrefs)
        reset_sw_points_layout.addWidget(reset_sw_button)

        switches_layout.addLayout(vref_on_layout)
        switches_layout.addSpacing(10)
        switches_layout.addLayout(vref_off_layout)
        switches_layout.addLayout(switch_filter_layout)
        switches_layout.addLayout(reset_sw_points_layout)
        vref_slider_layout.addLayout(vdd_layout)

        vdd_gb.setLayout(vref_slider_layout)
        switches_gb.setLayout(switches_layout)

        adjustments_layout.addWidget(vdd_gb)
        adjustments_layout.addWidget(switches_gb)

        return adjustments_layout

    def calibration_resistors(self):
        cal_res_gb = QtGui.QGroupBox("Resistor calibration")
        cal_res_layout = QtGui.QHBoxLayout()
        self.r_high_tb = QtGui.QLineEdit()
        self.r_mid_tb = QtGui.QLineEdit()
        self.r_lo_tb = QtGui.QLineEdit()
        self.cal_update_button = QtGui.QPushButton('Update')
        self.cal_reset_button = QtGui.QPushButton('Reset')
        self.cal_reset_button.setStatusTip("Reset to production values")

        self.r_high_tb.setStatusTip("Change to calibrate for high currents, lower value = higher result")
        self.r_mid_tb.setStatusTip("Change to calibrate for medium currents, lower value = higher result")
        self.r_lo_tb.setStatusTip("Change to calibrate for low currents, lower value = higher result")

        self.r_high_tb.returnPressed.connect(self.update_cal_res)
        self.r_mid_tb.returnPressed.connect(self.update_cal_res)
        self.r_lo_tb.returnPressed.connect(self.update_cal_res)
        self.cal_update_button.clicked.connect(self.update_cal_res)
        self.cal_reset_button.clicked.connect(self.reset_cal_res)

        cal_res_layout.addWidget(QtGui.QLabel("Hi"))
        cal_res_layout.addWidget(self.r_high_tb)
        cal_res_layout.addWidget(QtGui.QLabel("Mid"))
        cal_res_layout.addWidget(self.r_mid_tb)
        cal_res_layout.addWidget(QtGui.QLabel("Lo"))
        cal_res_layout.addWidget(self.r_lo_tb)
        cal_res_layout.addWidget(self.cal_update_button)
        cal_res_layout.addWidget(self.cal_reset_button)

        cal_res_gb.setMaximumHeight(70)
        cal_res_gb.setLayout(cal_res_layout)

        return cal_res_gb

    def update_cal_res(self):
        try:
            self.write_new_res(float(self.r_lo_tb.text()), float(self.r_mid_tb.text()), float(self.r_high_tb.text()))
        except:
            print("Invalid value")
        # print(float(self.r_lo_tb.text()), float(self.r_mid_tb.text()), float(self.r_high_tb.text()))

        self.plotdata.MEAS_RES_HI    = float(self.r_high_tb.text())
        self.plotdata.MEAS_RES_MID   = float(self.r_mid_tb.text())
        self.plotdata.MEAS_RES_LO    = float(self.r_lo_tb.text())

    def reset_cal_res(self):
        self.write_new_res(self.plotdata.CAL_MEAS_RES_LO, self.plotdata.CAL_MEAS_RES_MID, self.plotdata.CAL_MEAS_RES_HI)
        self.r_lo_tb.setText(str(self.plotdata.CAL_MEAS_RES_LO))
        self.r_mid_tb.setText(str(self.plotdata.CAL_MEAS_RES_MID))
        self.r_high_tb.setText(str(self.plotdata.CAL_MEAS_RES_HI))
        self.write_new_res(float(self.r_lo_tb.text()), float(self.r_mid_tb.text()), float(self.r_high_tb.text()))

        self.plotdata.CAL_MEAS_RES_HI    = float(self.r_high_tb.text())
        self.plotdata.CAL_MEAS_RES_MID   = float(self.r_mid_tb.text())
        self.plotdata.CAL_MEAS_RES_LO    = float(self.r_lo_tb.text())

    def calibrate_button_clicked(self):
        pass
        # self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_CALIBRATE_OFFSET])

    def set_trigger(self, trigger):
        high = (trigger >> 16) & 0xFF
        mid = (trigger >> 8) & 0xFF
        low = trigger & 0xFF
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TRIGGER_SET, high, mid, low])

    def set_single(self, trigger):
        high = (trigger >> 16) & 0xFF
        mid = (trigger >> 8) & 0xFF
        low = trigger & 0xFF
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_SINGLE_TRIG, high, mid, low])

    def TriggerStartButtonClicked(self):
        if self.trigger_start_button.text() == 'Start':
            self.TriggerLevelPressedReturn()
        else:
            self.trigger_start_button.setText('Start')
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TRIG_STOP])

    def AvgRunButtonClicked(self):
        if self.avg_run_button.text() == 'Stop':
            self.avg_run_button.setText('Start')
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_STOP])
        elif self.avg_run_button.text() == 'Start':
            self.avg_run_button.setText('Stop')
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RUN])

    def DUTPowerButtonPressed(self):
        if self.dut_power_button.text() == 'DUT Off':
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_DUT, 0])
            self.dut_power_button.setText("DUT On")
        else:
            self.dut_power_button.setText("DUT Off")
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_DUT, 1])

    def TriggerSingleButtonClicked(self):
        self.trigger_start_button.setText('Start')
        self.trigger_start_button.setEnabled(False)
        self.trigger_single_button.setText('Waiting...')
        trigger_level = int(self.triggerlevel_textbox.text())
        self.set_single(trigger_level)
        print(("Single run with trigger: %d%s" % (trigger_level, 'uA')))

    def TriggerLevelPressedReturn(self):
        self.trigger_start_button.setText("Stop")
        try:
            trigger_level = np.uint32(self.triggerlevel_textbox.text())
            self.set_trigger(trigger_level)

            print(("Triggering at %d%s" % (trigger_level, 'uA')))
        except OverflowError:
            print("The trigger value is too large")
        except ValueError:
            print("Invalid trigger value (not an integer)")

    def show_calib_msg_box(self):
        # Start a threaded procedure to avoid invoking in on main thread
        thread = ShowInfoWindow('Information', 'Calibrating...')
        thread.show_calib_signal.connect(self._show_calib_msg_box)
        thread.start()

    def _show_calib_msg_box(self, title, text):
        self.msgBox.setWindowTitle(title)
        self.msgBox.setIconPixmap(QtGui.QPixmap('images\icon.ico'))
        self.msgBox.setText(text)
        self.msgBox.show()

    def close_calib_msg_box(self):
        thread = CloseInfoWindow()
        thread.close_calib_signal.connect(self._close_calib_msg_box)
        thread.start()

    def _close_calib_msg_box(self):
        self.msgBox.close()

    def TriggerWindowSliderReleased(self):
        self.TriggerWindowValueChanged()

    def TriggerWindowValueChanged(self):
        # Format the inserted text to float, cast to int and convert to bytes as required later
        try:
            self.trig_window_val = int(float(self.trig_window_label.text().split('ms')[0].replace(' ', '')) / (self.plotdata.trig_interval * 1000.0) + 1)
            self.trigger_window_slider.setValue(self.trig_window_val)
        except Exception as e:
            print((str(e)))
            print((self.trig_window_label.text()))
            sys.stdout.flush()

        self.plotdata.trig_timewindow = self.plotdata.trig_interval * self.trig_window_val
        self.plotdata.trigger_high = self.trig_window_val >> 8
        self.plotdata.trigger_low = self.trig_window_val & 0xFF
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TRIG_WINDOW_SET, self.plotdata.trigger_high, self.plotdata.trigger_low])

        self.trig_bufsize = int(self.plotdata.trig_timewindow / self.plotdata.trig_interval)
        self.plotdata.trig_x = np.linspace(0.0, self.plotdata.trig_timewindow, self.trig_bufsize)
        self.plotdata.trig_y = np.zeros(self.trig_bufsize, dtype=np.float)

        self.trig_window_label.setText('%5.2f ms' % ((self.plotdata.trig_timewindow * 1000)))
        sys.stdout.flush()

    def TriggerWindowSliderMoved(self, val):
        ''' This method is for previewing the value that will be set upon release '''
        value = self.plotdata.trig_interval * val
        self.trig_window_label.setText('%5.2f ms' % (value * 1000))
        sys.stdout.flush()

    def AverageWindowSliderReleased(self):
        self.AverageWindowValueChanged()

    def AverageWindowValueChanged(self):
        avg_window_val = float(self.avg_window_label.text().split(' ')[0])
        self.plotdata.avg_timewindow = (avg_window_val)
        self.avg_window_slider.setValue(avg_window_val * 10)

        self.plotdata.avg_bufsize  = int(self.plotdata.avg_timewindow / (self.plotdata.avg_interval))
        self.plotdata.avg_x = np.linspace(0.0, self.plotdata.avg_timewindow, self.plotdata.avg_bufsize)
        self.plotdata.avg_y = np.zeros(self.plotdata.avg_bufsize, dtype=np.float)

        self.avg_window_label.setText('%.2f s' % (self.plotdata.avg_timewindow))

    def AverageWindowSliderMoved(self, val):
        ''' This method is for previewing the value that will be set upon release '''
        self.avg_window_label.setText('%.2f s' % (val / 10.0))

    def AverageIntervalSliderReleased(self):
        avg_samples_val = int(self.avg_sample_num_label.text())
        samples_high = (avg_samples_val / 10) >> 8
        samples_low  = (avg_samples_val / 10) & 0xFF
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_AVG_NUM_SET, samples_high, samples_low])

        self.plotdata.avg_interval   = self.plotdata.sample_interval * avg_samples_val
        self.plotdata.avg_bufsize  = int(self.plotdata.avg_timewindow / self.plotdata.avg_interval)
        self.plotdata.avg_x = np.linspace(0.0, self.plotdata.avg_timewindow, self.plotdata.avg_bufsize)
        self.plotdata.avg_y = np.zeros(self.plotdata.avg_bufsize, dtype=np.float)

    def AverageIntervalSliderMoved(self, val):
        self.avg_sample_num_label.setText('%d' % (val * 10))
        self.AverageIntervalSliderReleased()

    def curs_avg_en_changed(self, state):
        self.curs_avg_enabled = bool(state)
        if self.curs_avg_enabled:
            self.plot_window.avg_region.show()
        else:
            self.plot_window.avg_region.hide()

    def curs_trig_en_changed(self, state):
        self.curs_trig_enabled = bool(state)
        if self.curs_trig_enabled:
            self.plot_window.trig_region.show()
        else:
            self.plot_window.trig_region.hide()

    def external_trig_changed(self, state):
        self.external_trig_enabled = bool(state)
        self.trigger_start_button.setText('Start')
        if self.external_trig_enabled:
            self.triggerlevel_textbox.setEnabled(False)
            self.trigger_start_button.setEnabled(False)
            self.trigger_single_button.setEnabled(False)
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TRIG_STOP])
        else:
            self.trigger_single_button.setEnabled(True)
            self.trigger_start_button.setEnabled(True)
            self.triggerlevel_textbox.setEnabled(True)

        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_TOGGLE_EXT_TRIG])

    def rangeChanged(self, val):
        if self.rtt is None:
            return

        if val == 0:
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RANGE_SET, 0])
            print("10uA range")
        elif val == 1:
            print("1mA range")
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RANGE_SET, 1])
        elif val == 2:
            print("100mA range")
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RANGE_SET, 2])
        elif val == 3:
            print("Auto range")
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RANGE_SET, 3])

        sys.stdout.flush()

    def avg_region_changed(self):
        # getRegion returns tuple of min max, not cursor 1 and 2
        i, j = self.plot_window.avg_region.getRegion()
        ival, iunit = self.sec_unit_determine(i)
        jval, junit = self.sec_unit_determine(j)
        deltaval, deltaunit = self.sec_unit_determine(j - i)

        if((ival >= 0) and (jval >= 0)):
            self.curs_avg_cursx_label.setText("X1: <b>%.2f</b> %s X2: <b>%.2f</b> %s" % (ival, iunit, jval, junit))
            self.curs_avg_delta_label.setText("Cursor %s: <b>%.2f</b> %s" % (str_delta, deltaval, deltaunit))

    def trig_region_changed(self):
        i = self.plot_window.trig_region.getRegion()[0]
        j = self.plot_window.trig_region.getRegion()[1]
        ival, iunit = self.sec_unit_determine(i)
        jval, junit = self.sec_unit_determine(j)
        deltaval, deltaunit = self.sec_unit_determine(j - i)

        if((ival >= 0) and (jval >= 0)):
            self.curs_trig_cursx_label.setText("X1: <b>%.2f</b> %s X2: <b>%.2f</b> %s" % (ival, iunit, jval, junit))
            self.curs_trig_delta_label.setText("Cursor %s: <b>%.2f</b> %s" % (str_delta, deltaval, deltaunit))

    def vdd_changed(self):
        ''' Update label, but don't transfer command '''
        self.vdd_label.setText(str(self.vdd_slider.value()) + "mV")

    def vdd_set(self):

        target_vdd = self.vdd_slider.value()

        while (self.m_vdd != target_vdd):
            if (target_vdd > self.m_vdd):
                new = self.m_vdd + 100 if abs(target_vdd - self.m_vdd) > 100 else target_vdd
            else:
                new = self.m_vdd - 100 if abs(target_vdd - self.m_vdd) > 100 else target_vdd
            vdd_high_byte = new >> 8
            vdd_low_byte = new & 0xFF
            self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_SETVDD, vdd_high_byte, vdd_low_byte])
            self.m_vdd = new

    def vref_on_changed(self):
        # print "vref_on_slider_value %f.2" % (self.vref_on_slider.value())
        self.isw_on_1 = self.vref_on_slider.value() / self.plotdata.MEAS_RES_LO
        self.isw_on_2 = self.vref_on_slider.value() / self.plotdata.MEAS_RES_MID

        self.vref_on_label_1.setText("LO: %.0f%s" % (self.isw_on_1 * 1000, "uA"))
        self.vref_on_label_2.setText("HI: %.2f%s" % (self.isw_on_2, "mA"))
        self.vref_off_changed()

    def vref_on_set(self):
        pot = 27000.0 * ((10.98194 * self.vref_on_slider.value() / 1000) / 0.41 - 1)
        # print(self.vref_on_slider.value())
        # print(pot)

        vref_on_msb = int(pot / 2) >> 8
        vref_on_lsb = int(pot / 2) & 0xFF

        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_SETVREFHI, vref_on_msb, vref_on_lsb])

    def vref_off_changed(self):
        hysteresis = (self.vref_off_slider.value() / 100.0)
        # print(hysteresis)
        i_sw_on_3 = self.vref_on_slider.value()
        i_sw_off_1 = self.isw_on_2 / 16.3 / hysteresis
        i_sw_off_2 = i_sw_on_3 / 16.3 / hysteresis

        self.vref_off_label_1.setText(str("HI: %.2fmA" % (i_sw_off_1)))
        self.vref_off_label_2.setText(str("LO: %.2fuA" % (i_sw_off_2)))

    def vref_off_set(self):
        pot = 2000.0 * (16.3 * self.vref_off_slider.value() / 100.0 - 1) - 30000.0
        vref_off_msb = int(pot / 2) >> 8
        vref_off_lsb = int(pot / 2) & 0xFF

        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_SETVREFLO, vref_off_msb, vref_off_lsb])

        # print("Sent vref lo pot: " + str(pot))
        # print("Sent vref lo: " + str(self.vref_off_slider.value()))

    def reset_vrefs(self):
        self.vref_on_slider.setSliderPosition(int(((int(self.plotdata.vref_hi) * 2 / 27000.0) + 1) * (0.41 / 10.98194) * 1000))
        self.vref_off_slider.setSliderPosition((((int(self.plotdata.vref_lo) * 2 + 30000) / 2000.0 + 1) / 16.3) * 100)
        self.vref_on_set()
        self.vref_on_set()

    def sec_unit_determine(self, timestamp):
        val = 0
        unit = "[s]"
        if timestamp > 1:
            val = timestamp
            unit = "[s]"
        elif timestamp >= 1.0e-3:
            val = timestamp * 1.0e3
            unit = "[ms]"
        elif (timestamp < 1.0e-3) & (timestamp >= 1.0e-6):
            val = timestamp * 1.0e6
            unit = '[\u03bcs]'
        else:
            val = timestamp * 1.0e9
            unit = "[ns]"
        return val, unit

    def amp_unit_determine(self, current_A):
        val = 0
        unit = "mA"
        if current_A >= 1.0e-3:
            val = current_A * 1.0e3
            unit = "[mA]"
        elif (current_A < 1.0e-3) & (current_A >= 1.0e-6):
            val = current_A * 1.0e6
            unit = str_uA
        elif (current_A < 1.0e-6) & (current_A > -1.0e-6):
            val = current_A * 1.0e9
            unit = "[nA]"

        elif (current_A <= -1.0e-6) & (current_A > -1.0e-3):
            val = current_A * 1.0e6
            unit = str_uA
        elif (current_A <= -1.0e-3):
            val = current_A * 1.0e3
            unit = "[mA]"
        else:
            pass  # Handle unit determine error

        return val, unit

    def charge_unit_determine(self, charge_C):
        val = 0
        unit = "mC"
        if charge_C >= 1.0e-3:
            val = charge_C * 1.0e3
            unit = "[mC]"
        elif (charge_C < 1.0e-3) & (charge_C >= 1.0e-6):
            val = charge_C * 1.0e6
            unit = str_uC
        elif (charge_C < 1.0e-6) & (charge_C > -1.0e-6):
            val = charge_C * 1.0e9
            unit = "[nC]"

        elif (charge_C <= -1.0e-6) & (charge_C > -1.0e-3):
            val = charge_C * 1.0e6
            unit = str_uA
        elif (charge_C <= -1.0e-3):
            val = charge_C * 1.0e3
            unit = "[mC]"
        else:
            pass  # Handle unit determine error

        return val, unit

    def update_status(self):
        try:
            _max = max(self.plotdata.avg_y)
            _min = min(self.plotdata.avg_y)
            _rms = rms_flat(self.plotdata.avg_y)
            _avg = np.average(self.plotdata.avg_y)

            max_val, max_unit = self.amp_unit_determine(_max)
            min_val, min_unit = self.amp_unit_determine(_min)
            rms_val, rms_unit = self.amp_unit_determine(_rms)
            avg_val, avg_unit = self.amp_unit_determine(_avg)

            status_font = QtGui.QFont("Arial", 8)
            self.statusbarLabel.setFont(status_font)
            self.statusbarLabel.setText("max: <b>%.2f</b> %s min: <b>%.2f</b> %s rms: <b>%.2f</b> %s avg: <b>%.2f</b> %s"
                                        % (max_val, max_unit, min_val, min_unit, rms_val, rms_unit, avg_val, avg_unit))
            self.plot_window.trig_curve.setData(self.plotdata.trig_x, self.plotdata.trig_y)

            if self.curs_avg_enabled:
                samples_per_us = len(self.plotdata.avg_x) / self.plotdata.avg_timewindow  # us
                curs1, curs2 = self.plot_window.avg_region.getRegion()
                byte_position_curs1 = int(samples_per_us * curs1)
                byte_position_curs2 = int(samples_per_us * curs2)

                try:
                    if(byte_position_curs1 < 0):
                        self.plot_window.avg_region.setRegion([0, curs2])

                    curs1_y_val, curs1_y_unit = self.amp_unit_determine(self.plotdata.avg_y[byte_position_curs1])
                    curs2_y_val, curs2_y_unit = self.amp_unit_determine(self.plotdata.avg_y[byte_position_curs2])

                    curs_avg_val, curs_avg_unit = self.amp_unit_determine(np.average(self.plotdata.avg_y[byte_position_curs1:byte_position_curs2]))
                    curs_rms_val, curs_rms_unit = self.amp_unit_determine(rms_flat(self.plotdata.avg_y[byte_position_curs1:byte_position_curs2]))
                    curs_max_val, curs_max_unit = self.amp_unit_determine(np.max(self.plotdata.avg_y[byte_position_curs1:byte_position_curs2]))

                    charge = (np.average(self.plotdata.avg_y[byte_position_curs1:byte_position_curs2]) * (curs2 - curs1))
                    curs_charge_cal, curs_charge_unit = self.charge_unit_determine(charge)

                    self.curs_avg_rms_label.setText("RMS: <b>%.2f</b> %s" % (curs_rms_val, curs_rms_unit))
                    self.curs_avg_avg_label.setText("AVG: <b>%.2f</b> %s" % (curs_avg_val, curs_avg_unit))
                    self.curs_avg_max_label.setText("MAX: <b>%.2f</b> %s" % (curs_max_val, curs_max_unit))
                    self.curs_avg_coloumb_label.setText("Charge: <b>%.2f</b>  %s" % (curs_charge_cal, curs_charge_unit))
                    self.curs_avg_cursy_label.setText("Y1: <b>%5.2f</b> %s Y2: <b>%5.2f</b> %s" % (curs1_y_val, curs1_y_unit, curs2_y_val, curs2_y_unit))

                except IndexError:
                    self.plot_window.avg_region.setRegion([curs1, self.plotdata.avg_timewindow - 1e-9])

                except Exception as e:
                    print(str(e))

            if self.curs_trig_enabled:
                samples_per_us = len(self.plotdata.trig_x) / self.plotdata.trig_timewindow  # us
                curs1, curs2 = self.plot_window.trig_region.getRegion()
                byte_position_curs1 = int(samples_per_us * curs1)
                byte_position_curs2 = int(samples_per_us * curs2)

                try:
                    if(byte_position_curs1 < 0):
                        self.plot_window.trig_region.setRegion([0, curs2])

                    curs1_y_val, curs1_y_unit = self.amp_unit_determine(self.plotdata.trig_y[byte_position_curs1])
                    curs2_y_val, curs2_y_unit = self.amp_unit_determine(self.plotdata.trig_y[byte_position_curs2])

                    curs_rms_val, curs_rms_unit = self.amp_unit_determine(rms_flat(self.plotdata.trig_y[byte_position_curs1:byte_position_curs2]))
                    curs_avg_val, curs_avg_unit = self.amp_unit_determine(np.average(self.plotdata.trig_y[byte_position_curs1:byte_position_curs2]))
                    curs_max_val, curs_max_unit = self.amp_unit_determine(np.max(self.plotdata.trig_y[byte_position_curs1:byte_position_curs2]))

                    charge = (np.average(self.plotdata.trig_y[byte_position_curs1:byte_position_curs2]) * (curs2 - curs1))
                    curs_charge_cal, curs_charge_unit = self.charge_unit_determine(charge)

                    self.curs_trig_rms_label.setText("RMS: <b>%.2f</b> %s" % (curs_rms_val, curs_rms_unit))
                    self.curs_trig_avg_label.setText("AVG: <b>%.2f</b> %s" % (curs_avg_val, curs_avg_unit))
                    self.curs_trig_max_label.setText("MAX: <b>%.2f</b> %s" % (curs_max_val, curs_max_unit))
                    self.curs_trig_coloumb_label.setText("Charge: <b>%.2f</b>  %s" % (curs_charge_cal, curs_charge_unit))
                    self.curs_trig_cursy_label.setText("Y1: <b>%.2f</b> %s Y2: <b>%.2f</b> %s" % (curs1_y_val, curs1_y_unit, curs2_y_val, curs2_y_unit))

                except IndexError:
                    self.plot_window.trig_region.setRegion([curs1, self.plotdata.trig_timewindow - 1e-9])

            self.plot_window.trig_curve.setData(self.plotdata.trig_x, self.plotdata.trig_y)
        except:
            pass
