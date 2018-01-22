import threading
import time
import os
from pynrfjprog import API, Hex

DEBUG = False

JLINK_PRO_V8    = 4000
JLINK_OBD       = 1000

# Always try to have highest speed
JLINK_SPEED_KHZ = JLINK_PRO_V8
# Enable this flag to show all errors/warnings
DEBUG = False

STX = 0x02
ETX = 0x03
ESC = 0x1F
STR = 0xF1

MODE_IDLE = 0
MODE_RECV = 1
MODE_ESC_RECV = 2

NRF_EGU0_BASE          = 0x40014000
TASKS_TRIGGER0_OFFSET  = 0
TASKS_TRIGGER1_OFFSET  = 4
TASKS_TRIGGER2_OFFSET  = 8
TASKS_TRIGGER3_OFFSET  = 12
TASKS_TRIGGER4_OFFSET  = 16
TASKS_TRIGGER5_OFFSET  = 20
TASKS_TRIGGER6_OFFSET  = 24
TASKS_TRIGGER7_OFFSET  = 28
TASKS_TRIGGER8_OFFSET  = 32
TASKS_TRIGGER9_OFFSET  = 36
TASKS_TRIGGER10_OFFSET = 40
TASKS_TRIGGER11_OFFSET = 44
TASKS_TRIGGER12_OFFSET = 48
TASKS_TRIGGER13_OFFSET = 52
TASKS_TRIGGER14_OFFSET = 56
TASKS_TRIGGER15_OFFSET = 60


class RTT_COMMANDS():
    RTT_CMD_TRIGGER_SET         = 0x01  # following trigger of type int16
    RTT_CMD_AVG_NUM_SET         = 0x02  # Number of samples x16 to average over
    RTT_CMD_TRIG_WINDOW_SET     = 0x03  # following window of type unt16
    RTT_CMD_TRIG_INTERVAL_SET   = 0x04  #
    RTT_CMD_SINGLE_TRIG         = 0x05
    RTT_CMD_RUN                 = 0x06
    RTT_CMD_STOP                = 0x07
    RTT_CMD_RANGE_SET           = 0x08
    RTT_CMD_LCD_SET             = 0x09
    RTT_CMD_TRIG_STOP           = 0x0A
    RTT_CMD_CALIBRATE_OFFSET    = 0x0B
    RTT_CMD_DUT                 = 0x0C
    RTT_CMD_SETVDD              = 0x0D
    RTT_CMD_SETVREFLO           = 0x0E
    RTT_CMD_SETVREFHI           = 0x0F
    RTT_CMD_TOGGLE_EXT_TRIG     = 0x11
    RTT_CMD_SET_RES_USER        = 0x12


def debug_print(line):
    if(DEBUG):
        print(line)
    else:
        pass


class rtt(object):
    def __init__(self, callback):
        self.alive = True
        # Open connection to debugger and rtt
        self.nrfjprog = API.API('NRF52')
        self.nrfjprog.open()
        try:
            self.nrfjprog.connect_to_emu_without_snr(jlink_speed_khz=JLINK_SPEED_KHZ)
        except:
            raise
        self.nrfjprog.sys_reset()
        self.nrfjprog.go()
        self.nrfjprog.rtt_start()
        time.sleep(1)

        self.callback = callback

    def start(self):
        # Start thread for reading rtt.
        self.read_thread = threading.Thread(target=self.t_read)
        self.read_thread.setDaemon(True)
        self.read_thread.start()

    def flash_application(self, hex_file_path):
        try:
            if os.path.exists(hex_file_path):
                pass
            else:
                return "Failed to locate hex file at %s" % (hex_file_path)

            application = Hex.Hex(hex_file_path)  # Parsing hex file into segments
            for segment in application:
                self.nrfjprog.write(segment.address, segment.data, True)

            return True
        except Exception as e:
            print((str(e)))
            print ("Failed to write device")
            return str(e)

    def t_read(self):
        try:
            self.read_mode = MODE_IDLE
            data_buffer = []
            while self.alive:
                try:
                    data = self.nrfjprog.rtt_read(0, 100, encoding=None)
                    if data != '':
                        for byte in data:
                            n = byte
                            if self.read_mode == MODE_IDLE:
                                ''' Mode Idle - Not Receiving '''
                                if n == STX:
                                    self.read_mode = MODE_RECV

                            elif self.read_mode == MODE_RECV:
                                ''' Mode Receiving - Receiving data '''
                                if n == ESC:
                                    self.read_mode = MODE_ESC_RECV
                                elif n == ETX:
                                    self.callback(data_buffer)
                                    data_buffer[:] = []
                                    self.read_mode = MODE_IDLE
                                elif n == STX:
                                    data_buffer[:] = []
                                else:
                                    data_buffer.append(n)

                            elif self.read_mode == MODE_ESC_RECV:
                                ''' Mode Escape Received - Convert next byte '''
                                data_buffer.append(n ^ 0x20)
                                self.read_mode = MODE_RECV

                except AttributeError as attre:
                    # RTT module reported error upon exit
                    debug_print(str(attre))
                    pass

                except Exception as e:
                    debug_print(str(e))
                    print ("Lost connection, retrying for 10 times")
                    print ("Reconnecting...")
                    connected = False
                    tries = 0
                    while(tries != 10):
                        try:
                            print(tries)
                            time.sleep(0.6)
                            self.nrfjprog.close()
                            self.nrfjprog = API.API('NRF52')
                            self.nrfjprog.open()
                            self.nrfjprog.connect_to_emu_without_snr(jlink_speed_khz=JLINK_SPEED_KHZ)
                            self.nrfjprog.sys_reset()
                            self.nrfjprog.go()
                            self.nrfjprog.rtt_start()
                            time.sleep(1)
                            print ("Reconnected, you may start the graphs again.")
                            connected = True
                            break

                        except Exception as e:
                            print ("Reconnecting...")
                            tries += 1
                            self.alive = connected
                    if (connected):
                        self.alive = True
                    else:
                        raise Exception("Failed to reconnect")

        except Exception as e:
            debug_print(str(e))
            self.alive = False

    def write_stuffed(self, cmd):
        s = ''
        s = chr(STX)
        for byte in cmd:
            if byte == STX or byte == ETX or byte == ESC:
                s = s + chr(ESC)
                s = s + chr(byte ^ 0x20)
            else:
                s = s + chr(byte)
        s = s + chr(ETX)

        try:
            try:
                debug_print("rtt write initiated")
                self.nrfjprog.rtt_write(0, s, encoding=None)
                debug_print("rtt write finished")
            except Exception as e:
                debug_print("write failed, %s") % str(e)

            while(True):
                try:
                    debug_print("write u32 initiated")
                    self.nrfjprog.write_u32(NRF_EGU0_BASE + TASKS_TRIGGER0_OFFSET, 0x00000001, 0)
                    debug_print("write u32 finished")
                    break
                except Exception as e:
                    debug_print("write u32 failed")
                    continue

            while(True):
                try:
                    time.sleep(0.1)
                    self.nrfjprog.go()
                    break
                except Exception as e:
                    debug_print("go failed, %s" % str(e))
                    continue

        except Exception as e:
            print(str(e))
            pass
