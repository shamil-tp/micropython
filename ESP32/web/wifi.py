import network
import time

SSID = "THOTTUNGAL4G"
PASSWORD = "shamil927"

def wconnect():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    
    if wifi.isconnected():
        print("Already connected to Wi-Fi.")
        print(f"IP Info: {wifi.ifconfig()}")
        return True
    
    print(f"Connecting to '{SSID}'...")
    wifi.connect(SSID, PASSWORD)
    
    timeout = 10
    while not wifi.isconnected() and timeout > 0:
        print(f"Waiting for connection... {timeout}s remaining")
        time.sleep(1)
        timeout -= 1
        
    if wifi.isconnected():
        print("\n--- Wi-Fi Connected Successfully ---")
        print(f"Network Config: {wifi.ifconfig()}")
        return True
    else:
        print("\n--- Wi-Fi Connection Failed ---")
        wifi.active(False)
        return False
