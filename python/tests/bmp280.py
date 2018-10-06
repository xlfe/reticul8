# Example to read a BMP280 I2C module


import asyncio
import logging
from reticul8.arduino import *

BMP280_REGISTER_CHIPID      = 0xD0
BMP280_REGISTER_VERSION     = 0xD1
BMP280_REGISTER_SOFTRESET   = 0xE0

BMP280_REGISTER_CALIB       = 0x88
BMP280_REGISTER_SENSORS     = 0xF7

BMP280_ADDR                 = 0x76
BMP280_REG_CTRL_MEAS        = 0xF4
BMP280_REG_CONFIG           = 0xF5

#
# BMP280 Config options
#
#
# OSRS_P = 1 # 16 Bit ultra low power
# OSRS_P = 2 # 17 Bit low power
# OSRS_P = 3 # 18 Bit standard resolution
# OSRS_P = 4 # 19 Bit high resolution
OSRS_P = 5 # 20 Bit ultra high resolution

# OSRS_T = 0 # skipped
# OSRS_T = 1 # 16 Bit
# OSRS_T = 2 # 17 Bit
# OSRS_T = 3 # 18 Bit
# OSRS_T = 4 # 19 Bit
OSRS_T = 5 # 20 Bit
#
# FILTER = 0
# FILTER = 1
# FILTER = 2
# FILTER = 3
# FILTER = 4
# FILTER = 5
# FILTER = 6
FILTER = 7
#
# standby settings (not used in forced mode)
# T_SB = 0 # 000 0,5ms
# T_SB = 1 # 001 62.5 ms
# T_SB = 2 # 010 125 ms
# T_SB = 3 # 011 250ms
# T_SB = 4 # 100 500ms
# T_SB = 5 # 101 1000ms
# T_SB = 6 # 110 2000ms
T_SB = 7 # 111 4000ms
#
# power mode
# POWER_MODE=0 # sleep mode
POWER_MODE=1 # forced mode
# POWER_MODE=2 # forced mode
# POWER_MODE=3 # normal mode
#

CONFIG  = ((T_SB <<5) + (FILTER <<2)) & 0xFF
CTRL_MEAS = ((OSRS_T <<5) + (OSRS_P <<2) + POWER_MODE) & 0xFF


def readU16LE(data, offset):
    return ((data[offset+1] << 8) | data[offset]) & 0xFFFF

def readS16LE(data, offset):
    result = readU16LE(data, offset)
    if result > 32767:
        result -= 65536
    return result

class BMP280(object):

    def __init__(self, node, sda, scl):
        self.node=node
        self.setup = False
        self.sda =sda
        self.scl =scl

    async def _setup(self):

        with self.node:
            assert await i2c_config(self.sda, self.scl)

            #soft reset
            assert await i2c_write(BMP280_ADDR, bytes([BMP280_REGISTER_SOFTRESET, 0xB6]))

            await asyncio.sleep(0.1)

            #config sensor
            assert await i2c_write(BMP280_ADDR, bytes([BMP280_REG_CONFIG, CONFIG]))

            #read 24 bytes of calibration data
            calibration = await i2c_read(BMP280_ADDR, BMP280_REGISTER_CALIB, 24)

            self.cal_REGISTER_DIG_T1 = readU16LE(calibration, 0)
            self.cal_REGISTER_DIG_T2 = readS16LE(calibration, 2)
            self.cal_REGISTER_DIG_T3 = readS16LE(calibration, 4)
            self.cal_REGISTER_DIG_P1 = readU16LE(calibration, 6)
            self.cal_REGISTER_DIG_P2 = readS16LE(calibration, 8)
            self.cal_REGISTER_DIG_P3 = readS16LE(calibration, 10)
            self.cal_REGISTER_DIG_P4 = readS16LE(calibration, 12)
            self.cal_REGISTER_DIG_P5 = readS16LE(calibration, 14)
            self.cal_REGISTER_DIG_P6 = readS16LE(calibration, 16)
            self.cal_REGISTER_DIG_P7 = readS16LE(calibration, 18)
            self.cal_REGISTER_DIG_P8 = readS16LE(calibration, 20)
            self.cal_REGISTER_DIG_P9 = readS16LE(calibration, 22)

        self.setup = True

    async def read_sensor(self):

        with self.node:
            #Force measurement
            assert await i2c_write(BMP280_ADDR, bytes([BMP280_REG_CTRL_MEAS, CTRL_MEAS]))

            #Wait for measurement
            await asyncio.sleep(0.1)

            #read temp and pressure
            reading = await i2c_read(BMP280_ADDR, BMP280_REGISTER_SENSORS, 6)

        self.adc_P = ((reading[0] << 8 | reading[1]) << 8 | reading[2]) >> 4
        self.adc_T = ((reading[3] << 8 | reading[4]) << 8 | reading[5]) >> 4

    def _temp(self):
        """temperature in degrees celsius"""

        TMP_PART1 = (((self.adc_T >> 3) - (self.cal_REGISTER_DIG_T1 << 1)) * self.cal_REGISTER_DIG_T2) >> 11
        TMP_PART2 = (((((self.adc_T >> 4) - (self.cal_REGISTER_DIG_T1)) * (
                    (self.adc_T >> 4) - (self.cal_REGISTER_DIG_T1))) >> 12) * (self.cal_REGISTER_DIG_T3)) >> 14
        TMP_FINE = TMP_PART1 + TMP_PART2
        self._tfine = TMP_FINE
        temp = ((TMP_FINE * 5 + 128) >> 8) / 100.0
        return temp

    def _pressure(self):
        """pressure in pascals"""

        var1 = self._tfine - 128000
        var2 = var1 * var1 * self.cal_REGISTER_DIG_P6
        var2 = var2 + ((var1 * self.cal_REGISTER_DIG_P5) << 17)
        var2 = var2 + ((self.cal_REGISTER_DIG_P4) << 35)
        var1 = ((var1 * var1 * self.cal_REGISTER_DIG_P3) >> 8) + ((var1 * self.cal_REGISTER_DIG_P2) << 12)
        var1 = ((((1) << 47) + var1)) * (self.cal_REGISTER_DIG_P1) >> 33

        if var1 == 0:
            return 0

        p = 1048576 - self.adc_P
        p = int((((p << 31) - var2) * 3125) / var1)
        var1 = ((self.cal_REGISTER_DIG_P9) * (p >> 13) * (p >> 13)) >> 25
        var2 = ((self.cal_REGISTER_DIG_P8) * p) >> 19

        p = ((p + var1 + var2) >> 8) + ((self.cal_REGISTER_DIG_P7) << 4)
        return p / 256.0

    @property
    async def temp_and_pressure(self):

        if not self.setup:
            await self._setup()

        await self.read_sensor()

        return self._temp(), self._pressure()

