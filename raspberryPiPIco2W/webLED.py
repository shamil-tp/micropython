import network
import socket
import time
import machine # 1. Import the hardware library

# 2. Initialize the onboard LED
led = machine.Pin("LED", machine.Pin.OUT)
led.value(0) # Ensure it starts turned off

# 3. Connect to your local Wi-Fi
ssid = 'THOTTUNGAL4G' 
password = 'shamil927'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)

ip_address = wlan.ifconfig()[0]
print(f"Connected! Your Pico's IP Address is: {ip_address}")

# 4. Dynamic HTML View
# We wrap the HTML in a function so we can pass the current LED state to it,
# similar to how you would pass data to an EJS template.
def get_html(led_state):
    state_text = "ON" if led_state else "OFF"
    text_color = "text-success" if led_state else "text-danger"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico 2W Server</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light d-flex align-items-center justify-content-center vh-100">
    <div class="text-center">
        <h1 class="display-4 fw-bold">LED is <span class="{text_color}">{state_text}</span></h1>
        <p class="lead">Control your Pico 2W hardware over Wi-Fi.</p>
        <div class="mt-4">
            <a href="/?led=on" class="btn btn-success btn-lg mx-2">Turn ON</a>
            <a href="/?led=off" class="btn btn-danger btn-lg mx-2">Turn OFF</a>
        </div>
    </div>
</body>
</html>
"""

# 5. Open a Socket Web Server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print('Listening on', addr)

# 6. Listen for incoming connections
while True:
    try:
        conn, addr = s.accept()
        print('Client connected from', addr)
        
        # Read the raw incoming HTTP request
        request = conn.recv(1024)
        request = str(request) # Convert the byte data to a string
        
        # 7. The "Router" Logic
        # We manually check if our specific paths are inside the raw HTTP request string
        if '/?led=on' in request:
            print("Command received: Turn LED ON")
            led.value(1)
        elif '/?led=off' in request:
            print("Command received: Turn LED OFF")
            led.value(0)
        
        # Generate the HTML, injecting the new LED state
        html_response = get_html(led.value())
        
        # Send back the HTTP response headers followed by our HTML string
        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        conn.send(html_response)
        
        # Close the connection
        conn.close()
        
    except OSError as e:
        conn.close()
        print('Connection closed')