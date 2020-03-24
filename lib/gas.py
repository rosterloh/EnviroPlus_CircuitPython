import time, board, digitalio, analogio

_is_setup = False

class Mics6814Reading(object):
    __slots__ = 'oxidising', 'reducing', 'nh3', "_OX", "_RED", "_NH3"

    def __init__(self, ox, red, nh3, OX, RED, NH3):
        self._OX = OX
        self._RED = RED
        self._NH3 = NH3
        self.oxidising = ox
        self.reducing = red
        self.nh3 = nh3

    def __repr__(self):
        fmt = """Oxidising: {ox:05.03f} Ohms
Reducing: {red:05.03f} Ohms
NH3: {nh3:05.03f} Ohms"""
        return fmt.format(
            ox=self.oxidising,
            red=self.reducing,
            nh3=self.nh3)

    __str__ = __repr__


def setup():
    global _is_setup, enable, OX, RED, NH3
    if _is_setup:
        return
    _is_setup = True


    enable = digitalio.DigitalInOut(board.A3)
    enable.direction = digitalio.Direction.OUTPUT
    enable.value = True

    OX = analogio.AnalogIn(board.A2)
    RED = analogio.AnalogIn(board.A1)
    NH3 = analogio.AnalogIn(board.A0)
    

def cleanup():
    enable.value = False


def read_all():
    """Return gas resistance for oxidising, reducing and NH3"""
    setup()

    try:
        ox = 56000/((65535/OX.value)-1)
        # Simplified from:
        # ox = 56000 * (1/ (OX.reference_voltage/(OX.value * (OX.reference_voltage / 65535)) -1))
    except ZeroDivisionError:
        ox = 0

    try:
        red = 56000/((65535/RED.value)-1)
    except ZeroDivisionError:
        red = 0

    try:
        nh3 = 56000/((65535/NH3.value)-1)
    except ZeroDivisionError:
        nh3 = 0

    return Mics6814Reading(ox, red, nh3, OX, RED, NH3)


def read_oxidising():
    """Return gas resistance for oxidising gases.
    Eg chlorine, nitrous oxide
    """
    setup()
    return read_all().oxidising


def read_reducing():
    """Return gas resistance for reducing gases.
    Eg hydrogen, carbon monoxide
    """
    setup()
    return read_all().reducing


def read_nh3():
    """Return gas resistance for nh3/ammonia"""
    setup()
    return read_all().nh3