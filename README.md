## reticul8

**What do you get if you combine Python and and MCUs?**

reticul8 allows you to use Python to remotely control a compatible microcontroller 
such as an Arduino or ESP32.

On the Python side, it uses Python 3.5+ and asyncio
On the microcontroller side it uses [PJON](https://github.com/gioblu/PJON) 
and [PJON-cython](https://github.com/xlfe/PJON-cython) to communicate with 
the micro controller - anything uC that can run PJON should be compatible.
It also uses [protocol buffers](reticul8.proto) to encapsulate the RPC messages.

For example, you could use the following setup to wirelessly control an
ESP32 using ESPNOW

```
Python <--Serial/UART--> ESP32(Router) <--ESPNOW--> ESP32(Node)
```


Includes an Arduino-like API:

```python
import asyncio
import uvloop
from reticul8 import rpc, pjon_strategies
from reticul8.arduino import *

class Node(rpc.Node):

    async def notify_startup(self):
        print("Received startup message from {}".format(self.device_id))

        with self:
            
            #manually blink the LED 

            await pinMode(22, OUTPUT)
            for i in range(5):
                await digitalWrite(22, HIGH)
                await sleep(.1)
                await digitalWrite(22, LOW)
                await sleep(.1)
                
            #read the value of the pin
            await pinMode(19, INPUT_PULLUP)
            value = await digitalRead(19)
            print("HIGH" if value == HIGH else "LOW")

            #ping the remote node
            for i in range(10):
                await ping()

            #an ESP32 feature - built in PWM
            await PWM_config(22)
            while True:
                await PWM_fade(pin=22, duty=0, fade_ms=500)
                await sleep(1)
                await PWM_fade(pin=22, duty=8192, fade_ms=500)
                await sleep(1)


class PJON(pjon_strategies.SerialAsyncio):

    def notify_connection_made(self):
        print("ESP32 connected")

    def notify_connection_lost(self):
        asyncio.get_event_loop().stop()
        

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()
transport = PJON(device_id=10, url="/dev/ttyUSB0", baudrate=115200)
Node(remote_device_id=11, transport=PJON)
loop.run_forever()
loop.close()
```

## Supported RPCs

GPIO 
* pinMode()
* digitalRead()
* digitalWrite()
* INPUT -> Watch pin for changes with callback on change, debounce

I2C
* i2c_read
* i2c_write

ESP32 specific features:
* PWM (ledc)
* OTA Update 

reticul8 helpers
* schedule commands to run repeatedly
* run multiple commands 


## Planned features

* Analog output
* Analog input
* Touch sensor (ESP32)
* Pulse counter (ESP32)
