# web_server.py
import socket
import json
import time

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ESP32 Alarm Clock</title>
    <style>
        body { font-family: -apple-system, sans-serif; background-color: #121212; color: #ffffff; text-align: center; margin: 0; padding: 20px; }
        .card { background: #1e1e1e; padding: 20px; border-radius: 12px; max-width: 400px; margin: 0 auto 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .time { font-size: 3em; font-weight: bold; margin: 10px 0; color: #4caf50; }
        .date { font-size: 1.2em; color: #aaaaaa; margin-bottom: 20px; }
        .status { font-size: 1.2em; margin-bottom: 15px; }
        .status.active { color: #f44336; font-weight: bold; animation: blink 1s infinite; }
        @keyframes blink { 50% { opacity: 0; } }
        input[type="time"] { background: #333; color: white; border: none; padding: 10px; font-size: 1.5em; border-radius: 6px; margin-bottom: 15px; }
        button { background: #3a3a3a; color: white; border: none; padding: 12px 20px; margin: 5px; font-size: 1em; border-radius: 6px; cursor: pointer; width: calc(50% - 15px); }
        button.primary { background: #2196F3; }
        button.danger { background: #f44336; width: 100%; margin-top: 15px; font-size: 1.2em; padding: 15px;}
        button.success { background: #4caf50; }
        button.warning { background: #ff9800; width: 100%; }
    </style>
</head>
<body>
    <div class="card">
        <div class="date" id="date">--/--/----</div>
        <div class="time" id="time">--:--:--</div>
        <div id="alarm-state" class="status">Loading...</div>
        <div class="status">Wi-Fi: <span style="color:#4caf50">Connected</span></div>
    </div>
    
    <div class="card" id="ringing-controls" style="display:none;">
        <h2 style="color:#f44336; margin-top:0;">ALARM RINGING!</h2>
        <button class="warning" onclick="api('snooze', {mins: 5})">Snooze 5 Min</button>
        <button class="danger" onclick="api('stop')">Stop Alarm</button>
    </div>

    <div class="card">
        <h2>Alarm Settings</h2>
        <input type="time" id="alarm-time"><br>
        <button class="primary" onclick="setAlarm()">Save Time</button>
        <button class="success" onclick="api('enable')">Enable</button>
        <button onclick="api('disable')" style="background:#555;">Disable</button>
    </div>
    
    <div class="card">
        <h2>Hardware Tests</h2>
        <button onclick="api('test/buzzer')">Test Buzzer</button>
        <button onclick="api('test/leds')">Test LEDs</button>
    </div>

    <script>
        async function fetchStatus() {
            try {
                let res = await fetch('/api/status');
                let data = await res.json();
                document.getElementById('time').innerText = data.time;
                document.getElementById('date').innerText = data.date;
                
                let stateText = data.alarm_enabled ? `Alarm Armed: ${data.alarm_time}` : "Alarm Disabled";
                let stateEl = document.getElementById('alarm-state');
                
                if(data.alarm_state === "RINGING") {
                    stateEl.innerText = "ALARM ACTIVE!";
                    stateEl.className = "status active";
                    document.getElementById('ringing-controls').style.display = 'block';
                } else if(data.alarm_state === "SNOOZE") {
                    stateEl.innerText = "Snoozing...";
                    stateEl.className = "status";
                    document.getElementById('ringing-controls').style.display = 'block';
                } else {
                    stateEl.innerText = stateText;
                    stateEl.className = "status";
                    document.getElementById('ringing-controls').style.display = 'none';
                }
                
                if(!document.getElementById('alarm-time').value) {
                    document.getElementById('alarm-time').value = data.alarm_time;
                }
            } catch(e) {}
        }
        
        async function api(endpoint, payload={}) {
            await fetch('/api/alarm/' + endpoint, {
                method: 'POST', 
                body: JSON.stringify(payload)
            });
            fetchStatus();
        }
        
        async function setAlarm() {
            let val = document.getElementById('alarm-time').value;
            let parts = val.split(':');
            await fetch('/api/alarm/set', {
                method: 'POST',
                body: JSON.stringify({hour: parseInt(parts[0]), minute: parseInt(parts[1])})
            });
            fetchStatus();
        }
        
        setInterval(fetchStatus, 1000);
        fetchStatus();
    </script>
</body>
</html>"""

class WebServer:
    def __init__(self, rtc, alarm, wifi):
        self.rtc = rtc
        self.alarm = alarm
        self.wifi = wifi
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 80))
        self.sock.listen(5)
        self.sock.setblocking(False)

    def update(self):
        try:
            conn, addr = self.sock.accept()
            conn.settimeout(0.5)
            request = conn.recv(1024).decode('utf-8')
            if not request:
                conn.close()
                return

            req_lines = request.split('\r\n')
            first_line = req_lines[0].split(' ')
            if len(first_line) < 2:
                conn.close()
                return
                
            method = first_line[0]
            path = first_line[1]

            response_body = ""
            content_type = "application/json"

            if method == "GET" and path == "/":
                response_body = HTML_PAGE
                content_type = "text/html"
            
            elif method == "GET" and path == "/api/status":
                response_body = json.dumps({
                    "time": self.rtc.get_time_string(),
                    "date": self.rtc.get_date_string(),
                    "alarm_time": f"{self.alarm.alarm_hour:02d}:{self.alarm.alarm_minute:02d}",
                    "alarm_enabled": self.alarm.enabled,
                    "alarm_state": self.alarm.state,
                    "ip": self.wifi.ip_address
                })

            elif method == "POST":
                # Find JSON body
                body_str = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else "{}"
                body = {}
                try: body = json.loads(body_str)
                except: pass

                if path == "/api/alarm/set":
                    self.alarm.alarm_hour = body.get('hour', self.alarm.alarm_hour)
                    self.alarm.alarm_minute = body.get('minute', self.alarm.alarm_minute)
                    self.alarm.save_settings()
                elif path == "/api/alarm/enable":
                    self.alarm.enable()
                elif path == "/api/alarm/disable":
                    self.alarm.disable()
                elif path == "/api/alarm/stop":
                    self.alarm.stop()
                elif path == "/api/alarm/snooze":
                    self.alarm.snooze(body.get('mins', 5))
                elif path == "/api/alarm/test/buzzer":
                    self.alarm.buzzer.value(1)
                    time.sleep(0.5)
                    self.alarm.buzzer.value(0)
                elif path == "/api/alarm/test/leds":
                    for led in [self.alarm.led_green, self.alarm.led_yellow, self.alarm.led_red]:
                        led.value(1)
                    time.sleep(0.5)
                    for led in [self.alarm.led_green, self.alarm.led_yellow, self.alarm.led_red]:
                        led.value(0)
                        
                response_body = '{"status":"ok"}'

            # Send HTTP response
            conn.send("HTTP/1.1 200 OK\r\n")
            conn.send(f"Content-Type: {content_type}\r\n")
            conn.send("Connection: close\r\n\r\n")
            conn.sendall(response_body)
            conn.close()

        except OSError:
            # No connection pending
            pass
        except Exception as e:
            print("Server error:", e)