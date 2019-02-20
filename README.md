## reticul8

**Remotely articulated MCU endpoints for Python**

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
                                          
"HUB" (Running Python) <--Serial/UART--> NODE 1 (ESP32)
                                          ^--ESPNOW --> NODE 2 (ESP32)
                                          ^--ESPNOW --> NODE n (ESP32)
```

### Rationale

reticul8 is designed to meet the following requirements :-

* The system should be able to run "complex application logic" and be "internet connected"
* Nodes in the system should be able to connect to the hub using a variety of media (wired and wireless)
* Nodes should be able to run on common MCU hardware (Arduino and ESP32 targeted initially)
* Nodes should be fast and reliable, but don't need to be "smart" - application logic can live elsewhere
* Communication between nodes and controller should be fast and reliable (ie not over the internet!)

Notice that one key requirement is the **absence of internet connectivity**. What happens to your home
automation system when the internet goes down? 

reticul8 is designed for a home automation system where the nodes are not (necessarily) directly connected
to the internet. This also has the benefit of making communication between the controller/hub and the nodes much 
faster than something like pub/sub (<70ms rtt for a two node setup with ESPNOW and ThroughSerial).

Building on PJON as the communication medium between the nodes allows for plenty of options.

reticul8 is designed to be part of a home automation system - specifically it allows nodes (eg an ESP32 or Arduino) to 
operate as dumb remote endpoints controlled by a smart controller (eg Python running on RaspberryPi).

Competing projects include :-

* Mongoose OS - An open source Operating System for the Internet of Things
* MicroPython - Python for microcontrollers
* Zerynth - The Middleware for IoT using Python on Microcontrollers

But when I looked at the features I required, none of these seemed like a good fit. MicroPython and Zerynth seemed to 
be too "resource heavy" to run a simple dumb endpoint. Mongoose OS was a pretty close fit but it still assumes your 
nodes are on the internet.

### Arduino-like API:

The nodes (endpoints) are controlled using Remote Procedure Calls (RPC) defined with [protocolbuf](reticul8.proto).

An Arduino-like API is provided :-

```python
import asyncio
import uvloop
from reticul8 import rpc, pjon_strategies
from reticul8.arduino import *

class Node(rpc.Node):

    async def notify_startup(self):
        print("Received startup message from {}".format(self.device_id))

        with self:

            # schedule the inbuilt LED to blink 10 times
            with Schedule(count=10, after_ms=100, every_ms=500):
                await digitalWrite(22, LOW)

            with Schedule(count=10, after_ms=600, every_ms=500):
                await digitalWrite(22, HIGH)

            await asyncio.sleep(10)

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


## Building an ESP-IDF component node

[Create a new ESP-IDF project](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html), 
and [add the Arduino component](https://github.com/espressif/arduino-esp32/blob/master/docs/esp-idf_component.md).

Add reticul8 as a component :-

```bash
cd components
git clone https://github.com/xlfe/reticul8
```

Your `main.cpp` just needs to setup your PJON buses, and pass these to the reticul8 class. Call setup and loop as per
the arduino functions.

```cpp

// Define Wifi config for ESPNOW 

#include "esp_wifi_types.h"
static wifi_country_t wifi_country = {
        cc:     "AU",
        schan:  1,
        nchan:  14,
        max_tx_power: 80, // Level 10
        policy: WIFI_COUNTRY_POLICY_MANUAL
};

#include "Arduino.h"

# PJON defines

#define PJON_INCLUDE_ANY
#define PJON_INCLUDE_TSA
#define PJON_INCLUDE_EN
#define TSA_RESPONSE_TIME_OUT 100000

#include <reticul8.h>

PJON<Any> *bus = NULL;
RETICUL8 *r8 = NULL;

void loop() {
    r8->loop();
}

void setup() {

    Serial.begin(115200);
    Serial.flush();

    //EPSNOW
    StrategyLink <ESPNOW> *link_esp = new StrategyLink<ESPNOW>;
    PJON<Any> *bus_esp = new PJON<Any>();

    bus_esp->set_asynchronous_acknowledge(false);
    bus_esp->set_synchronous_acknowledge(true);
    bus_esp->set_packet_id(true);
    bus_esp->set_crc_32(true);
    bus_esp->strategy.set_link(link_esp);

    //Uncomment the line below to make a single bus device (eg leaf)
    // otherwise the device is initialised as a bridge between esp-now and serial

    // r8 = new RETICUL8(bus_esp, 10); /*


    //Serial
    StrategyLink <ThroughSerialAsync> *link_tsa = new StrategyLink<ThroughSerialAsync>;
    link_tsa->strategy.set_serial(&Serial);

    bus = new PJON<Any>(11);
    bus->strategy.set_link(link_tsa);
    bus->set_asynchronous_acknowledge(false);
    bus->set_synchronous_acknowledge(false);
    bus->set_packet_id(false);
    bus->set_crc_32(false);

    PJON<Any> *secondary[1] = {bus_esp};
    r8 = new RETICUL8(bus, 10, secondary, 1);
    //*/

    r8->begin();
}
```

Finally, make sure your `component.mk` (in same directory as main.cpp) includes the following :-

```cmake
COMPONENT_DEPENDS += reticul8

#Used for build timestamp
CPPFLAGS += -D"__COMPILE_TIME__ =`date '+%s'`"
```
