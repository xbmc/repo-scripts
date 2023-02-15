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
from metoffice.utilities import gettext as _
from metoffice.constants import WINDOW, ADDON, API_KEY, ADDON_DATA_PATH, ADDON_BANNER_PATH
from metoffice import urlcache, properties, utilities
import socket
import sys

import setlocation

socket.setdefaulttimeout(20)


@utilities.failgracefully
def main():
    if ADDON.getSetting('EraseCache') == 'true':
        try:
            urlcache.URLCache(ADDON_DATA_PATH).erase()
        finally:
            ADDON.setSetting('EraseCache', 'false')

    if not API_KEY:
        raise Exception(_("No API Key."), _("Enter your Met Office API Key under settings."))

    if sys.argv[1] in ['ObservationLocation', 'ForecastLocation', 'RegionalLocation']:
        setlocation.main(sys.argv[1])

    properties.observation()
    properties.daily()
    properties.threehourly()
    properties.sunrisesunset()

    WINDOW.setProperty('WeatherProvider', ADDON.getAddonInfo('name'))
    WINDOW.setProperty('WeatherProviderLogo', ADDON_BANNER_PATH)
    WINDOW.setProperty('ObservationLocation', ADDON.getSetting('ObservationLocation'))
    WINDOW.setProperty('Current.Location', ADDON.getSetting('ForecastLocation'))
    WINDOW.setProperty('ForecastLocation', ADDON.getSetting('ForecastLocation'))
    WINDOW.setProperty('RegionalLocation', ADDON.getSetting('RegionalLocation'))
    WINDOW.setProperty('Location1', ADDON.getSetting('ForecastLocation'))
    WINDOW.setProperty('Locations', '1')

    # Explicitly set unused flags to false, so there are no unusual side
    # effects/residual data when moving from another weather provider.
    WINDOW.setProperty('36Hour.IsFetched', '')
    WINDOW.setProperty('Weekend.IsFetched', '')
    WINDOW.setProperty('Map.IsFetched', '')
    WINDOW.setProperty('Weather.CurrentView', '')


if __name__ == '__main__':
    main()
