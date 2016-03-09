# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import Utils
import googlemaps

MAPQUEST_KEY = "lACkugtJjBp3lSA1ajvP05Sb6SikjNAW"
MAX_LIMIT = 25
BASE_URL = 'http://www.mapquestapi.com/traffic/v2/'

incident_types = {1: "Construction",
                  2: "Event",
                  3: "Congestion / Flow",
                  4: "Incident / Accident"}


def get_incidents(lat, lon, zoom):
    lat_high, lon_high, lat_low, lon_low = Utils.get_bounding_box(lat, lon, zoom)
    params = {"key": MAPQUEST_KEY,
              "inFormat": "kvp",
              "boundingBox": "%s,%s,%s,%s" % (lat_high, lon_high, lat_low, lon_low)}
    url = BASE_URL + 'incidents?' + urllib.urlencode(params)
    results = Utils.get_JSON_response(url)
    places = []
    pins = ""
    letter = ord('A')
    if results['info']['statuscode'] == 400:
        Utils.notify("Error", " - ".join(results['info']['messages']), time=10000)
        return [], ""
    elif "incidents" not in results:
        Utils.notify("Error", "Could not fetch results")
        return [], ""
    for i, place in enumerate(results['incidents']):
        lat = str(place['lat'])
        lon = str(place['lng'])
        params = {"key": MAPQUEST_KEY,
                  "mapLat": place['lat'],
                  "mapLng": place['lng'],
                  "mapHeight": 400,
                  "mapWidth": 400,
                  "mapScale": 433342}
        url = BASE_URL + "flow?" + urllib.urlencode(params)
        googlemap = googlemaps.get_static_map(lat=lat,
                                              lon=lon)
        props = {'name': place['shortDesc'],
                 'label': place['shortDesc'],
                 'label2': place['startTime'],
                 'description': place['fullDesc'],
                 'distance': str(place['distance']),
                 'delaytypical': str(place['delayFromTypical']),
                 'delayfreeflow': str(place['delayFromFreeFlow']),
                 "GoogleMap": googlemap,
                 "venue_image": url,
                 "thumb": url,
                 "icon": place['iconURL'],
                 'date': place['startTime'],
                 'severity': str(place['severity']),
                 'type': incident_types.get(place['type'], ""),
                 "letter": chr(letter + i),
                 "lat": lat,
                 "lon": lon}
        pins += "&markers=color:blue%7Clabel:{0}%7C{1},{2}".format(chr(letter + i), lat, lon)
        places.append(props)
        if i > MAX_LIMIT:
            break
    box_params = ["&path=color:0x00000000",
                  "weight:5",
                  "fillcolor:0xFFFF0033",
                  "%s,%s" % (lat_high, lon_high),
                  "%s,%s" % (lat_high, lon_low),
                  "%s,%s" % (lat_low, lon_low),
                  "%s,%s" % (lat_low, lon_high)]
    pins = pins + "%7C".join(box_params)
    return places, pins
