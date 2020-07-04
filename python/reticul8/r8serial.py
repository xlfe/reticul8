import time
import asyncio
import logging
import datetime


R8_SERIAL_MAX_PACKET = 254
R8_SERIAL_OVERHEAD   = 1+2+4
R8_SERIAL_BUF_SZ     = (R8_SERIAL_MAX_PACKET + R8_SERIAL_OVERHEAD)
R8_SERIAL_START      = 149
R8_SERIAL_END        = 234
R8_SERIAL_ESC        = 187

def crc32_compute(data):

    crc = 0xFFFFFFFF

    for b in data:

        if b < 0:
            b += 256

        crc ^= b
        for i in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                 crc =  crc >> 1
    return ~crc



def crc32_to_bytes(crc):

    d = []

    for x in range(4):
        i = 4-x

        c_x = (crc >> (8 * (i - 1))) & 0xFF
        if c_x < 0:
            c_x += 256

        d.append(c_x)
    return bytes(d)


def crc32_compare(computed, received):
    return crc32_to_bytes(computed) == received

    # for x in range(4):
    #     i = 4-x
    #
    #     c_x = (computed >> (8 * (i - 1))) & 0xFF
    #     if c_x < 0:
    #         c_x += 256
    #
    #     r_x = (received[3 - (i - 1)])
    #
    #     if c_x != r_x:
    #         return False
    #
    # return True




class Reticul8Packet(object):

    def __init__(self, incoming_packet_queue):
        self.incoming_packet_queue = incoming_packet_queue
        self.clear()

    def clear(self):
        self.buf = []
        self.esc = False
        self.packet_in_progress = False

    def data_recv(self, data):

        failures = sum(map(self.byte_recv,data))

    def byte_recv(self, b):

        if self.packet_in_progress:

            if self.esc:
                self.buf.append(b ^ R8_SERIAL_ESC)
                self.esc = False
                return 0
            elif b == R8_SERIAL_ESC:
                self.esc = True
                return 0
            elif b == R8_SERIAL_END:

                try:
                    self.check_packet()
                    self.clear()
                    return 0
                except:
                    logging.error("Bad packet received ", self.buf)
                    self.clear()
                    return 1

            else:
                self.buf.append(b)
                return 0

        elif b == R8_SERIAL_START:
            self.clear()
            self.packet_in_progress = True
            return 0
        else:
            return 1



    def check_packet(self):

        assert self.buf[2] == (len(self.buf) - R8_SERIAL_OVERHEAD)

        pkt = bytes(self.buf[:-4])
        crc = bytes(self.buf[-4:])

        assert len(crc) == 4, len(crc)

        assert len(pkt) -3 == self.buf[2], 'pkt len {} != {}'.format(len(pkt), self.buf[2])

        crc_computed = crc32_compute(pkt)

        assert crc32_compare(crc_computed, crc) is True

        self.incoming_packet_queue.put_nowait((datetime.datetime.utcnow(), pkt))


class Reticul8Serial(asyncio.Protocol):

    def __init__(self, incoming_packet_queue):
        super().__init__()
        self._transport = None
        self.r8packet = Reticul8Packet(incoming_packet_queue)
        self.msg_id = 0

    def connection_made(self, transport):
        self._transport = transport

        # Reset device
        self._transport.serial.setDTR(True)
        self._transport.serial.setRTS(True)
        time.sleep(0.01)
        self._transport.serial.setDTR(False)
        self._transport.serial.setRTS(False)

    def data_received(self, data):
        self.r8packet.data_recv(data)

    def connection_lost(self, exc):
        self._transport.loop.stop()

    def pause_writing(self):
        print(self._transport.get_write_buffer_size())

    def resume_writing(self):
        print(self._transport.get_write_buffer_size())


    def send_packet(self, source, dest, packet):

        if packet.HasField('msg_id') is not True:
            msg_id = self.msg_id
            self.msg_id += 1
            packet.msg_id = msg_id
        pbytes = packet.SerializeToString()
        plen = len(pbytes)
        assert plen< R8_SERIAL_MAX_PACKET

        b = bytes([dest, source, plen]) + pbytes
        crc = crc32_compute(b)

        b += crc32_to_bytes(crc)

        outbuf = [R8_SERIAL_START]

        for _ in b:
            if _ == R8_SERIAL_ESC or _ == R8_SERIAL_START or _ == R8_SERIAL_END:
                outbuf.append(R8_SERIAL_ESC)
                outbuf.append(_ ^ R8_SERIAL_ESC)
            else:
                outbuf.append(_)
        outbuf.append(R8_SERIAL_END)

        self._transport.write(bytes(outbuf))
        return packet.msg_id



