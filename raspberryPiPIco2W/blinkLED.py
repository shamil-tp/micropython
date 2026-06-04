import machine
import time

# Initialize the onboard LED pin
led = machine.Pin("LED", machine.Pin.OUT)

# Create an infinite loop to toggle the light
while True:
    led.toggle()
    print("Blink!")
    time.sleep(2)