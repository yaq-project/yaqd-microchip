#! /usr/bin/env python3


__all__ = ["MCP3428"]


import asyncio
import smbus  # type: ignore
from yaqd_core import Sensor


# least significant bit (V)
lsb = {12: 1e-3, 14: 2.5e-4, 16: 6.25e-5}


class MCP3428(Sensor):
    _kind = "MCP3428"
    traits = ["uses-i2c", "uses-serial"]

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self.address = config["address"]
        self.bus = smbus.SMBus(1)
        self.bus.write_byte_data(self.address, 0xC0, 0x00)
        self.channels = {
            "channel_0": ("V", ()),
            "channel_1": ("V", ()),
            "channel_2": ("V", ()),
            "channel_3": ("V", ()),
        }
        self._set_mode("one-shot")
        self._channel_register = 0
        # the following defaults will be overwritten
        self._gain = 1
        self._size = 12
        self._mode_register = 0
        self._size_register = 0
        self._gain_register = 0

    def get_state(self):
        state = super().get_state()
        state["gain"] = self._gain
        state["size"] = self._size
        return state

    def _load_state(self, state):
        self._set_gain(state.get("gain", 1))
        self._set_size(state.get("size", 12))

    async def _measure(self):
        out = {}
        for channel in range(4):
            self._set_channel(channel)
            self._write_configuration_register()
            await asyncio.sleep(0.1)
            # data arrives as (most significant byte, least significant byte)
            # MSB is sign
            data = self.bus.read_i2c_block_data(self.address, 0x00, 3)
            value = (data[0] << 8) | data[1]
            if value >= (1 << self._size):
                value = (1 << self._size) - value
            # the following is a hack, and should be corrected
            # value *= lsb[self._size]  # correct
            value -= 5813
            value *= 18 / 23577
            value += 4
            out[f"channel_{channel}"] = value
        return out

    def _set_channel(self, index):
        self._channel_register = int(index)

    def _set_gain(self, gain=1):
        self._gain = gain
        choices = [1, 2, 4, 8]
        self._gain_register = choices.index(gain)

    def _set_mode(self, mode="continous"):
        choices = ["one-shot", "continous"]
        self._mode_register = choices.index(mode)

    def _set_size(self, size=12):
        self._size = size
        choices = [12, 14, 16]
        self._size_register = choices.index(size)

    def _write_configuration_register(self, ready=True):
        out = 0
        if ready:
            out |= 1 << 7  # write ready bit
        out |= self._channel_register << 5
        out |= self._mode_register << 4
        out |= self._size_register << 2
        out |= self._gain_register
        self.bus.write_byte(self.address, out)
