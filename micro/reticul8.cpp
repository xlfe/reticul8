#include "reticul8.h"

RETICUL8::RETICUL8(PJON <Any> *bus, uint8_t master_id) {
    this->bus = bus;
    this->master_id = master_id;

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        this->watched_pins[i].state = WATCH_NOT_IN_USE;
    }
}

void receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info) {
    ((RETICUL8*)packet_info.custom_pointer)->r8_receiver_function(payload, length, packet_info);
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
    bus->set_custom_pointer(this);
    bus->set_receiver(receiver_function);
    bus->set_error(error_handler);
    bus->set_crc_32(true);
    bus->begin();
//    bus->send_repeatedly(master_id, data, PJON_PACKET_MAX_LENGTH -10, 10000000);
}

void RETICUL8::loop() {
    bus->receive();
    bus->update();
    vTaskDelay(1);
}


void RETICUL8::check_for_events() {

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

bool RETICUL8::watch_pin(uint8_t pin) {

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].pin == pin) {
            //Already watching this pin...
            return true;
        }
    }

    for(uint16_t i = 0; i < RETICUL8_MAX_WATCHED_PINS; i++) {
        if (this->watched_pins[i].state == WATCH_NOT_IN_USE) {

            this->watched_pins[i].state = WATCH_IN_USE;

            return true;

        }
    }

    return false;

}


void RETICUL8::r8_receiver_function(uint8_t *payload, uint16_t length, const PJON_Packet_Info &packet_info) {

    RPC request = RPC_init_zero;
    bool status;
    pb_istream_t in_stream = pb_istream_from_buffer(payload, length);

    status = pb_decode(&in_stream, RPC_fields, &request);

    if (!status) {
        printf("Decoding failed: %s\n", PB_GET_ERROR(&in_stream));
        return;
    }

    uint8_t reply_buf[Call_Reply_size];
    Call_Reply reply = Call_Reply_init_zero;
    reply.msg_id = request.msg_id;
    reply.result = ResultType_RT_ERROR;

    switch (request.which_call) {
        case (RPC_gpio_config_tag):

            switch (request.call.gpio_config.mode) {
                case (PinMode_OUTPUT):
                    pinMode(request.call.gpio_config.pin, OUTPUT);
                    reply.result = ResultType_RT_SUCCESS;
                    break;
                case (PinMode_INPUT_PULLDOWN):
                    pinMode(request.call.gpio_config.pin, INPUT_PULLDOWN);
                    reply.result = ResultType_RT_SUCCESS;
                    break;
                case (PinMode_INPUT_PULLUP):
                    pinMode(request.call.gpio_config.pin, INPUT_PULLUP);
                    reply.result = ResultType_RT_SUCCESS;
                    break;
            }

            break;

        case (RPC_gpio_write_tag):

            switch (request.call.gpio_write.value) {
                case (PinValue_HIGH):
                    digitalWrite(request.call.gpio_write.pin, HIGH);
                    reply.result = ResultType_RT_SUCCESS;
                    break;
                case (PinValue_LOW):
                    digitalWrite(request.call.gpio_write.pin, LOW);
                    reply.result = ResultType_RT_SUCCESS;
                    break;
            }

            break;

        case (RPC_gpio_read_tag):

            switch (digitalRead(request.call.gpio_read.pin)) {
                case (HIGH):
                    reply.result = ResultType_RT_SUCCESS;
                    reply.value = ResultValue_PIN_HIGH;
                    break;
                case (LOW):
                    reply.result = ResultType_RT_SUCCESS;
                    reply.value = ResultValue_PIN_LOW;
                    break;
            }
            break;

        case (RPC_gpio_monitor_tag):
            break;

        case (RPC_pwm_config_tag):
            break;

        case (RPC_pwm_duty_tag):
            break;

        case (RPC_pwm_fade_tag):
            break;

        case (RPC_ping_tag):
            reply.result = ResultType_RT_SUCCESS;
            break;

        default:
            reply.result = ResultType_RT_UNKNOWN;
            break;
    }

    pb_ostream_t reply_stream = pb_ostream_from_buffer(reply_buf, sizeof(reply_buf));
    status = pb_encode(&reply_stream, Call_Reply_fields, &reply);

    if (!status) {
        printf("Encoding failed: %s\n", PB_GET_ERROR(&reply_stream));
    } else {
        this->bus->reply((char*)reply_buf, reply_stream.bytes_written);
    }

}



