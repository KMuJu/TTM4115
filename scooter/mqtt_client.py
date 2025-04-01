import paho.mqtt.client as mqtt
from threading import Thread
import json

from stmpy import Driver

from scooter_stm import Scooter_stm

machine = "scooter"

class MQTT_client:
    def __init__(self, serial_number:int) -> None:
        self.stm_driver : Driver
        self.client: mqtt.Client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.serial_number = serial_number

    def set_driver(self, driver): self.stm_driver = driver

    def on_connect(self, client, userdata, flags, rc):
        print(f"on_connect(): {mqtt.connack_string(rc)}")

    def on_message(self, client, userdata, msg):
        print(f"on_message(): topic: {msg.topic}")
        print(f"Message: {msg.payload.decode()}")

        if msg.topic == "/commands":
            try:
                command = json.loads(msg.payload.decode())
                if command["scooter_id"] != self.serial_number:
                    return
                if command["command"] == "reserved" or command["command"] == "qr_code_activated":
                    stm: Scooter_stm = self.stm_driver._stms_by_id[machine] # Get stm from private variable
                    stm.set_userid(int(command["user_id"]))
                    self.stm_driver.send(command["command"], machine)
                elif command["command"] == "user_cancel":
                    self.stm_driver.send(command["command"], machine)
                else:
                    print("Command not recognized")
            except:
                print("Data sent to commands is not json")
                return


        self.stm_driver.send(msg.payload.decode(), machine)

    def start(self, broker, port):
        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        # self.client.subscribe(f"/scooter/{self.serial_number}/reserver")
        self.client.subscribe("/commands")
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()


    def publish(self, topic, message):
        self.client.publish(topic, message)

    def subscribe(self, topic):
        self.client.subscribe(topic)
