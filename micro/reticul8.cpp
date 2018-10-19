#define ESP32 1
#include "reticul8.h"

RETICUL8::RETICUL8(PJON <Any> *bus, uint8_t master_id, PJON <Any> *secondary[], uint8_t secondary_bus_count) {
    this->bus = bus;
    this->_master_id = master_id;
    this->secondary_bus_count = secondary_bus_count;
    for (uint8_t i=0;i<secondary_bus_count;i++) {
        this->secondary[i] = secondary[i];
    }

    memset(&this->watched_pins, 0, sizeof this->watched_pins);
    memset(&this->scheduled_commands, 0, sizeof this->scheduled_commands);

#if ESP32
    memset(&this->ledc_channels, 0, sizeof this->ledc_channels);
#endif


}


PJON <Any> * RETICUL8::get_bus(uint8_t idx) {
    if (!secondary_bus_count || secondary_bus_count <= idx ) {
        return NULL;
    }
    return secondary[idx];
}


/*
 * Primary Bus has only the master connected (eg through serial)
 *
 * Any packet received on this bus is checked for destination -
 * if the destination is not this device, check if we know which bus to put it on
 * if not, send it to all busses
 *
 */

void primary_bus_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info) {

    RETICUL8 * r8 = ((RETICUL8 *) packet_info.custom_pointer);
    PJON<Any> *to_bus = NULL;

    if (packet_info.receiver_id == r8->bus->device_id()) {
        //Packet meant for this device
        r8->r8_receiver_function(payload, length, packet_info);
    } else {
        //Packet not meant for this device
        uint16_t bus_idx = r8->get_device_bus(packet_info.receiver_id);

        if (bus_idx == RETICUL8_UNKNOWN_BUS) {
            //Don't know where this bus is...

            for (bus_idx=0; bus_idx < r8->secondary_bus_count; bus_idx++){
                to_bus = r8->get_bus(bus_idx);

                if (r8->forward_packet(r8->_master_id, packet_info.receiver_id, r8->bus, to_bus, payload, length) == PJON_ACK) {
                    r8->set_device_bus(packet_info.receiver_id, bus_idx);
                    break;
                }
            }

            //Don't do anything...

        } else {
            to_bus = r8->get_bus(bus_idx);
            if (to_bus == NULL)
                return;
            r8->forward_packet(r8->_master_id, packet_info.receiver_id,
                    r8->bus, to_bus, payload, length, packet_info.header & PJON_ACK_REQ_BIT);
        }
        // figure out which bus this packet needs to go on
        // send blocking with timeout
        // once PJON_ACK is received, send an ack back on the primary bus
    }
}

uint16_t RETICUL8::get_device_bus(uint8_t device_id) {

    std::map<uint8_t, uint8_t>::iterator it = this->secondary_bus_lookup.find(device_id);

    if (it == this->secondary_bus_lookup.end()) {
        return RETICUL8_UNKNOWN_BUS;
    }
    return it->second;
}

void RETICUL8::set_device_bus(uint8_t device_id, uint8_t bus) {
    this->secondary_bus_lookup[device_id] = bus;
}


uint16_t RETICUL8::forward_packet(
        uint8_t from_id,
        uint8_t to_id,
        PJON<Any> *from_bus,
        PJON<Any> *to_bus,
        uint8_t *payload,
        uint16_t length,
        bool send_ack) {

    uint16_t ret;
    uint8_t to_bus_original_id = to_bus->device_id();
    to_bus->set_id(from_id);

    if ((ret = to_bus->send_packet(
            to_id,
            (char*)payload,
            length)
//            PJON_NO_HEADER,
//            0,
//            PJON_BROADCAST,
//            50000)
            ) == PJON_ACK) {
        if (send_ack) {
            from_bus->send_synchronous_acknowledge();
        }
    }
    to_bus->set_id(to_bus_original_id);
    return ret;
}


/*
 * Any packet received on the secondary bus should be forwarded to the master
 *
 * Devices operating on the secondary bus should address packets to the master
 *
 */
void secondary_bus_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info) {

    BUS_DETAILS *bd = ((BUS_DETAILS*)packet_info.custom_pointer);
    PJON<Any> *my_bus = bd->r8->get_bus(bd->bus_idx);

    //make sure we know which bus this sender_id is on
    bd->r8->set_device_bus(packet_info.sender_id, bd->bus_idx);
    bd->r8->forward_packet(packet_info.sender_id, bd->r8->_master_id,
            my_bus, bd->r8->bus, payload, length, packet_info.header & PJON_ACK_REQ_BIT);

}

void error_handler(uint8_t code, uint16_t data, void *custom_pointer) {
    if(code == PJON_CONNECTION_LOST) {
        ESP_LOGE("MAIN", "Connection lost");
    }
    if(code == PJON_PACKETS_BUFFER_FULL) {
        ESP_LOGE("MAIN", "Packet buffer is full, has now a length of %d",data);
    }
    if(code == PJON_CONTENT_TOO_LONG) {
        ESP_LOGE("MAIN", "Content is too long, length: %d",data);
    }
}


void RETICUL8::begin(){
    if ((PJON_PACKET_MAX_LENGTH - bus->packet_overhead()) < RPC_size) {
//        don't start packet if the configuration might break...
       return;
    }

    bus->set_custom_pointer(this);
    bus->set_receiver(primary_bus_receiver_function);
    bus->set_error(error_handler);
    if (this->secondary_bus_count) {
        //do we need to route packets to other buses?
        bus->set_router(true);
    }

    for (uint8_t i=0;i<secondary_bus_count;i++) {
        BUS_DETAILS *bd = new BUS_DETAILS;
        bd->r8 = this;
        bd->bus_idx = i;
        secondary[i] -> set_custom_pointer(bd);
        secondary[i] -> set_receiver(secondary_bus_receiver_function);
        // for devices on the secondary bus - this device should take the master_id...
        secondary[i] -> set_id(_master_id);
        secondary[i] -> begin();
    }

    bus->begin();

    FROM_MICRO m = FROM_MICRO_init_zero;
    m.which_msg = FROM_MICRO_startup_tag;

#ifdef ESP32
    {
        m.msg.startup = STARTUP_REASON_SR_UNKNOWN;

        switch (rtc_get_reset_reason(0))
        {
            case 1 :  m.msg.startup = STARTUP_REASON_ESP32_POWERON_RESET; break;
            case 3 :  m.msg.startup = STARTUP_REASON_ESP32_SW_RESET;break;
            case 4 :  m.msg.startup = STARTUP_REASON_ESP32_OWDT_RESET;break;
            case 5 :  m.msg.startup = STARTUP_REASON_ESP32_DEEPSLEEP_RESET;break;
            case 6 :  m.msg.startup = STARTUP_REASON_ESP32_SDIO_RESET;break;
            case 7 :  m.msg.startup = STARTUP_REASON_ESP32_TG0WDT_SYS_RESET;break;
            case 8 :  m.msg.startup = STARTUP_REASON_ESP32_TG1WDT_SYS_RESET;break;
            case 9 :  m.msg.startup = STARTUP_REASON_ESP32_RTCWDT_SYS_RESET;break;
            case 10 : m.msg.startup = STARTUP_REASON_ESP32_INTRUSION_RESET;break;
            case 11 : m.msg.startup = STARTUP_REASON_ESP32_TGWDT_CPU_RESET;break;
            case 12 : m.msg.startup = STARTUP_REASON_ESP32_SW_CPU_RESET;break;
            case 13 : m.msg.startup = STARTUP_REASON_ESP32_RTCWDT_CPU_RESET;break;
            case 14 : m.msg.startup = STARTUP_REASON_ESP32_EXT_CPU_RESET;break;
            case 15 : m.msg.startup = STARTUP_REASON_ESP32_RTCWDT_BROWN_OUT_RESET;break;
            case 16 : m.msg.startup = STARTUP_REASON_ESP32_RTCWDT_RTC_RESET;break;
            case NO_MEAN: break;
        }
    }

    m.which_data = FROM_MICRO_raw_tag;
    memcpy(m.data.raw.bytes, &this->BUILD, sizeof(this->BUILD));
    m.data.raw.size = sizeof(this->BUILD);

    /*
        uint8_t sha_256[32] = { 0 };
        m.which_data = FROM_MICRO_raw_tag;
        esp_partition_get_sha256(esp_ota_get_running_partition(), sha_256);
        memcpy(m.data.raw.bytes, sha_256, 32);
        m.data.raw.size = 32;
    */

#endif

    this->notify_event(&m);

}

uint8_t LED_STATUS = 0;
void RETICUL8::loop() {
    check_for_events();
    check_for_scheduled_commands();
    bus->update();
    vTaskDelay(1);
    bus->receive();

    for (uint8_t i=0;i<secondary_bus_count;i++) {
        secondary[i] -> update();
        secondary[i] -> receive();
    }

}

void RETICUL8::notify_event(FROM_MICRO *m) {

    uint8_t notify_buf[FROM_MICRO_size];

    m->heap_usage = ESP.getFreeHeap();
    m->uptime_ms = millis();

    pb_ostream_t notify_stream = pb_ostream_from_buffer(notify_buf, sizeof(notify_buf));
    bool status = pb_encode(&notify_stream, FROM_MICRO_fields, m);

    if (status) {
        this->bus->send(this->_master_id, (char*)notify_buf, notify_stream.bytes_written);
    }
}

void RETICUL8::check_for_scheduled_commands() {

    for (uint16_t i = 0; i < RETICUL8_MAX_SCHEDULED_COMMANDS; i++) {
        if (this->scheduled_commands[i].state == SCHEDULE_COMMAND_IN_USE) {

            if (this->scheduled_commands[i].next_execution < millis()){

                FROM_MICRO m = FROM_MICRO_init_zero;
                m.which_msg = FROM_MICRO_result_tag;
                m.msg.result.result = RESULT_TYPE_RT_ERROR;
                m.msg.result.msg_id = this->scheduled_commands[i].command.msg_id;

                this->run_command(&this->scheduled_commands[i].command, &m);
                m.which_data = FROM_MICRO_schedules_remaining_tag;
                m.data.schedules_remaining = this->scheduled_commands[i].command.schedule.count;
                this->notify_event(&m);

                if (this->scheduled_commands[i].command.schedule.count != -1) {
                    this->scheduled_commands[i].command.schedule.count --;
                }

                if (this->scheduled_commands[i].command.schedule.count == 0){
                    memset(&this->scheduled_commands[i], 0, sizeof(SCHEDULED_COMMAND));
                } else {
                    this->scheduled_commands[i].next_execution += this->scheduled_commands[i].command.schedule.every_ms;
                }
            }
        }
    }
}

bool RETICUL8::add_scheduled_command(uint8_t *payload, uint16_t length) {

    for (uint16_t i = 0; i < RETICUL8_MAX_SCHEDULED_COMMANDS; i++) {
        if (this->scheduled_commands[i].state == SCHEDULE_COMMAND_NOT_IN_USE) {

            bool status;
            pb_istream_t in_stream = pb_istream_from_buffer(payload, length);

            status = pb_decode(&in_stream, RPC_fields, &this->scheduled_commands[i].command);

            if (!status) {
                return false;
            }

            this->scheduled_commands[i].next_execution = millis() + this->scheduled_commands[i].command.schedule.after_ms;
            this->scheduled_commands[i].state = SCHEDULE_COMMAND_IN_USE;
            return true;
        }
    }
    return false;
}

void RETICUL8::check_for_events() {

    for (uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].state == WATCH_IN_USE) {

            uint8_t reading = digitalRead(this->watched_pins[i].pin);

            if (reading != this->watched_pins[i].last_reading) {
                this->watched_pins[i].last_debounce = millis();
                this->watched_pins[i].last_reading = reading;
            }

            if ((millis() - this->watched_pins[i].last_debounce) > this->watched_pins[i].debounce_ms) {

                if (reading != this->watched_pins[i].notified_value) {

                    this->watched_pins[i].notified_value = reading;

                    FROM_MICRO m = FROM_MICRO_init_zero;
                    m.which_msg = FROM_MICRO_pin_change_tag;
                    m.msg.pin_change.pin = this->watched_pins[i].pin;
                    m.msg.pin_change.value = reading == 0 ? PIN_VALUE_PV_LOW : PIN_VALUE_PV_HIGH;

                    this->notify_event(&m);

                }
            }
        }
    }
}

bool RETICUL8::unwatch_pin(uint8_t pin) {

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].pin == pin) {
            memset(&this->watched_pins[i], 0, sizeof(struct WATCHED_PIN));
            return true;
        }
    }

    return false;
}

void RETICUL8::setup_watched_pin(WATCHED_PIN &p, uint8_t pin, uint16_t debounce_ms) {
    p.state = WATCH_IN_USE;
    p.pin = pin;
    p.notified_value = 0xFF-1;
    p.last_reading = 0xFF;
    p.last_debounce = 0;
    p.debounce_ms = debounce_ms;
}

bool RETICUL8::watch_pin(uint8_t pin, uint16_t debounce_ms) {

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].pin == pin) {
            this->setup_watched_pin(this->watched_pins[i], pin, debounce_ms);
            return true;
        }
    }

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].state == WATCH_NOT_IN_USE) {
            this->setup_watched_pin(this->watched_pins[i], pin, debounce_ms);
            return true;
        }
    }

    return false;

}

#ifdef ESP32
bool esp32_ledc_setup = false;

bool setup_esp32_ledc_timer() {

    if (esp32_ledc_setup) {
        return true;
    }

    ledc_timer_config_t ledc_timer;
    ledc_timer.speed_mode = LEDC_HIGH_SPEED_MODE;
    ledc_timer.duty_resolution = LEDC_TIMER_13_BIT;
    ledc_timer.timer_num = LEDC_TIMER_0;
    ledc_timer.freq_hz = 5000;
    if (ledc_timer_config(&ledc_timer) == ESP_OK) {
        esp32_ledc_setup = true;
        return true;
    }

    return false;
}

bool RETICUL8::check_if_pin_is_ledc_channel(uint8_t pin) {
    if (!setup_esp32_ledc_timer()) {
        return false;
    }

    for(uint16_t i = 0; i < RETICUL8_MAX_LEDC_CHANNELS; i++) {
        if (this->ledc_channels[i].config.gpio_num == pin) {
            return true;
        }
    }

    return false;
}

bool RETICUL8::stop_ledc_channel(uint8_t pin) {

    if (!setup_esp32_ledc_timer()) {
        return false;
    }

    for(uint16_t i = 0; i < RETICUL8_MAX_LEDC_CHANNELS; i++) {
        if (this->ledc_channels[i].config.gpio_num == pin) {
            if(ledc_stop(this->ledc_channels[i].config.speed_mode, (ledc_channel_t)i, 0) == ESP_OK &&
                gpio_reset_pin((gpio_num_t)this->ledc_channels[i].config.gpio_num) == ESP_OK) {
                memset(&this->ledc_channels[i], 0, sizeof this->ledc_channels[i]);
                return true;
            }
        }
    }

    return false;

}

bool RETICUL8::setup_ledc_channel(uint8_t pin) {

    if (!setup_esp32_ledc_timer()) {
        return false;
    }

    if (check_if_pin_is_ledc_channel(pin)) {
        return true;
    }


    for(uint16_t i = 0; i < RETICUL8_MAX_LEDC_CHANNELS; i++) {
        if (this->ledc_channels[i].state == LEDC_NOT_IN_USE) {

            this->ledc_channels[i].config.channel = (ledc_channel_t)i;
            this->ledc_channels[i].config.duty = 0;
            this->ledc_channels[i].config.gpio_num = pin;
            this->ledc_channels[i].config.speed_mode = LEDC_HIGH_SPEED_MODE;
            this->ledc_channels[i].config.timer_sel = LEDC_TIMER_0;

            if (ledc_channel_config(&this->ledc_channels[i].config) == ESP_OK) {
                this->ledc_channels[i].state = LEDC_IN_USE;
                return true;
            };
        }
    }

    return false;

}
bool RETICUL8::set_ledc_duty(uint8_t pin, uint32_t duty) {

    for(uint16_t i = 0; i < RETICUL8_MAX_LEDC_CHANNELS; i++) {
        if (this->ledc_channels[i].config.gpio_num == pin) {

            if (ledc_set_duty(LEDC_HIGH_SPEED_MODE, (ledc_channel_t)i, duty) != ESP_OK) {
                return false;
            }

            if (ledc_update_duty(LEDC_HIGH_SPEED_MODE, (ledc_channel_t)i) != ESP_OK) {
                return false;
            }

            return true;
        }
    }


    return false;
}
bool RETICUL8::set_ledc_fade(uint8_t pin, uint32_t duty, uint32_t fade_ms) {
    ledc_fade_func_install(0);

    for(uint16_t i = 0; i < RETICUL8_MAX_LEDC_CHANNELS; i++) {
        if (this->ledc_channels[i].config.gpio_num == pin) {

            if (ledc_set_fade_with_time(LEDC_HIGH_SPEED_MODE, (ledc_channel_t)i, duty, fade_ms) != ESP_OK){
                return false;
            }

            if (ledc_fade_start(LEDC_HIGH_SPEED_MODE, (ledc_channel_t)i, LEDC_FADE_NO_WAIT) != ESP_OK) {
                return false;
            }

            return true;
        }
    }

    return false;
}


#endif


#ifdef ESP32
    bool RETICUL8::i2c_setup(uint8_t sda, uint8_t scl) {
        if (is_i2c_setup) {
            return true;
        }
        if (Wire.begin(sda, scl) == true) {
            is_i2c_setup = true;
            return true;
        }
        return false;
    }

#else

    bool RETICUL8::i2c_setup() {
        if (is_i2c_setup) {
            return true;
        }
        Wire.begin();
        is_i2c_setup = true;
        return true;
    }
#endif

bool RETICUL8::i2c_write(uint8_t device, uint8_t *data, uint8_t len) {

    Wire.beginTransmission(device);

    for(uint8_t i = 0; i < len; i++) {
        Wire.write(data[i]);
    }

    if (Wire.endTransmission() == 0){
        return true;
    }
    return false;
}

uint8_t RETICUL8::i2c_read(uint8_t device, uint8_t address, uint8_t len, uint8_t *buf) {

    Wire.beginTransmission(device);
    Wire.write(address);
    Wire.endTransmission();

    Wire.requestFrom(device, len);

    if (Wire.available() == len) {
        for (uint8_t i=0; i<len; i++) {
            buf[i] = Wire.read();
        }
    } else {
        return 0;
    }

    return len;

}

void RETICUL8::r8_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info) {

    RPC request = RPC_init_zero;
    bool status;
    pb_istream_t in_stream = pb_istream_from_buffer(payload, length);

    status = pb_decode(&in_stream, RPC_fields, &request);

    if (!status) {
        return;
    }

    FROM_MICRO m = FROM_MICRO_init_zero;
    m.which_msg = FROM_MICRO_result_tag;
    m.msg.result.result = RESULT_TYPE_RT_ERROR;
    m.msg.result.msg_id = request.msg_id;

    if (request.has_schedule) {

        if (this->add_scheduled_command(payload, length)) {
            m.msg.result.result = RESULT_TYPE_RT_SUCCESS;
        }

    } else {
        this->run_command(&request, &m);
    }

    this->notify_event(&m);
}

bool RETICUL8::r8_inflate_init() {

    stream.avail_in = 0;
    stream.zalloc = (alloc_func)0;
    stream.zfree = (free_func)0;
    stream.opaque = (voidpf)0;

    int err= inflateInit(&stream);

    if (err != Z_OK) {

        switch (err){
            case Z_MEM_ERROR:
                ESP_LOGD("Inflate_Init","MEM_ERROR"); break;
            case Z_VERSION_ERROR:
                ESP_LOGD("Inflate_Init","VERSION_ERROR"); break;
            case Z_STREAM_ERROR:
                ESP_LOGD("Inflate_Init","STREAM_ERROR"); break;
        }

        return false;
    }

    return true;
}


bool RETICUL8::r8_inflate(Bytef *dest, uLongf *destLen, const Bytef *source, uLong *sourceLen, bool more) {

    uLong len, left, start;
    int err;

    if (*destLen == 0) {
        return Z_BUF_ERROR;
    }

    len = *sourceLen;
    left = *destLen;
    start = stream.total_out;
    *destLen = 0;

    stream.next_in = (Bytef*)source;
    stream.next_out = dest;
    stream.avail_out = 0;

    do {
        if (stream.avail_out == 0) {
            stream.avail_out = left;
            left -= stream.avail_out;
        }
        if (stream.avail_in == 0) {
            stream.avail_in = len;
            len -= stream.avail_in;
        }
        err = inflate(&stream, more ? Z_SYNC_FLUSH : Z_FINISH);
    } while (err == Z_OK);

    *sourceLen -= len + stream.avail_in;
    *destLen = stream.total_out - start;

    if (more) {

        switch (err) {
            case Z_OK:
                ESP_LOGD("INFLATE", "Z_OK"); break;
            case Z_STREAM_END:
                ESP_LOGD("INFLATE", "STREAM_END"); break;
            case Z_NEED_DICT:
                ESP_LOGD("INFLATE", "NEED_DICT"); break;
            case Z_ERRNO:
                ESP_LOGD("INFLATE", "ERRNO"); break;
            case Z_STREAM_ERROR:
                ESP_LOGD("INFLATE", "STREAM_ERROR"); break;
            case Z_DATA_ERROR:
                ESP_LOGD("INFLATE", "%s", stream.msg);
                ESP_LOGD("INFLATE", "DATA_ERROR"); break;
            case Z_MEM_ERROR:
                ESP_LOGD("INFLATE", "MEM_ERROR"); break;
            case Z_BUF_ERROR:
                ESP_LOGD("INFLATE", "BUF_ERROR"); break;
            case Z_VERSION_ERROR:
                ESP_LOGD("INFLATE", "VERSION_ERROR"); break;
        }

        return err == Z_BUF_ERROR;
    } else {
        inflateEnd(&stream);
        return err == Z_STREAM_END;
    }

}

void RETICUL8::run_command(RPC *request, FROM_MICRO *m) {
#ifdef ESP32
    _ret = ESP_OK;
#endif

    switch (request->which_call) {
        case (RPC_gpio_config_tag):

#ifdef ESP32
            if (!digitalPinIsValid(request->call.gpio_config.pin)) {
                break;
            }

            if (check_if_pin_is_ledc_channel(request->call.gpio_config.pin)) {
                if (!stop_ledc_channel(request->call.gpio_config.pin)) {
                    break;
                }
            }
#endif

            switch (request->call.gpio_config.mode) {
                case (PIN_MODE_PM_OUTPUT):
                    pinMode(request->call.gpio_config.pin, OUTPUT);
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    break;
                case (PIN_MODE_PM_INPUT_PULLDOWN):
                    pinMode(request->call.gpio_config.pin, INPUT_PULLDOWN);
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    break;
                case (PIN_MODE_PM_INPUT_PULLUP):
                    pinMode(request->call.gpio_config.pin, INPUT_PULLUP);
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    break;
            }

            break;

        case (RPC_gpio_write_tag):

            switch (request->call.gpio_write.value) {
                case (PIN_VALUE_PV_HIGH):
                    digitalWrite(request->call.gpio_write.pin, HIGH);
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    break;
                case (PIN_VALUE_PV_LOW):
                    digitalWrite(request->call.gpio_write.pin, LOW);
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    break;
            }

            break;

        case (RPC_gpio_read_tag):

            switch (digitalRead(request->call.gpio_read.pin)) {
                case (HIGH):
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    m->msg.result.has_pin_value = true;
                    m->msg.result.pin_value = PIN_VALUE_PV_HIGH;
                    break;
                case (LOW):
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    m->msg.result.has_pin_value = true;
                    m->msg.result.pin_value = PIN_VALUE_PV_LOW;
                    break;
            }
            break;

        case (RPC_gpio_monitor_tag):

            if (request->call.gpio_monitor.debounce_ms < 0xFFFF) {
                if (this->watch_pin(request->call.gpio_monitor.pin, request->call.gpio_monitor.debounce_ms)) {
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                }
            }
            break;

#ifdef ESP32
        // ESP32 PWM support via "LEDC"

        case (RPC_pwm_config_tag):

            if (setup_ledc_channel(request->call.pwm_config.pin)) {
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            }

            break;

        case (RPC_pwm_duty_tag):

            if(set_ledc_duty(request->call.pwm_duty.pin, request->call.pwm_duty.duty)) {
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            }
            break;

        case (RPC_pwm_stop_tag):

            if (stop_ledc_channel(request->call.pwm_fade.pin)){
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            }

            break;
        case (RPC_pwm_fade_tag):

            if (set_ledc_fade(request->call.pwm_fade.pin, request->call.pwm_fade.duty, request->call.pwm_fade.fade_ms)) {
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            }

            break;
#endif

        case (RPC_ping_tag):
            m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            break;

        case (RPC_i2c_config_tag):

#ifdef ESP32
            if (request->call.i2c_config.has_pin_scl && request->call.i2c_config.has_pin_sda) {
                if (i2c_setup(request->call.i2c_config.pin_sda, request->call.i2c_config.pin_scl)) {
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                }
            }
#else
            if (i2c_setup()) {
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                }
#endif
            break;

        case (RPC_i2c_write_tag):

            if (i2c_write(request->call.i2c_write.device, request->call.i2c_write.data.bytes, request->call.i2c_write.data.size)){
                m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
            }
            break;

        case (RPC_i2c_read_tag):
            {
                uint8_t i2c_buf[32];

                uint8_t i2c_bytes_read = i2c_read(request->call.i2c_read.device, request->call.i2c_read.address, request->call.i2c_read.len, i2c_buf);

                if (i2c_bytes_read == request->call.i2c_read.len) {
                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                    m->which_data = FROM_MICRO_raw_tag;
                    memcpy(&m->data.raw.bytes, i2c_buf, i2c_bytes_read);
                    m->data.raw.size = i2c_bytes_read;
                }
            }
            break;


#ifdef ESP32
        case (RPC_ota_update_tag):
        {
            decomp_inbuf_len = request->call.ota_update.data.size;
            decomp_outbuf_len = DECOMP_SIZE;
            if (decomp_outbuf != NULL) {
                memset((void*)decomp_outbuf, 0x00, DECOMP_SIZE);
            }

            if (update_in_progress) {

                if (update_chunk == request->call.ota_update.chunk) {

                    //Another chunk

                    if (r8_inflate(
                            (unsigned char*)decomp_outbuf,
                            &decomp_outbuf_len,
                            request->call.ota_update.data.bytes,
                            &decomp_inbuf_len, true)) {

                        if ((_ret = esp_ota_write(update_handle, (const void *) decomp_outbuf, decomp_outbuf_len)) == ESP_OK) {
                            m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                            _crc32 = crc32_le(0xffffffff, (const unsigned char*)decomp_outbuf, decomp_outbuf_len);

                            m->which_data = FROM_MICRO_raw_tag;
                            memcpy(&m->data.raw.bytes, &_crc32, sizeof(_crc32));
                            m->data.raw.size = sizeof(_crc32);

                            update_chunk += 1;
                        }
                    }

                } else if (request->call.ota_update.chunk == 0) {

                    //Finish update


                    if (r8_inflate(
                            (unsigned char*)decomp_outbuf,
                            &decomp_outbuf_len,
                            request->call.ota_update.data.bytes,
                            &decomp_inbuf_len, false)) {

                        if ((_ret = esp_ota_write(update_handle, (const void *) decomp_outbuf, decomp_outbuf_len)) == ESP_OK) {

                            m->which_data = FROM_MICRO_raw_tag;
                            _crc32 = crc32_le(0xffffffff, (const unsigned char*)decomp_outbuf, decomp_outbuf_len);
                            memcpy(&m->data.raw.bytes, &_crc32, sizeof(_crc32));
                            m->data.raw.size = sizeof(_crc32);

                            if ((_ret = esp_ota_end(update_handle)) == ESP_OK) {
                                if ((_ret = esp_ota_set_boot_partition(update_partition)) == ESP_OK) {
                                    m->msg.result.result = RESULT_TYPE_RT_SUCCESS;
                                    update_in_progress = false;
                                }
                            }
                        }
                    }
                }
                break;

            } else {

                //start an ota update

                if (!r8_inflate_init()){
                    break;
                }

                decomp_outbuf = (uint8_t*)malloc(DECOMP_SIZE);
                if (decomp_outbuf == NULL) {
                    break;
                }

                update_partition = esp_ota_get_next_update_partition(NULL);

                if (update_partition == NULL) {
                    free(decomp_outbuf);
                    break;
                }

                if (request->call.ota_update.chunk == 0 &&
                        (_ret = esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &update_handle)) == ESP_OK) {


                    if (r8_inflate(
                            decomp_outbuf,
                            &decomp_outbuf_len,
                            request->call.ota_update.data.bytes,
                            &decomp_inbuf_len, true)) {

                        if ((_ret = esp_ota_write(update_handle, (const void *) decomp_outbuf, decomp_outbuf_len)) == ESP_OK) {

                            m->msg.result.result = RESULT_TYPE_RT_SUCCESS;

                            m->which_data = FROM_MICRO_raw_tag;
                            _crc32 = crc32_le(0xffffffff, (const unsigned char*)decomp_outbuf, decomp_outbuf_len);
                            memcpy(&m->data.raw.bytes, &_crc32, sizeof(_crc32));
                            m->data.raw.size = sizeof(_crc32);

                            update_chunk = 1;
                            update_in_progress = true;
                        }
                    }
                }
            }
        }
        break;

        case (RPC_reboot_tag): {
            esp_restart();
        }
        break;
#endif

        default:
            m->msg.result.result = RESULT_TYPE_RT_UNKNOWN;
            break;
    }

#ifdef ESP32

    if (_ret != ESP_OK) {
            m->which_data = FROM_MICRO_raw_tag;
            strcpy((char*)m->data.raw.bytes, esp_err_to_name(_ret));
            m->data.raw.size = strlen(esp_err_to_name(_ret));
    }

#endif

}



