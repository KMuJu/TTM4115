from stmpy import Machine, Driver # type: ignore
from scooter_stm import Scooter_stm, transitions, states, sense
from mqtt_client import MQTT_client

broker, port = "192.168.210.166", 1883
scooter_serial = 123456

"""
skriv status til scooter/serial/status
oppstart
    -> send scooter:serial til commands

les triggers fra scooter/serial/commands
fjerne timer fra reserved, skal være en trigger fra serveren
    ha en timer som er litt lengre enn den på serveren

endre idle entry publish til idle fra available
"""

def main():
    scooter = Scooter_stm(scooter_serial)
    stm = Machine(transitions=transitions, obj=scooter, states=states, name='scooter')
    scooter.set_stm(stm)

    driver = Driver()
    driver.add_machine(stm)

    client = MQTT_client(scooter_serial)
    scooter.set_client(client)
    client.set_driver(driver)

    driver.start()
    client.start(broker, port)


    client.client.publish("scooters/"+str(scooter_serial)+"/status", "available")
    client.client.publish("scooters/"+str(scooter_serial)+"/battery", "99")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sense.clear()
        exit(0)
