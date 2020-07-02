import board
from neopixel import NeoPixel

class LedStatus():

    INDEX_COLOURS = [0x9CFF9C, 0x31FF00, 0x31CF00, 0xF0F000, 0xFFCF00, 0xFF9A00, 0xFF6464, 0xFF0000, 0x900000, 0xCE30FF]

    def __init__(self):
        self.neo = NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
        self.neo.fill(0)

    def show_air_quality(self, reading):
        # From: https://uk-air.defra.gov.uk/air-pollution/daqi?view=more-info&pollutant=pm25#pollutant
        if reading >= 71:
            self.neo.fill(self.INDEX_COLOURS[9])
        elif reading >= 65 and reading <= 70:
            self.neo.fill(self.INDEX_COLOURS[8])
        elif reading >= 59 and reading <= 64:
            self.neo.fill(self.INDEX_COLOURS[7])
        elif reading >= 54 and reading <= 58:
            self.neo.fill(self.INDEX_COLOURS[6])
        elif reading >= 48 and reading <= 53:
            self.neo.fill(self.INDEX_COLOURS[5])
        elif reading >= 42 and reading <= 47:
            self.neo.fill(self.INDEX_COLOURS[4])
        elif reading >= 36 and reading <= 41:
            self.neo.fill(self.INDEX_COLOURS[3])
        elif reading >= 24 and reading <= 35:
            self.neo.fill(self.INDEX_COLOURS[2])
        elif reading >= 12 and reading <= 23:
            self.neo.fill(self.INDEX_COLOURS[1])
        else:
            self.neo.fill(self.INDEX_COLOURS[0])