from stmpy import Machine, Driver
from scooter_stm import Scooter_stm, transitions, states
from mqtt_client import MQTT_client
from lights import sense
# import paho.mqtt.client as mqtt

broker, port = "mqtt20.iik.ntnu.no", 1883
scooter_serial = 32467129

def main():
    scooter = Scooter_stm(scooter_serial)
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sense.clear()
        exit(0)
