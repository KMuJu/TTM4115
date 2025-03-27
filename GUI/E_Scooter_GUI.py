import paho.mqtt.client as mqtt
import logging
from threading import Thread
import json
from appJar import gui
import time

# MQTT Configuration
MQTT_BROKER = 'mqtt.item.ntnu.no'
MQTT_PORT = 1883
MQTT_TOPIC_COMMANDS = 'commands'  # Topic for sending commands to the server
MQTT_TOPIC_AVAILABLE_SCOOTERS = 'available_scooters/'  # Topic for receiving available scooters

# Application States
DEFAULT_VIEW = "Default View"
INSPECT_SCOOTER = "Inspect Scooter"
RESERVE_SCOOTER = "Reserve Scooter"
ACTIVE_SCOOTER = "Active Scooter"
WAITING_FOR_QR_CODE = "Waiting for QR-code Confirmation"

class EScooterAppComponent:
    def __init__(self, user_id="TestUser_GUI"):
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting E-Scooter App Component')
        
        self.user_id = user_id
        self.available_scooters = []
        self.selected_scooter = None
        self.has_reservation = False
        self.reserved_scooter_id = None
        self.current_state = DEFAULT_VIEW  # Initial state
        
        # Create MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        self.mqtt_client.loop_start()
        
        # Create GUI
        self.create_gui()
        
        # Timer for reservation timeout
        self.reservation_timer = None
    
    def on_connect(self, client, userdata, flags, rc):
        self._logger.debug('MQTT connected to {}'.format(client))
        # Subscribe to available scooters
        self.mqtt_client.subscribe(MQTT_TOPIC_AVAILABLE_SCOOTERS)
    
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            self._logger.debug("Received message: {}".format(payload))
            
            if msg.topic == MQTT_TOPIC_AVAILABLE_SCOOTERS:
                self.update_scooter_list(payload)
            elif msg.topic.startswith("scooter/"):
                scooter_id = msg.topic.split("/")[1]
                if msg.topic.endswith("/battery"):
                    self.update_scooter_battery(scooter_id, payload)
                elif msg.topic.endswith("/status"):
                    self.update_scooter_status(scooter_id, payload)
            # Add more message types as needed
        except Exception as e:
            self._logger.error("Error processing message: {}".format(e))
    
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
        self.app.addButton("Scan QR Code", self.scan_qr_code)  # Implemented
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
        self.mqtt_client.publish(MQTT_TOPIC_COMMANDS, payload=payload, qos=2)
    
    def request_available_scooters(self):
        """Request a list of available scooters from the server"""
        self.app.setLabel("status", "Requesting available scooters...")
        command = {
            "command": "find_scooters",
            "user_id": self.user_id
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
            
            # Subscribe to battery and status topics for the selected scooter
            self.mqtt_client.subscribe(f"scooter/{self.selected_scooter['id']}/battery")
            self.mqtt_client.subscribe(f"scooter/{self.selected_scooter['id']}/status")
    
    def update_scooter_battery(self, scooter_id, battery_level):
        """Update the battery level of a specific scooter"""
        if self.selected_scooter and self.selected_scooter['id'] == scooter_id:
            self.selected_scooter['battery'] = battery_level
            self.app.setLabel("status", f"Scooter {scooter_id} battery: {battery_level}%")
    
    def update_scooter_status(self, scooter_id, status):
        """Update the status of a specific scooter"""
        if self.selected_scooter and self.selected_scooter['id'] == scooter_id:
            self.selected_scooter['status'] = status
            self.app.setLabel("status", f"Scooter {scooter_id} status: {status}")
    
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
        
        # Start reservation timer
        self.start_reservation_timer()
    
    def start_reservation_timer(self):
        if self.reservation_timer:
            self.reservation_timer.cancel()
        self.reservation_timer = Thread(target=self.reservation_timeout)
        self.reservation_timer.start()
    
    def reservation_timeout(self):
        time.sleep(300)  # Simulate 5-minute reservation timeout
        if self.has_reservation:
            self.app.setLabel("status", "Reservation timed out. Scooter unreserved.")
            self.cancel_reservation()
    
    def cancel_reservation(self):
        if self.reserved_scooter_id:
            command = {
                "command": "cancel_reservation",
                "scooter_id": self.reserved_scooter_id,
                "user_id": self.user_id
            }
            self.publish_command(command)
            self.has_reservation = False
            self.reserved_scooter_id = None
            self.app.setButtonState("Unlock Scooter", "disabled")
            self.app.setButtonState("End Ride", "disabled")
            self.app.setLabel("status", "Reservation canceled.")
    
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
        }
        self.publish_command(command)
    
    def scan_qr_code(self):
        """Scan QR code to activate the scooter"""
        if not self.has_reservation:
            self.app.setLabel("status", "No active reservation to scan QR code")
            return
        
        self.app.setLabel("status", "Scanning QR code...")
        command = {
            "command": "scan_qr_code",
            "scooter_id": self.reserved_scooter_id,
            "user_id": self.user_id
        }
        self.publish_command(command)
        self.current_state = WAITING_FOR_QR_CODE
    
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
        }
        self.publish_command(command)
        
        # Reset app state
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
app = EScooterAppComponent()