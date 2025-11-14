# MFRC522 driver for CircuitPython (RP2040)
# Supports NTAG21x + Mifare Classic
# SPI locking fixed for CircuitPython busio.SPI

import time
import digitalio

class MFRC522:
    DEBUG = True

    OK = 0
    NOTAGERR = 1
    ERR = 2

    REQIDL = 0x26
    REQALL = 0x52

    ANTENNA_GAIN_48DB = 0x07

    def __init__(self, spi, cs, rst):
        self.spi = spi
        self.cs = cs
        self.cs.direction = digitalio.Direction.OUTPUT
        self.cs.value = True

        self.rst = rst
        self.rst.direction = digitalio.Direction.OUTPUT

        # Take SPI lock once for whole lifetime:
        while not self.spi.try_lock():
            pass

        # Configure SPI (RC522 works well at 1 MHz, Mode=0)
        self.spi.configure(baudrate=1000000, phase=0, polarity=0)

        self.rst.value = False
        time.sleep(0.05)
        self.rst.value = True
        time.sleep(0.05)

        if self.DEBUG:
            print("MFRC522: Reset complete")

        self._init()

    # SPI helpers
    def _spi_write(self, reg, val):
        address = (reg << 1) & 0x7E
        self.cs.value = False
        self.spi.write(bytes([address, val]))
        self.cs.value = True

    def _spi_read(self, reg):
        address = ((reg << 1) & 0x7E) | 0x80
        self.cs.value = False
        outbuf = bytearray(1)
        self.spi.write(bytes([address]))
        self.spi.readinto(outbuf)
        self.cs.value = True
        return outbuf[0]

    def _set_bitmask(self, reg, mask):
        self._spi_write(reg, self._spi_read(reg) | mask)

    def _clear_bitmask(self, reg, mask):
        self._spi_write(reg, self._spi_read(reg) & (~mask))

    def _init(self):
        self._spi_write(0x01, 0x0F)
        time.sleep(0.1)

        self._spi_write(0x2A, 0x8D)
        self._spi_write(0x2B, 0x3E)
        self._spi_write(0x2D, 30)
        self._spi_write(0x2C, 0)
        self._spi_write(0x15, 0x40)

        # 48 dB gain
        self._spi_write(0x26, self.ANTENNA_GAIN_48DB << 4)

        if self.DEBUG:
            gain = self._spi_read(0x26)
            print("MFRC522: Antenna gain set:", hex(gain))

        self.antenna_on()
        if self.DEBUG:
            print("MFRC522: Antenna enabled | TxControlReg =", hex(self._spi_read(0x14)))

    def antenna_on(self):
        if ~(self._spi_read(0x14) & 0x03):
            self._set_bitmask(0x14, 0x03)

    def _to_card(self, cmd, send):
        recv = []
        bits = 0

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30
        else:
            irq_en = 0x00
            wait_irq = 0x00

        self._spi_write(0x02, irq_en | 0x80)
        self._clear_bitmask(0x04, 0x80)
        self._set_bitmask(0x0A, 0x80)
        self._spi_write(0x01, 0x00)

        for c in send:
            self._spi_write(0x09, c)

        self._spi_write(0x01, cmd)

        if cmd == 0x0C:
            self._set_bitmask(0x0D, 0x80)

        i = 2000
        while True:
            n = self._spi_read(0x04)
            if n & wait_irq:
                break
            if n & 1:
                break
            i -= 1
            if i == 0:
                return (self.ERR, None, 0)

        self._clear_bitmask(0x0D, 0x80)

        if self._spi_read(0x06) & 0x1B:
            return (self.ERR, None, 0)

        if n & irq_en & 0x01:
            return (self.NOTAGERR, None, 0)

        if cmd == 0x0C:
            length = self._spi_read(0x0A)
            last_bits = self._spi_read(0x0C) & 0x07
            if last_bits != 0:
                bits = (length - 1) * 8 + last_bits
            else:
                bits = length * 8

            for _ in range(length):
                recv.append(self._spi_read(0x09))

        return (self.OK, recv, bits)

    def request(self, mode):
        self._spi_write(0x0D, 0x07)
        (stat, back, bits) = self._to_card(0x0C, [mode])
        if self.DEBUG:
            # print("REQ: stat=", stat, ", bits=", bits)
            pass
        if stat != self.OK or bits not in (16, 0x10, 0x18):
            return (self.ERR, None)
        return (self.OK, bits)

    def anticoll(self):
        (stat, back, bits) = self._to_card(0x0C, [0x93, 0x20])
        if self.DEBUG:
            print("ANTICOLL:", stat, back)
        if stat != self.OK:
            return (self.ERR, None)
        return (self.OK, back)

    def read_uid(self):
        (stat, _) = self.request(self.REQIDL)
        if stat != self.OK:
            return None

        (stat, uid) = self.anticoll()
        if stat != self.OK:
            return None

        return uid
