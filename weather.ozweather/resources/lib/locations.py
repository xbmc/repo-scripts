import xbmc
import xbmcgui

from resources.lib.common import *
from resources.lib.weatherzone import *


def refresh_locations():
    """
    Set the location and radar code properties from settings -> window
    """
    log("Refreshing locations from settings")
    location_set1 = ADDON.getSetting('Location1')
    location_set2 = ADDON.getSetting('Location2')
    location_set3 = ADDON.getSetting('Location3')
    locations = 0
    if location_set1 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location1', location_set1)
    else:
        set_property(WEATHER_WINDOW, 'Location1')
    if location_set2 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location2', location_set2)
    else:
        set_property(WEATHER_WINDOW, 'Location2')
    if location_set3 != '':
        locations += 1
        set_property(WEATHER_WINDOW, 'Location3', location_set3)
    else:
        set_property(WEATHER_WINDOW, 'Location3')

    set_property(WEATHER_WINDOW, 'Locations', str(locations))

    log("Refreshing radar locations from settings")
    radar_set1 = ADDON.getSetting('Radar1')
    radar_set2 = ADDON.getSetting('Radar2')
    radar_set3 = ADDON.getSetting('Radar3')
    radars = 0
    if radar_set1 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar1', radar_set1)
    else:
        set_property(WEATHER_WINDOW, 'Radar1')
    if radar_set2 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar2', radar_set2)
    else:
        set_property(WEATHER_WINDOW, 'Radar2')
    if radar_set3 != '':
        radars += 1
        set_property(WEATHER_WINDOW, 'Radar3', radar_set3)
    else:
        set_property(WEATHER_WINDOW, 'Radar3')

    set_property(WEATHER_WINDOW, 'Radars', str(locations))


def find_location():
    """
    Find a location (= WeatherZone url path) - when the user inputs a postcode or suburb
    """
    keyboard = xbmc.Keyboard('', LANGUAGE(32195), False)
    keyboard.doModal()

    if keyboard.isConfirmed() and keyboard.getText() != '':
        text = keyboard.getText()

        log("Doing locations search for " + text)
        locations, location_url_paths = getLocationsForPostcodeOrSuburb(text)

        # Now get them to choose an actual location
        dialog = xbmcgui.Dialog()
        if locations:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                ADDON.setSetting(sys.argv[1], locations[selected])
                ADDON.setSetting(sys.argv[1] + 'UrlPath', location_url_paths[selected])
        # Or indicate we did not receive any locations
        else:
            dialog.ok(ADDON_NAME, xbmc.getLocalizedString(284))
