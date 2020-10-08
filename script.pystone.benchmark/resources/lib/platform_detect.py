#   Copyright (C) 2020 Lunatixz
#
#
# This file is part of CPU Benchmark.
#
# CPU Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CPU Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CPU Benchmark.  If not, see <http://www.gnu.org/licenses/>.

import platform, re
from kodi_six import xbmcvfs

def platform_detect():
    """Detect if running on the Raspberry Pi or Beaglebone Black and return the
    platform type.  Will return RASPBERRY_PI, BEAGLEBONE_BLACK, or UNKNOWN."""
    # Handle Raspberry Pi
    pi = pi_version()
    if pi is not None:
        return 'Raspberry Pi gen.%s'%(pi)

    # Handle Beaglebone Black
    # TODO: Check the Beaglebone Black /proc/cpuinfo value instead of reading
    # the platform.
    plat = platform.platform()
    if plat.lower().find('armv7l-with-debian') > -1:
        return 'Beaglebone Black'
    elif plat.lower().find('armv7l-with-ubuntu') > -1:
        return 'Beaglebone Black'
    elif plat.lower().find('armv7l-with-glibc2.4') > -1:
        return 'Beaglebone Black'
    elif plat.lower().find('armv7l-with-arch') > -1:
        return 'Beaglebone Black'
    elif plat.lower().startswith('arm'): 
        return 'ARM Architecture'
    return plat

def pi_version(processor=False):
    """Detect the version of the Raspberry Pi.  Returns either 1, 2, 3 or
    None depending on if it's a Raspberry Pi 1 (model A, B, A+, B+),
    Raspberry Pi 2 (model B+), Raspberry Pi 3,Raspberry Pi 3 (model B+), Raspberry Pi 4
    or not a Raspberry Pi.
    """
    # Check /proc/cpuinfo for the Hardware field value.
    # 2708 is pi 1
    # 2709 is pi 2
    # 2835 is pi 3 or pi 4
    # 2837 is pi 3b+
    # Anything else is not a pi.
    with xbmcvfs.File('/proc/cpuinfo', 'r') as infile:
        cpuinfo = infile.read()
    # Match a line like 'Hardware   : BCM2709'
    match = re.search('^Hardware\s+:\s+(\w+)$', cpuinfo,
                      flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        # Couldn't find the hardware, assume it isn't a pi.
        return None
    if match.group(1) == 'BCM2708':
        # Pi 1
        if processor: return 'BCM2708'
        else: return 1
    elif match.group(1) == 'BCM2709':
        # Pi 2
        if processor: return 'BCM2709'
        else: return 2
    elif match.group(1) == 'BCM2835':
        # Pi 3 or Pi 4
        if processor: return 'BCM2835'
        else: return 3
    elif match.group(1) == 'BCM2837':
        # Pi 3b+
        if processor: return 'BCM2837'
        else: return 3
    else:
        # Something else, not a pi.
        return None
        
def processor_detect():
    pi = pi_version(processor=True)
    if pi is None: return platform.processor()
    
    
def getcpu():
    # find the CPU name (which needs a different method per OS), and return it
    # If none found, return platform.platform().

    cputype = None

    try:
        if platform.system() == "Windows":
            import winreg

            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Hardware\Description\System\CentralProcessor\0")
            cputype = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)

        elif platform.system() == "Darwin":
            cputype = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()

        elif platform.system() == "Linux":
            with open("/proc/cpuinfo") as fp:
                for myline in fp.readlines():
                    if myline.startswith("model name"):
                        # Typical line:
                        # model name      : Intel(R) Xeon(R) CPU           E5335  @ 2.00GHz
                        cputype = myline.split(":", 1)[1]  # get everything after the first ":"
                        break  # we're done
        cputype = cputype.decode(locale.getpreferredencoding())
    except:
        # An exception, maybe due to a subprocess call gone wrong
        pass

    if cputype:
        # OK, found. Remove unwanted spaces:
        cputype = " ".join(cputype.split())
    else:
        # Not found, so let's fall back to platform()
        cputype = platform.platform()
    return cputype