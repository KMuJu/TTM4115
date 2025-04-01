from threading import Thread
from stmpy import Machine
from mqtt_client import MQTT_client
from lights import RedLightThread, sense


class Scooter_stm:
    def __init__(self, serial_number:int) -> None:
        self.stm : Machine
        self.client : MQTT_client
        self.serial_number = serial_number
        self.battery_level = 100
        self.red_light_thread = RedLightThread()
        self.light = ""
        self.userid = -1

    def set_client(self, client): self.client = client
    def set_stm(self, stm): self.stm = stm
    def update_battery_level(self, battery_level: int): self.battery_level = battery_level
    def set_userid(self, userid: int): self.userid = userid

    def idle_entry(self):
        self.client.publish(f"{self.serial_number}/status", "available")
        self.client.subscribe(f"{self.serial_number}/status")
        self.light_send("off")

    def reserved_entry(self):
        self.light_send("red_blink")
        self.proximity_sensor_listen(self.userid)

    def active_but_static_entry(self):
        print("active but static entry")

    def battery_low(self):
        self.client.publish(f"{self.serial_number}/status", "bill_user")
        self.client.publish(f"{self.serial_number}/battery", self.battery_level)

    def user_cancel(self):
        self.client.publish(f"{self.serial_number}/status", "bill_user")
        self.client.publish(f"{self.serial_number}/battery", self.battery_level)
        self.userid = -1

    def static_timeout(self):
        self.client.publish(f"{self.serial_number}/status", "bill_user")
        self.client.publish(f"{self.serial_number}/battery", self.battery_level)

    def qr_qode_activated(self):
        self.client.publish(f"{self.serial_number}/status", "active")
        self.light_send("driving_lights")

    def reserved_timeout(self):
        self.client.publish(f"{self.serial_number}/status", "rerserved_but_ignored")
        self.client.publish(f"{self.serial_number}/battery", self.battery_level)

    def proximity(self):
        self.client.publish(f"{self.serial_number}/status", "active")
        self.light_send("driving_lights")


    def light_send(self, type_str):
        print("changing light to", type_str)
        if self.light == "red_blink":
            self.red_light_thread.stop()
            self.red_light_thread.join()
            self.red_light_thread = RedLightThread()

        sense.clear()
        if type_str == "red_blink":
            self.red_light_thread.start()
        elif type_str == "driving_lights":
            sense.clear((255, 255, 255))

        self.light = type_str

    def proximity_sensor_listen(self, userid):
        print("proximity sensor listen to", userid)


init = {
        "source": "initial",
        "target": "idle",
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


cancel = {
        "trigger": "user_cancel",
        "source" : "active_but_static",
        "target" : "idle",
        "effect" : "user_cancel"
        }

static_timeout = {
        "trigger": "t_s",
        "source" : "active_but_static",
        "target" : "idle",
        "effect" : "static_timeout"
        }

qr_qode = {
        "trigger": "qr_code_activated",
        "source" : "idle",
        "target" : "active_but_static",
        "effect" : "qr_qode_activated"
        }

reserved_t = {
        "trigger": "reserved",
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
        cancel,
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
        "entry": "start_timer('t_r', 6000);reserved_entry",
        }

active_but_static = {
        "name": "active_but_static",
        "entry": "start_timer('t_s', 3000);active_but_static_entry",
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
