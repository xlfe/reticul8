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

            await ping()

            await pinMode(22, OUTPUT)
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
                await ping()
            while True:
                await PWM_fade(22, 0, 500)
                await sleep(1)
                await PWM_fade(22, 8192, 500)
                await sleep(1)


class TSA_Node(rpc.Node):

    async def notify_startup(self):
        print("startup from {}!".format(self.device_id))

        with self:

            await ping()

            await pinMode(22, OUTPUT)
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
            while True:
                await ping()

            while True:
                await PWM_fade(22, 0, 500)
                await sleep(1)
                await PWM_fade(22, 8192, 500)
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






