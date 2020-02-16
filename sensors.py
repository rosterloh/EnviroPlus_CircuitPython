import board
import time

class Sensors:
    def __init__(
        self,
    ):
        self.current_time = time.monotonic()

        # callbacks
        self._on_update_callbacks = []

        self._init_sensors()

    def _init_sensors(self):
        i2c = board.I2C()

    def run(self):
        while True:
            self.current_time = time.monotonic()