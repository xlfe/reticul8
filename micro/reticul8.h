
#pragma once

//#define PJON_INCLUDE_ANY
//#define PJON_INCLUDE_EN

#define PJON_PACKET_MAX_LENGTH 246
#define PJON_INCLUDE_PACKET_ID true
//#define PJON_INCLUDE_ASYNC_ACK true

#include "Arduino.h"
#include "wire.h"
#include <PJON.h>

#include <pb.h>
#include <pb_encode.h>
#include <pb_decode.h>
#include "reticul8.pb.h"

#define RETICUL8_MAX_WATCHED_PINS 20


#ifdef ESP32

#define LEDC_NOT_IN_USE 0
#define LEDC_IN_USE 1

#include "driver/ledc.h"

#define RETICUL8_MAX_LEDC_CHANNELS LEDC_CHANNEL_MAX

struct LEDC_CHANNEL {
    ledc_channel_config_t config;
    uint8_t state;
};

#endif



#define WATCH_NOT_IN_USE 0
#define WATCH_IN_USE 1

struct WATCHED_PIN {
    uint8_t state;
    uint8_t pin;
    uint8_t notified_value;
    uint8_t last_reading;
    uint32_t last_debounce;
    uint16_t debounce_ms;
};


class RETICUL8 {

public:
    RETICUL8(PJON <Any> *bus, uint8_t master_id);
    void loop();
    void begin();
    void r8_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info);


private:
    PJON <Any> *bus;
    uint8_t master_id;
    void check_for_events();

    struct WATCHED_PIN watched_pins[RETICUL8_MAX_WATCHED_PINS];
    void notify_event(EVENT event);
    void setup_watched_pin(WATCHED_PIN &p, uint8_t pin, uint16_t debounce_ms);
    bool watch_pin(uint8_t pin, uint16_t debounce_ms);
    bool unwatch_pin(uint8_t pin);


#ifdef ESP32
    struct LEDC_CHANNEL ledc_channels[RETICUL8_MAX_LEDC_CHANNELS];
    bool setup_ledc_channel(uint8_t pin);
    bool set_ledc_duty(uint8_t pin, uint32_t duty);
    bool set_ledc_fade(uint8_t pin, uint32_t duty, uint32_t fade_ms);
#endif


    bool is_i2c_setup = false;
#ifdef ESP32
    bool i2c_setup(uint8_t sda, uint8_t scl);
#else
    bool i2c_setup();
#endif
    bool i2c_write(uint8_t device, uint8_t *data, uint8_t len);
    uint8_t i2c_read(uint8_t device, uint8_t address, uint8_t len, uint8_t *buf);




};

