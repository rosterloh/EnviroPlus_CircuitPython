from network import Network
from sensors import Sensors

nw = Network()
sns = Sensors()

@sns.on_update
def on_update(readings):
    nw.connect_and_send(readings)

sensors.run()