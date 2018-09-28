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

    def handle_packet(self, packet):

        if packet.WhichOneof('msg') == 'startup':
            logging.info("startup")
            if self.startup is None:
                self.startup = datetime.datetime.now()
                time.sleep(1)
                self.cmd_ping()
                self.cmd_ping()
        elif packet.WhichOneof('msg') == 'result':
            packet = packet.result
            try:
                sent = self.waiting_ack_packets.pop(packet.msg_id)
                self.cmd_ping()
                logging.info('{} - {:,}  ({})'.format(
                    packet.msg_id,
                    (datetime.datetime.now()  - sent).microseconds,
                    (self.msg_id/(1.0*(datetime.datetime.now() - self.startup).total_seconds()))))
            except KeyError:
                logging.info('.')

    def sendp(self, packet):
        packet.msg_id = self.msg_id + 0
        self.waiting_ack_packets[packet.msg_id] = datetime.datetime.now()
        self.send(11, packet.SerializeToString())
        self.msg_id += 1

    def cmd_ping(self):
        rpc = r8.RPC()
        rpc.ping.ping = True
        # rpc.ota_update.uri = b'F'*192
        self.sendp(rpc)

    def print_waiting(self):
        last =None
        for i,ts in self.waiting_ack_packets.items():
            if last is not None:
                print (i, ts, ts-last)
            last =ts



ts = ThroughSerial(10, b"/dev/tty.wchusbserial1410", 115200*2)

def coro():

    while True:
        try:
            ts.loop()
            time.sleep(0.0005)
        except (SystemError, pjon_cython.PJON_Connection_Lost):
            # logging.warning('ConnectionLost with {} packets {}'.format(ts.get_packets_count(), len(ts.waiting_ack_packets)))
            # ts.print_waiting()
            raise
            # ts.cmd_ping()


coro()





