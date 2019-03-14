import uvloop, asyncio, logging


from reticul8 import reticul8_pb2 as r8
from reticul8 import rpc
from kirke import Object, State
logger = logging.getLogger('reticul8.circe')

check_success = lambda _:_ is not None and _.result.result == r8.RT_SUCCESS

class AsyncStateOutput(object):

    def __init__(self, state_mappings: dict):
        self.state_mappings = state_mappings
        self._locked= None

    async def acquire_lock(self, new_state):
        assert self._locked is None
        assert new_state in self.state_mappings
        self._locked = new_state

    async def change(self):
        self.result = await self.state_mappings[self._locked]()


    async def release_lock(self):
        logger.debug(self.result)
        assert check_success(self.result)
        self._locked = None

    def require_async(self):
        return True



class Output(Object):

    def __init__(self, pin, **kwargs):
        self.pin = pin
        self._circe_add_child('state', State(['high', 'low']))
        self.state.set_output(AsyncStateOutput(
            state_mappings=dict(high=lambda: self.set_state(r8.PV_HIGH), low=lambda : self.set_state(r8.PV_LOW))
        ))


    def send_packet(self, packet):
        return asyncio.ensure_future(self.__parent__.send_packet(packet))

    def set_state(self, value):
        return self.__parent__.send_packet(rpc.RPC_Wrapper().gpio_write(pin=self.pin, value=value))

    def set_state_from_read(self, future):
        self.state = 'high' if future.result().result.pin_value == 1 else 'low'

    def _circe_child_init(self):
        logger.debug('Output init for pin {}'.format(self.pin))
        self.send_packet(rpc.RPC_Wrapper().gpio_config(pin=self.pin, mode=r8.PM_OUTPUT))
        self.send_packet(rpc.RPC_Wrapper().gpio_read(pin=self.pin)).add_done_callback(self.set_state_from_read)



class Node(Object):
    """A node is a single uC running reticul8"""

    def __init__(self, device_id, **kwargs):
        self.device_id = device_id
        self.startup = None
        self.futures = []
        self._circe_add_child('health', State(['offline','online']))

    def _circe_child_init(self):
        logger.debug('Added {}'.format(self.device_id))
        self.transport.add_node(self)


    @property
    def transport(self):
        return self.__parent__.transport

    async def notify_startup(self):
        self.health = 'online'


    async def send_packet(self, packet):
        while not self.health.ONLINE:
            await asyncio.sleep(0.01)
        logger.debug('Sending to {} packet {}'.format(self.device_id, packet))
        return await self.transport.send_packet_blocking(self.device_id, packet)

class System(Object):


    def __init__(self, name, transport, loop, debug=False, **kwargs):
        logging.getLogger('circe').setLevel(level=logging.DEBUG if debug else logging.INFO)
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.transport = transport
        self.__name__ = name
        self.loop = loop
        self.loop.set_debug(debug)
        self._circe_add_child('internet', State(states=['offline', 'online'], default='offline'))
        self._circe_add_child('alarm', State(states=['disarmed', 'armed'], default='disarmed'))

    def run(self):
        self._circe_state_init()
        self.loop.run_forever()









