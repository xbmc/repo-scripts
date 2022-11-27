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
socket.setdefaulttimeout(20)


@utilities.failgracefully
def main():
    if ADDON.getSetting('EraseCache') == 'true':
        try:
            urlcache.URLCache(ADDON_DATA_PATH).erase()
        finally:
            ADDON.setSetting('EraseCache', 'false')  # @UndefinedVariable

    if not API_KEY:
        raise Exception(_("No API Key."), _("Enter your Met Office API Key under settings."))

    properties.observation()
    properties.daily()
    properties.threehourly()
    properties.sunrisesunset()

    WINDOW.setProperty('WeatherProvider', ADDON.getAddonInfo('name'))  # @UndefinedVariable
    WINDOW.setProperty('WeatherProviderLogo', ADDON_BANNER_PATH)  # @UndefinedVariable
    WINDOW.setProperty('ObservationLocation', ADDON.getSetting('ObservationLocation'))  # @UndefinedVariable
    WINDOW.setProperty('Current.Location', ADDON.getSetting('ForecastLocation'))  # @UndefinedVariable
    WINDOW.setProperty('ForecastLocation', ADDON.getSetting('ForecastLocation'))  # @UndefinedVariable
    WINDOW.setProperty('RegionalLocation', ADDON.getSetting('RegionalLocation'))  # @UndefinedVariable
    WINDOW.setProperty('Location1', ADDON.getSetting('ForecastLocation'))  # @UndefinedVariable
    WINDOW.setProperty('Locations', '1')  # @UndefinedVariable

    # Explicitly set unused flags to false, so there are no unusual side
    # effects/residual data when moving from another weather provider.
    WINDOW.setProperty('36Hour.IsFetched', '')  # @UndefinedVariable
    WINDOW.setProperty('Weekend.IsFetched', '')  # @UndefinedVariable
    WINDOW.setProperty('Map.IsFetched', '')  # @UndefinedVariable
    WINDOW.setProperty('Weather.CurrentView', '')  # @UndefinedVariable


if __name__ == '__main__':
    main()
