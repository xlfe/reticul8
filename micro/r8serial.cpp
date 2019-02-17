#include "r8serial.h"




R8Serial::R8Serial() {
    Serial.begin(R8_SERIAL_BAUD);
    while (!Serial) {
        ; // wait for serial port to connect. Needed for native USB port only
    }
}


bool R8Serial::packet_waiting() {

    while (!this->_packet_waiting_recv && Serial.available()) {

        int byte = Serial.read();
        if (byte < 0) {
            continue;
        }

        if (this->_packet_in_progress) {

            if (this->_esc) {
                this->_buf[this->_recv_len++] = (uint8_t) byte ^ R8_SERIAL_ESC;
                this->_esc = false;
            } else if (byte == R8_SERIAL_ESC) {
                this->_esc = true;
            } else if (byte == R8_SERIAL_END) {

                if (this->check_packet()) {
                    this->_packet_waiting_recv = true;
                }
                this->_packet_in_progress = false;
            } else {
                this->_buf[this->_recv_len++] = (uint8_t) byte;
            }
        } else {

            if (byte == R8_SERIAL_START) {
                this->_packet_in_progress = true;
            }

        }
    }

    return this->_packet_waiting_recv;

}

bool R8Serial::check_packet() {
    // byte 0 - destination ID
    // byte 1 - source ID
    // byte 2 - packet data size <= R8_SERIAL_MAX_PACKET
    // byte 3... packet
    // byte n-3, n-2, n-1, n crc32

    if (this->_buf[2] != (this->_recv_len - R8_SERIAL_OVERHEAD)) {
        return false;
    }

    if (!PJON_crc32::compare(
            PJON_crc32::compute(this->_buf + 3, this->_buf[2]),
            this->_buf + 3 + ((uint8_t)this->_buf[2])
    )) {
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
    this->_recv_len = 0;
    memset(this->_buf, 0, sizeof(this->_buf));
    this->_packet_waiting_recv = false;
}

void R8Serial::send(uint8_t dest, uint8_t source, uint8_t *buf, uint8_t len) {

    uint16_t sb_ptr = 0;
    uint8_t _send_buf[2*R8_SERIAL_BUF_SZ];

    _send_buf[sb_ptr++] = R8_SERIAL_START;
    _send_buf[sb_ptr++] = dest;
    _send_buf[sb_ptr++] = source;
    _send_buf[sb_ptr++] = len;

    for (uint16_t i=0;i<len; i++) {
        if (buf[i] == R8_SERIAL_START || buf[i] == R8_SERIAL_END || buf[i] == R8_SERIAL_ESC) {
            _send_buf[sb_ptr++] = R8_SERIAL_ESC;
            _send_buf[sb_ptr++] = buf[i] ^ R8_SERIAL_ESC;
        } else {
            _send_buf[sb_ptr++] = buf[i];
        }
    }
    uint32_t computed = PJON_crc32::compute(_send_buf, sb_ptr);
    for(uint8_t i = 4; i > 0; i--) {
        _send_buf[sb_ptr++] = (uint8_t)(computed >> (8 * (i - 1)));
    }
    _send_buf[sb_ptr++] = R8_SERIAL_END;
    Serial.write(_send_buf, sb_ptr);
    Serial.flush();
}
