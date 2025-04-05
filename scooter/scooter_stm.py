from threading import Thread
from stmpy import Machine
from mqtt_client import MQTT_client
# from lights import RedLightThread, sense
from constants import BASE
from joystick_thread import JoystickThread
from sense_hat import SenseHat
from time import sleep

sense = SenseHat()

class Scooter_stm:
    def __init__(self, serial_number:int) -> None:
        self.stm : Machine
        self.client : MQTT_client
        self.serial_number = serial_number
        self.battery_level = 100
        self.red_light_thread = Thread(target=self.red_light)
        self.proximity_thread = Thread(target=self.handle_proximity)
        self.driving_thread = Thread(target=self.handle_driving)
        self.light = ""
        self.userid = -1
        self.isDriving = False
        self.isProximity = False
        self.driving = False

    def init(self):
        self.client.publish(f"commands", f"serial:{self.serial_number}")

    def set_client(self, client): self.client = client
    def set_stm(self, stm): self.stm = stm
    def update_battery_level(self, battery_level: int): self.battery_level = battery_level
    def set_userid(self, userid: int): self.userid = userid

    def idle_entry(self):
        self.client.publish(f"scooter/{self.serial_number}/status", "idle")
        self.client.subscribe(f"scooter/{self.serial_number}/status")
        self.light_send("off")

    def reserved_entry(self):
        self.light_send("red_blink")
        self.proximity_sensor_listen(self.userid)

    def active_but_static_entry(self):
        sense.show_letter("S")
        self.driving_listen()

    def battery_low(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "bill_user")
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/battery", self.battery_level)

    def user_cancel(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "bill_user")
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/battery", self.battery_level)
        self.userid = -1

    def cancel_reservation(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "bill_user")
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/battery", self.battery_level)
        self.userid = -1

    def static_timeout(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "bill_user")
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/battery", self.battery_level)

    def qr_qode_activated(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "active")
        self.light_send("driving_lights")

    def reserved_timeout(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "reserved_timeout")
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/battery", self.battery_level)

    def proximity(self):
        self.client.publish(f"{BASE}/scooter/{self.serial_number}/status", "active")
        self.light_send("driving_lights")

    def light_send(self, type_str):
        print("changing light to", type_str)
        s = self.light
        self.light = type_str
        if s == "red_blink":
            self.red_light_thread.join()
            self.red_light_thread = Thread(target=self.red_light)

        sense.clear()
        if type_str == "red_blink":
            self.red_light_thread.start()
        elif type_str == "driving_lights":
            sense.clear((255, 255, 255))


    def proximity_sensor_listen(self, userid):
        print("proximity sensor listen to", userid)
        self.isProximity = True
        if self.proximity_thread is not None and self.proximity_thread.is_alive():
            return
        self.proximity_thread = Thread(target = self.handle_proximity) # Trigger proximity when pressed
        self.proximity_thread.start()

    def driving_listen(self):
        self.isDriving = True
        if self.driving_thread is not None and self.driving_thread.is_alive():
            return
        self.driving_thread = Thread(target = self.handle_driving) # Trigger driving when pressed
        self.driving_thread.start()

    def reserved_exit(self):
        print("Stopping proximity")
        if self.proximity_thread.is_alive():
            self.isProximity = False
            self.proximity_thread.join()
        if self.driving_thread.is_alive():
            self.isDriving = False
            self.driving_thread.join()

    def handle_proximity(self):
        while self.isProximity:
            for event in sense.stick.get_events():
                if event.action == "pressed" and event.direction == "middle":
                    sense.show_letter("P")
                    self.stm.send("proximity")

    def handle_driving(self):
        while self.isDriving:
            for event in sense.stick.get_events():
                if event.action == "pressed" and event.direction != "middle":
                    sense.show_letter("D")
                    self.driving = True
                    self.stm.send("driving")
                elif self.driving and event.action == "released":
                    self.driving = False
                    self.isDriving = False
                    self.stm.send("standing_still")
        self.driving = False

    def red_light(self):
        while self.light == "red_blink":
            sense.clear((255, 0, 0))
            sleep(0.5)
            sense.clear()
            sleep(0.5)



init = {
        "source": "initial",
        "target": "idle",
        "effect": "init"
        }

battery_low_static = {
        "trigger": "battery_low_static",
        "source": "active_but_static",
        "target": "idle",
        "effect": "battery_low"
        }

battery_low_mobile = {
        "trigger": "battery_low_mobile",
        "source" : "active_but_mobile",
        "target" : "active_but_static"
        }

driving = {
        "trigger": "driving",
        "source" : "active_but_static",
        "target" : "active_but_mobile"
        }

standing_still = {
        "trigger": "standing_still",
        "source" : "active_but_mobile",
        "target" : "active_but_static"
        }


end_ride = {
        "trigger": "end_ride",
        "source" : "active_but_static",
        "target" : "idle",
        "effect" : "user_cancel"
        }

cancel_reservation = {
        "trigger": "cancel_reservation",
        "source" : "reserved",
        "target" : "idle",
        "effect" : "cancel_reservation"
        }

static_timeout = {
        "trigger": "t_s",
        "source" : "active_but_static",
        "target" : "idle",
        "effect" : "static_timeout"
        }

qr_qode = {
        "trigger": "scan_qr_code",
        "source" : "idle",
        "target" : "active_but_static",
        "effect" : "qr_qode_activated"
        }

reserved_t = {
        "trigger": "reserve_scooter",
        "source" : "idle",
        "target" : "reserved"
        }

reserved_timeout = {
        "trigger": "t_r",
        "source" : "reserved",
        "target" : "idle",
        "effect" : "reserved_timeout"
        }

proximity = {
        "trigger": "proximity",
        "source" : "reserved",
        "target" : "active_but_static",
        "effect" : "proximity"
        }

transitions = [
        init,
        battery_low_static,
        battery_low_mobile,
        driving,
        standing_still,
        end_ride,
        cancel_reservation,
        static_timeout,
        qr_qode,
        reserved_t,
        reserved_timeout,
        proximity
        ]

idle = {
        "name": "idle",
        "entry": "idle_entry",
        }

reserved = {
        "name": "reserved",
        "entry": "start_timer('t_r', 60000);reserved_entry",
        "exit": "reserved_exit"
        }

active_but_static = {
        "name": "active_but_static",
        "entry": "start_timer('t_s', 30000);active_but_static_entry",
        }

active_but_mobile = {
        "name": "active_but_mobile",
        }

states = [
        idle,
        reserved,
        active_but_static,
        active_but_mobile
        ]
