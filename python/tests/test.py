#
# To test on RPi 3b using hardware serial
# add to /boot/config.txt   dtoverlay=pi3-disable-bt
# run                       sudo systemctl disable hciuart
# connect   GPIO18 (Pin 12) to the EN pin on the ESP32
#           GND <-> GND and 5v <-> 5v
#           ESP32 RX Pin <-> RPi UART TX (Pin 08 / GPIO14)
#           ESP32 TX Pin <-> RPi UART RX (Pin 10 / GPIO15)


import uvloop
import time
import asyncio
import datetime
import logging
import os

from bmp280 import BMP280

try:
    import gpiozero
    esp = gpiozero.OutputDevice(pin=18, active_high=True, initial_value=True)
except:
    #assume were using usb serial, device will be reset when serial connects
    esp = None

LARGE_PING = True
PING_WAIT = 0.0001

from reticul8 import pjon_strategies, rpc, block_compressor
from reticul8.arduino import *
class ESP_Node(rpc.Node):

    async def notify_startup(self):
        print("STARTUP from {}!".format(self.device_id))


        await ota_update(self, os.path.join(path.expanduser('~'), 'esp/xha_32/build/reticul8_esp32.bin'))
        # self.bmp = BMP280(self, 33, 32)
        # print(await self.bmp.temp_and_pressure)

        with self:

            while True:
                await ping()
                await asyncio.sleep(0.2)


            for i in range(5):
                await digitalWrite(22, HIGH)
                await sleep(.1)
                await digitalWrite(22, LOW)
                await sleep(.1)
            await pinMode(19, INPUT_PULLUP)
            value = await digitalRead(19)
            print("HIGH" if value == HIGH else "LOW")

            for i in range(10):
                await ping()

            await PWM_config(22)
            # print(await self.bmp.temp_and_pressure)
            while True:
                await PWM_fade(22, 0, 500)
                await sleep(1)
                await PWM_fade(22, 8192, 500)
                await sleep(1)





async def ota_update(node, filename):
    """send an OTA update using zlib compression.
    In testing, a release build esp32 binary is compressed to
    approx  71 percent of its original size using this method"""

    OTA_UPDATE_SIZE = 200
    chunk = 0
    original_timeout = node.transport.TIMEOUT_US
    # first packet takes > 800ms - I guess the ESP32 is wiping the partition?
    node.transport.TIMEOUT_US = 15 * 100000

    with open(filename, 'rb') as rom:

        blocks = block_compressor.block_compressor(rom, OTA_UPDATE_SIZE)

        with node:

            logging.debug('Starting update')

            for crc32, size, block in blocks.blocks():

                logging.info('{:.0f}% / {:.2f} - Sending chunk {:>5,} - {:,}b -> {}b - crc32: {}'.format(blocks.percent, blocks.ratio, chunk, size, len(block), crc32))
                result = await rpc.node.get().send_packet(rpc.RPC_Wrapper().ota_update(chunk=chunk if blocks.more else 0, data=block))
                assert check_success(result)
                remote_crc = pjon_strategies.decode_uint32t(result.raw)
                if crc32 != remote_crc:
                    logging.error('CRC Mismatch Local {} remote {}'.format(crc32, remote_crc))
                    exit(1)
                chunk += 1

            # logging.info('Finalizing update')
            # assert check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().ota_update(chunk=0, data=bytes([0,0]))))
            logging.info('Done!')

    node.transport.TIMEOUT_US = original_timeout




from os import path

class TSA_Node(rpc.Node):

    async def notify_startup(self):
        print("startup from {}!".format(self.device_id))

        if False:
            other = self.transport.nodes[12]
            other.startup = datetime.datetime.now()
            asyncio.ensure_future(other.notify_startup())

        with self:

            assert await pinMode(22, OUTPUT)

            with Schedule(count=10, after_ms=0, every_ms=500):
                await digitalWrite(22, LOW)

            with Schedule(count=10, after_ms=500, every_ms=500):
                await digitalWrite(22, HIGH)

            await asyncio.sleep(10)

            while True:
                await ping()
                await asyncio.sleep(2)

            for i in range(3):
                await digitalWrite(22, HIGH)
                await sleep(.1)
                await digitalWrite(22, LOW)
                await sleep(.1)

            # await esp32_reboot()

            await pinMode(19, INPUT_PULLUP)
            assert await digitalRead(19) == HIGH

            await PWM_config(22)

            for i in range(1):
                await PWM_fade(22, 0, 500)
                await sleep(1)
                await PWM_fade(22, 8192, 500)
                await sleep(1)

            await PWM_fade(22,0, 5000)
            await asyncio.sleep(5)
            assert await pinMode(22, OUTPUT) is True

            while True:
                await digitalWrite(22, HIGH)
                await sleep(1)
                await digitalWrite(22, LOW)
                await sleep(1)




class ESPTSA(pjon_strategies.SerialAsyncio):

    def notify_connection_made(self):
        if esp is not None:
            esp.on()
            time.sleep(1)

    def notify_connection_lost(self):
        asyncio.get_event_loop().stop()



asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
loop.set_debug(True)
logging.basicConfig(level=logging.INFO)

UART_PORT = [
    # '/dev/ttyUSB0',
    # '/dev/ttyAMA0',
    '/dev/tty.wchusbserial1410',
    '/dev/tty.wchusbserial14120',
    '/dev/tty.SLAB_USBtoUART'
    ]

for port in UART_PORT:
    if os.path.exists(port):
        if esp is not None:
            esp.off()
        tsaio = ESPTSA(10, url=port, baudrate=115200)
        break


n1= TSA_Node(11, transport=tsaio)
node = ESP_Node(12, transport=tsaio)
n1.other = node



# async def test_router():
#     await asyncio.sleep(2)
#     await node.notify_startup()
# n1.notify_startup = test_router

loop.run_forever()
loop.close()





