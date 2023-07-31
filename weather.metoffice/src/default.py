# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
import socket
import sys
import traceback
from urllib.error import HTTPError

import xbmc

import setlocation
from metoffice import properties, urlcache, utilities
from metoffice.constants import (
    ADDON_BANNER_PATH,
    ADDON_DATA_PATH,
    API_KEY,
    addon,
    window,
)
from metoffice.utilities import gettext as _

socket.setdefaulttimeout(20)


def main():
    if addon().getSetting("EraseCache") == "true":
        try:
            urlcache.URLCache(ADDON_DATA_PATH).erase()
        finally:
            addon().setSetting("EraseCache", "false")

    if not API_KEY:
        raise Exception(
            _("No API Key."), _("Enter your Met Office API Key under settings.")
        )

    if sys.argv[1] in ["ObservationLocation", "ForecastLocation", "RegionalLocation"]:
        setlocation.main(sys.argv[1])

    try:
        properties.observation()
        properties.daily()
        properties.threehourly()
        properties.sunrisesunset()
    except KeyError:
        # Expect KeyErrors to come from parsing JSON responses.
        # This is considered an intermittent error, so exception is eaten.
        utilities.log(traceback.format_exc(), xbmc.LOGERROR)
    except HTTPError:
        # HTTPErrors are most likely to occur when the user hasn't set their API
        # key, so allow the script to raise to produce a parp.
        utilities.log(
            (
                "Error fetching data.\n"
                "Ensure the API key in addon configuration is correct and try again.\n"
                "You can get an API key by creating an account at\n"
                "https://register.metoffice.gov.uk/WaveRegistrationClient/public/register.do?service=datapoint"
            ),
            xbmc.LOGERROR,
        )
        raise

    window().setProperty("WeatherProvider", addon().getAddonInfo("name"))
    window().setProperty("WeatherProviderLogo", ADDON_BANNER_PATH)
    window().setProperty(
        "ObservationLocation", addon().getSetting("ObservationLocation")
    )
    window().setProperty("Current.Location", addon().getSetting("ForecastLocation"))
    window().setProperty("ForecastLocation", addon().getSetting("ForecastLocation"))
    window().setProperty("RegionalLocation", addon().getSetting("RegionalLocation"))
    window().setProperty("Location1", addon().getSetting("ForecastLocation"))
    window().setProperty("Locations", "1")

    # Explicitly set unused flags to false, so there are no unusual side
    # effects/residual data when moving from another weather provider.
    window().setProperty("36Hour.IsFetched", "")
    window().setProperty("Weekend.IsFetched", "")
    window().setProperty("Map.IsFetched", "")
    window().setProperty("Weather.CurrentView", "")


if __name__ == "__main__":
    main()
