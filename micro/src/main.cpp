// Define Wifi config for ESPNOW 
#include <Arduino.h>
#include <WiFi.h>

// Define WiFi country configuration
static wifi_country_t wifi_country = {
  cc : "AU",
  schan : 1,
  nchan : 14,
  max_tx_power : 1,
  policy : WIFI_COUNTRY_POLICY_MANUAL
};

#define PJON_INCLUDE_ANY
#define PJON_INCLUDE_EN
#define PJON_INCLUDE_TSA
#define PJON_INCLUDE_SWBB
#define TSA_RESPONSE_TIME_OUT 100000

#include <PJON.h>
#include "reticul8.h"

PJON<Any> *bus = NULL;
RETICUL8 *r8 = NULL;

void loop() {
    r8->loop();
}

void setup() {

    Serial.begin(115200);
    Serial.flush();

    //EPSNOW
    StrategyLink<ESPNOW> *link_esp = new StrategyLink<ESPNOW>;
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

    PJON<Any> *buses[2] = {bus, bus_esp};
    r8 = new RETICUL8(10, true, buses, 2);
    //*/

    r8->begin();
}
