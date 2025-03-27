import paho.mqtt.client as mqtt
from threading import Thread

from stmpy import Driver

machine = "scooter"

class MQTT_client:
    def __init__(self):
        self.stm_driver : Driver
        self.client: mqtt.Client

    def set_driver(self, driver): self.stm_driver = driver

    def on_connect(self, client, userdata, flags, rc):
        print(f"on_connect(): {mqtt.connack_string(rc)}")

    def on_message(self, client, userdata, msg):
        print(f"on_message(): topic: {msg.topic}")
        print(f"Message: {msg.payload.decode()}")

        self.stm_driver.send(msg.payload.decode(), machine)

    def start(self, broker, port):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        self.client.subscribe("group19/#")
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()
