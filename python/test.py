import pjon_cython
import reticul8_pb2 as r8
import time
import random
import asyncio
import datetime
import logging
from google.protobuf.message import DecodeError

logging.basicConfig(level=logging.INFO)



class ThroughSerial(pjon_cython.ThroughSerialAsync):

    def __init__(self, device_id, serial_port, baud_rate):
        pjon_cython.ThroughSerialAsync.__init__(self, device_id, serial_port, baud_rate)
        # self.set_asynchronous_acknowledge(True)
        self.set_synchronous_acknowledge(True)
        # self.set_packet_id(True)
        self.set_crc_32(True)

        self.waiting_ack_packets = {}
        self.startup = None
        self.msg_id = 0
        self.recv_q = asyncio.Queue()
        self.send_q = asyncio.Queue()

    def receive(self, data, length, packet_info):
        self.recv_q.put_nowait((data, packet_info))

    async def send_queue(self):
        while True:
            await asyncio.sleep(0.05)
            i, msg_id, packet = await self.send_q.get()
            self.waiting_ack_packets[msg_id] = datetime.datetime.now()
            self.send(i, packet)
            self.send_q.task_done()

    async def recv_queue(self):
        while True:
            await asyncio.sleep(0.05)
            data, packet_info = await self.recv_q.get()
            packet = r8.FROM_MICRO()
            try:
                packet.ParseFromString(data)
                if packet.IsInitialized():
                    self.handle_packet(packet)
                else:
                    logging.warning('Packet not Initialized: {}'.format(data))
            except (DecodeError):
                logging.warning('Packet not decoded: {}'.format(data))

            self.recv_q.task_done()

    def handle_packet(self, packet):

        if packet.WhichOneof('msg') == 'startup':
            logging.info("startup")
            if self.startup is None:
                self.startup = datetime.datetime.now()
                time.sleep(1)
                self.setup_led()
                self.cmd_schedule()
                # self.cmd_ping()
                # self.cmd_ping()
        elif packet.WhichOneof('msg') == 'result':
            packet = packet.result
            try:
                sent = self.waiting_ack_packets.pop(packet.msg_id)
            except KeyError:
                sent = datetime.datetime.now()

            self.cmd_ping()
            logging.info('{:,}  ({:.2f}) {}'.format(
                (datetime.datetime.now()  - sent).microseconds,
                (self.msg_id/(1.0*(datetime.datetime.now() - self.startup).total_seconds())),
                str(packet).replace('\n',' ')
                ))
        else:
            logging.warning(packet)

    def sendp(self, packet):
        packet.msg_id = self.msg_id
        self.msg_id += 1
        self.send_q.put_nowait((11, packet.msg_id, packet.SerializeToString()))
        # self.send(11, packet.SerializeToString())

    def cmd_ping(self):
        rpc = r8.RPC()
        rpc.ping.ping = True
        # rpc.ota_update.uri = b'F'*192
        self.sendp(rpc)

    def setup_led(self):
        led = r8.RPC()
        led.gpio_config.pin = 22
        led.gpio_config.mode = r8.PM_OUTPUT
        self.sendp(led)

        # led = r8.RPC()
        # led.gpio_write.pin = 22
        # led.gpio_write.mode = r8.PV_LOW
        # self.sendp(led)


    def cmd_schedule(self):
        s1 = r8.RPC()
        s1.schedule.count = 1
        s1.schedule.after_ms = 50000
        s1.schedule.every_ms = 0
        s1.gpio_write.pin = 22
        s1.gpio_write.value = r8.PV_LOW
        self.sendp(s1)

        # s2 = r8.RPC()
        # s2.schedule.count = -1
        # s2.schedule.after_ms = 2000
        # s2.schedule.every_ms = 500
        # s2.gpio_write.pin = 22
        # s2.gpio_write.value = r8.PV_HIGH
        # self.sendp(s2)


    def print_waiting(self):
        last =None
        for i,ts in self.waiting_ack_packets.items():
            if last is not None:
                print (i, ts, ts-last)
            last =ts




async def coro():
    ts = ThroughSerial(10, b"/dev/tty.wchusbserial1410", 115200*2)

    asyncio.run_coroutine_threadsafe(ts.send_queue(), loop=asyncio.get_event_loop())
    asyncio.run_coroutine_threadsafe(ts.recv_queue(), loop=asyncio.get_event_loop())
    while True:
        try:
            ts.loop()
            await asyncio.sleep(0.0001)
        except (SystemError, pjon_cython.PJON_Connection_Lost):
            # logging.warning('ConnectionLost with {} packets {}'.format(ts.get_packets_count(), len(ts.waiting_ack_packets)))
            # ts.print_waiting()
            raise
            # ts.cmd_ping()


asyncio.run(coro(), debug=True)





