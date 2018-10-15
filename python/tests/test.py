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

from reticul8 import pjon_strategies, rpc
from reticul8.arduino import *
class ESP_Node(rpc.Node):

    async def notify_startup(self):
        print("STARTUP from {}!".format(self.device_id))

        self.bmp = BMP280(self, 33, 32)
        print(await self.bmp.temp_and_pressure)

        with self:

            assert await pinMode(22, OUTPUT)
            h = 0
            while True:
                await digitalWrite(22, LOW if h ==0 else HIGH)
                h = 0 if h == 1 else 1
                await ota_test()

            await ping()

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
            print(await self.bmp.temp_and_pressure)
            while True:
                await PWM_fade(22, 0, 500)
                await sleep(1)
                await PWM_fade(22, 8192, 500)
                await sleep(1)

OTA_UPDATE_SIZE = 192

async def ota_update(node, filename):
    chunk = 0

    original_timeout = node.transport.TIMEOUT_US
    # first packet takes > 800ms
    node.transport.TIMEOUT_US = 15 * 100000

    with open(filename, 'rb') as rom:

        with node:

            logging.debug('Starting update')

            chunk_data = rom.read(192)
            while len(chunk_data):

                logging.info('Sending chunk {} ({:,} total sent)'.format(chunk, chunk*192))
                assert check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().ota_update(chunk=chunk, data=chunk_data)))
                chunk_data = rom.read(192)
                chunk += 1

            logging.info('Finalizing update')
            assert check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().ota_update(chunk=0, data=bytes([0]))))
            logging.info('Done!')

    node.transport.TIMEOUT_US = original_timeout




from os import path

class TSA_Node(rpc.Node):

    async def notify_startup(self):
        print("startup from {}!".format(self.device_id))
        await ota_update(self, os.path.join(path.expanduser('~'), 'esp/xha_32/build/reticul8_esp32.bin'))
        return
        if False:
            other = self.transport.nodes[12]
            other.startup = datetime.datetime.now()
            asyncio.ensure_future(other.notify_startup())

        with self:

            await ping()

            await pinMode(22, OUTPUT)
            for i in range(3):
                await digitalWrite(22, HIGH)
                await sleep(.1)
                await digitalWrite(22, LOW)
                await sleep(.1)

            await esp32_reboot()

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
logging.basicConfig(level=logging.DEBUG)

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
        tsaio = ESPTSA(10, url=port, baudrate=115200)
        break


n1= TSA_Node(11, transport=tsaio)
node = ESP_Node(12, transport=tsaio)



# async def test_router():
#     await asyncio.sleep(2)
#     await node.notify_startup()
# n1.notify_startup = test_router

loop.run_forever()
loop.close()






