from stmpy import Machine


class Scooter_stm:
    def __init__(self, serial_number:int) -> None:
        self.stm : Machine
        self.client = None
        self.serial_number = serial_number

    def set_client(self, client): self.client = client
    def set_stm(self, stm): self.stm = stm

    def idle_entry(self):
        print("idle entry")

    def reserved_entry(self):
        print("reserved entry")

    def active_but_static_entry(self):
        print("active but static entry")

    def battery_low(self):
        print("battery low")

    def user_cancel(self):
        print("user cancel")

    def static_timeout(self):
        print("static timeout")

    def qr_qode_activated(self):
        print("qr qode activated")

    def reserved_timeout(self):
        print("reserved timeout")

    def proximity(self):
        print("proximity")


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

speeding = {
        "trigger": "speeding",
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
        "trigger": "t",
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
        "trigger": "t",
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
        speeding,
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
        "entry": "start_timer('t', 6000);reserved_entry",
        }

active_but_static = {
        "name": "active_but_static",
        "entry": "start_timer('t', 3000);active_but_static_entry",
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
