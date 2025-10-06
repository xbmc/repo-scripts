from bossanova808.constants import ADDON, WEATHER_WINDOW
from bossanova808.utilities import set_property
from bossanova808.logger import Logger


def refresh_locations():
    """
    Get the user's location and radar code choices from the addon settings, and set them as window properties
    """
    Logger.info("Refreshing locations from settings")

    location1 = ADDON.getSetting('Location1BOM') or ""
    location2 = ADDON.getSetting('Location2BOM') or ""
    location3 = ADDON.getSetting('Location3BOM') or ""

    Logger.info(f"Location1: {location1}")
    Logger.info(f"Location2: {location2}")
    Logger.info(f"Location3: {location3}")

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
    Logger.info(f"Total locations: {locations}")
    set_property(WEATHER_WINDOW, 'Locations', str(locations))

    Logger.info("Refreshing radar locations from settings")

    radar1 = ADDON.getSetting('Radar1') or ADDON.getSetting('Location1ClosestRadar') or ""
    radar2 = ADDON.getSetting('Radar2') or ADDON.getSetting('Location2ClosestRadar') or ""
    radar3 = ADDON.getSetting('Radar3') or ADDON.getSetting('Location3ClosestRadar') or ""

    Logger.info(f"Radar1: {radar1}")
    Logger.info(f"Radar2: {radar2}")
    Logger.info(f"Radar3: {radar3}")

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
    Logger.info(f"Total radars: {radars}")
    set_property(WEATHER_WINDOW, 'Radars', str(radars))
