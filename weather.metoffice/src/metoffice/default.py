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

import sys
import socket
socket.setdefaulttimeout(20)
import utilities, properties, urlcache
from utilities import gettext as _
from constants import WINDOW, ADDON, API_KEY, CURRENT_VIEW, ADDON_DATA_PATH

@utilities.failgracefully
def main():
    if ADDON.getSetting('EraseCache') == 'true':
        try:
            urlcache.URLCache(ADDON_DATA_PATH).erase()
        finally:
            ADDON.setSetting('EraseCache', 'false')#@UndefinedVariable

    if not API_KEY:
        raise Exception(_("No API Key."), _("Enter your Met Office API Key under settings."))

    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        properties.observation()
    if not CURRENT_VIEW:
        properties.daily()
    elif CURRENT_VIEW == '3hourly':
        properties.threehourly()
    elif CURRENT_VIEW == 'forecastmap':
        properties.forecastlayer()
    elif CURRENT_VIEW == 'observationmap':
        properties.observationlayer()
    elif CURRENT_VIEW == 'text':
        properties.text()

    WINDOW.setProperty('WeatherProvider', ADDON.getAddonInfo('name'))#@UndefinedVariable
    WINDOW.setProperty('ObservationLocation', ADDON.getSetting('ObservationLocation'))#@UndefinedVariable
    WINDOW.setProperty('ForecastLocation', ADDON.getSetting('ForecastLocation'))#@UndefinedVariable
    WINDOW.setProperty('RegionalLocation', ADDON.getSetting('RegionalLocation'))#@UndefinedVariable
    WINDOW.setProperty('Location1', ADDON.getSetting('ObservationLocation'))#@UndefinedVariable
    WINDOW.setProperty('Locations', '1')#@UndefinedVariable

if __name__ == '__main__':
    main()