<!-- 
*** pyspid
-->

[![GitHub license](https://img.shields.io/github/license/josephwkania/pyspid?style=flat-square)](https://github.com/josephwkania/pyspid/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

# PySPID

`pyspid` is a python interfere for SPID RAS rotators. It has two classes, 
`PySpid` which can send Altitude and Azimuth (Alt & AZ) from the rotator, as well as tell
the rotator to spot moving.
`SpidTracker` can tell the rotator and point and follow a celestial coordinate given in
Right Ascension and Declination (RA & Dec). This class can also tell you where the rotator is pointing
in Alt & Az, RA & Dec, and Galactic Latitude and Longitude (l & b). 

## Installation
You can install this using pip

```bash
pip install git+https://github.com/josephwkania/spidpy.git
```

## Use
```python
ipython
from pyspid import PySpid
pyspid_obj = PySpid("/dev/ttyUSB0") # make the object
pyspid_obj.get_location() # gets the current alt, az
pyspid_obj.go_to(alt=your_az, el=your_el) # go to your_az, your_el
pyspid_obj.stop() # stops the rotator
pyspid_obj.end() # closes the port
```

```python
ipython
from pyspid import SpidTracker
from time import sleep
tracker = SpidTracker(ra=None, dec=None, lat=39.1, lon=-79.2, height=100)
# First four are in degrees, height is in meters
# when ra=None or dec=None, telescope does not move,
# only location gets updated
j = 0
while j < 10:
    print(tracker.current_alt_az)
    j += 1
    sleep(60)
    # prints pointing location every minute
print(tracker.current_ra_dec)
# print ra, dec
tracker.end() # tells telescope to stop 
# and end the loop, closes the port
```

## License
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