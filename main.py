import board 
from adafruit_display_text import label
import terminalio

from led_status import LedStatus
from sensors import Sensors
from network_service import NetworkService
from display import Display
from plotter import Plotter

led = LedStatus()
lcd = Display(backlight_control=True, baudrate=8000000)
nws = NetworkService()
sns = Sensors(update_timeout=30.0, debug=True)

plotter = Plotter(lcd,
                  style="lines", #"dots"
                  mode="scroll", #"wrap"
                  screen_width=160, screen_height=80,
                  plot_width=112, plot_height=41)

plotter.display_on()
plotter.clear_all()
plotter.title = "Enviro+"
plotter.y_axis_lab = ""
# The range on graph will start at this value
plotter.y_range = (20, 60)
plotter.y_min_range = 1
# Sensor/data source is expected to produce data between these values
plotter.y_full_range = (0, 100)
plotter.channels = 3  # Can be between 1 and 3
plotter.channel_colidx = [0xffff00, 0x00ffff, 0xff0080]

@sns.on_update
def on_update(readings):
    led.show_air_quality(int(readings.pm2_5))
    lcd.update(readings)
    # plotter.data_add((readings.temperature, readings.pm2_5, readings.humidity))
    # nw.connect_and_send(readings)

while True:
    sns.run()