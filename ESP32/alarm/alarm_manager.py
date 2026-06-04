# alarm_manager.py
import json
import time
from machine import Pin
import config

class AlarmManager:
    def __init__(self, rtc):
        self.rtc = rtc
        self.led_green = Pin(config.PINS["LED_GREEN"], Pin.OUT)
        self.led_yellow = Pin(config.PINS["LED_YELLOW"], Pin.OUT)
        self.led_red = Pin(config.PINS["LED_RED"], Pin.OUT)
        self.buzzer = Pin(config.PINS["BUZZER"], Pin.OUT)
        
        self.state = "NORMAL" # NORMAL, ARMED, RINGING, SNOOZE, WIFI_SETUP
        self.alarm_hour = 6
        self.alarm_minute = 30
        self.enabled = False
        
        self.snooze_until = 0 # Epoch equivalent
        self.last_toggle = time.ticks_ms()
        self.blink_state = False
        
        self.load_settings()
        self.update_state_machine()

    def load_settings(self):
        try:
            with open("alarm.json", "r") as f:
                data = json.loads(f.read())
                self.alarm_hour = data.get("hour", 6)
                self.alarm_minute = data.get("minute", 30)
                self.enabled = data.get("enabled", False)
        except:
            self.save_settings()

    def save_settings(self):
        with open("alarm.json", "w") as f:
            f.write(json.dumps({
                "hour": self.alarm_hour,
                "minute": self.alarm_minute,
                "enabled": self.enabled
            }))
            
    def set_wifi_setup_mode(self, active):
        if active:
            self.state = "WIFI_SETUP"
        else:
            self.update_state_machine()

    def enable(self):
        self.enabled = True
        self.state = "ARMED"
        self.save_settings()

    def disable(self):
        self.enabled = False
        self.state = "NORMAL"
        self.save_settings()

    def stop(self):
        if self.state in ["RINGING", "SNOOZE"]:
            self.update_state_machine()
            # Prevent immediate re-triggering within the same minute
            time.sleep(1)

    def snooze(self, minutes):
        if self.state in ["RINGING", "SNOOZE"]:
            t = self.rtc.get_time()
            # Simple epoch calculation approximation for snooze
            current_mins_today = t[3] * 60 + t[4]
            self.snooze_until = current_mins_today + minutes
            self.state = "SNOOZE"

    def update_state_machine(self):
        if self.state == "WIFI_SETUP": return
        if self.state in ["RINGING", "SNOOZE"]: return
        
        if self.enabled:
            self.state = "ARMED"
        else:
            self.state = "NORMAL"

    def update(self):
        now = time.ticks_ms()
        t = self.rtc.get_time()
        curr_hour, curr_min = t[3], t[4]
        
        # Check alarm trigger
        if self.state == "ARMED":
            if curr_hour == self.alarm_hour and curr_min == self.alarm_minute and t[5] == 0:
                self.state = "RINGING"
                
        # Check snooze expiration
        if self.state == "SNOOZE":
            current_mins = curr_hour * 60 + curr_min
            if current_mins >= self.snooze_until:
                self.state = "RINGING"

        # Hardware indication timers
        if time.ticks_diff(now, self.last_toggle) > 500:
            self.blink_state = not self.blink_state
            self.last_toggle = now

        # Hardware outputs based on state
        self.buzzer.value(1 if self.state == "RINGING" and self.blink_state else 0)

        if self.state == "NORMAL":
            self.led_green.value(1)
            self.led_yellow.value(0)
            self.led_red.value(0)
        elif self.state == "ARMED":
            self.led_green.value(1)
            self.led_yellow.value(1)
            self.led_red.value(0)
        elif self.state == "RINGING":
            self.led_green.value(0)
            self.led_yellow.value(0)
            self.led_red.value(1 if self.blink_state else 0)
        elif self.state == "SNOOZE":
            self.led_green.value(1)
            self.led_yellow.value(1 if self.blink_state else 0)
            self.led_red.value(0)
        elif self.state == "WIFI_SETUP":
            self.led_green.value(1 if self.blink_state else 0)
            self.led_yellow.value(0)
            self.led_red.value(0)