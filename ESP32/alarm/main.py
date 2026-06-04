# main.py
import machine
import time
import config

from wifi_manager import WiFiManager
from rtc_manager import RTCManager
from lcd_manager import LCDManager
from alarm_manager import AlarmManager
from web_server import WebServer

def main():
    print("--- Starting Smart Alarm Clock ---")
    
    # Initialize I2C Bus
    i2c = machine.I2C(0, scl=machine.Pin(config.PINS["I2C_SCL"]), sda=machine.Pin(config.PINS["I2C_SDA"]), freq=400000)
    
    # Initialize Managers
    lcd = LCDManager(i2c)
    rtc = RTCManager(i2c)
    alarm = AlarmManager(rtc)
    wifi = WiFiManager()
    server = WebServer(rtc, alarm, wifi)

    # Initial UI State
    alarm.set_wifi_setup_mode(True)
    lcd.print_text("Connecting WiFi.", 0)
    lcd.print_text(config.WIFI_SSID, 1)

    # Connect Wi-Fi
    if wifi.connect():
        lcd.print_text("WiFi Connected! ", 0)
        lcd.print_text(wifi.ip_address, 1)
        time.sleep(2)
    else:
        lcd.print_text("WiFi Failed!    ", 0)
        lcd.print_text("Offline Mode    ", 1)
        time.sleep(2)

    alarm.set_wifi_setup_mode(False)

    print("Entering Main Loop...")
    
    # Non-blocking Main Loop
    while True:
        # Update components
        wifi.update()
        alarm.update()
        server.update()

        # Update LCD UI
        if alarm.state == "RINGING":
            lcd.print_text("*** ALARM *** ", 0)
            lcd.print_text(f"{alarm.alarm_hour:02d}:{alarm.alarm_minute:02d} WAKE UP", 1)
        else:
            time_str = rtc.get_time_string()
            lcd.print_text(f"Time: {time_str}  ", 0)
            
            if alarm.enabled:
                lcd.print_text(f"Alarm: {alarm.alarm_hour:02d}:{alarm.alarm_minute:02d} ON ", 1)
            else:
                lcd.print_text("Alarm: OFF      ", 1)

        # Small yield to prevent hardware watchdog trigger
        time.sleep_ms(50)

if __name__ == "__main__":
    main()