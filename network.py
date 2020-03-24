import time
import board
from busio import SPI
from digitalio import DigitalInOut
from neopixel import NeoPixel
from json import dumps

from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi.adafruit_esp32spi_wifimanager import ESPSPI_WiFiManager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_logging as logging
from adafruit_minimqtt import MQTT

try:
    from secrets import secrets
except ImportError:
    print("secrets.py not found!")
    raise

class Network():
    def __init__(
        self,
        device_name = "EnviroPlus",
    ):
        self.current_time = time.monotonic()
        self.logger = logging.getLogger('enviro+')
        self.device_name = device_name 

        self._setup_wifi()

    def _setup_wifi(self):
        esp32_cs = DigitalInOut(board.D13)
        esp32_reset = DigitalInOut(board.D12)
        esp32_ready = DigitalInOut(board.D11)
        # esp32_gpio0 = DigitalInOut(board.D10)
        
        spi = SPI(board.SCK, board.MOSI, board.MISO)
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset) #esp32_gpio0, debug=1)

        for _ in range(3): # retries
            try:
                self.logger.info("ESP firmware: " + ''.join([chr(b) for b in esp.firmware_version]))
                break
            except RuntimeError:
                self.logger.warning("Retrying ESP32 connection")
                time.sleep(1)
                esp.reset()
        else:
            self.logger.error("Was not able to find ESP32")
            return

        status_light = NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
        self.wifi = ESPSPI_WiFiManager(esp, secrets, status_light) #, debug=True)

        self.wifi.connect()

        MQTT.set_socket(socket, esp)

        self.mqtt_client = MQTT(broker = secrets['broker'],
                                username = secrets['user'],
                                password = secrets['pass'],
                                is_ssl = False)
 
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnected
        self.mqtt_client.on_subscribe = self._on_subscribe
        self.mqtt_client.on_publish = self._on_publish
        self.mqtt_client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.debug('CONNECT: Flags: {0}\n RC: {1}'.format(flags, rc))
    
    def _on_disconnected(self, client, userdata, rc):
        self.logger.debug('Disconnected from MQTT Broker!')
    
    def _on_subscribe(self, client, userdata, topic, granted_qos):
        self.logger.debug('Subscribed to {0} with QOS level {1}'.format(topic, granted_qos))
    
    def _on_publish(self, client, userdata, topic, pid):
        self.logger.debug('Published to {0} with PID {1}'.format(topic, pid))
    
    def _on_message(self, client, topic, message):
        self.logger.debug('New message on topic {0}: {1}'.format(topic, message))

    def create_payload(self, name, unit, value, uid, model, manufacturer, device_class=None):
        data = {
            "name": self.device_name + name,
            "state_topic": "homeassistant/sensor/" + self.device_name + "/state",
            "unit_of_measurement": unit,
            "value_template": value,
            "unique_id": self.device_name.lower() + uid,
            "device": {
                "identifiers": self.device_name.lower() + "_sensor",
                "name": self.device_name + "Sensors",
                "model": model,
                "manufacturer": manufacturer
            }
        }
        if device_class:
            data["device_class"] = device_class
        
        return dumps(data)

    def publish_topic_info(self):
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Temp/config",
            self.create_payload("Temp", "°C", "{{ value_json.temperature}}", "_sensor_temperature", "BME280", "Bosch", device_class="temperature"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Humidity/config",
            self.create_payload("Humidity", "%", "{{ value_json.humidity}}", "_sensor_humidity", "BME280", "Bosch", device_class="humidity"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Pressure/config",
            self.create_payload("Pressure", "kPa", "{{ value_json.pressure}}", "_sensor_pressure", "BME280", "Bosch", device_class="pressure"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Light/config",
            self.create_payload("Light", "lux", "{{ value_json.light}}", "_sensor_light", "LTR-559", "Lite-On", device_class="illuminance"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Oxidising/config",
            self.create_payload("Oxidising", "Ohms", "{{ value_json.oxidising}}", "_sensor_gas_oxidising", "MICS6814", "SGX Sensortech"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"Reducing/config",
            self.create_payload("Reducing", "Ohms", "{{ value_json.reducing}}", "_sensor_gas_reducing", "MICS6814", "SGX Sensortech"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"NH3/config",
            self.create_payload("NH3", "Ohms", "{{ value_json.nh3}}", "_sensor_gas_nh3", "MICS6814", "SGX Sensortech"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM1/config",
            self.create_payload("PM1", "ug/m3", "{{ value_json.pm1}}", "_sensor_pm1", "PMS5003", "Plantower"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM25/config",
            self.create_payload("PM2.5", "ug/m3", "{{ value_json.pm25}}", "_sensor_pm25", "PMS5003", "Plantower"),
            retain=True, qos=1
        )
        self.mqtt_client.publish(
            "homeassistant/sensor/"+ self.device_name +"/"+ self.device_name +"PM10/config",
            self.create_payload("PM10", "ug/m3", "{{ value_json.pm10}}", "_sensor_pm10", "PMS5003", "Plantower"),
            retain=True, qos=1
        )
    
    def connect_and_send(self, readings):
        if len(readings) > 0:
            self.wifi.connect()
            
            self.mqtt_client.connect()

            self.mqtt_client.disconnect()

            self.wifi.disconnect()
        else:
            self.logger.warning('No readings, skipping connect')
