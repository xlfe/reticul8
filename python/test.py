import uvloop
import pjon_cython
import reticul8_pb2 as r8
import time
import random
import asyncio
import datetime
import logging
from google.protobuf.message import DecodeError





class ThroughSerial(pjon_cython.ThroughSerialAsync):

    def __init__(self, device_id, serial_port, baud_rate):
        pjon_cython.ThroughSerialAsync.__init__(self, device_id, serial_port, baud_rate)
        # self.set_asynchronous_acknowledge(True)
        self.set_synchronous_acknowledge(True)
        # self.set_packet_id(True)
        self.set_crc_32(True)

        self.waiting_ack_packets = {}
        self.last_rtt = 100000
        self.startup = None
        self.msg_id = 0
        self.last_loop_count = 0
        self.proc_q = asyncio.Queue()

    def receive(self, data, length, packet_info):
        packet = r8.FROM_MICRO()
        try:
            packet.ParseFromString(data)
            if packet.IsInitialized():
                self.handle_packet(packet)
            else:
                logging.warning('Packet not Initialized: {}'.format(data))
        except (DecodeError):
            logging.warning('Packet not decoded: {}'.format(data))

    async def loop_task(self):

        while True:
            ready = await self.proc_q.get()
            count = 0
            while ready:
                pts, status = self.loop()
                count += 1
                if pts == 0 and status == pjon_cython.PJON_ACK:
                    ready = False
                else:
                    await asyncio.sleep(self.calc_sleep())
            # logging.info('Done after loop called {}'.format(count))
            self.last_loop_count = count
            self.proc_q.task_done()

    def calc_sleep(self):
        return 0.005
        return 100.0/self.last_rtt
        # else:

    def sendp(self, packet):
        packet.msg_id = self.msg_id+0
        self.waiting_ack_packets[packet.msg_id] = datetime.datetime.now()
        self.send(11, packet.SerializeToString())
        self.proc_q.put_nowait(True)
        self.msg_id += 1


    def handle_packet(self, packet):

        if packet.WhichOneof('msg') == 'startup':
            logging.info("startup")
            if self.startup is None:
                self.startup = datetime.datetime.now()
                asyncio.get_event_loop().call_later(0.01, self.setup_led)
                asyncio.get_event_loop().call_later(0.02, self.cmd_schedule)

        elif packet.WhichOneof('msg') == 'result':
            packet = packet.result

            try:
                sent = self.waiting_ack_packets.pop(packet.msg_id)
                self.last_rtt = rtt = (datetime.datetime.now()  - sent).microseconds

                if packet.msg_id not in [1,2]:
                    asyncio.get_event_loop().call_later(1, self.cmd_ping)
                    # asyncio.get_event_loop().call_soon(self.cmd_ping)

                average_pps = (self.msg_id/(1.0*(datetime.datetime.now() - self.startup).total_seconds()))
                logging.info('{:,}  ({:.2f}) {} - {} waiting {} {}'.format(
                    rtt,
                    average_pps,
                    str(packet).replace('\n',' '),
                    len(self.waiting_ack_packets),
                    self.calc_sleep(),
                    self.last_loop_count
                    ))
            except KeyError:
                rtt = 0
        else:
            logging.warning(packet)

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
        s1.pwm_fade.fade_ms = 200
        self.sendp(s1)

        s2 = r8.RPC()
        s2.schedule.count = -1
        s2.schedule.after_ms = 0
        s2.schedule.every_ms = 2000
        s2.pwm_fade.pin = 22
        s2.pwm_fade.duty = 8192
        s2.pwm_fade.fade_ms = 200
        self.sendp(s2)


import serial_asyncio

class Output(asyncio.Protocol):


    def connection_made(self, transport):

        self.transport = transport
        self.ts = ts = ThroughSerial(10, transport._serial.fd, 115200)

        # asyncio.create_task(ts.recv_queue())
        asyncio.create_task(ts.loop_task())

        print('port opened')
        def br():
            ts.proc_q.put_nowait(True)

        transport.serial.rts = False
        transport._read_ready = br

    def connection_lost(self, exc):
        asyncio.get_event_loop().stop()
        logging.error('port closed')

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.set_debug(True)
logging.basicConfig(level=logging.INFO)
coro = serial_asyncio.create_serial_connection(loop, Output, '/dev/tty.wchusbserial1410', baudrate=115200)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()






