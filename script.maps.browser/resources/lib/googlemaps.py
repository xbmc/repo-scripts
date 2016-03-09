# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import xbmc
import xbmcaddon
import Utils
from SearchSelectDialog import SearchSelectDialog


GOOGLEMAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
GOOGLE_STREETVIEW_KEY = 'AIzaSyCo31ElCssn5GfH2eHXHABR3zu0XiALCc4'

BASE_URL = "http://maps.googleapis.com/maps/api/"

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')


def get_static_map(lat=None, lon=None, location="", scale=2, zoom=13, maptype="roadmap", size="640x640"):
    if lat and lon:
        location = "%s,%s" % (lat, lon)
    params = {"sensor": "false",
              "scale": scale,
              "maptype": maptype,
              "format": ADDON.getSetting("ImageFormat"),
              "language": xbmc.getLanguage(xbmc.ISO_639_1),
              "center": location.replace('"', ''),
              "zoom": zoom,
              "markers": location.replace('"', ''),
              "size": size,
              "key": GOOGLEMAPS_KEY}
    return BASE_URL + 'staticmap?' + urllib.urlencode(params)


def get_streetview_image(lat=None, lon=None, fov=0, location="", heading=0, pitch=0, size="640x400"):
    params = {"sensor": "false",
              "format": ADDON.getSetting("ImageFormat"),
              "language": xbmc.getLanguage(xbmc.ISO_639_1),
              "fov": fov,
              "location": "%s,%s" % (lat, lon) if lat and lon else location.replace('"', ''),
              "heading": heading,
              "pitch": pitch,
              "size": size,
              "key": GOOGLE_STREETVIEW_KEY}
    return BASE_URL + "streetview?&" + urllib.urlencode(params)


def get_coords_by_location(show_dialog, search_string):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json?&sensor=false"
    url = "&address=%s" % (urllib.quote_plus(search_string))
    results = Utils.get_JSON_response(base_url + url)
    if not results or not results.get("results"):
        return None
    first_match = results["results"][0]["geometry"]["location"]
    if show_dialog and len(results["results"]) > 1:
        places = []
        for item in results["results"]:
            location = item["geometry"]["location"]
            googlemap = get_static_map(lat=location["lat"],
                                       lon=location["lng"],
                                       scale=1,
                                       size="320x320")
            places.append({'label': item['formatted_address'],
                           'lat': location["lat"],
                           'lon': location["lng"],
                           'thumb': googlemap,
                           'id': item['formatted_address']})
        w = SearchSelectDialog('DialogSelect.xml',
                               ADDON_PATH,
                               listing=Utils.create_listitems(places))
        w.doModal()
        if w.lat:
            return (float(w.lat), float(w.lon), 12)
    elif results["results"]:
        return (first_match["lat"], first_match["lng"], 12)  # no window when only 1 result
    return (self.lat, self.lon)  # old values when no hit
