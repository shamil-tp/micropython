# wifi_manager.py
import network
import time
import config

class WiFiManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.is_connected = False
        self.ip_address = ""

    def connect(self):
        if not self.wlan.isconnected():
            print("Connecting to network...")
            self.wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            
            # Timeout loop for initial connection
            start = time.ticks_ms()
            while not self.wlan.isconnected():
                if time.ticks_diff(time.ticks_ms(), start) > 10000:
                    print("Wi-Fi connection timeout.")
                    return False
                time.sleep(0.1)
                
        self.is_connected = True
        self.ip_address = self.wlan.ifconfig()[0]
        print("Network config:", self.wlan.ifconfig())
        return True

    def update(self):
        # Check connection status non-blocking
        if self.is_connected and not self.wlan.isconnected():
            self.is_connected = False
            self.ip_address = ""
            print("Wi-Fi disconnected! Reconnecting...")
            self.wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        elif not self.is_connected and self.wlan.isconnected():
            self.is_connected = True
            self.ip_address = self.wlan.ifconfig()[0]