import threading
from sense_hat import SenseHat

sense = SenseHat()

class JoystickThread(threading.Thread):
    def __init__(self, callback):
        super().__init__()
        self.stop_event = threading.Event()
        self.callback = callback

    def run(self):
        """Runs the given function in a loop until stopped."""
        while not self.stop_event.is_set():
            for event in sense.stick.get_events():
                # Check if the joystick was pressed
                    self.callback(event)


    def stop(self):
        """Stops the thread loop."""
        self.stop_event.set()

