import network
import socket
import time
import machine
import bluetooth
import ntptime

# ==========================================
# 1. HARDWARE INITIALIZATION
# ==========================================

# LED
led = machine.Pin("LED", machine.Pin.OUT)
led.value(0)

# Internal temperature sensor
sensor_temp = machine.ADC(4)
conversion_factor = 3.3 / 65535

# RTC
rtc = machine.RTC()

# ==========================================
# 2. BLUETOOTH (BLE)
# ==========================================

ble = bluetooth.BLE()

ble_connected = False


def bt_irq(event, data):
    global ble_connected

    # Central connected
    if event == 1:
        ble_connected = True

    # Central disconnected
    elif event == 2:
        ble_connected = False
        start_advertising()


ble.irq(bt_irq)


def start_advertising():
    """Advertise BLE so phone can connect"""
    name = "Pico-2W-Dashboard"
    payload = bytearray()

    # Flags
    payload += bytearray(
        [0x02, 0x01, 0x06]
    )

    # Complete local name
    name_bytes = name.encode()
    payload += bytes([len(name_bytes) + 1, 0x09])
    payload += name_bytes

    ble.gap_advertise(100_000, payload)


def bluetooth_on():
    ble.active(True)
    start_advertising()


def bluetooth_off():
    global ble_connected
    ble_connected = False
    ble.active(False)


# Start enabled
bluetooth_on()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def read_temperature():
    reading = sensor_temp.read_u16() * conversion_factor
    temp = 27 - (reading - 0.706) / 0.001721
    return round(temp, 1)


def get_time_string():
    t = rtc.datetime()
    return f"{t[4]:02d}:{t[5]:02d}:{t[6]:02d}"


def sync_ntp_time():
    """
    Sync RTC using pool.ntp.org
    """
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()

        # Convert UTC → IST (+5:30)
        now = time.time() + (5 * 3600) + (30 * 60)
        tm = time.localtime(now)

        rtc.datetime((
            tm[0],  # year
            tm[1],  # month
            tm[2],  # day
            tm[6],  # weekday
            tm[3],  # hour
            tm[4],  # minute
            tm[5],  # second
            0
        ))

        print("NTP time synced")
        return True

    except Exception as e:
        print("NTP sync failed:", e)
        return False


# ==========================================
# 4. WIFI
# ==========================================

ssid = "THOTTUNGAL4G"
password = "shamil927"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")

while not wlan.isconnected():
    time.sleep(1)

ip_address = wlan.ifconfig()[0]

print("Connected!")
print("Dashboard:", ip_address)

# Sync time once WiFi works
sync_ntp_time()

# ==========================================
# 5. HTML DASHBOARD
# ==========================================

def get_html():

    led_text = "ON" if led.value() else "OFF"

    bt_enabled = ble.active()

    if not bt_enabled:
        bt_state = "OFFLINE"
        bt_color = "danger"
    elif ble_connected:
        bt_state = "CONNECTED"
        bt_color = "success"
    else:
        bt_state = "WAITING"
        bt_color = "warning"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>Pico Dashboard</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body {{
    background:#121212;
    color:white;
    padding-top:20px;
}}

.card {{
    background:#1e1e1e;
    border:1px solid #333;
}}

.stat {{
    font-size:2rem;
    font-weight:bold;
}}
</style>

</head>

<body>

<div class="container">

<h2 class="text-center mb-4">
RP2350 System Monitor
</h2>

<div class="row g-3">

<div class="col-md-3 col-6">
<div class="card p-3 text-center">
<h6>Temperature</h6>
<div class="stat text-warning">
{read_temperature()}°C
</div>
</div>
</div>

<div class="col-md-3 col-6">
<div class="card p-3 text-center">
<h6>Time</h6>
<div class="stat text-info">
{get_time_string()}
</div>
</div>
</div>

<div class="col-md-3 col-6">
<div class="card p-3 text-center">
<h6>Bluetooth</h6>
<div class="stat text-{bt_color}">
{bt_state}
</div>

<a href="/?bt=on"
class="btn btn-success btn-sm mt-2">
Turn ON
</a>

<a href="/?bt=off"
class="btn btn-danger btn-sm mt-2">
Turn OFF
</a>
</div>
</div>

<div class="col-md-3 col-6">
<div class="card p-3 text-center">
<h6>LED ({led_text})</h6>

<a href="/?led=on"
class="btn btn-success btn-sm mt-2">
LED ON
</a>

<a href="/?led=off"
class="btn btn-danger btn-sm mt-2">
LED OFF
</a>
</div>
</div>

</div>

<div class="text-center mt-4">
<a href="/" class="btn btn-secondary">
Refresh
</a>
</div>

</div>
</body>
</html>
"""


# ==========================================
# 6. WEB SERVER
# ==========================================

addr = socket.getaddrinfo(
    '0.0.0.0',
    80
)[0][-1]

s = socket.socket()
s.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)

s.bind(addr)
s.listen(1)

print("Server started")

while True:
    conn = None

    try:
        conn, addr = s.accept()

        request = str(conn.recv(1024))

        # LED
        if '/?led=on' in request:
            led.value(1)

        elif '/?led=off' in request:
            led.value(0)

        # Bluetooth
        elif '/?bt=on' in request:
            bluetooth_on()

        elif '/?bt=off' in request:
            bluetooth_off()

        response = get_html()

        conn.send(
            'HTTP/1.0 200 OK\r\n'
            'Content-type: text/html\r\n\r\n'
        )

        conn.send(response)
        conn.close()

    except Exception as e:
        print("Error:", e)

        if conn:
            conn.close()