# The MIT License (MIT)

# Copyright (c) 2013-2022 Damien P. George

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
The original software is extensively modified by bachipeachy@gmail.com.
The code is organized to follow the protocol as explained in the document
http://www.dejazzer.com/ee379/lecture_notes/lec12_sd_card.pdf
as a learning excercise.
"""

import time

from machine import SoftSPI, Pin
from micropython import const

_R1_IDLE_STATE = const(1 << 0)
_R1_ILLEGAL_COMMAND = const(1 << 2)
_CMD_TIMEOUT = const(1000)
_TOKEN_DATA = const(0xFE)
_TOKEN_CMD25 = const(0xFC)
_TOKEN_STOP_TRAN = const(0xFD)


class SDCard:

    def __init__(self, spi=SoftSPI(sck=Pin(18), mosi=Pin(23), miso=Pin(38)), cs=Pin(4), debug=False):
        """
        get ready to read/write, the default Pins are set up for M5Stack Core2 hardware
        """
        self.spi = spi
        self.cs = cs
        self.cs.init(self.cs.OUT, value=0)
        self.debug = debug
        if self.debug:
            print("{}{} {}, cs={} state={}".format(SDCard, SDCard.__init__, self.spi, self.cs, self.cs.value()))
        self.sectors = None
        self.cdv = None
        self.init_card()

    def init_card(self):
        """
        initialize card and get Card Specific Date (CSD)
        """
        print("* starting card initializing ..")
        self.clock_card()
        self.go_idle()
        self.get_intf_cond()
        self.sectors = self.get_card_data()
        self.set_blksz()
        print("* card initializing complete ..")

    def clock_card(self):
        """
        clock card at slower baudrate with cs pin high for at least 100 cycles
        """
        self.set_baudrate(100000)
        self.cs(1)
        [self.spi.write(b"\xff") for _ in range(16)]
        if self.debug:
            print("{} for 16x8 bits at baudrate of 100,000".format(SDCard.clock_card))

    def go_idle(self):
        """
        cmd0 enter idle state -- make 5 attempts
        """
        for i in range(5):
            self.send_cmd(cmd=0, arg=0, crc=0x95)
            if self.debug:
                print("{} attempt {} of 5 attempts".format(SDCard.go_idle, i + 1))
            res = self.get_response()
            if res == _R1_IDLE_STATE:
                if self.debug:
                    print("{} SDCard in IDLE_STATE ".format(SDCard.go_idle))
                break
        else:
            raise OSError("no SD card")

    def get_intf_cond(self):
        """
        cmd8 check card version and its interface condition
        """
        if self.debug:
            print("{} sending cmd8".format(SDCard.get_intf_cond))
        self.send_cmd(cmd=8, arg=0x01AA, crc=0x87)
        res = self.get_response(byte_ct=4)
        if res == _R1_IDLE_STATE:
            self.card_v2()
        elif res == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            self.card_v1()
        else:
            raise OSError("couldn't determine SD card version")

    def get_card_data(self):
        """
        cmd9 read CSD register - number of sectors is of interest
        response R2 (R1 byte + 16-byte block read)
        """
        if self.debug:
            print("{} sending cmd9".format(SDCard.get_card_data))
        self.send_cmd(9, 0, 0)
        res = self.get_response(byte_ct=0, rel_card=False)
        if res != 0:
            raise OSError("no response from SDCard -- check if MCU power is on")

        csd = bytearray(16)
        self.read(csd)

        if csd[0] & 0xC0 == 0x40:  # CSD version 2.0
            sectors = ((csd[8] << 8 | csd[9]) + 1) * 1024
        elif csd[0] & 0xC0 == 0x00:  # CSD version 1.0 (old, <=2GB)
            c_size = csd[6] & 0b11 | csd[7] << 2 | (csd[8] & 0b11000000) << 4
            c_size_mult = ((csd[9] & 0b11) << 1) | csd[10] >> 7
            sectors = (c_size + 1) * (2 ** (c_size_mult + 2))
        else:
            raise OSError("SDCard CSD format not supported")
        if self.debug:
            print("{} sectors={}".format(SDCard.get_card_data, sectors))

        return sectors

    def set_blksz(self):
        """
        cmd16 set block length to 512 bytes
        """
        self.send_cmd(16, 512, 0)
        res = self.get_response()
        if self.debug:
            print("{} got cmd16 response = {}, blksz=512".format(SDCard.set_blksz, res))
        if res != 0:
            raise OSError("can't set 512 block size")
        self.set_baudrate(500000)

    def set_baudrate(self, baudrate):
        """
        slowdown baudrate to 100-400khz range during initialization and speedup at the end
        """
        self.spi.init(baudrate)
        if self.debug:
            print("{} {}".format(SDCard.set_baudrate, self.spi))

    def readblocks(self, block_num, buf):
        """
        cmd17 read one block
        cmd18 read multiple blocks
        cmd12 stop to read data
        """
        self.spi.write(b'\xff')  # PGH
        nblocks = len(buf) // 512
        assert nblocks and not len(buf) % 512, "Buffer length is invalid"

        if nblocks == 1:
            if self.debug:
                print("{} reading one block cmd17".format(SDCard.readblocks))
            self.send_cmd(17, block_num * self.cdv, 0)
            res = self.get_response(rel_card=False)
            if res != 0:
                # release the card
                self.cs(1)
                raise OSError(5)  # EIO
            # receive the data and release card
            self.read(buf)
        else:
            if self.debug:
                print("{} reading multiple blocks cmd18".format(SDCard.readblocks))
            self.send_cmd(18, block_num * self.cdv, 0)
            res = self.get_response(rel_card=False)
            if res != 0:
                # release the card
                self.cs(1)
                raise OSError(5)  # EIO
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                # receive the data and release card
                self.read(mv[offset: offset + 512])
                offset += 512
                nblocks -= 1
            if self.debug:
                print("{} stop reading data cmd12".format(SDCard.readblocks))
            self.send_cmd(12, 0, 0xFF)
            res = self.get_response(skip1=True)
            if res:
                raise OSError(5)  # EIO

    def writeblocks(self, block_num, buf):
        """
        cmd 24, cmd25 write SDCard blocks specified
        """
        # clock card at least 100 cycles with cs high
        self.spi.write(b'\xff')  # PGH
        nblocks, err = divmod(len(buf), 512)
        assert nblocks and not err, "Buffer length is invalid"
        if nblocks == 1:
            # CMD24: set write address for single block
            self.send_cmd(24, block_num * self.cdv, 0)
            res = self.get_response(rel_card=False)
            if self.debug:
                print("{} got cmd24 response = {}".format(SDCard.writeblocks, res))
            if res != 0:
                raise OSError(5)  # EIO
            # send the data
            self.write(_TOKEN_DATA, buf)
        else:
            # CMD25: set write address for first block
            self.send_cmd(25, block_num * self.cdv, 0)
            res = self.get_response(rel_card=False)
            if self.debug:
                print("{} got cmd25 response = {}".format(SDCard.writeblocks, res))
            if res != 0:
                raise OSError(5)  # EIO
            # send the data
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                self.write(_TOKEN_CMD25, mv[offset: offset + 512])
                offset += 512
                nblocks -= 1
            self.write_token(_TOKEN_STOP_TRAN)

    def send_cmd(self, cmd, arg, crc):
        """
        write cmd after setting cs pin low
        """
        self.cs(0)
        buf = bytearray(6)
        buf[0] = 0x40 | cmd
        buf[1] = arg >> 24
        buf[2] = arg >> 16
        buf[3] = arg >> 8
        buf[4] = arg
        buf[5] = crc
        self.spi.write(buf)
        return buf

    def get_response(self, byte_ct=0, rel_card=True, skip1=False):
        """
        readinto tokenbuf, get response immediately after send_cmd while writing 0xFF
        """
        tokenbuf = bytearray(1)
        if skip1:
            self.spi.readinto(tokenbuf, 0xFF)
        # wait for the response (response[7] == 0)
        for i in range(_CMD_TIMEOUT):
            self.spi.readinto(tokenbuf, 0xFF)
            res = tokenbuf[0]
            if not (res & 0x80):
                # this could be a big-endian integer that we are getting here
                if self.debug:
                    if byte_ct > 0:
                        print("{} spi.write {} times".format(SDCard.get_response, byte_ct))

                for j in range(byte_ct):
                    self.spi.write(b"\xff")

                if rel_card:
                    self.cs(1)
                    self.spi.write(b"\xff")
                    if self.debug:
                        print("{} release the card after each CMD".format(SDCard.get_response))

                return res
        # timeout
        self.cs(1)
        self.spi.write(b"\xff")
        return -1

    def card_v1(self):
        """
        cmd55 leading command of App. ACMD<n> CMD
        acmd41 sends host capacity support info
        v1 microSDCard introduced circa 2003 with max capacity 128MB not supported
        """
        if self.debug:
            print("{} sending cmd55 & acmd41 with {} millisec response timeout".format(SDCard.card_v1, _CMD_TIMEOUT))

        for i in range(_CMD_TIMEOUT):
            _ = self.send_cmd(55, 0, 0)
            _ = self.send_cmd(41, 0x40000000, 0)
            res = self.get_response(byte_ct=4)

            if res == 0:
                self.cdv = 512
                print("* found and initialized v1 card")
                return

        raise OSError("timeout waiting for v1 card")

    def card_v2(self):
        """
        cmd58 read OCR Operation Condition Register
        cmd55 leading command of App. ACMD<n> CMD
        acmd41 sends host capacity support info
        only supporting v2 microSDCard which was introduced circa 2006 with 64MB - 16GB
        """
        if self.debug:
            print("{} sending cmd58, cmd55, acmd41 with {} millisec response timeout".format(SDCard.card_v2,
                                                                                             _CMD_TIMEOUT))
        for i in range(_CMD_TIMEOUT):
            time.sleep_ms(50)
            self.send_cmd(58, 0, 0)
            _ = self.get_response(byte_ct=4)

            self.send_cmd(55, 0, 0)
            _ = self.get_response()

            self.send_cmd(41, 0x40000000, 0)
            res = self.get_response()

            if res == 0:
                self.send_cmd(58, 0, 0)
                _ = self.get_response(byte_ct=4)
                self.cdv = 1
                print("* found and initialized v2 card")
                return

        raise OSError("timeout waiting for v2 card")

    def read(self, buf):
        """
        readinto tokenbuf byte at a time not exceeding max blocksize 512 bytes
        """
        dummybuf = bytearray(512)
        tokenbuf = bytearray(1)
        for i in range(512):
            dummybuf[i] = 0xFF
        dummybuf_memoryview = memoryview(dummybuf)

        self.cs(0)
        # read until start byte (0xff)
        for i in range(_CMD_TIMEOUT):
            self.spi.readinto(tokenbuf, 0xFF)
            if tokenbuf[0] == _TOKEN_DATA:
                break
        else:
            if self.debug:
                print("tokenbuf[0]:{} should be equal to _TOKEN_DATA: {}".format(tokenbuf[0], _TOKEN_DATA))
            self.cs(1)
            raise OSError("timeout waiting for response - check power to MCU")

        # read data
        mv = dummybuf_memoryview
        if len(buf) != len(mv):
            mv = mv[: len(buf)]
        self.spi.write_readinto(mv, buf)

        # read checksum
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        self.cs(1)
        self.spi.write(b"\xff")

    def write_token(self, token):
        """
        write token
        """
        self.cs(0)
        self.spi.read(1, token)
        self.spi.write(b"\xff")
        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0x00:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def write(self, token, buf):
        """
        write buffer
        """
        self.cs(0)
        # send: start of block, data, checksum
        self.spi.read(1, token)
        self.spi.write(buf)
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        # check the response
        if (self.spi.read(1, 0xFF)[0] & 0x1F) != 0x05:
            self.cs(1)
            self.spi.write(b"\xff")
            return

        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def ioctl(self, op, org=None):
        """
        SDCard control commands -- only 0p 4 and op 5 supported
        """
        if op == 4:
            return self.sectors
        else:
            if self.debug:
                print("{} op code {} not implemented".format(SDCard.ioctl, op))
            return None
