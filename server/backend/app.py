import paho.mqtt.client as mqtt # type: ignore
from threading import Thread
import json
import stmpy # type: ignore
import logging
import time

MQTT_BROKER = 'mqtt-broker'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'commands'
MQTT_TOPIC_OUTPUT = 'debug'


class qr_code_scanner:
    def __init__(self, user_id, scooter_id):
        """
        The component handle a qr-code activation.
        """
        self._logger = logging.getLogger(__name__)
  
        self.user_id = user_id
        self.scooter_id = scooter_id

        # TODO: build the transitions


    def create_machine(user_id, scooter_id):
        """
        Create a complete state machine instance for the timer object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        qr_code_handler = qr_code_scanner(user_id=user_id, scooter_id=scooter_id)
        t0 = {'source': 'initial',
              'target': 'wait_for_response',
              'effect': 'initiate_scooter'}
        t1 = {
            'source': 'wait_for_response',
            'target': 'wait_for_cancellation',
            'trigger': 't',
            'effect': 'activation_timeout'}
        t2 = {
            'source': 'wait_for_response',
            'trigger': 'activate_scooter',
            'target': 'confirmed active',
            'effect': 'scooter_activated'}
        t3 = {
            'source': 'wait_for_cancellation',
            'trigger': 't1',
            'target': 'reset_scooter',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'wait_for_cancellation',
            'trigger': 'deactivated',
            'target': 'reset_scooter',
            'effect': 'data_reset'
        }
        qr_stm = stmpy.Machine(name=scooter_id+"_qr", transitions=[t0, t1, t2, t3, t4],
                                  obj=qr_code_handler)
        qr_code_handler.stm = qr_stm
        return qr_code_handler    


    # TODO define functions as transition effetcs

    def initiate_scooter(self):
        self.stm.start_timer('t' , 8 * 1000)
        # Example MQTT: self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
        # MQTT message to activate scooter
        # MQTT to remove scooter from available list

        self._logger.debug('Waiting for response started.'
                           .format(self.name, self.duration))

    def scooter_activated(self):
        self._logger.debug('Scooter {} is active for user {}.'.format(self.scooter_id, self.user_id))
        # Code to activate enabled scooter machine
        self.stm.terminate()

    def activation_timeout(self):
        self._logger.debug('Activated timed out. Deactivating scooter {}.'.format(self.scooter_id))
        self.stm.start_timer('t1' , 60 * 1000)
        # Publish message to scooter for deactivation
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
    
    def data_reset(self):
        self._logger.debug('Scooter {} deactivated and added back to pool.'.format(self.scooter_id))
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
        self.stm.terminate()

# -----------------------------

class reserve_scooter:
    def __init__(self, user_id, scooter_id):
        """
        The component handles a reservation and waits for scooter activation.
        """
        self._logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.scooter_id = scooter_id

        # TODO: build the transitions


    def create_machine(user_id, scooter_id):
        """
        Create a complete state machine instance for the reservation object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        reservation_handler = reserve_scooter(user_id=user_id, scooter_id=scooter_id)
        t0 = {'source': 'initial',
              'target': 'wait_for_activation',
              'effect': 'start_timers'}
        t1 = {
            'source': 'wait_for_activation',
            'target': 'wait_for_activation',
            'trigger': 't2',
            'effect': 'warn_user'}
        t2 = {
            'source': 'wait_for_activation',
            'trigger': 'activate_scooter',
            'target': 'active',
            'effect': 'scooter_activated'}
        t3 = {
            'source': 'wait_for_activation',
            'trigger': 't1',
            'target': 'reset_scooter',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'wait_for_activation',
            'trigger': 'cancel_reservation',
            'target': 'reset_scooter',
            'effect': 'reservation_cancel'
        }
        qr_stm = stmpy.Machine(name=scooter_id+"_reservation_machine", transitions=[t0, t1, t2, t3, t4],
                                  obj=reservation_handler)
        reservation_handler.stm = qr_stm
        return reservation_handler    


    # TODO define functions as transition effetcs

    def start_timers(self):
        self._logger.debug('Scooter {} is reserved for user {}.'.format(self.scooter_id, self.user_id))
        self.stm.start_timer('t1' , 10 * 60 * 1000)
        self.stm.start_timer('t2' , 5 * 60 * 1000)
        # Code to activate proximity activation
        # MQTT message to user that they have reserved

    def reservation_cancel(self):
        self.logger.debug('Reservation cancelled for scooter {}.'.format(self.scooter_id))
        # Code to cancel reservation
        # MQTT message to user that they have cancelled
        self.stm.terminate()

    def scooter_activated(self):
        self._logger.debug('Scooter {} is active for user {}.'.format(self.scooter_id, self.user_id))
        # Code to activate enabled scooter machine passing reservation_duration as 10 minutes - t1
        # MQTT message to user that they have activated the scooter
        self.stm.terminate()

    def warn_user(self):
        self._logger.debug('User {} has spent half their reservation time for scooter {}.'.format(self.user_id, self.scooter_id))
        # Publish message to scooter for deactivation
        # Set MQTT topic
        message = "You have spent half your reservation time. Please activate the scooter."
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
    
    def data_reset(self):
        self._logger.debug('Scooter {} deactivated and added back to pool.'.format(self.scooter_id))
        # Set MQTT topic
        message = "Your reservation has timed out. Scooter {} is now available for other users.".format(self.scooter_id)
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
        # Clean up of scooter parameters
        self.stm.terminate()
    
#-----------------------------

class active_scooter:
    def __init__(self, reservation_time, user_id, scooter_id):
        """
        The component handle a qr-code activation.
        """
        self._logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.scooter_id = scooter_id
        self.reservation_time = reservation_time
        self.start_time = time.time()

        # TODO: build the transitions


    def create_machine(reservation_time, user_id, scooter_id):
        """
        Create a complete state machine instance for the reservation object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        active_handler = active_scooter(name=scooter_id+"_active", reservation_time=reservation_time, user_id=user_id, scooter_id=scooter_id)
        t0 = {'source': 'initial',
              'target': 'active_scooter'}
        t1 = {
            'source': 'active_scooter',
            'target': 'trip_complete',
            'trigger': 'trip_complete',
            'effect': 'deactivate_scooter'}
        t2 = {
            'source': 'active_scooter',
            'trigger': 'scooter_inactive',
            'target': 'unactive',
            'effect': 'grace_wait'}
        t3 = {
            'source': 'unactive',
            'trigger': 't1',
            'target': 'reset_scooter',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'unactive',
            'trigger': 'qr_initiation',
            'target': 'qr_start_scooter',
            'effect': 'qr_code_starter'
        }
        qr_stm = stmpy.Machine(name=scooter_id+"_active", transitions=[t0, t1, t2, t3, t4],
                                  obj=active_handler)
        active_handler.stm = qr_stm
        return active_handler    


    # TODO define functions as transition effetcs

    def deactivate_scooter(self):
        self._logger.debug('Trip complete for {} for user {}. Resetting Scooter'.format(self.scooter_id, self.user_id))
        trip_time = time.time() - self.start_time + self.reservation_time
        message = "Trip complete. You have used the scooter for {} seconds.".format(trip_time)
        # Set MQTT topic
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
        # MQTT message to user that they have reserved
        # Reset scooter
        self.stm.terminate()

    def grace_wait(self):
        self._logger.debug('Scooter {} reports inactivity. User {} billed.'.format(self.scooter_id, self.user_id))
        # Prepare MQTT message to user about inactivity
        # Set scooter to available, but not in available scooter list
        # Bill user
        # Start timer 5 min

    def qr_code_starter(self):
        self._logger.debug('Scooter {} activation by QR-code started.'.format(self.scooter_id))
        # Start qr_code scanner
    
    def data_reset(self):
        self._logger.debug('Scooter {} added back to pool.'.format(self.scooter_id))
        # Set MQTT topic
        # Add scooter to available list
        self.stm.terminate()
    
#-----------------------------

class Server_listener:
    """
    The component is made to manage the handling of multiple scooters.

    """

    def on_connect(self, client, userdata, flags, rc):
        # we just log that we are connected
        self._logger.debug('MQTT connected to {}'.format(client))

    def on_message(self, client, userdata, msg):
        """
        Processes incoming MQTT messages.

        We assume the payload of all received MQTT messages is an UTF-8 encoded
        string, which is formatted as a JSON object. The JSON object contains
        a field called `command` which identifies what the message should achieve.

        As a reaction to a received message, we can for example do the following:

        * create a new state machine instance to handle the incoming messages,
        * route the message to an existing state machine session,
        * handle the message right here,
        * throw the message away.

        """
        self._logger.debug('Incoming message to topic {}'.format(msg.topic))

        # TODO unwrap JSON-encoded payload
        
        # TODO extract command

        # TODO determine what to do
        # encdoding from bytes to string. This
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
            return
        command = payload.get('command')
        self._logger.debug('Command in message is {}'.format(command))
        if command == 'user_reserve_scooter':
            try:
                print(type(self))
                user_id = payload.get('user')
                scooter_id = payload.get('serialnumber')
                # build reservation machine
                reservation_stm = reserve_scooter.create_machine(user_id, scooter_id, self)
                # add the machine to the driver to start it
                self.stm_driver.add_machine(reservation_stm)
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'qr_code_activation':
            try:
                print(type(self))
                user_id = payload.get('user')
                scooter_id = payload.get('serialnumber')
                # build qr-machine
                qr_stm = qr_code_scanner.create_machine(user_id, scooter_id, self)
                # add the machine to the driver to start it
                self.stm_driver.add_machine(qr_stm)
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'scooter_active':
            try:
                print(type(self))
                scooter_id = payload.get('serialnumber')
                # push resrvation handler along
                self.stm_driver.send('activate_scooter', scooter_id+"_reservation_machine")
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'scooter_active_qr':
            try:
                print(type(self))
                scooter_id = payload.get('serialnumber')
                # push resrvation handler along
                self.stm_driver.send('activate_scooter', scooter_id+"_qr")
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'user_cancels_reservation':
            try:
                print(type(self))
                scooter_id = payload.get('serialnumber')
                # push resrvation handler along
                self.stm_driver.send('cancel_reservation', scooter_id+"_reservation_machine")
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'park_scooter':
            # User ends trip
            try:
                print(type(self))
                scooter_id = payload.get('serialnumber')
                # push resrvation handler along
                self.stm_driver.send('trip_complete', scooter_id+"_active")
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'scooter_inactive':
            # Scooter reports inactivity
            try:
                print(type(self))
                scooter_id = payload.get('serialnumber')
                # push resrvation handler along
                self.stm_driver.send('scooter_inactive', scooter_id+"_active")
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        else:
            self._logger.error('Command {} not recognized. Ignoring message.'.format(command))
            


    def __init__(self):
        """
        Start the component.

        ## Start of MQTT
        We subscribe to the topic(s) the component listens to.
        The client is available as variable `self.client` so that subscriptions
        may also be changed over time if necessary.

        The MQTT client reconnects in case of failures.

        ## State Machine driver
        We create a single state machine driver for STMPY. This should fit
        for most components. The driver is available from the variable
        `self.driver`. You can use it to send signals into specific state
        machines, for instance.

        """
        # get the logger object for the component
        self._logger = logging.getLogger(__name__)
        print('logging under name {}.'.format(__name__))
        self._logger.info('Starting Component')

        # create a new MQTT client
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT))
        self.mqtt_client = mqtt.Client()
        # callback methods
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        # Connect to the broker
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe("scooters/+/status")

        self.mqtt_client.subscribe(MQTT_TOPIC_INPUT)
        # start the internal loop to process MQTT messages
        self.mqtt_client.loop_start()

        # we start the stmpy driver, without any state machines for now
        self.stm_driver = stmpy.Driver()
        self.stm_driver.start(keep_active=True)
        self._logger.debug('Component initialization finished')


    def stop(self):
        """
        Stop the component.
        """
        # stop the MQTT client
        self.mqtt_client.loop_stop()

        # stop the state machine Driver
        self.stm_driver.stop()

#-----------------------------


# Håndtere QR-kode-scanning
# Blokkere om reserver/aktiv


# Fjerne/legge til scootere til tilgjengelige scootere liste
# Blokkere reservering av en scooter som allerede er reservert/aktiv