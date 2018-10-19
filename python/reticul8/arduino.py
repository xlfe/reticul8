import itertools
import random
from . import reticul8_pb2 as r8
from . import rpc

import asyncio

HIGH = r8.PV_HIGH
LOW = r8.PV_LOW
sleep = asyncio.sleep
OUTPUT = r8.PM_OUTPUT
INPUT_PULLDOWN = r8.PM_INPUT_PULLDOWN
INPUT_PULLUP = r8.PM_INPUT_PULLUP

check_success = lambda _:_ is not None and _.result.result == r8.RT_SUCCESS
send_rpc = lambda _:rpc.node.get().send_packet(rpc.RPC_Wrapper())
Schedule = rpc.Schedule


async def ping():
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().ping()))

async def pinMode(pin, mode):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_config(pin=pin, mode=mode)))

async def digitalWrite(pin, value):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_write(pin=pin, value=value)))

async def digitalRead(pin):
    result = await rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_read(pin=pin))
    return result.result.pin_value

async def pinWatch(pin, debounce_ms=200):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().gpio_monitor(pin=pin, debounce_ms=debounce_ms)))

async def PWM_config(pin):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_config(pin=pin)))

async def PWM_duty(pin, duty):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_duty(pin=pin, duty=duty)))

async def PWM_fade(pin, duty, fade_ms):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_fade(pin=pin, duty=duty, fade_ms=fade_ms)))

async def PWM_stop(pin):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().pwm_stop(pin=pin)))

async def i2c_config(pin_sda, pin_scl):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().i2c_config(pin_sda=pin_sda, pin_scl=pin_scl)))

async def i2c_read(device, address, len):
    result = await rpc.node.get().send_packet(rpc.RPC_Wrapper().i2c_read(device=device, address=address,len=len))
    return result.raw

async def i2c_write(device, data):
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().i2c_write(device=device, data=data, len=len(data))))

async def ota_test():
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().ota_update(chunk=random.randint(0,1000000), data=200*b'd')))

async def esp32_reboot():
    return check_success(await rpc.node.get().send_packet(rpc.RPC_Wrapper().reboot()))



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

