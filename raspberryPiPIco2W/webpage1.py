import network
import socket
import time

# 1. Connect to your local Wi-Fi
ssid = 'THOTTUNGAL4G'
password = 'shamil927'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to Wi-Fi... test 4")
while not wlan.isconnected():
    time.sleep(1)

# Grab the IP assigned by your router
ip_address = wlan.ifconfig()[0]
print(f"Connected! Your Pico's IP Address is: {ip_address}")

# 2. Define the HTML View 
# Pulling in Bootstrap to handle mobile responsiveness effortlessly
html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico 2W Server</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark text-light d-flex align-items-center justify-content-center vh-100">
    <div class="text-center">
        <h1 class="display-4 fw-bold text-success">It Works!</h1>
        <p class="lead">Your Pico 2W is serving this page over Wi-Fi.</p>
        <button class="btn btn-primary btn-lg mt-3" onclick="alert('JavaScript is running on the client side!')">Test Button</button>
    </div>
</body>
</html>
"""

# 3. Open a Socket Web Server
# Listen on port 80 (standard HTTP port)
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print('Listening on', addr)

# 4. Listen for incoming connections from your phone
while True:
    try:
        # The script pauses here and waits until a browser makes a request
        conn, addr = s.accept()
        print('Client connected from', addr)
        
        # Read the incoming HTTP request
        request = conn.recv(1024)
        
        # Send back the HTTP response headers followed by our HTML string
        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        conn.send(html)
        
        # Close the connection to free up memory for the next visitor
        conn.close()
        
    except OSError as e:
        conn.close()
        print('Connection closed')