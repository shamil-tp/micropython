# lcd_manager.py
import time
import config

class LCDManager:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = config.I2C_ADDR_LCD
        self._backlight = 0x08
        self.current_line1 = ""
        self.current_line2 = ""
        self.init_display()

    def _write_byte(self, cmd, mode=0):
        try:
            high = mode | (cmd & 0xF0) | self._backlight
            low = mode | ((cmd << 4) & 0xF0) | self._backlight
            self.i2c.writeto(self.addr, bytearray([high | 0x04]))
            self.i2c.writeto(self.addr, bytearray([high]))
            self.i2c.writeto(self.addr, bytearray([low | 0x04]))
            self.i2c.writeto(self.addr, bytearray([low]))
        except Exception:
            pass

    def init_display(self):
        time.sleep_ms(50)
        for _ in range(3):
            self._write_byte(0x30)
            time.sleep_ms(5)
        self._write_byte(0x20)
        time.sleep_ms(1)
        # 4-bit, 2 lines, 5x8
        self._write_byte(0x28) 
        # Display on, no cursor
        self._write_byte(0x0C)
        # Clear
        self.clear()
        # Entry mode
        self._write_byte(0x06)

    def clear(self):
        self._write_byte(0x01)
        time.sleep_ms(2)
        self.current_line1 = ""
        self.current_line2 = ""

    def move_to(self, row, col):
        addr = col
        if row == 1:
            addr += 0x40
        self._write_byte(0x80 | addr)

    def print_text(self, text, row):
        # Pad with spaces to clear old text without flickering
        text = text[:16] + " " * (16 - len(text))
        
        # Only update if changed
        if row == 0 and text == self.current_line1: return
        if row == 1 and text == self.current_line2: return
        
        self.move_to(row, 0)
        for char in text:
            self._write_byte(ord(char), 1)
            
        if row == 0: self.current_line1 = text
        if row == 1: self.current_line2 = text