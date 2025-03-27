from sense_hat import SenseHat
from time import sleep
import threading

sense = SenseHat()

red = (255, 0, 0)
black = (0, 0, 0)
white = (255, 255, 255)

class RedLightThread(threading.Thread):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.stop_event = threading.Event()

    def run(self):
        """Runs the given function in a loop until stopped."""
        while not self.stop_event.is_set():
            sense.clear(red)
            sleep(1)
            sense.clear(black)
            sleep(1)

    def set_and_run(self, type_str):
        """Sets the function to run and starts the thread."""
        match type_str:
            case "red":
                self.function = red_light
            case "driving_lights":
                self.function = lambda: sense.clear(white)
            case _:
                print("Not implemented")
                self.function = lambda : 0 

        self.run()

    def stop(self):
        """Stops the thread loop."""
        self.stop_event.set()

