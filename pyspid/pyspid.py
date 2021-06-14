#!/usr/bin/env python3
"""
This is the object that communicated with the rotator.
"""
import os
import logging

logging.basicConfig(level=logging.DEBUG)


class PySpid:
    def __init__(self, alt: float, az: float, port: str = "/dev/ttyUSB0"):
        self.altitude = alt
        self.azimuth = az
        self.port = port

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port_str: str):
        # check to see if this exists
        # from https://stackoverflow.com/a/33685629
        try:
            os.stat(port_str)
        except OSError:
            raise ValueError(f"Given {port_str}, which does not exist!")
        self._port = port_str
        logging.debug("Set port to %s", port_str)

    @property
    def altitude(self):
        return self._altitude

    @altitude.setter
    def altitude(self, alt):
        pass
