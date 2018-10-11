
#pragma once
//#define PJON_INCLUDE_ANY
//#define PJON_INCLUDE_EN

#include "reticul8.pb.h"


#define PJON_PACKET_MAX_LENGTH (250-4)
#define PJON_INCLUDE_PACKET_ID true
#define PJON_INCLUDE_ASYNC_ACK true

#include "Arduino.h"
#include "wire.h"
#include <PJON.h>

#include <pb.h>
#include <pb_encode.h>
#include <pb_decode.h>

#define RETICUL8_MAX_WATCHED_PINS 20


#ifdef ESP32

#define LEDC_NOT_IN_USE 0
#define LEDC_IN_USE 1

#include <rom/rtc.h>
#include "driver/ledc.h"

#define RETICUL8_MAX_LEDC_CHANNELS LEDC_CHANNEL_MAX

struct LEDC_CHANNEL {
    ledc_channel_config_t config;
    uint8_t state;
};

#endif


#define RETICUL8_MAX_SCHEDULED_COMMANDS 20
#define SCHEDULE_COMMAND_NOT_IN_USE 0
#define SCHEDULE_COMMAND_IN_USE 1

struct SCHEDULED_COMMAND {
    uint8_t state;
    uint32_t next_execution;

    RPC command;
};



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


#define MAX_SECONDARY_BUSSES 2


struct BUS_DETAILS;


class RETICUL8 {

public:
    RETICUL8(
            PJON <Any> *bus,
            uint8_t master_id,
            PJON <Any> *secondary[] = NULL,
            uint8_t secondary_bus_count = 0);
    void loop();
    void begin();
    void r8_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info);

    uint8_t device_id() {
        return bus->device_id();
    }
    uint8_t master_id() {
        return _master_id;
    }

    PJON <Any> *get_bus(uint8_t idx) {
        if (idx == 0) {
            return bus;
        }
        if (idx > secondary_bus_count) {
            return NULL;
        }
        return secondary[idx - 1];
    }


private:
    PJON <Any> *bus;
    PJON <Any> *secondary[MAX_SECONDARY_BUSSES];
    uint8_t secondary_bus_count = 0;
    uint8_t _master_id;
    void check_for_events();

    void run_command(RPC *request, FROM_MICRO *reply);

    struct WATCHED_PIN watched_pins[RETICUL8_MAX_WATCHED_PINS];
    void notify_event(FROM_MICRO *m);
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


    struct SCHEDULED_COMMAND scheduled_commands[RETICUL8_MAX_SCHEDULED_COMMANDS];
    void check_for_scheduled_commands();
    bool add_scheduled_command(uint8_t *payload, uint16_t length);


};

struct BUS_DETAILS {
    RETICUL8 *r8;
    uint8_t bus_idx;
};

void blink(uint8_t count=1);

