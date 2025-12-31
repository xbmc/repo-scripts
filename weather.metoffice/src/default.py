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
import xbmcaddon
import xbmcgui

import setlocation
from metoffice import properties, urlcache, utilities
from metoffice.constants import (
    ADDON_BANNER_PATH,
    ADDON_DATA_PATH,
    ADDON_ID,
    API_KEY,
    SETTINGS_WINDOW_ID,
    WEATHER_WINDOW_ID,
)

window = xbmcgui.Window(WEATHER_WINDOW_ID)
addon = xbmcaddon.Addon(ADDON_ID)

socket.setdefaulttimeout(20)


def main():
    if sys.argv[1] in ["ObservationLocation", "ForecastLocation"]:
        setlocation.main(sys.argv[1])
        return

    if addon.getSetting("EraseCache") == "true":
        try:
            urlcache.URLCache(ADDON_DATA_PATH).erase()
        finally:
            addon.setSetting("EraseCache", "false")

    if not API_KEY:
        window.setProperty("Current.Condition", "[ Check API Key ]")
        window.setProperty("Current.OutlookIcon", "na.png")
        window.setProperty("Current.FanartCode", "na")

        if xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID:
            dialog = xbmcgui.Dialog()
            dialog.ok(
                "No API Key",
                "Please register for an API Key at https://register.metoffice.gov.uk. "
                "Then save your API Key under addon settings.",
            )

        return

    try:
        properties.observation()
        properties.daily()
        properties.threehourly()
        properties.sunrisesunset()
    except KeyError:
        # Expect KeyErrors to come from parsing JSON responses.
        # This is considered an intermittent error, so exception is eaten.
        utilities.log(traceback.format_exc(), xbmc.LOGERROR)
    except HTTPError as e:

        if e.code != 403:
            raise

        window.setProperty("Current.Condition", "[ Check API Key ]")
        window.setProperty("Current.OutlookIcon", "na.png")
        window.setProperty("Current.FanartCode", "na")
        utilities.log(
            (
                "Error fetching data.\n"
                "Ensure the API key in addon configuration is correct and try again.\n"
                "You can get an API key by creating an account at\n"
                "https://register.metoffice.gov.uk/WaveRegistrationClient/public/register.do?service=datapoint"
            ),
            xbmc.LOGERROR,
        )
        if (
            xbmcgui.getCurrentWindowId() == WEATHER_WINDOW_ID
            or xbmcgui.getCurrentWindowId() == SETTINGS_WINDOW_ID
        ):
            dialog = xbmcgui.Dialog()
            dialog.ok(
                "Cannot fetch data.",
                "Ensure the API key in addon configuration is correct and try again.",
            )

    window.setProperty("WeatherProvider", addon.getAddonInfo("name"))
    window.setProperty("WeatherProviderLogo", ADDON_BANNER_PATH)
    window.setProperty("ObservationLocation", addon.getSetting("ObservationLocation"))
    window.setProperty("Current.Location", addon.getSetting("ForecastLocation"))
    window.setProperty("ForecastLocation", addon.getSetting("ForecastLocation"))
    window.setProperty("Location1", addon.getSetting("ForecastLocation"))
    window.setProperty("Locations", "1")

    # Explicitly set unused flags to false, so there are no unusual side
    # effects/residual data when moving from another weather provider.
    window.setProperty("36Hour.IsFetched", "")
    window.setProperty("Weekend.IsFetched", "")
    window.setProperty("Map.IsFetched", "")
    window.setProperty("Weather.CurrentView", "")


if __name__ == "__main__":
    main()
