import itertools
from . import reticul8_pb2 as r8
from . import rpc

import asyncio

HIGH = r8.PV_HIGH
LOW = r8.PV_LOW
sleep = asyncio.sleep
OUTPUT = r8.PM_OUTPUT
INPUT_PULLDOWN = r8.PM_INPUT_PULLDOWN
INPUT_PULLUP = r8.PM_INPUT_PULLUP

def ping():
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().ping())

def pinMode(pin, mode):
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_config(pin=pin, mode=mode))

def digitalWrite(pin, value):
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_write(pin=pin, value=value))

async def digitalRead(pin):
    result = await rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_read(pin=pin))
    return result.pin_value

from concurrent.futures import ThreadPoolExecutor
def PWM_config(pin):
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_config(pin=pin))

def PWM_duty(pin, duty):
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_duty(pin=pin, duty=duty))

def PWM_fade(pin, duty, fade_ms):
    return rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_fade(pin=pin, duty=duty, fade_ms=fade_ms))





def blah(self):
    rpc = r8.RPC()

    rpc.hasField(args[0])

    if LARGE_PING:
        rpc.ota_update.data = b'F'*192
        rpc.ota_update.chunk = 0
    else:
        rpc.ping.ping = True
    self.send_packet(rpc)



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
    self.send_packet(11, s1)

    s2 = r8.RPC()
    s2.schedule.count = -1
    s2.schedule.after_ms = 0
    s2.schedule.every_ms = 2000
    s2.pwm_fade.pin = 22
    s2.pwm_fade.duty = 8192
    s2.pwm_fade.fade_ms = 200
    self.send_packet(11, s2)

