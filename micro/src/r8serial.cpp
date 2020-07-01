#include <Arduino.h>
#include "r8serial.h"
#include "utils/crc/PJON_CRC32.h"




R8Serial::R8Serial() {
    this->clear_packet();
    Serial.begin(R8_SERIAL_BAUD);
    while (!Serial) {
        ; // wait for serial port to connect. Needed for native USB port only
    }
}


bool R8Serial::packet_waiting() {

    while (!_packet_waiting_recv && Serial.available()) {

        int byte = Serial.read();
        if (byte < 0) {
            continue;
        }

        if (_recv_len >= R8_SERIAL_BUF_SZ) {
            clear_packet();
            return false;
        }

        if (_packet_in_progress) {

            if (_esc) {
                _buf[_recv_len++] = (uint8_t) (byte ^ R8_SERIAL_ESC);
                _esc = false;
            } else if (byte == R8_SERIAL_ESC) {
                _esc = true;
            } else if (byte == R8_SERIAL_END) {

                if (check_packet()) {
                    _packet_waiting_recv = true;
                } else {
                    clear_packet();
                }
                _packet_in_progress = false;
            } else {
                _buf[_recv_len++] = (uint8_t) byte;
            }
        } else {

            if (byte == R8_SERIAL_START) {
                clear_packet();
                _packet_in_progress = true;
            }

        }
    }

    return _packet_waiting_recv;

}

bool R8Serial::check_packet() {
    // byte 0 - destination ID
    // byte 1 - source ID
    // byte 2 - packet data size <= R8_SERIAL_MAX_PACKET
    // byte 3... packet
    // byte n-3, n-2, n-1, n crc32

    if (_buf[2] != (_recv_len - R8_SERIAL_OVERHEAD)) {
        ESP_LOGE("R8Serial", "Len Failed %d != %d",_buf[2], (_recv_len - R8_SERIAL_OVERHEAD));
        return false;
    }

    if (!PJON_crc32::compare(
            PJON_crc32::compute(_buf, _buf[2] + 3),
            _buf + 3 + (uint8_t)_buf[2]
    )) {
        ESP_LOGE("R8Serial", "CRC Failed");
        return false;
    }

    return true;
}

uint8_t R8Serial::get_dest() {
    if (!this->_packet_waiting_recv){
        return 0;
    }

    return this->_buf[0];
}

uint8_t R8Serial::get_source() {
    if (!this->_packet_waiting_recv){
        return 0;
    }

    return this->_buf[1];
}
uint8_t R8Serial::get_len() {
    if (!this->_packet_waiting_recv){
        return 0;
    }

    return this->_buf[2];
}

uint8_t * R8Serial::get_packet() {
    return this->_buf + 3;
}

void R8Serial::clear_packet() {
    memset(_buf, 0, sizeof(_buf));
    _recv_len = 0;
    _packet_waiting_recv = false;
    _packet_in_progress = false;
    _esc = false;
}

void R8Serial::send(uint8_t dest, uint8_t source, uint8_t *pkt, uint16_t len) {

    uint16_t _ptr = 0;
    uint8_t _buf[R8_SERIAL_BUF_SZ];

    if (len > R8_SERIAL_MAX_PACKET || len > 255) {
        return;
    }

    _buf[_ptr++] = dest;
    _buf[_ptr++] = source;
    _buf[_ptr++] = len;

    for (uint16_t i=0;i<len; i++) {
        _buf[_ptr++] = pkt[i];
    }

    //compute CRC on the three header bytes _and_ the packet
    uint32_t computed = PJON_crc32::compute(_buf, _ptr);
    for(uint8_t i = 4; i > 0; i--) {
        _buf[_ptr++] = (uint8_t)(computed >> (8 * (i - 1)));
    }

    Serial.write(R8_SERIAL_START);
    for (uint16_t i =0; i<_ptr; i++) {
        if (_buf[i] == R8_SERIAL_START || _buf[i] == R8_SERIAL_ESC || _buf[i] == R8_SERIAL_END) {
            Serial.write(R8_SERIAL_ESC);
            Serial.write(_buf[i] ^ R8_SERIAL_ESC);
        } else {
            Serial.write(_buf[i]);
        }
    }
    Serial.write(R8_SERIAL_END);
    Serial.flush();
}
