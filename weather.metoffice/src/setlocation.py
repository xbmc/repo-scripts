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

from metoffice import urlcache, utilities
from metoffice.constants import (
    ADDON_DATA_PATH,
    FORECAST_SITELIST_URL,
    GEOIP_PROVIDER,
    GEOLOCATION,
    LONG_REGIONAL_NAMES,
    OBSERVATION_SITELIST_URL,
    REGIONAL_SITELIST_URL,
    addon,
    dialog,
)
from metoffice.utilities import gettext as _


@utilities.xbmcbusy
def getsitelist(location, text=""):
    with urlcache.URLCache(ADDON_DATA_PATH) as cache:
        url = {
            "ForecastLocation": FORECAST_SITELIST_URL,
            "ObservationLocation": OBSERVATION_SITELIST_URL,
            "RegionalLocation": REGIONAL_SITELIST_URL,
        }[location]
        utilities.log("Fetching %s site list from the Met Office..." % location)
        try:
            filename = cache.get(url, lambda x: datetime.now() + timedelta(weeks=1))
        except HTTPError:
            dialog().ok(
                _("Error fetching %s site list" % location),
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
        if location == "RegionalLocation":
            # fix datapoint bug where keys start with @ in Regional Sitelist
            # Fixing up keys has to be a two step process. If we pop and add
            # in the same loop we'll get `RuntimeError: dictionary keys
            # changed during iteration.`
            for site in sitelist:
                # First add the correct keys.
                toremove = []
                for key in site:
                    if key.startswith("@"):
                        toremove.append(key)
                # Now remove the keys we found above.
                for key in toremove:
                    site[key[1:]] = site.pop(key)

                # Change regional names to long versions. Untouched otherwise.
                site["name"] = LONG_REGIONAL_NAMES.get(site["name"], site["name"])
        if text:
            sitelist[:] = filter(
                lambda x: x["name"].lower().find(text.lower()) >= 0, sitelist
            )

        if GEOLOCATION == "true":
            geo = {}
            url = GEOIP_PROVIDER["url"]
            filename = cache.get(url, lambda x: datetime.now() + timedelta(hours=1))
            try:
                with open(filename) as fh:
                    data = json.load(fh)
            except ValueError:
                utilities.log("Failed to fetch valid data from %s" % url)
            try:
                geolat = float(data[GEOIP_PROVIDER["latitude"]])
                geolong = float(data[GEOIP_PROVIDER["longitude"]])
                geo = {"lat": geolat, "long": geolong}
            except KeyError:
                utilities.log("Couldn't extract lat/long data from %s" % url)

            for site in sitelist:
                try:
                    site["distance"] = int(
                        utilities.haversine_distance(
                            geo["lat"],
                            geo["long"],
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
    # In this case we _have_ to create a keyboard object so that
    # we can test isConfirmed and getText.
    keyboard = xbmc.Keyboard()
    keyboard.doModal()
    text = keyboard.isConfirmed() and keyboard.getText()

    sitelist = getsitelist(location, text)
    if sitelist == []:
        dialog().ok(
            _("No Matches"), _("No locations found containing") + " {0}".format(text)
        )
        utilities.log("No locations found containing '%s'" % text)
    else:
        display_list = [site["display"] for site in sitelist]
        selected = dialog().select(_("Matching Sites"), display_list)
        if selected != -1:
            addon().setSetting(location, sitelist[selected]["name"])
            addon().setSetting("%sID" % location, sitelist[selected]["id"])
            addon().setSetting(
                "%sLatitude" % location, str(sitelist[selected].get("latitude"))
            )
            addon().setSetting(
                "%sLongitude" % location, str(sitelist[selected].get("longitude"))
            )
            utilities.log(
                "Setting '{location}' to '{name} ({id})'".format(
                    location=location,
                    name=sitelist[selected]["name"].encode("utf-8"),
                    id=sitelist[selected]["id"],
                )
            )
