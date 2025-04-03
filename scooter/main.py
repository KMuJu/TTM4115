from stmpy import Machine, Driver
from constants import COMMANDS
from scooter_stm import Scooter_stm, transitions, states
from mqtt_client import MQTT_client
from lights import sense
# import paho.mqtt.client as mqtt

broker, port = "mqtt20.iik.ntnu.no", 1883
scooter_serial = 32467129

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

    while True:
        s = input("Send to mqtt:")
        sending = '{"command":"reserve_scooter", "scooter_id":32467129, "user_id":100}' if s == "r"\
        else '{"command":"scan_qr_code", "scooter_id":32467129, "user_id":100}' if s == "q"\
        else '{"command":"end_ride", "scooter_id":32467129, "user_id":100}' if s == "u"\
        else '{"command":"cancel_reservation", "scooter_id":32467129, "user_id":100}' if s == "c"\
        else s
        print("Sending: ", sending)
        client.client.publish(COMMANDS, sending)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting")
        sense.clear()
        exit(0)
