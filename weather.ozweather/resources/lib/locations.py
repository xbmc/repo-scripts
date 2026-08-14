from bossanova808.constants import WEATHER_WINDOW
from bossanova808.utilities import set_property, get_setting
from bossanova808.logger import Logger


def refresh_locations():
    """
    Get the user's location and radar code choices from the addon settings, and set them as window properties
    """
    Logger.info("Refreshing weather locations from settings")

    location1 = get_setting('Location1BOM') or ""
    location2 = get_setting('Location2BOM') or ""
    location3 = get_setting('Location3BOM') or ""
    location4 = get_setting('Location4BOM') or ""
    location5 = get_setting('Location5BOM') or ""
    location6 = get_setting('Location6BOM') or ""

    Logger.info(f"Location1: {location1}")
    Logger.info(f"Location2: {location2}")
    Logger.info(f"Location3: {location3}")
    Logger.info(f"Location4: {location4}")
    Logger.info(f"Location5: {location5}")
    Logger.info(f"Location6: {location6}")	

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
    if location4 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location4', location4)	
    if location5 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location5', location5)
    if location6 != '':
        locations += 1
    set_property(WEATHER_WINDOW, 'Location6', location6)
	
    # and set count of locations
    Logger.info(f"Total locations: {locations}")
    set_property(WEATHER_WINDOW, 'Locations', str(locations))

    Logger.info("Refreshing radar locations from settings")

    radar1 = get_setting('Radar1') or get_setting('Location1ClosestRadar') or ""
    radar2 = get_setting('Radar2') or get_setting('Location2ClosestRadar') or ""
    radar3 = get_setting('Radar3') or get_setting('Location3ClosestRadar') or ""
    radar4 = get_setting('Radar4') or get_setting('Location4ClosestRadar') or ""
    radar5 = get_setting('Radar5') or get_setting('Location5ClosestRadar') or ""
    radar6 = get_setting('Radar6') or get_setting('Location6ClosestRadar') or ""

    Logger.info(f"Radar1: {radar1}")
    Logger.info(f"Radar2: {radar2}")
    Logger.info(f"Radar3: {radar3}")
    Logger.info(f"Radar4: {radar4}")
    Logger.info(f"Radar5: {radar5}")
    Logger.info(f"Radar6: {radar6}")	

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
    if radar4 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar4', radar4)	
    if radar5 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar5', radar5)	
    if radar6 != '':
        radars += 1
    set_property(WEATHER_WINDOW, 'Radar6', radar6)	

    # and set count of radars
    Logger.info(f"Total radars: {radars}")
    set_property(WEATHER_WINDOW, 'Radars', str(radars))
