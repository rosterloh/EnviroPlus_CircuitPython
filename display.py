import os
import board
import displayio
import pulseio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_st7735r import ST7735R

BLACK = 0x0
BLUE = 0x2020FF
GREEN = 0x00FF55
RED = 0xFF0000
YELLOW = 0xFFFF00

BACKGROUND_COLOR = 0
PROFILE_COLOR = 1
GRID_COLOR = 2
TEMP_COLOR = 3
AXIS_COLOR = 2

class Display():
    def __init__(
        self,
        backlight_control=True,
        baudrate=100000000
    ):
        spi = board.SPI()
        spi.try_lock()
        spi.configure(baudrate=baudrate)
        spi.unlock()

        displayio.release_displays()

        dev = os.uname().sysname
        if dev == 'samd51':
            print('Configuring for Feather M4 Express')
            cmd = board.D5
            cs = board.D6
            rst = board.D9
        elif dev == 'nrf52840':
            print('Configuring for Feather nRF52840')
            cmd = board.D2
            cs = board.D3
            rst = board.D4
        else:
            raise Exception('Unknown board ' + dev)

        if backlight_control:
            display_bus = displayio.FourWire(spi, command=cmd, chip_select=cs, reset=rst, baudrate=baudrate)
            self.pwm = None
        else:
            display_bus = displayio.FourWire(spi, command=cmd, chip_select=cs, baudrate=baudrate)
            self.pwm = pulseio.PWMOut(board.D4)
            self.pwm.duty_cycle = 2**15

        self.display = ST7735R(display_bus, width=160, height=80, colstart=26, rowstart=1, rotation=270, invert=True) #bgr=True
        self.init()

    def set_backlight(self, value):
        """Adjust the backlight.
        :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                    off, and ``1`` is 100% brightness.
        """
        val = max(0, min(1.0, val))
        if self.pwm:
            self.pwm.duty_cycle = int(val * 65535)
        else:
            self.display.auto_brightness = False
            self.display.brightness = value / 100

    def init(self):
        self.display_group = displayio.Group(max_size=10)
        self.display.show(self.display_group)
        # Draw background
        colour_bitmap = displayio.Bitmap(self.display.width, self.display.height, 1)
        colour_palette = displayio.Palette(1)
        colour_palette[0] = BLACK
        bg_sprite = displayio.TileGrid(colour_bitmap, pixel_shader=colour_palette, x=0, y=0)
        self.display_group.append(bg_sprite)
        # Load Fonts
        self.font1 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")
        self.font1.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')
        self.font2 = bitmap_font.load_font("/fonts/OpenSans-12.bdf")
        self.font2.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')
        self.font3 = bitmap_font.load_font("/fonts/OpenSans-16.bdf")
        self.font3.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')
        # Create labels
        self.label_temperature = Label(self.font2, text="--", max_glyphs=10, color=0xFFFFFF)
        self.label_temperature.x = 20
        self.label_temperature.y = 18
        self.display_group.append(self.label_temperature)
        self.label_humidity = Label(self.font2, text="--", max_glyphs=10, color=0xFFFFFF)
        self.label_humidity.x = 20
        self.label_humidity.y = 48
        self.display_group.append(self.label_humidity)

    def update(self, readings):
        self.label_temperature.text = str(int(readings.temperature)) +'°C'
        self.label_humidity.text = str(int(readings.humidity)) + '%'
