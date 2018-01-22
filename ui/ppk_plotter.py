import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
import struct
from libs.rtt import RTT_COMMANDS
from ui import ppk_settings
import csv
import threading

SAMPLE_INTERVAL = 13.0e-6
ADC_REF = 0.6
ADC_GAIN = 4.0
ADC_MAX = 8192.0

MEAS_RANGE_NONE = 0
MEAS_RANGE_LO = 1
MEAS_RANGE_MID = 2
MEAS_RANGE_HI = 3
MEAS_RANGE_INVALID = 4

MEAS_RANGE_POS = 14
MEAS_RANGE_MSK = (3 << 14)

MEAS_ADC_POS = 0
MEAS_ADC_MSK = 0x3FFF


class PlotData():
    def __init__(self):
        '''  '''
        self.trigger = 2500
        self.MEAS_RES_HI = None
        self.MEAS_RES_MID = None
        self.MEAS_RES_LO = None

        self.CAL_MEAS_RES_HI = None
        self.CAL_MEAS_RES_MID = None
        self.CAL_MEAS_RES_LO = None

        self.board_id = None

        self.sample_interval = SAMPLE_INTERVAL
        self.avg_interval   = self.sample_interval * 10  # num of samples averaged per packet
        self.avg_timewindow = 2  # avg_interval * 1024
        self.current_meas_range = 0
        self.trig_interval   = self.sample_interval
        self.trig_timewindow = self.trig_interval * (512 + 0)

        self.avg_bufsize  = int(self.avg_timewindow / self.avg_interval)
        self.trig_bufsize = int(self.trig_timewindow / self.trig_interval)

        self.avg_x = np.linspace(0.0, self.avg_timewindow, self.avg_bufsize)
        self.avg_y = np.zeros(self.avg_bufsize, dtype=np.float)
        self.trig_x = np.linspace(0.0, self.trig_timewindow, self.trig_bufsize)
        self.trig_y = np.zeros(self.trig_bufsize, dtype=np.float)

        self.trigger_high = self.trigger >> 8
        self.trigger_low = self.trigger & 0xFF

        self.vref_hi = 0
        self.vref_lo = 0
        self.vdd     = 0

        self.vref_hi_init = 0
        self.vref_lo_init = 0
        self.vdd_init     = 0


class ppk_plotter():
    def __init__(self):
        # This app instance must be constructed before all other elements are added
        self.plotdata = PlotData()
        self.calibrating = False
        self.calibrating_done = False
        self.global_offset = 0.0
        self.enable_log = False
        self.alive = True
        self.logfile_name = 'ppk_avg.csv'
        self.started_log = False
        self.log_stopped = False
        self.update_log = False

    def setup_graphics(self):
        self.setup_measurement_regions()
        pg.setConfigOption('background', 'k')  # Set white background
        self.gw = pg.GraphicsWindow()
        self.settings = ppk_settings.SettingsWindow(self.plotdata, self)
        self.gw.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.gw.destroyed.connect(self.destroyedEvent)
        ico = QtGui.QIcon('images\icon.ico')
        self.gw.setWindowIcon(ico)
        self.gw.move(475, 50)
        self.gw.setWindowTitle('Plots - Power Profiler Kit')
        self.gw.resize((self.gw.width()), (self.settings.settings_mainw.height()))
        self.setup_plot_window()
        # Need to connect these signals after the settings instance is created
        self.avg_region.sigRegionChanged.connect(self.settings.avg_region_changed)
        self.trig_region.sigRegionChanged.connect(self.settings.trig_region_changed)

    def set_rtt_instance(self, rtt):
        self.rtt = rtt
        self.settings.set_rtt_instance(rtt)

    def edit_colors(self):
        color = QtGui.QColorDialog.getColor()
        if color.isValid():
            self.trig_curve.setPen(color)
            self.avg_curve.setPen(color)

    def edit_bg(self):
        bg = QtGui.QColorDialog.getColor()
        if bg.isValid():
            self.gw.setBackground(bg)

    def destroyedEvent(self):
        self.rtt.alive = False
        try:
            QtGui.QApplication.quit()
        except:
            pass
        QtGui.QApplication.quit()
        try:
            self.alive = False
        except Exception as e:
            print(str(e))

    def setup_measurement_regions(self):
        # Cursor with window for calculating avereages
        region_brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 20))
        self.trig_region = pg.LinearRegionItem()
        # Cursor with window for calculating avereages
        self.avg_region = pg.LinearRegionItem()
        for line in self.trig_region.lines:
            line.setPen(255, 80, 80, 85, width=3)
            line.setHoverPen(255, 255, 255, 100, width=3)
        for line in self.avg_region.lines:
            line.setPen(255, 80, 80, 85, width=3)
            line.setHoverPen(255, 255, 255, 100, width=3)
        self.trig_region.setBrush(region_brush)
        self.avg_region.setBrush(region_brush)
        self.trig_region.setZValue(10)
        # Set cursors at 5 and 6 ms
        self.trig_region.setRegion([0.001, 0.004])

        self.avg_region.setZValue(10)
        # Set cursors at 5 and 6 ms
        self.avg_region.setRegion([0.5, 0.9])

    def setup_plot_window(self):
        self.avg_plot = self.gw.addPlot(title='Average', row=0, col=1, rowspan=1, colspan=1)
        trig_plot = self.gw.addPlot(title='Trigger', row=1, col=1, rowspan=1, colspan=1)

        self.avg_plot.setLabel('left', 'current', 'A')
        self.avg_plot.setLabel('bottom', 'time', 's')
        self.avg_plot.showGrid(x=True, y=True)

        trig_plot.setLabel('left', 'current', 'A')
        trig_plot.setLabel('bottom', 'time', 's')
        trig_plot.showGrid(x=True, y=True)

        # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this
        # item when doing auto-range calculations.
        self.avg_plot.addItem(self.avg_region, ignoreBounds=True)
        trig_plot.addItem(self.trig_region, ignoreBounds=True)
        # Create the curve for average data (top graph)
        self.avg_curve = self.avg_plot.plot(self.plotdata.avg_x, self.plotdata.avg_y)
        # Create the curve for trigger data (bottom graph)
        self.trig_curve = trig_plot.plot(self.plotdata.trig_x, self.plotdata.trig_y)

        # Bools for checking if we should update the curve when the update timer triggers
        self.update_trig_curve = False
        self.update_avg_curve = False

    def start(self, run=True):
        ''' Send trigger value and start to firmware.
            Starts timers for updating graphs and calculations.
        '''
        self.settings.m_vdd = int(self.plotdata.vdd)

        self.settings.vdd_slider.setSliderPosition(int(self.plotdata.vdd))
        self.settings.vref_on_slider.setSliderPosition(int(((int(self.plotdata.vref_hi) * 2 / 27000.0) + 1) * (0.41 / 10.98194) * 1000))
        self.settings.vref_off_slider.setSliderPosition((((int(self.plotdata.vref_lo) * 2 + 30000) / 2000.0 + 1) / 16.3) * 100)

        self.settings.r_high_tb.setText(str(self.plotdata.MEAS_RES_HI))
        self.settings.r_mid_tb.setText(str(self.plotdata.MEAS_RES_MID))
        self.settings.r_lo_tb.setText(str(self.plotdata.MEAS_RES_LO))

        self.rtt.start()
        # Trigger trigger window update, since production firmware uses wrong window value
        self.settings.TriggerWindowValueChanged()
        # Write the initial trigger value, set in self.plotdata
        self.settings.set_trigger(2500)
        # Timer to update graphs, continous shot
        self.calibrating = True

        timer = pg.QtCore.QTimer(self.gw)
        timer.timeout.connect(self.update)
        timer.start(1)  # 10us
        # Timer to update rms value
        timer_rms = pg.QtCore.QTimer(self.gw)
        timer_rms.timeout.connect(self.settings.update_status)
        timer_rms.start(200)  # 200ms
        self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_RUN])

    def reject_outliers(self, data, m=2.):
        d = np.abs(data - np.median(data))
        mdev = np.median(d)
        s = d / mdev if mdev else 0.
        return data[s < m]

    def start_log_thread(self):
        self.log_thread = threading.Thread(target=self.do_logging)
        self.log_thread.setDaemon(True)
        self.log_thread.start()

    def rtt_handler(self, data):
        ''' All measurments arrive here. 4 bytes for avg window, 16 bytes for trigger window '''

        if(not self.calibrating_done):
            if not hasattr(self, "calibration_counter"):
                self.calibration_counter = 10000  # it doesn't exist yet, so initialize it
                self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_DUT, 0])
                self.settings.show_calib_msg_box()

            if(self.calibrating):
                if(self.calibration_counter != 0):
                    self.calibration_counter = self.calibration_counter - 1
                    if (len(data) == 4):

                        s = ''.join([chr(b) for b in data])
                        f = struct.unpack('f', s)[0]        # Get the uA value

                        self.plotdata.avg_y[:-1] = self.plotdata.avg_y[1:]  # shift data in the array one sample left
                        self.plotdata.avg_y[-1] = f / 1e6

                        self.update_avg_curve = True

                else:
                    # Got all the samples
                    self.calibrating = False
            else:
                self.calibrating_done = True
                self.settings.close_calib_msg_box()
                self.global_offset = np.average(self.plotdata.avg_y[1000:8000])
                self.rtt.write_stuffed([RTT_COMMANDS.RTT_CMD_DUT, 1])
                del self.calibration_counter
                self.plotdata.avg_y = np.zeros(self.plotdata.avg_bufsize, dtype=np.float)

        if (len(data) == 4):
            # Average data received (in microamp)
            s = ''.join([chr(b) for b in data])
            f = struct.unpack('f', s)[0]
            self.plotdata.avg_y[:-1] = self.plotdata.avg_y[1:]  # shift data in the array one sample left
            self.plotdata.avg_y[-1] = f / 1e6 - self.global_offset

            self.update_avg_curve = True

            if (self.enable_log):
                try:
                    if(not self.started_log):
                        self.logfile = open(self.logfile_name, 'wb')
                        fieldnames = ['Time[s]', 'Current[uA]']
                        self.writer = csv.DictWriter(self.logfile, fieldnames=fieldnames)

                        self.writer.writeheader()
                        # Start thread for reading logging.
                        self.started_log = True
                        self.enable_log = False
                except Exception as e:
                    print(str(e))
            # Just set update log after every sample
            self.update_log = True

        else:
            # Trigger data received as raw adc float, with range flag prepended
            prev_meas_range = MEAS_RANGE_LO
            prev_data = None
            for i in range(0, len(data), 2):
                if (i + 1) < len(data):
                    tmp = np.uint16((data[i + 1] << 8) + data[i])
                    self.plotdata.current_meas_range = (tmp & MEAS_RANGE_MSK) >> MEAS_RANGE_POS
                    adc_val = (tmp & MEAS_ADC_MSK) >> MEAS_ADC_POS
                    sample_A = 0.0

                    if self.plotdata.current_meas_range == MEAS_RANGE_LO:
                        sample_A = adc_val * (ADC_REF / (ADC_GAIN * ADC_MAX * self.plotdata.MEAS_RES_LO))
                        sample_A = sample_A - self.global_offset

                    elif self.plotdata.current_meas_range == MEAS_RANGE_MID:
                        sample_A = adc_val * (ADC_REF / (ADC_GAIN * ADC_MAX * self.plotdata.MEAS_RES_MID))
                    elif self.plotdata.current_meas_range == MEAS_RANGE_HI:
                        sample_A = adc_val * (ADC_REF / (ADC_GAIN * ADC_MAX * self.plotdata.MEAS_RES_HI))
                    elif self.plotdata.current_meas_range == MEAS_RANGE_INVALID:
                        print("Range INVALID")
                    elif self.plotdata.current_meas_range == MEAS_RANGE_NONE:
                        print("Range not detected")

                    if(self.settings.switch_filter_enabled):
                        if(self.plotdata.current_meas_range != prev_meas_range):
                            # If switch, use last sample
                            sample_A = prev_data
                            prev_meas_range = self.plotdata.current_meas_range
                        else:
                            prev_data = sample_A

                        prev_meas_range = self.plotdata.current_meas_range

                    self.plotdata.trig_y[:-1] = self.plotdata.trig_y[1:]  # shift data in the array one sample left
                    self.plotdata.trig_y[-1] = sample_A

            # Update the trigger window when we have filled all samples
            self.update_trig_curve = True

    def do_logging(self):
        ts = 0
        while(self.alive):
            try:
                if(self.update_log and not self.log_stopped):
                    ts += self.plotdata.avg_interval
                    try:
                        self.writer.writerow({'Time[s]': '{0:f}'.format(ts), 'Current[uA]': '{0:f}'.format(self.plotdata.avg_y[-1])})
                        self.update_log = False
                    except:
                        # Exception happens before logging is started, due to no write instance
                        pass
                if(self.log_stopped):
                    ts = 0
                    try:
                        self.logfile.close()
                    except:
                        pass
            except Exception as e:
                print(str(e))

    def medfilt(self, x, k):
        """Apply a length-k median filter to a 1D array x.
        Boundaries are extended by repeating endpoints.
        """
        assert k % 2 == 1, "Median filter length must be odd."
        assert x.ndim == 1, "Input must be one-dimensional."
        k2 = (k - 1) // 2
        y = np.zeros((len(x), k), dtype=x.dtype)
        y[:, k2] = x
        for i in range(k2):
            j = k2 - i
            y[j:, i] = x[:-j]
            y[:j, i] = x[0]
            y[:-j, - (i + 1)] = x[j:]
            y[-j:, - (i + 1)] = x[-1]
        return np.median(y, axis=1)

    # update plots
    def update(self):
        if self.update_trig_curve:
            self.settings.trigger_single_button.setText("Single")
            if (not self.settings.external_trig_enabled):
                self.settings.trigger_start_button.setEnabled(True)
            self.trig_curve.setData(self.plotdata.trig_x, self.plotdata.trig_y)
            self.update_trig_curve = False

        if self.update_avg_curve:
            self.avg_curve.setData(self.plotdata.avg_x, self.plotdata.avg_y)
            self.update_avg_curve = False
