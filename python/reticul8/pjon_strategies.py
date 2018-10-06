import uvloop
import pjon_cython
import time
import random
import serial
from . import reticul8_pb2 as r8
import asyncio
from serial_asyncio import SerialTransport
import datetime
import logging
from google.protobuf.message import DecodeError
import os


LOOP_SLEEP = 0.0001




class SerialAsyncio(asyncio.Protocol, pjon_cython.ThroughSerialAsync):
    """Create a serial connection for """

    def __init__(self, device_id, *args, **kwargs):
        ser = serial.serial_for_url(*args, **kwargs)
        self.transport = SerialTransport(asyncio.get_event_loop(), self, ser)
        self.device_id = device_id
        self.nodes = {}
        self.waiting_ack_packets = {}
        self.received_ack_packets = {}

    def add_node(self, node):
        self.nodes[node.device_id] = node

    def connection_made(self, transport):

        logging.debug('Serial port opened {}'.format(transport._serial._port))

        pjon_cython.ThroughSerialAsync.__init__(self, self.device_id, transport._serial.fd, int(transport._serial._baudrate))
        self.set_asynchronous_acknowledge(False)
        self.set_synchronous_acknowledge(True)
        self.set_crc_32(True)

        # Tune this to your serial interface
        # A value of 0 seems to work well for USB serial interfaces,
        # where as the RPi hardware serial requires a minimum of 10
        self.set_flush_offset(10)

        self.msg_id = 0
        self.proc_q = asyncio.Queue()
        self.recv_q = asyncio.Queue()

        asyncio.ensure_future(self.loop_task())
        asyncio.ensure_future(self.recv_task())

        def br():
            self.proc_q.put_nowait(True)

        transport._read_ready = br
        self.notify_connection_made()

    def receive(self, data, length, packet_info):
        self.recv_q.put_nowait((data, packet_info['sender_id']))

    async def recv_task(self):
        while True:
            data, source = await self.recv_q.get()
            packet = r8.FROM_MICRO()
            try:
                packet.ParseFromString(data)
                if packet.IsInitialized():
                    self.recv_packet(source, packet)
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

    def send_packet(self, destination, packet):
        packet.msg_id = self.msg_id
        self.msg_id += 1

        if len(self.waiting_ack_packets) > 0:
            asyncio.get_event_loop().call_later(LOOP_SLEEP, self.sendp, packet)
        else:
            self.waiting_ack_packets[packet.msg_id] = datetime.datetime.now()
            self.send(destination, packet.SerializeToString())
            self.proc_q.put_nowait(True)

        return packet.msg_id

    async def send_packet_blocking(self, destination, packet):
        while len(self.waiting_ack_packets) > 0:
            await asyncio.sleep(LOOP_SLEEP)
        msg_id = self.send_packet(destination, packet)
        while len(self.waiting_ack_packets) > 0:
            await asyncio.sleep(LOOP_SLEEP)

        return self.received_ack_packets.pop(msg_id)


    def recv_packet(self, source, packet):

        node = self.nodes[source]

        if packet.WhichOneof('msg') == 'startup':
            logging.debug("{} startup".format(source))
            if node.startup is None:
                node.startup = datetime.datetime.now()
                asyncio.ensure_future(node.notify_startup())
                # self.rpc.ping()
                # asyncio.get_event_loop().call_later(0.01, self.setup_led)
                # asyncio.get_event_loop().call_later(0.02, self.cmd_schedule)

        elif packet.WhichOneof('msg') == 'result':

            msg_id = packet.result.msg_id
            self.received_ack_packets[msg_id] = packet

            assert msg_id in self.waiting_ack_packets
            sent = self.waiting_ack_packets.pop(msg_id)
            self.last_rtt = rtt = (datetime.datetime.now()  - sent).microseconds
            average_pps = (self.msg_id/(1.0*(datetime.datetime.now() - node.startup).total_seconds()))

            # if packet.msg_id not in [1,2]:
            #     asyncio.get_event_loop().call_later(PING_WAIT, self.cmd_ping)

            logging.info('RTT:{:>3,} ms ~pps:({:>5.2f}) waiting: {:>2} {}'.format(
                    int(rtt/1000),
                    average_pps,
                    len(self.waiting_ack_packets),
                    str(packet).replace('\n',' ')
                    ))
        else:
            logging.warning(packet)

    def notify_connection_made(self):
        raise NotImplementedError()

    def notify_connection_lost(self):
        raise NotImplementedError()

    def connection_lost(self, exc):
        logging.error('port closed')
        self.notify_connection_lost()

