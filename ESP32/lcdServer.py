import network
import socket
import machine
import gc
import json
import time
import ntptime
import urequests
from machine import Pin, SoftI2C

# ==========================================
# 1. Configuration & Setup
# ==========================================
SSID = "THOTTUNGAL4G"
PASSWORD = "shamil927"

# Timezone Offset in seconds (e.g., India IST: +5:30 = 5.5 * 3600 = 19800)
TZ_OFFSET = 19800 

# Weather Coordinates (Default: Kochi/Kerala, adjust as needed)
LAT = "10.0"
LON = "76.3"
WEATHER_API_URL = f"http://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m"

# Initialize WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

print("Connecting to WiFi...", end="")
while not wlan.isconnected():
    time.sleep(0.5)
    print(".", end="")
print("\nConnected! ESP32 IP Address:", wlan.ifconfig()[0])

# Sync Time via NTP
print("Syncing time with NTP...")
try:
    ntptime.settime()
    print("Time synchronized successfully!")
except Exception as e:
    print("NTP Sync Failed:", e)

# Global variables for async updates
cached_weather_temp = "N/A"
last_weather_fetch = 0

def fetch_weather():
    global cached_weather_temp, last_weather_fetch
    # Fetch weather every 10 minutes (600 seconds) to avoid rate limits
    if time.time() - last_weather_fetch > 600 or cached_weather_temp == "N/A":
        try:
            res = urequests.get(WEATHER_API_URL, timeout=5)
            data = res.json()
            res.close()
            cached_weather_temp = f"{data['current']['temperature_2m']} °C"
            last_weather_fetch = time.time()
        except Exception as e:
            print("Weather Fetch Error:", e)
    return cached_weather_temp

def get_local_time_str():
    # Adjust UTC timestamp to local time
    local_timestamp = time.time() + TZ_OFFSET
    tm = time.localtime(local_timestamp)
    # Format: YYYY-MM-DD HH:MM:SS
    return f"{tm[0]:04d}-{tm[1]:02d}-{tm[2]:02d} {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"

# ==========================================
# 2. Hardware Setup (LCD & LED)
# ==========================================
class TinyI2CLcd:
    def __init__(self, i2c, i2c_addr):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.backlight = 0x08 # 0x08 is ON, 0x00 is OFF
        time.sleep_ms(20)
        for cmd in [0x33, 0x32, 0x28, 0x0C, 0x06, 0x01]:
            self.send(cmd, 0)
            time.sleep_ms(2)
            
    def send(self, data, mode):
        high = mode | (data & 0xF0) | self.backlight
        low = mode | ((data << 4) & 0xF0) | self.backlight
        self.i2c.writeto(self.i2c_addr, bytes([high | 0x04, high & ~0x04, low | 0x04, low & ~0x04]))
        time.sleep_us(50)
        
    def clear(self):
        self.send(0x01, 0)
        time.sleep_ms(2)
        
    def move_to(self, col, row):
        addr = 0x80 if row == 0 else 0xC0
        self.send(addr + col, 0)
        
    def putstr(self, string):
        for char in string:
            self.send(ord(char), 1)
            
    def set_backlight(self, state):
        if state:
            self.backlight = 0x08
        else:
            self.backlight = 0x00
        self.send(0, 0) # Send empty command to flush backlight bit update

# Initialize Hardware
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)
I2C_ADDR = 39 
lcd = TinyI2CLcd(i2c, I2C_ADDR)
led = Pin(2, Pin.OUT)

# State Tracking
current_lcd_msg = "System Ready!"
backlight_state = True

def update_lcd(msg):
    lcd.clear()
    msg = msg[:32]
    if len(msg) > 16:
        lcd.move_to(0, 0)
        lcd.putstr(msg[:16])
        lcd.move_to(0, 1)
        lcd.putstr(msg[16:])
    else:
        lcd.move_to(0, 0)
        lcd.putstr(msg)

update_lcd(current_lcd_msg)

# ==========================================
# 3. Web Server & Routing
# ==========================================
def unquote(string):
    res = []
    i = 0
    while i < len(string):
        if string[i] == '%':
            res.append(chr(int(string[i+1:i+3], 16)))
            i += 3
        elif string[i] == '+':
            res.append(' ')
            i += 1
        else:
            res.append(string[i])
            i += 1
    return "".join(res)

HTML = """<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Advanced Control Center</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-secondary mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#">ESP32 Dashboard</a>
            <ul class="nav nav-pills" id="navTabs" role="tablist">
                <li class="nav-item"><button class="nav-link active text-white" data-bs-toggle="tab" data-bs-target="#dashboard" type="button">Dashboard</button></li>
                <li class="nav-item"><button class="nav-link text-white" data-bs-toggle="tab" data-bs-target="#lcdManager" type="button">LCD Manager</button></li>
            </ul>
        </div>
    </nav>

    <div class="container tab-content">
        <div class="tab-pane fade show active" id="dashboard">
            <div class="row g-4 mb-4">
                <div class="col-md-6">
                    <div class="card bg-gradient bg-primary text-white border-0 shadow">
                        <div class="card-body">
                            <h6 class="card-subtitle mb-1 text-white-50">System Local Time (NTP)</h6>
                            <h2 class="card-title fw-bold" id="live-time">Loading Sync...</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-gradient bg-info text-dark border-0 shadow">
                        <div class="card-body">
                            <h6 class="card-subtitle mb-1 text-dark-50">Outdoor Weather Temperature</h6>
                            <h2 class="card-title fw-bold" id="weather-temp">Fetching API...</h2>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row g-4">
                <div class="col-md-6">
                    <div class="card bg-secondary border-0 shadow">
                        <div class="card-header bg-dark text-primary fw-bold">System Statistics</div>
                        <ul class="list-group list-group-flush" id="stats-list">
                            <li class="list-group-item bg-secondary text-light">Fetching data...</li>
                        </ul>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card bg-secondary border-0 shadow h-100">
                        <div class="card-header bg-dark text-success fw-bold">Hardware Controls</div>
                        <div class="card-body d-flex flex-column justify-content-center align-items-center">
                            <p class="fs-5">Built-in LED Status: <span id="led-badge" class="badge bg-danger">OFF</span></p>
                            <button class="btn btn-lg btn-success w-50" onclick="toggleLED()">Toggle LED</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="tab-pane fade" id="lcdManager">
            <div class="row g-4">
                <div class="col-md-8">
                    <div class="card bg-secondary border-0 shadow">
                        <div class="card-header bg-dark text-info fw-bold">I2C LCD Content Controller</div>
                        <div class="card-body">
                            <div class="alert alert-dark text-center fs-4 fw-mono mb-4 border border-info" id="lcd-current" style="letter-spacing: 2px;">...</div>
                            <div class="mb-3">
                                <label class="form-label fw-bold">Update Text Message (Max 32 characters)</label>
                                <input type="text" id="lcd-input" class="form-control bg-dark text-light border-secondary" maxlength="32" placeholder="Type message here...">
                            </div>
                            <button class="btn btn-primary me-2" onclick="sendToLCD()">Send to Display</button>
                            <button class="btn btn-warning" onclick="clearLCD()">Clear Display</button>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-secondary border-0 shadow">
                        <div class="card-header bg-dark text-warning fw-bold">LCD Hardware Settings</div>
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item bg-secondary text-light d-flex justify-content-between align-items-center">
                                <span>I2C Bus Address:</span>
                                <span class="badge bg-dark text-info fs-6">0x27 (39)</span>
                            </li>
                            <li class="list-group-item bg-secondary text-light d-flex justify-content-between align-items-center">
                                <span>Backlight Status:</span>
                                <span id="backlight-badge" class="badge bg-success">ON</span>
                            </li>
                        </ul>
                        <div class="card-body text-center">
                            <button class="btn btn-warning w-100" onclick="toggleBacklight()">Toggle Backlight</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function fetchStats() {
            try {
                let res = await fetch('/api/stats');
                let data = await res.json();
                
                document.getElementById('live-time').innerText = data.time;
                document.getElementById('weather-temp').innerText = data.weather;
                
                document.getElementById('stats-list').innerHTML = `
                    <li class="list-group-item bg-secondary text-light d-flex justify-content-between"><span>CPU Freq:</span> <strong>${data.cpu} MHz</strong></li>
                    <li class="list-group-item bg-secondary text-light d-flex justify-content-between"><span>RAM Free:</span> <strong>${data.ram_free} bytes</strong></li>
                    <li class="list-group-item bg-secondary text-light d-flex justify-content-between"><span>RAM Used:</span> <strong>${data.ram_used} bytes</strong></li>
                    <li class="list-group-item bg-secondary text-light d-flex justify-content-between"><span>Internal Temp:</span> <strong>${data.temp} °C</strong></li>
                `;
                
                let ledBadge = document.getElementById('led-badge');
                if(data.led === 1) {
                    ledBadge.innerText = 'ON'; ledBadge.className = 'badge bg-success';
                } else {
                    ledBadge.innerText = 'OFF'; ledBadge.className = 'badge bg-danger';
                }
                
                let bgBadge = document.getElementById('backlight-badge');
                if(data.backlight) {
                    bgBadge.innerText = 'ON'; bgBadge.className = 'badge bg-success';
                } else {
                    bgBadge.innerText = 'OFF'; bgBadge.className = 'badge bg-danger';
                }
                
                document.getElementById('lcd-current').innerText = data.lcd_msg || "[ Blank Display ]";
            } catch(e) { console.error("Error pooling metrics", e); }
        }

        async function toggleLED() {
            await fetch('/api/led/toggle', {method: 'POST'});
            fetchStats();
        }

        async function toggleBacklight() {
            await fetch('/api/lcd/backlight', {method: 'POST'});
            fetchStats();
        }

        async function sendToLCD() {
            let msg = document.getElementById('lcd-input').value;
            await fetch('/api/lcd/update?msg=' + encodeURIComponent(msg), {method: 'POST'});
            document.getElementById('lcd-input').value = '';
            fetchStats();
        }

        async function clearLCD() {
            await fetch('/api/lcd/clear', {method: 'POST'});
            fetchStats();
        }

        // Poll statistics and updates every 3 seconds
        setInterval(fetchStats, 3000);
        fetchStats();
    </script>
</body>
</html>"""

# Start Socket Server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

print("Web server running! Type the IP address in your browser.")

while True:
    try:
        conn, addr = s.accept()
        request = conn.recv(1024).decode('utf-8')
        
        if not request:
            conn.close()
            continue
            
        request_line = request.split('\r\n')[0]
        
        # --- ROUTER ---
        if "GET / " in request_line:
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n' + HTML
            conn.sendall(response.encode())
            
        elif "GET /api/stats" in request_line:
            gc.collect() 
            temp = (machine.temperature() - 32) * 5/9 if hasattr(machine, 'temperature') else 0 
            
            # Gather expanded analytics
            stats = {
                "cpu": machine.freq() // 1000000,
                "ram_free": gc.mem_free(),
                "ram_used": gc.mem_alloc(),
                "temp": round(temp, 1),
                "led": led.value(),
                "lcd_msg": current_lcd_msg,
                "backlight": backlight_state,
                "time": get_local_time_str(),
                "weather": fetch_weather()
            }
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n' + json.dumps(stats)
            conn.sendall(response.encode())
            
        elif "POST /api/led/toggle" in request_line:
            led.value(not led.value())
            conn.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"status":"ok"}')
            
        elif "POST /api/lcd/backlight" in request_line:
            backlight_state = not backlight_state
            lcd.set_backlight(backlight_state)
            conn.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"status":"ok"}')
            
        elif "POST /api/lcd/clear" in request_line:
            lcd.clear()
            current_lcd_msg = ""
            conn.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"status":"ok"}')
            
        elif "POST /api/lcd/update" in request_line:
            try:
                url_path = request_line.split(' ')[1]
                if "?msg=" in url_path:
                    raw_msg = url_path.split("?msg=")[1]
                    decoded_msg = unquote(raw_msg)
                    update_lcd(decoded_msg)
                    current_lcd_msg = decoded_msg
            except Exception as e:
                print("LCD Update Error:", e)
            conn.sendall(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n{"status":"ok"}')
            
        else:
            conn.sendall(b'HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n')
            
        conn.close()
        
    except OSError as e:
        conn.close()
        print("Socket Error:", e)