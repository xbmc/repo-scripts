import sys
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import xbmc
import xbmcgui

# Small hack to allow for unit testing - see common.py for explanation
if not xbmc.getUserAgent():
    sys.path.insert(0, '../../..')

from resources.lib.store import Store
from resources.lib.common import *


def getLocationsForPostcodeOrSuburb(text):
    """
    Returns an array of dicts, each with a Location name and LocationUrlPart.  Empty if no location found.
    [{'LocationName': u'Ascot Vale, VIC 3032', 'LocationUrlPart': u'/vic/melbourne/ascot-vale'}, ... ]
    """

    locations = []
    location_url_paths = []

    try:
        r = requests.post(Store.WEATHERZONE_SEARCH_URL, data={'q': text, 't': '3'})
        soup = BeautifulSoup(r.text, 'html.parser')
        log("Result url: " + r.url)

    except Exception as inst:
        log("Exception loading locations results in weatherzone.getLocationsForPostcodeOrSuburb" + str(inst))
        raise

    # Two responses are possible.
    try:

        # 1. A list of possible locations to choose from (e.g. several suburbs sharing one postcode)
        if r.url.endswith(Store.WEATHERZONE_SEARCH_URL):
            location_ul = soup.find("ul", class_="typ2")

            # Results block missing? Short circuit
            if not location_ul:
                return locations, location_url_paths

            for location_li in location_ul.find_all("li"):
                location = location_li.find("a")
                locations.append(location.text)
                location_url_paths.append(location.get('href'))

        # 2. Straight to one location
        else:
            h1 = soup.find("h1", class_="local")
            name = h1.text.split(" Weather")[0]
            url = urlparse(r.url).path
            locations.append(name)
            location_url_paths.append(url)

    except Exception as inst:
        log("Exception processing locations in weatherzone.getLocationsForPostcodeOrSuburb" + str(inst))
        raise

    log(locations)
    log(location_url_paths)

    return locations, location_url_paths


def find_weatherzone_location():
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


###########################################################
# MAIN (only for unit testing outside of Kodi)

if __name__ == "__main__":

    places_to_test = ['3032', 'ascot vale', 'MYRTLE BANK', 'no_results']
    for place in places_to_test:
        log(f'Testing location term "{place}"')
        getLocationsForPostcodeOrSuburb(place)
        log('')
