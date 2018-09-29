import uvloop
import pjon_cython
import reticul8_pb2 as r8
import time
import random
import asyncio
import datetime
import logging
from google.protobuf.message import DecodeError

logging.basicConfig(level=logging.INFO)

SLEEP_TIME=0.0001



class ThroughSerial(pjon_cython.ThroughSerialAsync):

    def __init__(self, device_id, serial_port, baud_rate):
        pjon_cython.ThroughSerialAsync.__init__(self, device_id, serial_port, baud_rate)
        # self.set_asynchronous_acknowledge(True)
        self.set_synchronous_acknowledge(True)
        # self.set_packet_id(True)
        # self.set_crc_32(True)

        self.waiting_ack_packets = {}
        self.startup = None
        self.msg_id = 0
        self.recv_q = asyncio.Queue()
        self.send_q = asyncio.Queue()

    def receive(self, data, length, packet_info):
        self.recv_q.put_nowait((data, packet_info))
        asyncio.get_event_loop().call_later(0.001, self.loop)

    async def send_queue(self):
        while True:
            # await asyncio.sleep(SLEEP_TIME)
            i, msg_id, packet = await self.send_q.get()
            self.waiting_ack_packets[msg_id] = datetime.datetime.now()
            self.send(i, packet)

            # asyncio.get_event_loop().call_soon(self.loop)
            # packets = self.bus_update()
            # packets = await asyncio.get_event_loop().call_later(0, self.bus_update)
            # while packets > 0:
            #     packets = await asyncio.get_event_loop().call_later(0, self.bus_update)
            # logging.info('Sent: {}'.format(msg_id))
            self.send_q.task_done()

    async def recv_queue(self):
        while True:
            data, packet_info = await self.recv_q.get()
            packet = r8.FROM_MICRO()
            try:
                packet.ParseFromString(data)
                if packet.IsInitialized():
                    await self.handle_packet(packet)
                else:
                    logging.warning('Packet not Initialized: {}'.format(data))
            except (DecodeError):
                logging.warning('Packet not decoded: {}'.format(data))

            # pjon_status = self.bus_receive(0)
            # asyncio.get_event_loop().call_later(0.01, self.bus_receive)
            # asyncio.get_event_loop().call_soon(self.loop)
            # while pjon_status != pjon_cython.PJON_FAIL:
            #     pjon_status = await asyncio.get_event_loop().call_later(0, self.bus_receive, 0)
            self.recv_q.task_done()

    async def loop_task(self):
        while True:
            # asyncio.get_event_loop().call_soon(self.loop)
            pts, status = self.loop()
            if pts > 0:
                await asyncio.sleep(0.001)
            else:
                await asyncio.sleep(0.1)

    async def handle_packet(self, packet):

        if packet.WhichOneof('msg') == 'startup':
            logging.info("startup")
            if self.startup is None:
                self.startup = datetime.datetime.now()
                self.setup_led()
                self.cmd_schedule()
                # self.cmd_ping()

        elif packet.WhichOneof('msg') == 'result':
            packet = packet.result

            try:
                sent = self.waiting_ack_packets.pop(packet.msg_id)
                ms = (datetime.datetime.now()  - sent).microseconds
            except KeyError:
                ms = 0

            if packet.msg_id not in [1,2]:
                asyncio.get_event_loop().call_later(0.001, self.cmd_ping)


            logging.info('{:,}  ({:.2f}) {}'.format(
                ms,
                (self.msg_id/(1.0*(datetime.datetime.now() - self.startup).total_seconds())),
                str(packet).replace('\n',' ')
                ))
        else:
            logging.warning(packet)

    def sendp(self, packet):
        packet.msg_id = self.msg_id+0
        self.send_q.put_nowait((11, packet.msg_id, packet.SerializeToString()))
        asyncio.get_event_loop().call_later(0.001, self.loop)
        self.msg_id += 1
        # self.send(11, packet.SerializeToString())

    def cmd_ping(self):
        rpc = r8.RPC()
        rpc.ping.ping = True
        # rpc.ota_update.uri = b'F'*192
        self.sendp(rpc)

    def setup_led(self):
        led = r8.RPC()
        led.pwm_config.pin = 22
        # led.gpio_config.mode = r8.PM_OUTPUT
        self.sendp(led)

        # led = r8.RPC()
        # led.gpio_write.pin = 22
        # led.gpio_write.mode = r8.PV_LOW
        # self.sendp(led)


    def cmd_schedule(self):
        s1 = r8.RPC()
        s1.schedule.count = -1
        s1.schedule.after_ms = 1000
        s1.schedule.every_ms = 2000
        s1.pwm_fade.pin = 22
        s1.pwm_fade.duty = 0
        s1.pwm_fade.fade_ms = 500

        s2 = r8.RPC()
        s2.schedule.count = -1
        s2.schedule.after_ms = 0
        s2.schedule.every_ms = 2000
        s2.pwm_fade.pin = 22
        s2.pwm_fade.duty = 8192
        s2.pwm_fade.fade_ms = 500

        self.sendp(s1)
        # await asyncio.sleep(.1)
        self.sendp(s2)
        # await asyncio.sleep(.1)


    def print_waiting(self):
        last =None
        for i,ts in self.waiting_ack_packets.items():
            if last is not None:
                print (i, ts, ts-last)
            last =ts



import serial_asyncio

class Output(asyncio.Protocol):


    def connection_made(self, transport):

        self.transport = transport
        self.ts = ts = ThroughSerial(10, transport._serial.fd, 115200)

        asyncio.run_coroutine_threadsafe(ts.send_queue(), loop=transport._loop)
        asyncio.run_coroutine_threadsafe(ts.recv_queue(), loop=transport._loop)
        asyncio.run_coroutine_threadsafe(ts.loop_task(), loop=transport._loop)

        print('port opened')
        def br():
            asyncio.get_event_loop().call_soon(ts.loop)
            # ts.bus_receive()
            # logging.warning('br')
            # ts.loop()

        transport.serial.rts = False
        transport._read_ready = br

    def connection_lost(self, exc):
        print('port closed')
        # asyncio.get_event_loop().stop()

loop = asyncio.get_event_loop()
loop.set_debug(True)
coro = serial_asyncio.create_serial_connection(loop, Output, '/dev/tty.wchusbserial1410', baudrate=115200)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()

# def coro():
#     asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    # os.read(ts._fd(),1000)

    # def doloop():
    #     ts.loop()

    # asyncio.get_event_loop().add_reader(ts._fd(), doloop)

    # while True:
    #     ts.loop()
        # await asyncio.sleep(SLEEP_TIME/4)

    # asyncio.get_event_loop().run_forever()

# coro()
# asyncio.run(coro(), debug=True)
# loop.run_forever()






