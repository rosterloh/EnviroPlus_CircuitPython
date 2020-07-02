import gc
import time
import board
from digitalio import DigitalInOut
import json
import rtc

from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import PWMOut
from adafruit_esp32spi.adafruit_esp32spi_wifimanager import ESPSPI_WiFiManager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_logging as logging
import adafruit_minimqtt as MQTT
import adafruit_requests as requests
import adafruit_rgbled

try:
    from secrets import secrets
except ImportError:
    print("secrets.py not found!")
    raise

TIME_SERVICE = (
    "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
)
# our strftime is %Y-%m-%d %H:%M:%S.%L %j %u %z %Z see http://strftime.net/ for decoding details
# See https://apidock.com/ruby/DateTime/strftime for full options
TIME_SERVICE_STRFTIME = (
    "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"
)

class NetworkService:
    def __init__(
        self,
        device_name="EnviroPlus",
        debug=False
    ):
        self.current_time = time.monotonic()
        self.logger = logging.getLogger('enviro+')
        self.device_name = device_name 
        self.debug = debug
        self.connected = False

        if self.debug:
            self.logger.set_logger_level("DEBUG")
        else:
            self.logger.set_logger_level("INFO")

        self._setup_wifi()

    def _setup_wifi(self):
        esp32_cs = DigitalInOut(board.D13)
        esp32_reset = DigitalInOut(board.D12)
        esp32_ready = DigitalInOut(board.D11)
        esp32_gpio0 = DigitalInOut(board.D10)
        
        spi = board.SPI()
        self.esp = adafruit_esp32spi.ESP_SPIcontrol(
            spi, esp32_cs, esp32_ready, esp32_reset, esp32_gpio0
        )
        # self._esp._debug = 1

        for _ in range(3): # retries
            try:
                self.logger.info("ESP firmware: " + ''.join([chr(b) for b in self.esp.firmware_version]))
                break
            except RuntimeError:
                self.logger.warning("Retrying ESP32 connection")
                time.sleep(1)
                self.esp.reset()
        else:
            self.logger.error("Was not able to find ESP32")
            return

        if self.debug:
            while not self.esp.is_connected:
                try:
                    self.esp.connect(secrets)
                    self.logger.debug("IP address is {0}".format(self.esp.pretty_ip(self.esp.ip_address)))
                except RuntimeError as error:
                    self.logger.error("Could not connect to internet. {0}".format(error))            

        RED_LED = PWMOut.PWMOut(self.esp, 26)
        GREEN_LED = PWMOut.PWMOut(self.esp, 27)
        BLUE_LED = PWMOut.PWMOut(self.esp, 25)
        status_light = adafruit_rgbled.RGBLED(RED_LED, BLUE_LED, GREEN_LED)
        self.wifi = ESPSPI_WiFiManager(self.esp, secrets, status_light) #, debug=True)

        self.wifi.connect()

        self.get_local_time()

        # MQTT.set_socket(socket, self.esp)

        # self.mqtt_client = MQTT.MQTT(broker=secrets['broker'],
        #                              username=secrets['user'],
        #                              password=secrets['pass'],
        #                              is_ssl=False)

        if self.debug:
            self.mqtt_client.set_logger_level("DEBUG")
 
        # self.mqtt_client.on_message = self._on_message
        # self.mqtt_client.on_connect = self._on_connect
        # self.mqtt_client.on_disconnect = self._on_disconnected
        # self.mqtt_client.on_publish = self._on_publish
        # self.mqtt_client.on_subscribe = self._on_subscribe
        # self.mqtt_client.on_unsubscribe = self._on_unsubscribe
        
        # self.mqtt_client.connect()
        # self.publish_topic_info()
        # self.mqtt_client.subscribe('homeassistant/sensor/{0}/state'.format(self.device_name))

    def _on_message(self, client, topic, message):
        self.logger.debug('MESSAGE: {0}: {1}'.format(topic, message))
    
    def _on_connect(self, client, userdata, flags, rc):
        self.logger.debug('CONNECT: Flags: {0} RC: {1}'.format(flags, rc))
        if rc == 0:
            self.connected = True
    
    def _on_disconnected(self, client, userdata, rc):
        self.logger.debug('DISCONNECT: RC: {0}'.format(rc))
        self._connected = False

    def _on_publish(self, client, userdata, topic, pid):
        self.logger.debug('PUBLISH: {0} PID: {1}'.format(topic, pid))
    
    def _on_subscribe(self, client, userdata, topic, granted_qos):
        self.logger.debug('SUBSCRIBE: {0} QOS: {1}'.format(topic, granted_qos))
    
    def _on_unsubscribe(self, client, userdata, topic, pid):
        self.logger.debug('UNSUBSCRIBE: {0} PID: {1}'.format(topic, pid))

    def create_payload(self, name, unit, value, uid, model, manufacturer, device_class=None):
        # More info: https://www.home-assistant.io/docs/mqtt/discovery/
        data = {
            "~": 'homeassistant/sensor/{0}'.format(self.device_name),
            "name": '{0}{1}'.format(self.device_name, name),
            "stat_t": '~/state'.format(self.device_name),
            "unit_of_meas": '{0}'.format(unit),
            "val_tpl": '{0}'.format(value),
            "uniq_id": '{0}{1}'.format(self.device_name.lower(), uid),
            # "dev": {
                # "ids": '{0}_sensor'.format(self.device_name.lower()),
                # "name": '{0}Sensors'.format(self.device_name),
                # "mdl": '{0}'.format(model),
                # "mf": '{0}'.format(manufacturer)
            # }
        }
        if device_class:
            data["dev_cla"] = device_class
        
        return json.dumps(data)

    def publish_topic_info(self):
        data = self.create_payload("Temp", "°C", "{{ value_json.temperature}}", "_sensor_temperature", "BME280", "Bosch", device_class="temperature")
        self.logger.debug("Sending {0} bytes".format(len(data)))
        self.mqtt_client.publish(
            'homeassistant/sensor/{0}/{1}Temp/config'.format(self.device_name, self.device_name),
            data,
            retain=True, qos=1
        )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Humidity/config",
        #     self.create_payload("Humidity", "%", "{{ value_json.humidity}}", "_sensor_humidity", "BME280", "Bosch", device_class="humidity"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Pressure/config",
        #     self.create_payload("Pressure", "kPa", "{{ value_json.pressure}}", "_sensor_pressure", "BME280", "Bosch", device_class="pressure"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Light/config",
        #     self.create_payload("Light", "lux", "{{ value_json.light}}", "_sensor_light", "LTR-559", "Lite-On", device_class="illuminance"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Oxidising/config",
        #     self.create_payload("Oxidising", "Ohms", "{{ value_json.oxidising}}", "_sensor_gas_oxidising", "MICS6814", "SGX Sensortech"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Reducing/config",
        #     self.create_payload("Reducing", "Ohms", "{{ value_json.reducing}}", "_sensor_gas_reducing", "MICS6814", "SGX Sensortech"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"NH3/config",
        #     self.create_payload("NH3", "Ohms", "{{ value_json.nh3}}", "_sensor_gas_nh3", "MICS6814", "SGX Sensortech"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM1/config",
        #     self.create_payload("PM1", "ug/m3", "{{ value_json.pm1}}", "_sensor_pm1", "PMS5003", "Plantower"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM25/config",
        #     self.create_payload("PM2.5", "ug/m3", "{{ value_json.pm25}}", "_sensor_pm25", "PMS5003", "Plantower"),
        #     retain=True, qos=1
        # )
        # self.mqtt_client.publish(
        #     "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM10/config",
        #     self.create_payload("PM10", "ug/m3", "{{ value_json.pm10}}", "_sensor_pm10", "PMS5003", "Plantower"),
        #     retain=True, qos=1
        # )
    
    def connect_and_send(self, readings):
        if len(readings) > 0:
            self.wifi.connect()            
            self.mqtt_client.connect()
            self.mqtt_client.disconnect()
            self.wifi.disconnect()
        else:
            self.logger.warning('No readings, skipping connect')

    def get_local_time(self, location=None):
        api_url = None
        try:
            aio_username = secrets["aio_username"]
            aio_key = secrets["aio_key"]
        except KeyError:
            raise KeyError(
                "\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'"  # pylint: disable=line-too-long
            )

        location = secrets.get("timezone", location)
        if location:
            api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
        else:  # we'll try to figure it out from the IP address
            api_url = TIME_SERVICE % (aio_username, aio_key)
        api_url += TIME_SERVICE_STRFTIME
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code != 200:
                raise ValueError(response.text)
            if self.debug:
                print("Time request: ", api_url)
                print("Time reply: ", response.text)
            times = response.text.split(" ")
            the_date = times[0]
            the_time = times[1]
            year_day = int(times[2])
            week_day = int(times[3])
            is_dst = None  # no way to know yet
        except KeyError:
            raise KeyError(
                "Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones"
            )
        year, month, mday = [int(x) for x in the_date.split("-")]
        the_time = the_time.split(".")[0]
        hours, minutes, seconds = [int(x) for x in the_time.split(":")]
        now = time.struct_time(
            (year, month, mday, hours, minutes, seconds, week_day, year_day, is_dst)
        )
        print(now)
        rtc.RTC().datetime = now

        # now clean up
        response.close()
        response = None
        gc.collect()
