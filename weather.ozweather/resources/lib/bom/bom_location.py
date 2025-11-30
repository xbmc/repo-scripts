import requests
import sys
import xbmc
import xbmcgui

# Allow for unit testing this file (remember to install kodistubs!)
# This brings this addon's resources, and bossanova808 module stuff into scope
# (only when running this module *outside* of Kodi)
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')
    sys.path.insert(0, '../../../../script.module.bossanova808/resources/lib')

from resources.lib.store import Store
from resources.lib.bom.bom_radar import closest_radar_to_lat_lon
from bossanova808.constants import ADDON, ADDON_NAME, TRANSLATE
from bossanova808.logger import Logger


def get_bom_locations_for(text):
    """
    Return list of location names and geohashes the match the given text
    """

    locations = []
    location_geohashes = []

    try:
        r = requests.get(Store.BOM_API_LOCATIONS_URL, params={'search': text}, timeout=15)
        for result in r.json()['data']:
            Logger.debug(result)
            locations.append(f'{result["name"]}, {result["state"]} {result["postcode"]} ({result["geohash"]})')
            location_geohashes.append(result["geohash"])
        Logger.debug(locations)
        Logger.debug(location_geohashes)

        return locations, location_geohashes

    except Exception as inst:
        Logger.error(f'Exception getting locations from {Store.BOM_API_LOCATIONS_URL} for search term {text}')
        Logger.error(str(inst))
        raise


def find_bom_location():
    """
    Find BOM locations when the user inputs a postcode or suburb
    What we need is actually a geohash we can then use with the BOM API
    Save the chosen result, e.g. Ascot Vale, VIC 3032 and geohash r1r11df
    """
    keyboard = xbmc.Keyboard('', TRANSLATE(32195), False)
    keyboard.doModal()

    if keyboard.isConfirmed() and keyboard.getText() != '':
        text = keyboard.getText()

        Logger.info("Doing locations search for " + text)
        locations, location_geohashes = get_bom_locations_for(text)

        # Now get them to choose an actual location from the returned matched
        dialog = xbmcgui.Dialog()

        # None  found?
        if not locations:
            dialog.ok(ADDON_NAME, xbmc.getLocalizedString(284))
        # Show the list, let the user choose
        else:
            selected = dialog.select(xbmc.getLocalizedString(396), locations)
            if selected != -1:
                # Get the full location info for the chosen geohash, notably lat & long
                # Don't save the settings is this goes wrong
                location_info_url = f'https://api.weather.bom.gov.au/v1/locations/{location_geohashes[selected]}'
                try:
                    location_info = requests.get(location_info_url, timeout=15).json()['data']
                    Logger.debug(location_info)
                except:
                    Logger.debug(f"Error retrieving location info for geohash {location_geohashes[selected]}")
                    raise

                # Save the geohash and latitude and longitude of the location
                ADDON.setSetting(sys.argv[1] + 'BOM', locations[selected])
                ADDON.setSetting(sys.argv[1] + 'BOMGeoHash', location_geohashes[selected])
                ADDON.setSetting(sys.argv[1] + 'Lat', str(location_info['latitude']))
                ADDON.setSetting(sys.argv[1] + 'Lon', str(location_info['longitude']))
                # Use the lat, long to find the closest radar
                radar = closest_radar_to_lat_lon((location_info['latitude'], location_info['longitude']))
                Logger.info(f'Closest radar found: {radar}')
                ADDON.setSetting('Radar' + sys.argv[1][-1] + 'Lat', str(radar[0]))
                ADDON.setSetting('Radar' + sys.argv[1][-1] + 'Lon', str(radar[1]))
                ADDON.setSetting(sys.argv[1] + 'ClosestRadar', f'{radar[2]} - {radar[3]}')


###########################################################
# MAIN (only for unit testing outside Kodi)

if __name__ == "__main__":

    places_to_test = ['3032', 'ascot vale', 'MYRTLE BANK', 'no_results']
    for place in places_to_test:
        Logger.info(f'Testing location term "{place}"')
        get_bom_locations_for(place)
        Logger.info('')

"""
{
    "data": {
        "geohash": "r659gg5", 
        "has_wave": true, 
        "id": "Gosford-r659gg5", 
        "latitude": -33.42521667480469, 
        "longitude": 151.3414764404297, 
        "marine_area_id": "NSW_MW009", 
        "name": "Gosford", 
        "state": "NSW", 
        "tidal_point": "NSW_TP036", 
        "timezone": "Australia/Sydney"
    }, 
    "metadata": {
        "response_timestamp": "2021-04-28T04:50:20Z"
    }
}
"""
