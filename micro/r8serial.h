
#pragma once
#include "Arduino.h"
#include <PJON.h>

#define R8_SERIAL_BAUD          115200
#define R8_SERIAL_MAX_PACKET    254
#define R8_SERIAL_OVERHEAD      1+2+4
#define R8_SERIAL_BUF_SZ        (R8_SERIAL_MAX_PACKET + R8_SERIAL_OVERHEAD)


#define R8_SERIAL_START        149
#define R8_SERIAL_END          234
#define R8_SERIAL_ESC          187



class R8Serial {

public:
    R8Serial();

    bool packet_waiting();
    uint8_t get_dest();
    uint8_t get_source();
    uint8_t get_len();
    uint8_t * get_packet();
    void clear_packet();

    void send(uint8_t dest, uint8_t source, uint8_t *buf, uint8_t len);

private:

    bool check_packet();
    uint8_t _buf[R8_SERIAL_BUF_SZ];
    uint16_t sb_ptr = 0;
    bool _esc = false;
    bool _packet_in_progress = false;
    bool _packet_waiting_recv = false;
    uint8_t _recv_len = 0;


};

