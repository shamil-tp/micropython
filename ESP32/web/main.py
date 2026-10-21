import usocket as socket
import network
import espnow
import gc
import time
from machine import Pin
from wifipy import wconnect

# 1. Connect Wi-Fi
wconnect()

# 2. Hardware Setup & ESP-NOW
# GPIO 2 configured with Active LOW logic: 0 = ON, 1 = OFF
LED_PIN = 2
led = Pin(LED_PIN, Pin.OUT)
led.value(1)  # Initialize to 1 so LED starts OFF

wlan = network.WLAN(network.STA_IF)
e = espnow.ESPNow()
e.active(True)

def blink_led(times=6, delay=0.15):
    """Blinks the LED using Active LOW logic (0=ON, 1=OFF)."""
    for _ in range(times):
        led.value(0)  # Turn ON
        time.sleep(delay)
        led.value(1)  # Turn OFF
        time.sleep(delay)

def stream_html_file(conn):
    """Streams index.html in 2 KB chunks to keep RAM usage low."""
    try:
        gc.collect()
        import os
        file_size = os.stat('index.html')[6]
        header = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {file_size}\r\nConnection: close\r\n\r\n"
        conn.sendall(header.encode('utf-8'))
        
        with open('index.html', 'r') as f:
            while True:
                chunk = f.read(2048)
                if not chunk:
                    break
                conn.sendall(chunk)
    except Exception as err:
        err_msg = f"<h1>Error loading dashboard: {err}</h1>"
        err_header = f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/html\r\nContent-Length: {len(err_msg)}\r\nConnection: close\r\n\r\n"
        conn.sendall(f"{err_header}{err_msg}")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

print(f"\nServer active on port 80! Testing GPIO {LED_PIN} (Active LOW)...")

# Fast startup blink to confirm hardware function on boot
blink_led(times=4, delay=0.1)

while True:
    try:
        conn, addr = s.accept()
        request = conn.recv(1024).decode('utf-8')
        first_line = request.split('\r\n')[0] if request else ""
        
        if 'GET / ' in first_line:
            stream_html_file(conn)

        elif 'GET /api/led/on' in first_line:
            led.value(0)  # LOW = ON
            print("Action: LED ON (GPIO 2 LOW)")
            json_body = f'{{"status": "success", "led": "ON", "pin": {LED_PIN}, "logic": "active_low"}}'
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            conn.sendall(response)

        elif 'GET /api/led/off' in first_line:
            led.value(1)  # HIGH = OFF
            print("Action: LED OFF (GPIO 2 HIGH)")
            json_body = f'{{"status": "success", "led": "OFF", "pin": {LED_PIN}, "logic": "active_low"}}'
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            conn.sendall(response)

        elif 'GET /api/led/blink' in first_line:
            print("Action: BLINK LED")
            blink_led(times=6, delay=0.15)
            json_body = f'{{"status": "success", "action": "BLINK", "pin": {LED_PIN}}}'
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            conn.sendall(response)

        elif 'POST /api/send_espnow' in first_line:
            try:
                body = request.split('\r\n\r\n')[1]
                mac_str = body.split('"mac":"')[1].split('"')[0]
                payload_str = body.split('"payload":"')[1].split('"')[0]

                mac_bytes = bytes.fromhex(mac_str.replace(':', ''))
                try:
                    e.add_peer(mac_bytes)
                except OSError:
                    pass

                e.send(mac_bytes, payload_str.encode('utf-8'))
                
                json_body = f'{{"status": "success", "target": "{mac_str}", "payload": "{payload_str}"}}'
                response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            except Exception as err:
                json_body = f'{{"status": "error", "message": "{err}"}}'
                response = f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            
            conn.sendall(response)

        else:
            json_body = f'{{"status": "error", "message": "Route not found"}}'
            response = f"HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nContent-Length: {len(json_body)}\r\nConnection: close\r\n\r\n{json_body}"
            conn.sendall(response)

        conn.close()
        gc.collect()

    except Exception as e_err:
        print(f"Socket Error: {e_err}")
