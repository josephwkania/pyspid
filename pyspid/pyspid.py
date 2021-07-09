#!/usr/bin/env python3
"""
This is the object that communicates with the rotator.
Property:
    port - the port to connect to

Functions:
    get_location() - gets the current pointing
    get_response() - talks to the rotator, keeps trying for
                     10 attempts or until a repsonce of the
                     correct length
    go_to() - send the rotator to this postion
    stop() - stop the rotator where ever it is
    end() - end the serial connection to the rotator
            and exit

Based on ALFARAS.py by ALFARadio, which implements
Program_format-Komunicacji-2005-08-10-p2.pdf
also see https://web.archive.org/web/20160401023247/http://ryeng.name/blog/3

This is published under GPL-v3, which states
"THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW"

and

"... ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS
THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY
GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE
USE OR INABILITY TO USE THE PROGRAM"

You should test this program before using it. I have only tested this
with one SPID rotator.
Behavior might be different for different models/versions.
"""
import logging
import os
from collections import namedtuple
from time import sleep

import serial

logging.basicConfig(level=logging.DEBUG)

five_0 = chr(0) + chr(0) + chr(0) + chr(0) + chr(0)


class PySpid:
    """
    The object that will communicate with the rotator
    """

    def __init__(self, port: str = "/dev/ttyUSB0"):
        """
        args:
            port - The port to which the rotator is connected too
        """
        # go_to_alt: float, go_to_az: float,
        # self.go_to_altitude = go_to_alt
        # self.go_to_elevation = go_to_elivation
        self.port = port
        self.serial_obj = serial.Serial(port, 600, timeout=0)
        response = self.get_response()
        self.az_multi = response[5]
        self.el_multi = response[10]
        self._az = None
        self._el = None

    @property
    def port(self):
        """
        Return the port the object if conencted to
        """
        return self._port

    @port.setter
    def port(self, port_str: str):
        # check to see if this exists
        # from https://stackoverflow.com/a/33685629
        try:
            os.stat(port_str)
        except OSError as os_error:
            raise ValueError(f"Given {port_str}, which does not exist!") from os_error
        self._port = port_str
        logging.debug("Set port to %s", port_str)

    # @property
    # def go_to_elevation(self):
    #     return self._go_to_elevation

    # @go_to_elevation.setter
    # def go_to_elevation(self, el):
    #     if not 0 <= el <= 180:
    #         logging.warning(
    #             "%f is outside [0, 180], altitude staying at %f",
    #             el,
    #             self.go_to_elevation,
    #         )
    #     else:
    #         self._go_to_elevation = el

    # @property
    # def go_to_azimuth(self):
    #     return self._go_to_azimuth

    # @go_to_azimuth.setter
    # def go_to_azimuth(self, az):
    #     if not 0 <= az <= 360:
    #         logging.warning(
    #             "%f is outside [0, 360], azimuth staying at %f",
    #             az,
    #             self.go_to_azimuth,
    #         )
    #     else:
    #         self._go_to_azimuth = az

    def get_location(self) -> namedtuple:
        """
        This function talks to the rotator and gets the location.
        """
        out = chr(87) + five_0 + five_0 + chr(15) + chr(32)
        out_resp = self.serial_obj.write(out.encode())
        logging.debug("Out response: %s", out_resp)
        # Wait for answer from controller
        sleep(0.75)
        response = self.get_response()
        self._az = response[1] * 100 + response[2] * 10 + response[3] + response[4] / 10
        self._el = response[6] * 100 + response[7] * 10 + response[8] + response[9] / 10
        # Since the controller sends the status based on 0 degrees = 360
        # remove the 360 here
        self._az -= 2 * 360
        # jwk: need to subtract off another
        # 360 for some unknown reason
        self._el -= 360
        logging.debug(
            "Rotator at %.1f Deg Azimuth and %.1f Deg Elevation",
            self._az,
            self._el,
        )
        logging.debug(
            "Azimuth multiplier: %i, Elevation Multiplier is %i",
            response[5],
            response[10],
        )

        alt_az_tuple = namedtuple("current_Alt_Az", ("Alt, Az"))
        return alt_az_tuple(self._az, self._el)

    def get_response(self):
        """
        This tries to communicate with the rotator,
        It sometimes takes multiple tries to get a response,
        hence the loop
        """
        out = chr(87) + five_0 + five_0 + chr(31) + chr(32)
        count = 0
        response = b""
        while count < 10:
            _ = self.serial_obj.write(out.encode())
            sleep(0.75)
            response = self.serial_obj.read(12)
            logging.debug("response: %s", response)
            if len(response) >= 12:
                break
        else:
            logging.error("Did not get response, closing!")
            self.end()
        return response

    def go_to(self, az: float = None, el: float = None) -> bool:
        """
        Communicates with the rotator to set the desired pointing location.

        args:
            az - desired azimuth, must be between [0, 180]

            el - desired elivation
        returns
            success - weather the message was sent.
        """
        if not 0 <= el <= 180:
            logging.warning("%f is outside [0, 180], staying at %f EL", el, self._el)
            return False
        if not 0 <= az <= 360:
            logging.warning(
                "%f is outside [0, 360], staying at %f az",
                az,
                self._az,
            )
            return False

        az += 2 * 360
        el += 360

        az *= self.az_multi
        el *= self.el_multi

        az = str(az)
        el = str(el)

        if len(az) == 3:
            logging.debug("Padding az w/ 0")
            az = "0" + az
        if len(el) == 3:
            logging.debug("Padding el w/ 0")
            el = "0" + el

        # Message to send
        message = (
            chr(87)
            + az
            + chr(self.az_multi)
            + el
            + chr(self.el_multi)
            + chr(47)
            + chr(32)
        )

        # Send message
        _ = self.serial_obj.write(message.encode())
        return True

    def stop(self):
        """
        Stops the rotator.
        """
        stop_message = chr(87) + five_0 + five_0 + chr(15) + chr(32)
        _ = self.serial_obj.write(stop_message.encode())
        sleep(0.75)

    def end(self):
        """
        Closes the port and exits
        """
        logging.debug("Closing port %s and exiting", self._port)
        self.serial_obj.close()  # close the port
        # sys.exit()  $ probably don't want to exit
