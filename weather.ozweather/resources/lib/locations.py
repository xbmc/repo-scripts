# noinspection PyPackages
from .common import *


def refresh_locations():
    """
    Get the user's location and radar code choices from the addon settings, and set them as window properties
    """
    log("Refreshing locations from settings")

    location1 = ADDON.getSetting('Location1BOM') or ""
    location2 = ADDON.getSetting('Location2BOM') or ""
    location3 = ADDON.getSetting('Location3BOM') or ""

    log("Location1: " + location1)
    log("Location2: " + location2)
    log("Location3: " + location3)

    locations = 0

    # If either the main location or the fallback is set, then enable the location
    # This is to cope with the transition period where folks will have the fallbacks set from their legacy settings
    # But not the new BOM locations
    if location1 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location1', location1)
    if location2 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location2', location2)
    if location3 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location3', location3)

    # and set count of locations
    log(f"Total locations: {locations}")
    set_property(WEATHER_WINDOW, 'Locations', str(locations))

    log("Refreshing radar locations from settings")

    radar1 = ADDON.getSetting('Radar1') or ADDON.getSetting('Location1ClosestRadar') or ""
    radar2 = ADDON.getSetting('Radar2') or ADDON.getSetting('Location2ClosestRadar') or ""
    radar3 = ADDON.getSetting('Radar3') or ADDON.getSetting('Location3ClosestRadar') or ""

    log("Radar1: " + radar1)
    log("Radar2: " + radar2)
    log("Radar3: " + radar3)

    radars = 0

    if radar1 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar1', radar1)
    if radar2 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar2', radar2)
    if radar3 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar3', radar3)

    # and set count of radars
    log(f"Total radars: {radars}")
    set_property(WEATHER_WINDOW, 'Radars', str(radars))

