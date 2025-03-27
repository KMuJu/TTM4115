from stmpy import Machine, Driver
from scooter import Scooter_stm, transitions, states
from mqtt_client import MQTT_client
import paho.mqtt.client as mqtt

broker, port = "mqtt20.iik.ntnu.no", 1883

scooter = Scooter_stm()
stm = Machine(transitions=transitions, obj=scooter, states=states, name='scooter')
scooter.set_stm(stm)

driver = Driver()
driver.add_machine(stm)

client = MQTT_client()
scooter.set_client(client)
client.set_driver(driver)

driver.start()
client.start(broker, port)

while True:
    s = input("Send to mqtt:")
    print("Sending: ", s)
    client.client.publish("group19/test", s)
