from pynrfjprog import API, Hex

if __name__ == "__main__":
        hexfile = "ppk_110.hex"
        success = False
        retries = 5
        # Open connection to debugger and rtt
        nrfjprog = API.API('NRF52')
        nrfjprog.open()
        nrfjprog.connect_to_emu_without_snr()
        while(success is False or retries == 0):
            try:
                nrfjprog.recover()
                print "PPK erased"
                success = True
            except:
                print "failed, retrying"
                retries -= 1
                pass
        try:
            application = Hex.Hex(hexfile)
            for segment in application:
                nrfjprog.write(segment.address, segment.data, True)
            print "PPK reprogrammed"
            nrfjprog.sys_reset()
            nrfjprog.go()
            nrfjprog.rtt_start()
            print "PPK ready to go"
        except Exception as e:
            print str(e)
            print "Unable to flash " + hexfile + ", make sure this file is found in working directory."
        raw_input("Press any key to finish...")
