#!/usr/bin/env python3
"""
This is the object that communicated with the rotator.
"""
import os
import logging

logging.basicConfig(level=logging.DEBUG)


class PySpid:
    def __init__(self, go_to_alt: float, go_to_az: float, port: str = "/dev/ttyUSB0"):
        self.go_to_altitude = go_to_alt
        self.go_to_azimuth = go_to_az
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
    def go_to_altitude(self):
        return self._go_to_altitude

    @go_to_altitude.setter
    def go_to_altitude(self, alt):
        if not 0 <= alt <= 180:
            logging.warning(
                "%f is outside [0,180], to to alt staying at %f",
                alt,
                self.go_to_altitude,
            )
        else:
            self._go_to_alt = alt

    @property
    def go_to_azimuth(self, az):
        return self._go_to_azimuth

    @go_to_azimuth.setter
    def go_to_azimuth(self, az):
        if not 0 <= az <= 360:
            logging.warning(
                "%f is outside [0,180], to to alt staying at %f",
                az,
                self.go_to_azimuth,
            )
        else:
            self._go_to_azimuth = az
