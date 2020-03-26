import board 
from neopixel import NeoPixel
from adafruit_display_text import label
import terminalio

from sensors import Sensors
from network_service import NetworkService
from display import Display

red = 0xFF0000
green = 0x00FF00
blue = 0x0000FF

neo = NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
neo.fill(0)

lcd = Display(backlight_control=True, baudrate=8000000)
nws = NetworkService()
sns = Sensors(update_timeout=30.0, debug=True)

lcd.init_plotter([red, green, blue, red+green+blue], max_value=70, min_value=0, top_space=10)
lcd.group.append(label.Label(terminalio.FONT, text="{:0.1f} C".format(0), color=red, x=0, y=5, max_glyphs=15))
lcd.group.append(label.Label(terminalio.FONT, text="{:0.1f} ppm".format(0), color=green, x=50, y=5, max_glyphs=15))
lcd.group.append(label.Label(terminalio.FONT, text="{:0.1f} %".format(0), color=blue, x=120, y=5, max_glyphs=15))

@sns.on_update
def on_update(readings):
    lcd.update(
        # scale to 70 as that's the number of pixels height available
        lcd.remap(readings.temperature, 0, 50, 0, 70),
        lcd.remap(readings.pm10, 975, 1025, 0, 70),
        lcd.remap(readings.humidity, 0, 100, 0, 70),
    )
    # update the labels
    lcd.group[1].text = "{:0.1f} C".format(readings.temperature)
    lcd.group[2].text = "{:0.1f} ug/m3".format(readings.pm10)
    lcd.group[3].text = "{:0.1f} %".format(readings.humidity)

    # nw.connect_and_send(readings)

sns.run()