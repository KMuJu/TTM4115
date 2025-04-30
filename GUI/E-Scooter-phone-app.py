# Component got from the course website, last unit. Needs to be modified.
import paho.mqtt.client as mqtt # type: ignore
import logging
from threading import Thread
import json
from appJar import gui # type: ignore
import ast

# TODO: choose proper MQTT broker address
MQTT_BROKER = '192.168.210.166'
MQTT_PORT = 1883

USER_ID = "testuser1123"
# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'commands'
MQTT_TOPIC_OUTPUT = f'users/{USER_ID}'
MQTT_TOPIC_AVAILABLE_SCOOTERS = 'available_scooters'


class ScooterApp:
    """
    The component to give user a scooter client.
    """

    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        self._logger.debug('MQTT message received: {}'.format(msg))
        if msg.topic == MQTT_TOPIC_OUTPUT:
            self._logger.debug('MQTT message received on topic {}: {}'.format(msg.topic, msg.payload.decode()))
            self.app.setLabel('server_messages', 'Server message: {}'.format(msg.payload.decode()))
        elif msg.topic == MQTT_TOPIC_AVAILABLE_SCOOTERS:
            available_scooters = ast.literal_eval(msg.payload.decode())
            print(available_scooters)
            self._logger.debug('Available scooters: {}'.format(available_scooters))
            self.available_scooters = available_scooters
            self.app.updateListBox("scooters", available_scooters)
        elif msg.topic.startswith('scooters/') and msg.topic.endswith('/status'): # This should deselect the scooter if it is activated by another user.
            scooter_id = msg.topic.split('/')[1]
            status = msg.payload.decode()
            if status == 'active' and self.reserved_scooter_id == scooter_id:
                self._logger.info('Scooter {} is active'.format(scooter_id))
                self.has_active_ride = True
                self.app.setLabel('status', 'Scooter Status: {}'.format(status))
            elif status != 'available' and self.reserved_scooter_id != scooter_id: # This deselects the scooter, which is also removed from the list of available scooters.
                self._logger.info('Selected scooter unavailable'.format(scooter_id))
                # Clear selection
            elif status == 'available' and self.reserved_scooter_id == scooter_id:
                self._logger.info('Scooter {} is available'.format(scooter_id))
                self.has_active_ride = False
                self.has_reservation = False
                self.reserved_scooter_id = None
                self.app.setLabel('status', 'Scooter Status: {}'.format(status))
            elif scooter_id == self.selected_scooter:
                self.app.setLabel('status', 'Scooter Status: {}'.format(status))
            else:
                pass
        elif msg.topic.startswith('scooters/') and msg.topic.endswith('/battery'):
            scooter_id = msg.topic.split('/')[1]
            battery_level = int(msg.payload.decode())
            if scooter_id == self.selected_scooter:
                self.app.setLabel('battery_level', 'Battery Level: {}'.format(str(battery_level)))
        else:
            self._logger.warning('Unknown MQTT message received on topic {}: {}'.format(msg.topic, msg.payload.decode()))
            pass
            
    def __init__(self):
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        self.user_id = USER_ID
        self.available_scooters = []
        self.selected_scooter = None
        self.has_reservation = False
        self.reserved_scooter_id = None
        self.has_active_ride = False

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.subscribe(MQTT_TOPIC_AVAILABLE_SCOOTERS)
        self.mqtt_client.subscribe(MQTT_TOPIC_OUTPUT)
        # start the internal loop to process MQTT messages
        #self.mqtt_client.loop_start()

        self.create_gui()

        # start the MQTT client loop in a separate thread
        self.mqtt_thread = Thread(target=self.mqtt_client.loop_forever)
        self.mqtt_thread.daemon = True
        self.mqtt_thread.start()

        self.app.go()


    def create_gui(self):
        self.app = gui("E-Scooter App", "500x600")
        self.app.setBg("lightblue")
        self.app.setFont(14)

        def update_scooter_data(scooter_id):
            if scooter_id is None:
                self.app.setLabel("client_messages", "Client Message: Please select a scooter first, by getting scooter data.")
                return
            if scooter_id not in self.available_scooters:
                self.app.setLabel("client_messages", "Client Message: Scooter not available.")
                return
            if self.has_active_ride or self.has_reservation:
                self.app.setLabel("client_messages", "Client Message: You already have a ride or reservation.")
                return
            print(scooter_id)
            self.mqtt_client.unsubscribe(f'scooters/{self.selected_scooter}/status')
            self.mqtt_client.unsubscribe(f'scooters/{self.selected_scooter}/battery')
            self.selected_scooter = str(scooter_id)
            self.mqtt_client.subscribe(f'scooters/{self.selected_scooter}/status')
            self.mqtt_client.subscribe(f'scooters/{self.selected_scooter}/battery')
            self.app.setLabel('scooter_id', 'Scooter ID: {}'.format(scooter_id))


        def reserve_scooter(scooter_id):
            if scooter_id is None:
                self.app.setLabel("client_messages", "Client Message: Please select a scooter first, by getting scooter data.")
                return
            if self.has_reservation:
                self.app.setLabel("client_messages", "Client Message: You already have a reservation.")
                return
            if scooter_id not in self.available_scooters:
                self.app.setLabel("client_messages", "Client Message: Scooter not available.")
                return
            if self.has_active_ride:
                self.app.setLabel("client_messages", "Client Message: You already have a ride.")
                return
            command = "user_reserve_scooter"
            publish_command(self.user_id, scooter_id, command)
            self.has_reservation = True
            self.reserved_scooter_id = scooter_id
            self.app.setLabel("client_messages", "Client Message: Scooter reserved.")

        def cancel_reservation():
            if self.reserved_scooter_id is None:
                self.app.setLabel("client_messages", "Client Message: You don't have a reservation.")
                return
            if self.has_active_ride:
                self.app.setLabel("client_messages", "Client Message: Your scooter is active, not reserved.")
                return
            command = "user_cancel_reservation"
            publish_command(self.user_id, self.reserved_scooter_id, command)
            self.has_reservation = False
            self.reserved_scooter_id = None
            self.app.setLabel("client_messages", "Client Message: Reservation cancelled.")

        def scan_qr_code(scooter_id):
            if scooter_id is None:
                self.app.setLabel("client_messages", "Client Message: Please select a scooter first, by getting scooter data.")
                return
            if self.has_active_ride or self.has_reservation:
                self.app.setLabel("client_messages", "Client Message: You already have a ride or reservation.")
                return
            if scooter_id not in self.available_scooters:
                self.app.setLabel("client_messages", "Client Message: Scooter not available.")
                return
            command = "qr_code_activation"
            publish_command(self.user_id, scooter_id, command)
            self.app.setLabel("client_messages", "Client Message: QR-Code scanned.")
            self.has_active_ride = True
            self.reserved_scooter_id = scooter_id
            self.app.setLabel("scooter_id", "Scooter ID: {}".format(scooter_id))

        def end_ride():
            if self.reserved_scooter_id is None:
                self.app.setLabel("client_messages", "Client Message: You don't have a scooter.")
                return
            if self.has_active_ride is False:
                self.app.setLabel("client_messages", "Client Message: You don't have an active ride.")
                return
            command = "park_scooter"
            publish_command(self.user_id, self.reserved_scooter_id, command)
            self.app.setLabel("client_messages", "Client Message: Ride ended.")
            self.reserved_scooter_id = None
            self.has_reservation = False
            self.has_active_ride = False

        def publish_command(user_id, scooter_id, command):
            payload = json.dumps({
                "user": user_id,
                "serialnumber": scooter_id,
                "command": command
            })
            self._logger.info(payload)
            self.mqtt_client.publish(MQTT_TOPIC_INPUT, payload=payload, qos=1)

        


        self.app.startLabelFrame('Information:')
        self.app.addLabel('user_id', 'User ID: {}'.format(self.user_id))
        self.app.addLabel('scooter_id', 'Scooter ID: {}'.format(None))
        self.app.addLabel('status', 'Scooter Status: {}'.format(None))
        self.app.addLabel('battery_level', 'Battery Level: {}'.format(None))
        self.app.stopLabelFrame()

        self.app.startLabelFrame("Messages:")
        self.app.addLabel("client_messages", f"Client Message: {None}")
        self.app.addLabel("server_messages", f"Server message: {None}")
        self.app.stopLabelFrame()

        self.app.startLabelFrame('Available Scooters:')
        self.app.addListBox("scooters", self.available_scooters)
        self.app.addButton("Get Scooter Data", lambda: update_scooter_data(self.app.getListBox("scooters")[0]))
        self.app.addButton("Reserve", lambda: reserve_scooter(self.app.getListBox("scooters")[0]))
        self.app.addButton("Cancel Reservation", lambda: cancel_reservation())
        self.app.addButton("Scan QR-Code", lambda: scan_qr_code(self.app.getListBox("scooters")[0]))
        self.app.addButton("End Ride", lambda: end_ride())
        self.app.stopLabelFrame()

    

    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()


# logging.DEBUG: Most fine-grained logging, printing everything
# logging.INFO:  Only the most important informational log items
# logging.WARN:  Show only warnings and errors.
# logging.ERROR: Show only error messages.
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

s = ScooterApp()