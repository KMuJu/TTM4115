import paho.mqtt.client as mqtt # type: ignore
from threading import Thread
import json
import stmpy # type: ignore
import logging

MQTT_BROKER = 'mqtt20.iik.ntnu.no'
MQTT_PORT = 1883

# TODO: choose proper topics for communication
MQTT_TOPIC_INPUT = 'ttm4115/team_19/command'
MQTT_TOPIC_OUTPUT = 'ttm4115/team_19/answer'


class qr_code_scanner:
    def __init__(self, name, duration, user_id, scooter_id):
        """
        The component handle a qr-code activation.
        """
        self._logger = logging.getLogger(__name__)
        self.name = name
        self.duration = duration
        self.user_id = user_id
        self.scooter_id = scooter_id

        # TODO: build the transitions


    def create_machine(timer_name, duration, user_id, scooter_id):
        """
        Create a complete state machine instance for the timer object.
        Note that this method is static (no self argument), since it is a helper
        method to create this object.
        """
        qr_code_handler = qr_code_scanner(name=timer_name, duration=duration, user_id=user_id, scooter_id=scooter_id)
        t0 = {'source': 'initial',
              'target': 'active',
              'effect': 'started'}
        t1 = {
            'source': 'active',
            'target': 'completed',
            'trigger': 't',
            'effect': 'timer_completed'}
        t2 = {
            'source': 'active',
            'trigger': 'report',
            'target': 'active',
            'effect': 'report_status'}
        t3 = {
            'source': 'active',
            'trigger': 'cancel',
            'target': 'completed',
            'effect': 'cancel_timer'
        }
        qr_stm = stmpy.Machine(name=timer_name, transitions=[t0, t1, t2, t3],
                                  obj=qr_code_handler)
        qr_code_handler.stm = qr_stm
        return qr_code_handler    


    # TODO define functions as transition effetcs

    def started(self):
        self.stm.start_timer('t', self.duration * 1000)
        self._logger.debug('New timer {} with duration {} started.'
                           .format(self.name, self.duration))

    def timer_completed(self):
        self._logger.debug('Timer {} expired.'.format(self.name))
        self.stm.terminate()

    def report_status(self):
        self._logger.debug('Checking timer status.')
        time = int(self.stm.get_timer('t') / 1000)
        message = 'Timer {} has about {} seconds left'.format(self.name, time)
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
    
    def cancel_timer(self):
        self._logger.debug('Cancelling timer {}.'.format(self.name))
        message = 'Timer {} has been terminated'.format(self.name)
        self.component.mqtt_client.publish(MQTT_TOPIC_OUTPUT, message)
        self.stm.terminate()
    
#-----------------------------

class TimerManagerComponent:
    """
    The component to manage named timers in a voice assistant.

    This component connects to an MQTT broker and listens to commands.
    To interact with the component, do the following:

    * Connect to the same broker as the component. You find the broker address
    in the value of the variable `MQTT_BROKER`.
    * Subscribe to the topic in variable `MQTT_TOPIC_OUTPUT`. On this topic, the
    component sends its answers.
    * Send the messages listed below to the topic in variable `MQTT_TOPIC_INPUT`.

        {"command": "new_timer", "name": "spaghetti", "duration":50}

        {"command": "status_all_timers"}

        {"command": "status_single_timer", "name": "spaghetti"}

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
        if command == 'new_timer':
            try:
                print(type(self))
                timer_name = payload.get('name')
                duration = int(payload.get('duration'))
                # create a new instance of the timer logic state machine
                timer_stm = TimerLogic.create_machine(timer_name, duration, self)
                # add the machine to the driver to start it
                self.stm_driver.add_machine(timer_stm)
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'status_all_timers':
            s = "List of all timers"
            # We loop over all state machines in the driver. All of them are a
            # timer that we should include in our list that we present to the
            # user.
            for name, stm in self.stm_driver._stms_by_id.items():
                time = int(stm.get_timer('t')/1000)
                s = s + 'Timer {} has about {} seconds left. '.format(stm.id, time)
            self.mqtt_client.publish(MQTT_TOPIC_OUTPUT, s)
        elif command == 'status_single_timer':
            # report the status of a single timer
            try:
                print(type(self))
                timer_name = payload.get('name')
                # send a signal to the corresponding timer state machine to
                # trigger reporting the status.
                self.stm_driver.send('report', timer_name)
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        elif command == 'cancel_timer':
            # report the status of a single timer
            try:
                print(type(self))
                timer_name = payload.get('name')
                # send a signal to the corresponding timer state machine to
                # trigger reporting the status.
                self.stm_driver.send('cancel', timer_name)
            except Exception as err:
                self._logger.error('Invalid arguments to command. {}'.format(err))
        else:
            self._logger.error('Unknown command {}. Message ignored.'.format(command))


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