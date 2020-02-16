import time
import board
from busio import SPI
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_logging as logging
from adafruit_minimqtt import MQTT

try:
    from secrets import secrets
except ImportError:
    print("secrets.py not found!")
    raise

class Network:
    def __init__(
        self,
    ):
        self.current_time = time.monotonic()
        self.logger = logging.getLogger('enviro+')

        self._setup_wifi()

    def _setup_wifi(self):
        esp32_cs = DigitalInOut(board.D13)
        esp32_ready = DigitalInOut(board.D11)
        esp32_reset = DigitalInOut(board.D12)
        
        spi = SPI(board.SCK, board.MOSI, board.MISO)
        esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
        self.wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets)#, status_light)

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

    def connect_and_send(self, readings):
        if len(readings) > 0:
            self.wifi.connect()

            client = MQTT(socket,
                          broker = secrets['broker'],
                          port = 1883,
                          username = secrets['user'],
                          password = secrets['pass'],
                          network_manager = self.wifi)
 
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnected
            client.on_subscribe = self._on_subscribe
            client.on_publish = self._on_publish
            client.on_message = self._on_message
            
            client.connect()
        else:
            self.logger.warning('No readings, skipping connect')
