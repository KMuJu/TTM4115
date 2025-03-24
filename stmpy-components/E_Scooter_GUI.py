import paho.mqtt.client as mqtt
import logging
from threading import Thread
import json
from appJar import gui

# TODO: Update MQTT broker if needed
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883

# TODO: Update with your team's topics
MQTT_TOPIC_APP_TO_SERVER = 'ttm4115/team_19/app_to_server'
MQTT_TOPIC_SERVER_TO_APP = 'ttm4115/team_19/server_to_app'


class EScooterAppComponent:
    """
    The component representing the E-Scooter phone application.
    """

    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
        self._logger.debug('MQTT connected to {}'.format(client))
        # Subscribe to server messages
        self.mqtt_client.subscribe(MQTT_TOPIC_SERVER_TO_APP)

    def on_message(self, client, userdata, msg):
        """Handle incoming messages from the server"""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self._logger.debug("Received message: {}".format(payload))
            
            # TODO: Implement handling of different message types
            if 'type' in payload:
                if payload['type'] == 'available_scooters':
                    self.update_scooter_list(payload['scooters'])
                elif payload['type'] == 'reservation_confirmation':
                    self.show_reservation_confirmation(payload)
                elif payload['type'] == 'unlock_confirmation':
                    self.show_unlock_confirmation(payload)
                # Add more message types as needed
        except Exception as e:
            self._logger.error("Error processing message: {}".format(e))

    def __init__(self, user_id="user123"):
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting E-Scooter App Component')
        
        # Store the user ID
        self.user_id = user_id
        
        # Store list of available scooters
        self.available_scooters = []
        
        # Store currently selected scooter
        self.selected_scooter = None
        
        # Track reservation status
        self.has_reservation = False
        self.reserved_scooter_id = None

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        self.create_gui()

    def create_gui(self):
        self.app = gui("E-Scooter App", "500x600")
        
        # Request available scooters section
        self.app.addButton("Find Available Scooters", self.request_available_scooters)
        
        # Scooter list section
        self.app.startLabelFrame("Available Scooters")
        self.app.addListBox("scooters", [])
        self.app.setListBoxChangeFunction("scooters", self.select_scooter)
        self.app.stopLabelFrame()
        
        # Buttons for actions
        self.app.startLabelFrame("Actions")
        self.app.addButton("Reserve Selected Scooter", self.reserve_scooter)
        self.app.addButton("Unlock Scooter", self.unlock_scooter)
        self.app.addButton("End Ride", self.end_ride)
        self.app.setButtonState("Unlock Scooter", "disabled")
        self.app.setButtonState("End Ride", "disabled")
        self.app.stopLabelFrame()
        
        # Status section
        self.app.startLabelFrame("Status")
        self.app.addLabel("status", "Ready")
        self.app.stopLabelFrame()
        
        # Start the GUI
        self.app.go()

    def publish_command(self, command):
        """Publish a command to the server"""
        payload = json.dumps(command)
        self._logger.info("Publishing: {}".format(command))
        self.mqtt_client.publish(MQTT_TOPIC_APP_TO_SERVER, payload=payload, qos=2)

    def request_available_scooters(self):
        """Request a list of available scooters from the server"""
        self.app.setLabel("status", "Requesting available scooters...")
        command = {
            "command": "find_scooters",
            "user_id": self.user_id
            # TODO: Add location data here
        }
        self.publish_command(command)

    def update_scooter_list(self, scooters):
        """Update the GUI with the list of available scooters"""
        self.available_scooters = scooters
        scooter_display = [f"ID: {s['id']} - Battery: {s['battery']}% - Distance: {s['distance']}m" 
                          for s in scooters]
        self.app.updateListBox("scooters", scooter_display)
        self.app.setLabel("status", f"Found {len(scooters)} available scooters")

    def select_scooter(self, selection):
        """Handle selection of a scooter from the list"""
        if selection is not None and len(selection) > 0:
            index = self.app.getListBox("scooters").index(selection[0])
            self.selected_scooter = self.available_scooters[index]
            self.app.setLabel("status", f"Selected scooter {self.selected_scooter['id']}")

    def reserve_scooter(self):
        """Reserve the selected scooter"""
        if self.selected_scooter is None:
            self.app.setLabel("status", "Please select a scooter first")
            return
            
        self.app.setLabel("status", f"Reserving scooter {self.selected_scooter['id']}...")
        command = {
            "command": "reserve_scooter",
            "scooter_id": self.selected_scooter['id'],
            "user_id": self.user_id
        }
        self.publish_command(command)

    def show_reservation_confirmation(self, payload):
        """Handle reservation confirmation from server"""
        if payload.get('success', False):
            self.has_reservation = True
            self.reserved_scooter_id = payload.get('scooter_id')
            self.app.setLabel("status", f"Scooter {self.reserved_scooter_id} reserved successfully!")
            self.app.setButtonState("Unlock Scooter", "normal")
        else:
            self.app.setLabel("status", f"Reservation failed: {payload.get('message', 'Unknown error')}")

    def unlock_scooter(self):
        """Unlock the reserved scooter"""
        if not self.has_reservation:
            self.app.setLabel("status", "No active reservation")
            return
            
        self.app.setLabel("status", f"Unlocking scooter {self.reserved_scooter_id}...")
        command = {
            "command": "unlock_scooter",
            "scooter_id": self.reserved_scooter_id,
            "user_id": self.user_id
            # TODO: Add proximity verification data here
        }
        self.publish_command(command)

    def show_unlock_confirmation(self, payload):
        """Handle unlock confirmation from server"""
        if payload.get('success', False):
            self.app.setLabel("status", f"Scooter {self.reserved_scooter_id} unlocked! Enjoy your ride.")
            self.app.setButtonState("End Ride", "normal")
            self.app.setButtonState("Unlock Scooter", "disabled")
        else:
            self.app.setLabel("status", f"Unlock failed: {payload.get('message', 'Unknown error')}")

    def end_ride(self):
        """End the current ride"""
        if self.reserved_scooter_id is None:
            self.app.setLabel("status", "No active ride")
            return
            
        self.app.setLabel("status", f"Ending ride on scooter {self.reserved_scooter_id}...")
        command = {
            "command": "end_ride",
            "scooter_id": self.reserved_scooter_id,
            "user_id": self.user_id
            # TODO: Add ride metrics here (distance, time, etc.)
        }
        self.publish_command(command)
        
        # TODO: Implement server confirmation handler for end_ride
        # Reset app state for now
        self.has_reservation = False
        self.reserved_scooter_id = None
        self.app.setButtonState("End Ride", "disabled")
        self.app.setButtonState("Unlock Scooter", "disabled")
        self.app.setLabel("status", "Ride ended. Thank you for using E-Scooter!")

    def stop(self):
        """Stop the component."""
        # stop the MQTT client
        self.mqtt_client.loop_stop()


# Set up logging configuration
debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# Start the application
# TODO: Implement user authentication/login before creating the app component
app = EScooterAppComponent()