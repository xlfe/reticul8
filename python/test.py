#
# To test on RPi 3b using hardware serial
# add to /boot/config.txt   dtoverlay=pi3-disable-bt
# run                       sudo systemctl disable hciuart
# connect   GPIO18 (Pin 12) to the EN pin on the ESP32
#           GND <-> GND and 5v <-> 5v
#           ESP32 RX Pin <-> RPi UART TX (Pin 08 / GPIO14)
#           ESP32 TX Pin <-> RPi UART RX (Pin 10 / GPIO15)


import uvloop
import pjon_cython
import reticul8_pb2 as r8
import time
import random
import serial
import asyncio
from serial_asyncio import SerialTransport
import datetime
import logging
from google.protobuf.message import DecodeError
import os

try:
    import gpiozero
    esp = gpiozero.OutputDevice(pin=18, active_high=True, initial_value=True)
except:
    #assume were using usb serial, device will be reset when serial connects
    esp = None

LOOP_SLEEP = float(os.getenv('LOOP_SLEEP', 0.0001))
PING_WAIT = float(os.getenv('PING_WAIT', 0.0001))
LARGE_PING = os.getenv('LARGE_PING', None) != None


class ThroughSerial(pjon_cython.ThroughSerialAsync):

    def __init__(self, device_id, serial_port, baud_rate):
        pjon_cython.ThroughSerialAsync.__init__(self, device_id, serial_port, baud_rate)
        self.set_asynchronous_acknowledge(False)
        self.set_synchronous_acknowledge(True)
        self.set_crc_32(True)

        # Tune this to your serial interface
        # A value of 0 seems to work well for USB serial interfaces,
        # where as the RPi hardware serial requires a minimum of 10
        self.set_flush_offset(10)

        self.waiting_ack_packets = {}
        self.last_rtt = 100000
        self.startup = None
        self.msg_id = 0
        self.proc_q = asyncio.Queue()
        self.recv_q = asyncio.Queue()

    def receive(self, data, length, packet_info):
        self.recv_q.put_nowait(data)

    async def recv_task(self):
        while True:
            data = await self.recv_q.get()
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

    async def loop_task(self):

        while True:
            await self.proc_q.get()
            while True:
                pts, status = self.loop()
                await asyncio.sleep(LOOP_SLEEP)
                if len(self.waiting_ack_packets) == 0:
                    break
            self.proc_q.task_done()

    def sendp(self, packet):
        if len(self.waiting_ack_packets) > 0:
            asyncio.get_event_loop().call_later(LOOP_SLEEP, self.sendp, packet)
        else:

            self.waiting_ack_packets[self.msg_id] = datetime.datetime.now()
            packet.msg_id = self.msg_id
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
            if self.startup is None:
                logging.warning("received non startup packet, but haven't received startup packet")
                return
            packet = packet.result

            if packet.msg_id in self.waiting_ack_packets:
                sent = self.waiting_ack_packets.pop(packet.msg_id)
                self.last_rtt = rtt = (datetime.datetime.now()  - sent).microseconds
                average_pps = (self.msg_id/(1.0*(datetime.datetime.now() - self.startup).total_seconds()))
            else:
                self.last_rtt = rtt = 0
                average_pps = 0

            if packet.msg_id not in [1,2]:
                asyncio.get_event_loop().call_later(PING_WAIT, self.cmd_ping)

            logging.info('RTT:{:>3,} ms ~pps:({:>5.2f}) waiting: {:>2} {}'.format(
                    int(rtt/1000),
                    average_pps,
                    len(self.waiting_ack_packets),
                    str(packet).replace('\n',' ')
                    ))
        else:
            logging.warning(packet)

    def cmd_ping(self):
        rpc = r8.RPC()
        if LARGE_PING:
            rpc.ota_update.data = b'F'*192
            rpc.ota_update.chunk = 0
        else:
            rpc.ping.ping = True
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



class ThroughSerialAsyncIO(asyncio.Protocol):

    def __init__(self, *args, **kwargs):
        ser = serial.serial_for_url(*args, **kwargs)
        self.transport = SerialTransport(asyncio.get_event_loop(), self, ser)


    def connection_made(self, transport):

        logging.info('Serial port opened')
        self.ts = ts = ThroughSerial(10, transport._serial.fd, 115200)



        if esp is not None:
            esp.on()
            time.sleep(1)

        asyncio.ensure_future(ts.loop_task())
        asyncio.ensure_future(ts.recv_task())

        def br():
            ts.proc_q.put_nowait(True)

        # transport.serial.rts = False
        # transport.serial.dtr = False
        transport._read_ready = br

    def connection_lost(self, exc):
        asyncio.get_event_loop().stop()
        logging.error('port closed')

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.set_debug(True)
logging.basicConfig(level=logging.INFO)

UART_PORT = [
    '/dev/ttyUSB0',
    '/dev/ttyAMA0',
    '/dev/tty.wchusbserial1410',
    '/dev/tty.SLAB_USBtoUART'
    ]

for port in UART_PORT:
    if os.path.exists(port):
        if esp is not None:
            esp.off()
        tsaio = ThroughSerialAsyncIO(url=port, baudrate=115200)
        break




# loop.run_until_complete(coro)
loop.run_forever()
loop.close()






