"""
MFRC522 Python Library for Raspberry Pi Pico / CircuitPython
"""

import time
from digitalio import Direction

class MFRC522:

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61

    def __init__(self, spi, cs, rst):
        self.spi = spi
        self.cs = cs
        self.rst = rst

        self.cs.direction = Direction.OUTPUT
        self.cs.value = True

        self.rst.direction = Direction.OUTPUT

        self.rst.value = False
        time.sleep(0.05)
        self.rst.value = True
        time.sleep(0.05)

        # Init
        self._init()

    def _spi_write(self, reg, val):
        self.cs.value = False
        self.spi.write(bytes([(reg << 1) & 0x7E, val]))
        self.cs.value = True

    def _spi_read(self, reg):
        self.cs.value = False
        buf = bytearray(1)
        self.spi.write(bytes([((reg << 1) & 0x7E) | 0x80]))
        self.spi.readinto(buf)
        self.cs.value = True
        return buf[0]

    def _init(self):
        self.reset()
        self._spi_write(0x2A, 0x8D)
        self._spi_write(0x2B, 0x3E)
        self._spi_write(0x2D, 30)
        self._spi_write(0x2C, 0)
        self._spi_write(0x15, 0x40)
        self._spi_write(0x11, 0x3D)

        self.antenna_on()

    def reset(self):
        self._spi_write(0x01, 0x0F)

    def antenna_on(self):
        val = self._spi_read(0x14)
        if ~(val & 0x03):
            self._spi_write(0x14, val | 0x03)

    def _to_card(self, command, send):
        back_data = []
        back_len = 0
        status = self.ERR

        irq_en = 0x00
        wait_irq = 0x00

        if command == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif command == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self._spi_write(0x02, irq_en | 0x80)
        self._spi_write(0x04, 0x00)
        self._spi_write(0x0A, 0x80)

        # Write data
        for c in send:
            self._spi_write(0x09, c)

        self._spi_write(0x01, command)

        if command == 0x0C:
            self._spi_write(0x0D, 0x80)

        i = 2000
        while True:
            n = self._spi_read(0x04)
            i -= 1
            if not (i != 0 and not (n & 0x01) and not (n & wait_irq)):
                break

        if i != 0:
            if (self._spi_read(0x06) & 0x1B) == 0x00:
                status = self.OK

                if n & irq_en & 0x01:
                    status = self.NOTAGERR

                if command == 0x0C:
                    n = self._spi_read(0x0A)
                    last_bits = self._spi_read(0x0C) & 0x07
                    back_len = n * 8
                    if last_bits:
                        back_len = (n - 1) * 8 + last_bits

                    for _ in range(n):
                        back_data.append(self._spi_read(0x09))
        return status, back_data, back_len

    def request(self, mode):
        self._spi_write(0x0D, 0x07)
        stat, back, bits = self._to_card(0x0C, [mode])
        if stat != self.OK:
            return self.ERR, None
        return self.OK, bits

    def anticoll(self):
        ser_num = [0x93, 0x20]
        stat, back, bits = self._to_card(0x0C, ser_num)
        if stat != self.OK:
            return self.ERR, None
        return self.OK, back
