#!/usr/bin/env python3
"""
Tells SPID to track astronomical coordinates.
Gives current pointing into in Altitude & Azimuth,
Right Ascension & Declination, and Galactic Longitude and Latitude.

Properities:
    current_alt_az - gives the current alt & az
    current_ra_dec - Current Right Ascension and Declination
    current_l_b - current galactic Longitude and Latitude
    on_source - If the antenna is on source (and tracking)

Functions:
    _tracker - Tracks a celestial coordinate, called if
               RA and Dec are None
    _update_location - Updates telescope location, called if
                       RA or Dec are None.
    end - Ends the loop and closes the serial port.
"""
import logging
import threading
from collections import namedtuple
from datetime import datetime, timedelta
from time import sleep

from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time

from pyspid import PySpid


class SpidTracker:
    """
    Make the SPID rotator track a celestial object.
    Get and stores pointing info, which it can
    report in Horizontal, Equatorial and Galactic
    coordinate systems.
    """

    def __init__(
        self,
        lat: float,
        lon: float,
        height: float,
        ra: str = None,
        dec: str = None,
        tolerance: float = 2.0,
        cadence: float = 30,
        port: str = "/dev/ttyUSB0",
    ):
        """
        args:
            lat - Latitude of telescope in degrees
                  Southern Hemisphere - remember the negative

            lon - Longitude of telesdcope in degrees
                  Western Hemisphere - remember the negative

            height - height above sea leavel in meters

            ra - Right assentation to track in decimal degrees.
                 If None, does not move telescope

            dec - Decimation to track in decimal degrees

            tolerance - Pointing tolerance to maintain, in degrees

            cadence - How often to check the pointing, in seconds

            port - Port to talk to the rotator

        """
        self.pyspid_obj = PySpid(port)
        self.update = True
        self.on_source = False
        self.current_az = None
        self.current_alt = None

        if not 0 <= tolerance < 30:
            raise ValueError("tolerance must be [0,30), given {tolerance}")
        self.location = EarthLocation(
            lat=lat * u.degree, lon=lon * u.degree, height=height * u.meter
        )
        logging.debug("Using earth location %s", self.location)

        if ra is not None and dec is not None:
            self.track_coord = SkyCoord(ra * u.degree, dec * u.degree, frame="icrs")
            logging.info("Tracking %s", self.track_coord)
            thread = threading.Thread(
                target=self._tracker,
                args=(
                    self.location,
                    tolerance,
                    cadence,
                ),
            )
            thread.daemon = True
            thread.start()
        else:
            logging.info("RA+Dec not given, updating location only")
            thread = threading.Thread(target=self._update_location, args=(cadence,))
            thread.daemon = True
            thread.start()

    @property
    def current_alt_az(self) -> namedtuple:
        """
        The current Altitude and Azimuth in degrees.
        """
        alt_az_tuple = namedtuple("current_Alt_Az", ("Alt, Az"))
        return alt_az_tuple(self.current_alt, self.current_az)

    @property
    def current_ra_dec(self) -> namedtuple:
        """
        The current Right Ascension and Declination in degrees.
        """
        current_time = Time(datetime.now())
        alt_az = AltAz(location=self.location, obstime=current_time)
        telescope_pointing = SkyCoord(
            az=self.current_az * u.degree, alt=self.current_alt * u.degree, frame=alt_az
        )
        ra_dec_tuple = namedtuple("current_RA_Dec", ("RA", "Dec"))
        return ra_dec_tuple(
            telescope_pointing.icrs.ra.deg, telescope_pointing.icrs.dec.deg
        )

    @property
    def current_l_b(self) -> namedtuple:
        """
        The current Galactic Longitude and Latitude in degrees.
        """
        current_time = Time(datetime.now())
        alt_az = AltAz(location=self.location, obstime=current_time)
        telescope_pointing = SkyCoord(
            az=self.current_az * u.degree, alt=self.current_alt * u.degree, frame=alt_az
        )
        l_b_tuple = namedtuple("current_l_b", ("l", "b"))
        return l_b_tuple(
            telescope_pointing.galactic.l.deg, telescope_pointing.galactic.b.deg
        )

    @property
    def on_souce(self):
        """
        Return the on source variable. This is true when the antenna is
        within twice the tolerance, (as should happen when the antenna is tracking)
        """
        return self.on_source

    def _tracker(
        self, location: object, tolerance: float = 2.0, cadence: int = 30
    ) -> None:
        """
        Tracks the requestied position.

        args:
            location - Astropy location object for the telescope

            tolerance - Move the telescope if the beam is this many degrees from the
                        target

            cadence - how often to check the telescope position, in seconds.

        This function loops while self.update == True,
        everytime it loops it checks the separation between the antenna and the source
        If this separation is greater than tolerance, this will send a command to move
        move the antenna will be in cadence seconds. I did this to try and keep the main
        lobe on source longer and to minimize the amounts of slews needed.

        If the antenna is twice the tolerance, self.on_source gets set to false.
        This will send the corridantes a total of three times to try and
        go back on source, is they does not happen, the loop terminates.
        I did this so it does not contiguously try to move past the mechanical
        limits, etc.
        """
        off_source_count = 0
        while self.update:
            self.current_az, self.current_alt = self.pyspid_obj.get_location()
            current_time = Time(datetime.now())
            alt_az = AltAz(location=location, obstime=current_time)
            telescope_pointing = SkyCoord(
                az=self.current_az * u.degree,
                alt=self.current_alt * u.degree,
                frame=alt_az,
            )
            separation = telescope_pointing.separation(self.track_coord).deg
            logging.debug("Target-Telescope separation: %.2f deg", separation)
            if separation > tolerance:
                logging.debug(
                    "Target-Telescope separation is outside tolerance, moving"
                )
                time_future = current_time + timedelta(seconds=cadence)
                alt_az_future = AltAz(location=location, obstime=time_future)
                track_altaz_future = self.track_coord.transform_to(alt_az_future)
                alt_future = track_altaz_future.alt.deg
                az_future = track_altaz_future.az.deg
                if alt_future <= 0:
                    self.end()
                    raise RuntimeError("Target has set! Ending")

                logging.debug(
                    "Target will be at %.1f alt, %.1f az in %i sec, moving there",
                    alt_future,
                    az_future,
                    cadence,
                )
                # self.pyspid_obj.go_to(az=az_future, el=alt_future)
            elif separation > 2 * tolerance:
                logging.warning(
                    "Target-Telescope separation is %.1f, 2x what it should be",
                    separation,
                )
                self.on_source = False
                off_source_count += 1
                if off_source_count >= 2:
                    self.end()
                    raise RuntimeError(
                        "Can't get on source in 3 attempts, something is wrong. Ending!"
                    )
            else:
                logging.debug("Within tolerance, not moving")
                self.on_source = True
            sleep(cadence)

    def _update_location(self, cadence: int = 30) -> None:
        """
        Updates pointing location without moving the telescope.
        """
        while self.update:
            self.current_az, self.current_alt = self.pyspid_obj.get_location()
            sleep(cadence)

    def end(self) -> None:
        """
        Nicely Terminates the loop and closes the port.
        """
        logging.info("Endpoint called, ending loop, closing port.")
        self.update = False
        self.pyspid_obj.end()
