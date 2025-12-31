"""
Sets the forecast location by providing a keyboard prompt
to the user. The name entered by the user is searched in
site list. All matches are presented as a select list to
the user. On successful selection internal addon setting
is set.
"""

import json
from datetime import datetime, timedelta
from operator import itemgetter
from urllib.error import HTTPError

import xbmc
import xbmcaddon
import xbmcgui

from metoffice import urlcache, utilities
from metoffice.constants import (
    ADDON_DATA_PATH,
    ADDON_ID,
    API_KEY,
    FORECAST_SITELIST_URL,
    GEOIP_PROVIDERS,
    OBSERVATION_SITELIST_URL,
)
from metoffice.utilities import gettext as _

dialog = xbmcgui.Dialog()
addon = xbmcaddon.Addon(ADDON_ID)


def get_geolocation(provider: dict):
    # Fetch the data from the given provider.
    url = provider["url"]

    utilities.log("Fetching location from '%s'" % url)
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        filename = cache.get(url, lambda x: datetime.now() + timedelta(hours=1))
    with open(filename) as fh:
        data = json.load(fh)

    # Transform the data.
    # The "latitude" and "longitude" values are intended to provide
    # key translations for those proiders who have different key names.
    # Eg, "lat", "long", "lon" etc.
    geolat = float(data[provider["latitude"]])
    geolong = float(data[provider["longitude"]])
    return {"lat": geolat, "long": geolong}


@utilities.xbmcbusy
def getsitelist(location, text=""):
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        url = {
            "ForecastLocation": FORECAST_SITELIST_URL,
            "ObservationLocation": OBSERVATION_SITELIST_URL,
        }[location]
        utilities.log("Fetching %s site list from the Met Office..." % location)
        try:
            filename = cache.get(url, lambda x: datetime.now() + timedelta(weeks=1))
        except HTTPError:
            dialog.ok(
                _("Error fetching site list" % location),
                _("Check your Met Office API Key under settings and try again."),
            )
            utilities.log(
                "Error fetching %s site list. Check your API Key and try again"
                % location,
                xbmc.LOGERROR,
            )
            raise
        with open(filename, encoding="utf-8") as fh:
            data = json.load(fh)
        sitelist = data["Locations"]["Location"]
        if text:
            sitelist[:] = filter(
                lambda x: x["name"].lower().find(text.lower()) >= 0, sitelist
            )

        if addon.getSetting("GeoLocation") == "true":
            provider_id = int(addon.getSetting("GeoIPProvider"))
            provider = GEOIP_PROVIDERS[provider_id]
            location = get_geolocation(provider)

            for site in sitelist:
                try:
                    site["distance"] = int(
                        utilities.haversine_distance(
                            location["lat"],
                            location["long"],
                            float(site["latitude"]),
                            float(site["longitude"]),
                        )
                    )
                    site["display"] = "{0} ({1}km)".format(
                        site["name"], site["distance"]
                    )
                except KeyError:
                    site["display"] = site["name"]
            try:
                sitelist = sorted(sitelist, key=itemgetter("distance"))
            except KeyError:
                sitelist = sorted(sitelist, key=itemgetter("name"))
        else:
            for site in sitelist:
                site["display"] = site["name"]
            sitelist = sorted(sitelist, key=itemgetter("name"))
        return sitelist


def main(location):
    # We assume that the invocation was from settings configuration, so
    # we don't have to check if it's acceptable to show a dialog; the user
    # is engaged in this content.
    if not API_KEY:
        dialog.ok(
            "No API Key",
            "Please register for an API Key at https://register.metoffice.gov.uk. Then save your API Key under addon settings.",
        )
        return
    # In this case we _have_ to create a keyboard object so that
    # we can test isConfirmed and getText.
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    text = keyboard.isConfirmed() and keyboard.getText()

    sitelist = getsitelist(location, text)
    if sitelist == []:
        dialog.ok(
            _("No Matches"), _("No locations found containing") + " '{0}'".format(text)
        )
        utilities.log("No locations found containing '%s'" % text)
    else:
        display_list = [site["display"] for site in sitelist]
        selected = dialog.select(_("Matching Sites"), display_list)
        if selected != -1:
            addon.setSetting(location, sitelist[selected]["name"])
            addon.setSetting("%sID" % location, sitelist[selected]["id"])
            addon.setSetting(
                "%sLatitude" % location, str(sitelist[selected].get("latitude"))
            )
            addon.setSetting(
                "%sLongitude" % location, str(sitelist[selected].get("longitude"))
            )
            utilities.log(
                "Setting '{location}' to '{name} ({id})'".format(
                    location=location,
                    name=sitelist[selected]["name"].encode("utf-8"),
                    id=sitelist[selected]["id"],
                )
            )
