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
#define PJON_INCLUDE_SWBB

#include <PJON.h>
#include "reticul8.h"

RETICUL8 *r8 = NULL;

void loop() {
    r8->loop();
}

void setup() {

    StrategyLink<ESPNOW> *esp = new StrategyLink<ESPNOW>;
    //Configure ESPNOW options
    char pmk[17] = "\x2b\xb2\x1e\x7a\x83\x13\x76\x9f\xf8\xa9\x3b\x1b\x5b\x52\xd0\x70";
    esp->strategy.set_channel(1);
    esp->strategy.set_pmk(pmk);


    StrategyLink<SoftwareBitBang> *swbb = new StrategyLink<SoftwareBitBang>;
    //Configure SoftwareBitBang options
    swbb->strategy.set_pin(12);

    //Start Reticul8 MASTER NODE
    StrategyLinkBase *strategies[2] = {esp, swbb};
    r8 = new RETICUL8(R8_MASTER_NODE_ID, strategies, 2);
    r8->begin();
}
