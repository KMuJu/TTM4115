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


# Oppdater til scooter-per-basis topic
# scooter lager sin topic
# Skrive initialtre til mqtt på boot


class Qr_code_scanner:
    def __init__(self, name, user_id, scooter_id, component):
        """
        The component handle a qr-code activation.
        """
        self._logger = logging.getLogger(__name__)
        self.name = name
        self.user_id = user_id
        self.scooter_id = scooter_id
        self.component = component


    def create_machine(name, user_id, scooter_id, component):
        """
        Create a complete state machine instance for the timer object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        qr_code_handler = Qr_code_scanner(name=name, user_id=user_id, scooter_id=scooter_id,
                                          component=component)
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
            'target': 'final',
            'effect': 'scooter_activated'}
        t3 = {
            'source': 'wait_for_cancellation',
            'trigger': 't1',
            'target': 'final',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'wait_for_cancellation',
            'trigger': 'deactivated',
            'target': 'final',
            'effect': 'data_reset'
        }
        wait_for_activation = {
            'name': 'wait_for_activation',
            }
        wait_for_response = {
            'name': 'wait_for_response',
            'deactivated': 'defer',
            }
        wait_for_cancellation = {
            'name': 'wait_for_cancellation',
            }
        final = {
            'name': 'final',
            }
        
        qr_stm = stmpy.Machine(name=name, transitions=[t0, t1, t2, t3, t4],
                                  obj=qr_code_handler, states=[wait_for_activation, wait_for_response, wait_for_cancellation, final])
        qr_code_handler.stm = qr_stm
        return qr_stm    


    # TODO define functions as transition effetcs

    def initiate_scooter(self):
        self.stm.start_timer('t' , 8 * 1000)
        message = {
            "command": "scan_qr_code",
            "user_id": self.user_id,
        }
        message = json.dumps(message)
        topic = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
        self._logger.debug('Waiting for response started.')

    def scooter_activated(self):
        self._logger.debug('Scooter {} is active for user {}.'.format(self.scooter_id, self.user_id))
        active_stm = Active_scooter.create_machine(name=str(self.scooter_id)+"_active", reservation_time=0, user_id=self.user_id, 
                                                   scooter_id=self.scooter_id, component=self.component)
        self.component.stm_driver.add_machine(active_stm)
        message = "Scooter {} is now active.".format(self.scooter_id)
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
        # message2 = "active"
        # topic2 = "scooters/{}/status".format(self.scooter_id)
        # self.component.mqtt_client.publish(topic2, message2)
        self.stm.terminate()

    def activation_timeout(self):
        self._logger.debug('Scooter timed out. Deactivating scooter {}.'.format(self.scooter_id))
        self.stm.start_timer('t1' , 60 * 1000)
        message = "end_ride"
        topic = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
    
    def data_reset(self):
        self._logger.debug('Scooter {} deactivated and added back to pool.'.format(self.scooter_id))
        message = "available"
        topic = "scooters/{}/status".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
        message2 = "System could not activate scooter {}. Please try again.".format(self.scooter_id)
        topic2 = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic2, message2)
        self.stm.terminate()

# -----------------------------

class Reserve_scooter:
    """
    The component handles a reservation and waits for scooter activation.
    """
    def __init__(self, name, start_time, user_id, scooter_id, component):
        self._logger = logging.getLogger(__name__)
        self.start_time = start_time
        self.name = name
        self.component = component
        self.user_id = user_id
        self.scooter_id = scooter_id
        self.start_time = start_time

    def create_machine(name, start_time, user_id, scooter_id, component):
        """
        Create a complete state machine instance for the reservation object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        reservation_handler = Reserve_scooter(name=name, start_time=start_time, user_id=user_id,
                                               scooter_id=scooter_id, component=component)
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
            'target': 'final',
            'effect': 'scooter_activated'}
        t3 = {
            'source': 'wait_for_activation',
            'trigger': 't1',
            'target': 'final',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'wait_for_activation',
            'trigger': 'cancel_reservation',
            'target': 'final',
            'effect': 'reservation_cancel'
        }
        qr_stm = stmpy.Machine(name=name, transitions=[t0, t1, t2, t3, t4],
                                  obj=reservation_handler)
        reservation_handler.stm = qr_stm
        return qr_stm    


    # TODO define functions as transition effetcs

    def start_timers(self):
        self._logger.debug('Scooter {} is reserved for user {}.'.format(self.scooter_id, self.user_id))
        self.stm.start_timer('t1' , 10 * 60 * 1000)
        self.stm.start_timer('t2' , 5 * 60 * 1000)
        message = {
            "command": "reserved",
            "user_id": self.user_id,
        }
        message = json.dumps(message)
        topic = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
        message2 = "Scooter {} is reserved for you.".format(self.scooter_id)
        topic2 = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic2, message2)

    def reservation_cancel(self):
        # self.logger.debug('Reservation cancelled for scooter {}.'.format(self.scooter_id))
        message = "cancel"
        topic = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
        message2 = "Reservation cancelled."
        topic2 = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic2, message2)
        self.stm.terminate()

    def scooter_activated(self):
        self._logger.debug('Scooter {} is active for user {}.'.format(self.scooter_id, self.user_id))
        message = "Scooter {} is now active.".format(self.scooter_id)
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
        # message2 = "active"
        # topic2 = "scooters/{}/status".format(self.scooter_id)
        # self.component.mqtt_client.publish(topic2, message2)
        active_stm = Active_scooter.create_machine(name=str(self.scooter_id)+"_active", reservation_time=(time.time()-self.start_time), user_id=self.user_id, 
                                                   scooter_id=self.scooter_id, component=self.component)
        self.component.stm_driver.add_machine(active_stm)
        self.stm.terminate()

    def warn_user(self):
        self._logger.debug('User {} has spent half their reservation time for scooter {}.'.format(self.user_id, self.scooter_id))
        message = "You have spent half your reservation time. Please activate the scooter."
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
    
    def data_reset(self):
        self._logger.debug('Scooter {} deactivated and added back to pool.'.format(self.scooter_id))
        # Set MQTT topic
        message = "Your reservation has timed out. Scooter {} is now available for other users.".format(self.scooter_id)
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
        # Clean up of scooter parameters
        message2 = "cancel"
        topic2 = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic2, message2)
        self.stm.terminate()
    
#-----------------------------

class Active_scooter:
    def __init__(self, name, reservation_time, user_id, scooter_id, component):
        """
        The component handle a qr-code activation.
        """
        self._logger = logging.getLogger(__name__)
        self.user_id = user_id
        self.name = name
        self.scooter_id = scooter_id
        self.reservation_time = reservation_time
        self.start_time = time.time()
        self.component = component

    def create_machine(name, reservation_time, user_id, scooter_id, component):
        """
        Create a complete state machine instance for the reservation object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        active_handler = Active_scooter(name=name, reservation_time=reservation_time,
                                         user_id=user_id, scooter_id=scooter_id, component=component)
        t0 = {'source': 'initial',
              'target': 'active_scooter'}
        t1 = {
            'source': 'active_scooter',
            'target': 'final',
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
            'target': 'final',
            'effect': 'data_reset'
        }
        t4 = {
            'source': 'unactive',
            'trigger': 'qr_initiation',
            'target': 'final',
            'effect': 'qr_code_starter'
        }
        qr_stm = stmpy.Machine(name=scooter_id+"_active", transitions=[t0, t1, t2, t3, t4],
                                  obj=active_handler)
        active_handler.stm = qr_stm
        return qr_stm    



    def deactivate_scooter(self):
        self._logger.debug('Trip complete for {} for user {}. Resetting Scooter'.format(self.scooter_id, self.user_id))
        trip_time = time.time() - self.start_time + self.reservation_time
        message = "Trip complete. You have used the scooter for {} seconds. You have spent {}kr".format(int(trip_time), int(trip_time*0.5//60))
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
        message2 = "end_ride"
        topic2 = "scooters/{}/commands".format(self.scooter_id)
        self.component.mqtt_client.publish(topic2, message2)
        self.stm.terminate()

    def grace_wait(self):
        trip_time = time.time() - self.start_time + self.reservation_time
        self._logger.debug('Scooter {} reports inactivity. User {} billed {}kr.'.format(self.scooter_id, self.user_id, trip_time*0.5//60))
        message = "Your scooter {} has been inactive for 5 minutes. You will be billed {}kr.".format(self.scooter_id, trip_time*0.5//60)
        topic = "users/{}".format(self.user_id)
        self.component.mqtt_client.publish(topic, message)
        self.stm.start_timer('t1' ,  60 * 1000)

    
    def data_reset(self):
        self._logger.debug('Scooter {} added back to pool.'.format(self.scooter_id))
        message = "available"
        topic = "scooters/{}/status".format(self.scooter_id)
        self.component.mqtt_client.publish(topic, message)
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
        # is necessary since the payload is a byte array
        # and we need to decode it to a string
        if msg.topic.startswith("scooters/") and msg.topic.endswith("/status"):
            scooter_id = msg.topic.split('/')[1]
            try:
                payload = msg.payload.decode("utf-8")
                is_available = True if payload == "available" else False
                # If the scooter is available, publish it to a new topic
                if is_available:
                    if scooter_id not in self.available_scooters:
                        self.available_scooters.append(scooter_id)
                else:
                    if scooter_id in self.available_scooters:
                        self.available_scooters.remove(scooter_id)  
                available_topic = "available_scooters"
                available_message = str(self.available_scooters)
                self.mqtt_client.publish(available_topic, available_message)
                self._logger.debug(f"Payload: {payload}")
                self._logger.debug(f"Published available scooter: {available_message}")

                if payload == 'active':
                    try:
                        print(type(self))
                        # push resrvation handler along
                        if scooter_id+"_reservation_machine" in self.stm_driver._stms_by_id:
                            self.stm_driver.send('activate_scooter', scooter_id+"_reservation_machine")
                        elif scooter_id+"_qr" in self.stm_driver._stms_by_id:
                            self.stm_driver.send('activate_scooter', scooter_id+"_qr")
                        else:
                            self._logger.error('No machine to send to. {}'.format(scooter_id))
                    except Exception as err:
                        self._logger.error('Invalid arguments to command. {}'.format(err))
                elif payload == 'idle':
                # Scooter reports inactivity
                    try:
                        print(type(self))
                        # push resrvation handler along
                        # elif self.stm_driver.get_machine(scooter_id+"_reservation_machine") is not None:
                        #     self.stm_driver.send('activate_scooter', scooter_id+"_reservation_machine")
                        try:
                            self.stm_driver.send('deactivate', scooter_id+"_qr")
                        except Exception as err:
                            print("hello")
                            try:
                                self.stm_driver.send('scooter_inactive', scooter_id+"_active")
                            except Exception as err:
                                print("hello")
                                message = "available"
                                topic = "scooters/{}/status".format(self.scooter_id)
                                self.component.mqtt_client.publish(topic, message)
                                self._logger.error('Relevant machine not found. Scooter reset. {}'.format(msg.topic, err))
                            
                            print("hello")
                        # elif self.stm_driver.get_machine(scooter_id+"_reservation_machine") is not None:
                        #     self.stm_driver.send('activate_scooter', scooter_id+"_reservation_machine")
                            
                    
                    except Exception as err:
                        self._logger.error('Invalid arguments to command. {}'.format(err))
                elif payload == 'bill_user':
                # Scooter reports inactivity
                    try:
                        print(type(self))
                        # push resrvation handler along
                        self.stm_driver.send('trip_complete', scooter_id+"_active")
                    except Exception as err:
                        self._logger.error('Invalid arguments to command. {}'.format(err))
            except Exception as err:
                self._logger.error(f"Failed to process message: {err}")

        # if msg.topic.startswith("scooters/") and msg.topic.endswith("/commands"):
        #     # TODO handle scooter commands
        #     scooter_id = msg.topic.split('/')[1]
        #     try:
        #         payload = json.loads(msg.payload.decode("utf-8"))
        #         command = payload.get("command")
        #         self._logger.debug('Command in message is {}'.format(command))
        #         if command == 'scooter_active':
        #             try:
        #                 print(type(self))
        #                 # push resrvation handler along
        #                 self.stm_driver.send('activate_scooter', scooter_id+"_reservation_machine")
        #             except Exception as err:
        #                 self._logger.error('Invalid arguments to command. {}'.format(err))
        #         elif command == 'scooter_active_qr':
        #             try:
        #                 print(type(self))
        #                 scooter_id = payload.get('serialnumber')
        #                 # push resrvation handler along
        #                 self.stm_driver.send('activate_scooter', scooter_id+"_qr")
        #             except Exception as err:
        #                 self._logger.error('Invalid arguments to command. {}'.format(err))
        #         elif command == 'bill_user':
        #         # Scooter reports inactivity
        #             try:
        #                 print(type(self))
        #                 scooter_id = payload.get('serialnumber')
        #                 # push resrvation handler along
        #                 self.stm_driver.send('scooter_inactive', scooter_id+"_active")
        #             except Exception as err:
        #                 self._logger.error('Invalid arguments to command. {}'.format(err))
        #     except Exception as err:
        #         self._logger.error(f"Failed to process message: {err}")
            
            

        if msg.topic == MQTT_TOPIC_INPUT:
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except Exception as err:
                self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err))
                self._logger.debug('Message was {}'.format(msg.payload.decode("utf-8")))
                return
            command = payload.get('command')
            self._logger.debug('Command in message is {}'.format(command))
            if command == 'user_reserve_scooter':
                try:
                    print(type(self))
                    user_id = payload.get('user')
                    scooter_id = payload.get('serialnumber')
                    name = str(scooter_id)+"_reservation_machine"
                    # build reservation machine
                    reservation_stm = Reserve_scooter.create_machine(name, time.time(), user_id, scooter_id, self)
                    # add the machine to the driver to start it
                    self.stm_driver.add_machine(reservation_stm)
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))
            elif command == 'qr_code_activation':
                try:
                    print(type(self))
                    user_id = payload.get('user')
                    scooter_id = payload.get('serialnumber')
                    name = str(scooter_id)+"_qr"
                    # build qr-machine
                    qr_stm = Qr_code_scanner.create_machine(name, user_id, scooter_id, self)
                    # add the machine to the driver to start it
                    self.stm_driver.add_machine(qr_stm)
                except Exception as err:
                    self._logger.error('Invalid arguments to command. {}'.format(err))
            elif command == 'user_cancel_reservation':
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
        # self.mqtt_client.subscribe("scooters/+/commands")
        self.available_scooters = []


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


debug_level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(debug_level)
ch = logging.StreamHandler()
ch.setLevel(debug_level)
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

t = Server_listener()
