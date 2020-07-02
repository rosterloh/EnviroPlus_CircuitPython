import board
import time
from digitalio import DigitalInOut, Direction
from analogio import AnalogIn

import adafruit_logging as logging
from adafruit_bme280 import Adafruit_BME280_I2C
from adafruit_pm25 import PM25_UART
from adafruit_sgp30 import Adafruit_SGP30
from ltr559 import LTR559

WAITING = 0
READING = 1
UPDATED = 2
CALIBRATING = 3
ERROR = 4

class SensorData():
    def __init__(self):
        self.temperature = 0.0
        self.humidity = 0.0
        self.pressure = 0.0
        self.altitiude = 0.0
        self.pm1 = 0.0
        self.pm2_5 = 0.0
        self.pm10 = 0.0
        self.eco2 = 0
        self.tvoc = 0
        self.light = 0.0
        self.battery_voltage = 0

    def __repr__(self):
        fmt = """
Temperature: {temp:.02f} C
Humidity:    {hum:.02f} %
Pressure:    {pres:.02f} hPa
Altitude:    {alt:.02f} m
PM1.0:       {p1:.02f} ug/m3
PM2.5:       {p2:.02f} ug/m3
PM10:        {p10:.02f} ug/m3
eCO2:        {co2:d} ppm
TVOC:        {voc:d} ppb
Light:       {lux:.02f} lux
Battery:     {bat:d} mV
"""
        return fmt.format(
            temp=self.temperature,
            hum=self.humidity,
            pres=self.pressure,
            alt=self.altitiude,
            p1=self.pm1,
            p2=self.pm2_5,
            p10=self.pm10,
            co2=self.eco2,
            voc=self.tvoc,
            lux=self.light,
            bat=self.battery_voltage)

    __str__ = __repr__

class Sensors:
    def __init__(
        self,
        update_timeout=2.0,
        debug=False
    ):
        self.current_time = time.monotonic()
        self.logger = logging.getLogger('enviro+')
        self.state = WAITING
        self.prev_state = self.state
        self.readings = SensorData()
        self.update_timeout = update_timeout
        self.calibration_timeout = 30.0 * 60
        self.last_update_time = 0
        self.last_calibration_time = 0
        self.debug = debug

        # callbacks
        self._on_update_callbacks = []

        self._init_sensors()

    def _scan_bus(self, i2c):
        while not i2c.try_lock():
            pass

        if self.debug:
            self.logger.debug("I2C addresses found: {}".format([hex(device_address)
                                   for device_address in i2c.scan()]))

        i2c.unlock()

    def _init_sensors(self):
        i2c = board.I2C()
        
        if self.debug:
            self._scan_bus(i2c)

        self.bme280 = Adafruit_BME280_I2C(i2c, address=0x76)
        self.bme280.sea_level_pressure = 1026

        try:
            self.sgp30 = Adafruit_SGP30(i2c)
            self.sgp30.iaq_init()
            self.sgp30.set_iaq_baseline(0x8973, 0x8AAE)
        except ValueError as err: 
            self.logger.warning("SGP30 not found")
            self.sgp30 = None

        # self._pm_reset = DigitalInOut(board.D6)
        # self._pm_enable = DigitalInOut(board.D5)
        # self._pm_enable.direction = Direction.OUTPUT
        # self._pm_enable.value = True

        # uart = board.UART()
        # uart.baudrate = 9600
        # uart.timeout = 4

        # self.pms5003 = PM25_UART(uart, self._pm_reset)
        self.pms5003 = None
        
        self.ltr559 = LTR559(i2c_dev=i2c)

        self.battery = AnalogIn(board.VOLTAGE_MONITOR)
        self.divider_ratio = 2

    def run(self):
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
            
            self.readings = SensorData()

        elif self.state == READING:
            self.readings.temperature = self.bme280.temperature
            self.readings.humidity = self.bme280.humidity
            self.readings.pressure = self.bme280.pressure
            self.readings.altitiude = self.bme280.altitude
            
            if self.pms5003:
                try:
                    data = self.pms5003.read()
                    self.readings.pm1 = data["pm10 env"]
                    self.readings.pm2_5 = data["pm25 env"]
                    self.readings.pm10 = data["pm100 env"]
                except RuntimeError as err:
                    self.logger.error("{0}".format(err))
            
            if self.sgp30:
                self.readings.eco2 = self.sgp30.eCO2
                self.readings.tvoc = self.sgp30.TVOC
            
            self.ltr559.update_sensor()
            self.readings.light = self.ltr559.get_lux()

            battery_voltage = (
                self.battery.value
                / 2 ** 16
                * self.divider_ratio
                * self.battery.reference_voltage  # pylint: disable=no-member
            )
            self.readings.battery_voltage = int(battery_voltage * 1000)

            if self.debug:
                print(self.readings)

            self.last_update_time = self.current_time
            self.state = UPDATED

        elif self.state == CALIBRATING:
            if self.sgp30:
                print(
                    "**** Baseline values: eCO2 = 0x%x, TVOC = 0x%x"
                    % (sgp30.baseline_eCO2, sgp30.baseline_TVOC)
                )
            self.last_calibration_time = self.current_time
            self.state = WAITING

        elif self.state == WAITING:
            update_elapsed = self.current_time - self.last_update_time
            calibrate_elapsed = self.current_time - self.last_calibration_time
            if update_elapsed > self.update_timeout:
                self.state = READING
            elif calibrate_elapsed > self.calibration_timeout:
                self.state = CALIBRATING

    def _notify_callbacks(self):
        state_changed = self.prev_state != self.state
        self.prev_state = self.state
        if not state_changed:
            return

        if self.state == UPDATED:
            for on_update_callback in self._on_update_callbacks:
                on_update_callback(self.readings)
