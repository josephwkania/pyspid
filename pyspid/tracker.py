#!/usr/bin/env python3
"""
Tells SPID to track astronomical coordinates
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
    def current_alt_az(self):
        """
        The current Altitude and Azimuth in degrees
        """
        alt_az_tuple = namedtuple("current_Alt_Az", ("Alt, Az"))
        return alt_az_tuple(self.current_alt, self.current_az)

    @property
    def current_ra_dec(self):
        """
        The current Right ascension and Declination in degrees
        """
        current_time = Time(datetime.now())
        alt_az = AltAz(location=self.location, obstime=current_time)
        telescope_pointing = SkyCoord(
            az=self.current_az * u.degree, alt=self.current_alt * u.degree, frame=alt_az
        )
        ra_dec_tuple = namedtuple("current_ra_dec", ("RA", "Dec"))
        return ra_dec_tuple(
            telescope_pointing.icrs.ra.deg, telescope_pointing.icrs.dec.deg
        )

    @property
    def current_l_b(self):
        """
        The current Galactic Longitude and Latitude in degrees
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

    def _tracker(
        self, location: object, tolerance: float = 2.0, cadence: int = 30
    ) -> None:
        """
        Tracks the requestied position
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
        Updates pointing location without moving the telescope
        """
        while self.update:
            self.current_az, self.current_alt = self.pyspid_obj.get_location()
            sleep(cadence)

    def end(self) -> None:
        """
        Nicely Terminates the program
        """
        logging.info("Endpoint called, ending loop, closing port.")
        self.update = False
        self.pyspid_obj.end()
