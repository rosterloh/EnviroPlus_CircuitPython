import board
import time
from busio import I2C
from digitalio import DigitalInOut

import adafruit_bme280
import adafruit_logging as logging
from pms5003 import PMS5003
from ltr559 import LTR559

WAITING = 0
READING = 1
UPDATED = 2
ERROR = 3

class Sensors:
    def __init__(
        self,
        update_timeout = 2.0,
        debug=False
    ):
        self.current_time = time.monotonic()
        self.logger = logging.getLogger('enviro+')
        self.state = WAITING
        self.prev_state = self.state
        self.readings = {}
        self.update_timeout = update_timeout
        self.last_update_time = 0
        self.debug = debug

        # callbacks
        self._on_update_callbacks = []

        self._init_sensors()

    def _scan_bus(self, i2c):
        while not i2c.try_lock():
            pass

        self.logger.debug("I2C addresses found: {}".format([hex(device_address)
                                   for device_address in i2c.scan()]))

        i2c.unlock()

    def _init_sensors(self):
        i2c = I2C(board.SCL, board.SDA)
        
        if self.debug:
            self._scan_bus(i2c)

        self.bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
        self.pms5003 = PMS5003(baudrate=9600, pin_enable=board.D5 , pin_reset=board.D6)
        self.ltr559 = LTR559(i2c_dev=i2c)

    def run(self):
        while True:
            self.current_time = time.monotonic()
            self._update_values()
            self._notify_callbacks()
            # self._update_display()

    def on_update(self, func):
        self.add_on_update(func)
        return func

    def add_on_update(self, new_callback):
        self._on_update_callbacks.append(new_callback)

    def _update_values(self):
        if self.state == UPDATED:
            self.state = WAITING
            
            self.readings = {}

        elif self.state == READING:
            self.readings['temperature'] = self.bme280.temperature
            self.readings['humidity'] = self.bme280.humidity
            self.readings['pressure'] = self.bme280.pressure
            self.readings['altitiude'] = self.bme280.altitude
            try:
                data = self.pms5003.read()
                self.readings['PM1.0'] = data.pm_ug_per_m3(1.0)
                self.readings['PM2.5'] = data.pm_ug_per_m3(2.5)
                self.readings['PM10'] = data.pm_ug_per_m3(10)
            except RuntimeError as err:
                self.logger.error("{0}".format(err))

            self.ltr559.update_sensor()
            self.readings['light'] = self.ltr559.get_lux()

            self.last_update_time = self.current_time
            self.state = UPDATED

        elif self.state == WAITING:
            update_elapsed = self.current_time - self.last_update_time
            if update_elapsed > self.update_timeout:
                self.state = READING

    def _notify_callbacks(self):
        state_changed = self.prev_state != self.state
        self.prev_state = self.state
        if not state_changed:
            return

        if self.state == UPDATED:
            for on_update_callback in self._on_update_callbacks:
                on_update_callback(self.readings)
