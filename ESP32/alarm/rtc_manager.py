# rtc_manager.py
import time
import config

class RTCManager:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = config.I2C_ADDR_RTC

    def _bcd2dec(self, bcd):
        return ((bcd >> 4) * 10) + (bcd & 0x0F)

    def _dec2bcd(self, dec):
        return ((dec // 10) << 4) | (dec % 10)

    def get_time(self):
        try:
            data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
            ss = self._bcd2dec(data[0] & 0x7F)
            mm = self._bcd2dec(data[1])
            hh = self._bcd2dec(data[2] & 0x3F)
            # data[3] is day of week
            DD = self._bcd2dec(data[4])
            MM = self._bcd2dec(data[5] & 0x7F)
            YY = self._bcd2dec(data[6]) + 2000
            return (YY, MM, DD, hh, mm, ss)
        except Exception as e:
            print("RTC Read Error:", e)
            return (2000, 1, 1, 0, 0, 0) # Fallback safe time

    def get_time_string(self):
        t = self.get_time()
        return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])

    def get_date_string(self):
        t = self.get_time()
        return "{:02d}/{:02d}/{:04d}".format(t[2], t[1], t[0])