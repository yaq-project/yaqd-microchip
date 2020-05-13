#! /usr/bin/env python3


__all__ = ["MCP9600"]


import asyncio
import smbus  # type: ignore
from yaqd_core import Sensor


class MCP9600(Sensor):
    traits = ["uses-i2c", "uses-serial"]
    _kind = "MCP9600"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self.address = config["address"]
        self.bus = smbus.SMBus(1)
        # in the future, some of these settings could be exposed
        # for now, keeping this daemon minimal
        # ---Blaise 2019-10-20
        self.bus.write_byte_data(self.address, 0xC0, 0x00)  # WRITE command
        self.bus.write_byte_data(self.address, 0x05, 0x01)  # type K, filter n=1
        self.bus.write_byte_data(self.address, 0x06, 0x00)  # highest resolution
        self.channels = {"temperature": ("deg_C", ())}

    async def _measure(self):
        out = {}
        # for reasons I don't understand, sometimes this sensor returns bad data
        # this is always in the form of bytes 0000001 0000001
        # in this special case, I try again
        while True:
            # clear status register
            self.bus.write_byte_data(self.address, 0x04, 0x00)
            # wait until hot junction temperature has been updated
            while True:
                status = self.bus.read_i2c_block_data(self.address, 0x04, 1)[0]
                if status > 64:
                    break
                await asyncio.sleep(0)
            await asyncio.sleep(0.1)
            # read off hot junction temperature
            data = self.bus.read_i2c_block_data(self.address, 0x00, 2)
            if data[0] != data[1]:
                break
        temperature = ((data[0] & 0x7F) * 16) + (float(data[1]) / 16)
        if data[0] & 0x80:
            temperature = 1024 - temperature
        out["temperature"] = temperature
        return out
