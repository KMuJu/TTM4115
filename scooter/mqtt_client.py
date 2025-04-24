import paho.mqtt.client as mqtt # type: ignore
from threading import Thread
import json

from stmpy import Driver # type: ignore

from constants import COMMANDS

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

    def get_commands(self):
        return f"scooters/{self.serial_number}/commands"

    def on_message(self, client, userdata, msg):
        """
        msg is either a json or a string
        json schould be 
        {
            "command": "command",
            "user_id": id
        }

        command should be in
        - reserved


        string should be in
        - cancel
        - scan_qr_code
        - end_ride
        """
        print(f"on_message(): topic: {msg.topic}")
        print(f"Message: {msg.payload.decode()}")

        try:
            command = json.loads(msg.payload.decode("utf-8"))
            if command["command"]  == "reserved":
                stm = self.stm_driver._stms_by_id[machine]._obj # Get stm from private variable
                stm.set_userid(command["user_id"])
                self.stm_driver.send("reserve_scooter", machine)
            elif command["command"] == "scan_qr_code":
                stm = self.stm_driver._stms_by_id[machine]._obj
                stm.set_userid(command["user_id"])
                self.stm_driver.send("scan_qr_code", machine)
            else:
                print("Command not recognized")
        except:
            print("Data sent to commands is not json")
            self.stm_driver.send(msg.payload.decode(), machine)

    def start(self, broker, port):
        print("Connecting to {}:{}".format(broker, port))
        self.client.connect(broker, port)

        # self.client.subscribe(f"/scooter/{self.serial_number}/reserver")
        self.client.subscribe(COMMANDS)
        try:
            thread = Thread(target=self.client.loop_forever)
            thread.start()
        except KeyboardInterrupt:
            print("Interrupted")
            self.client.disconnect()


    def publish(self, topic, message):
        self.client.publish(topic, message, qos=1)

    def subscribe(self, topic):
        self.client.subscribe(topic)
