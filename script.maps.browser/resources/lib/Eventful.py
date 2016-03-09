# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
import urllib

import Utils
import googlemaps
import re
EVENTFUL_KEY = 'Nw3rh3mXn8RhMQNK'
BASE_URL = "http://api.eventful.com/json/"


class Eventful():

    def __init__(self):
        pass

    def select_category(self):
        results = self.get_data(method="categories/list",
                                cache_days=7)
        modeselect = [Utils.LANG(32122)]
        modeselect += [Utils.cleanText(i["name"]) for i in results["category"]]
        index = xbmcgui.Dialog().select(Utils.LANG(32123), modeselect)
        if index == -1:
            return None
        if index > 0:
            return results["category"][index - 1]["id"]
        elif index == 0:
            return ""

    def get_events(self, lat="", lon="", query="", category="", radius=30):
        params = {"image_sizes": "large",
                  "include": "price",
                  "units": "km",
                  "page_size": 26,
                  "sort_order": "date",
                  "date": "Future",
                  "where": "%.8f,%.8f" % (lat, lon),
                  "within": max(int(radius), 5),
                  "query": query,
                  "category": category}
        results = self.get_data(method="events/search",
                                params=params,
                                cache_days=7)
        return self.handle_events(results['events']['event'])

    def get_venue_info(self, event_id=""):
        results = self.get_data(method="venues/get",
                                params={"id": event_id},
                                cache_days=7)
        if not results:
            return []
        return self.handle_events(results['venue'])

    def get_event_info(self, event_id=""):
        params = {"id": event_id,
                  "image_sizes": "blackborder500,edpborder500"}
        results = self.get_data(method="events/get",
                                params=params,
                                cache_days=7)
        if not results:
            return []
        return self.handle_events(results['event'])

    def handle_events(self, results):
        pins = ""
        places = []
        letter = ord('A')
        if not isinstance(results, list):
            results = [results]
        for i, venue in enumerate(results):
            venuename = Utils.cleanText(venue['venue_name'])
            lat = str(venue['latitude'])
            lon = str(venue['longitude'])
            googlemap = googlemaps.get_static_map(lat=lat,
                                                  lon=lon)
            photo = venue["image"]["large"]["url"] if venue.get("image") else ""
            if venue["start_time"] == venue["stop_time"] or not venue["stop_time"]:
                date = venue["start_time"]
            elif venue["start_time"][:10] == venue["stop_time"][:10]:
                date = venue["start_time"] + " - " + venue["stop_time"][:10]
                date = re.sub(r"\d{2}:\d{2}:\d{2}", "", date)
            else:
                date = venue["start_time"] + " - " + venue["stop_time"]
                date = re.sub(r"\d{2}:\d{2}:\d{2}", "", date)
            props = {"id": str(venue['id']),
                     "eventful_id": str(venue['venue_id']),
                     "eventname": Utils.cleanText(venue['title']),
                     "description": Utils.cleanText(venue['description']),
                     "name": venuename,
                     "label": venuename,
                     "label2": date.replace("00:00:00", ""),
                     "photo": photo,
                     "thumb": photo,
                     "date": date,
                     "address": Utils.cleanText(venue["venue_address"]),
                     "GoogleMap": googlemap,
                     "letter": chr(letter + i),
                     "lat": lat,
                     "lon": lon}
            pins += "&markers=color:blue%7Clabel:{0}%7C{1},{2}".format(chr(letter + i), lat, lon)
            places.append(props)
        return places, pins

    def get_data(self, method, params={}, cache_days=0.5):
        params["app_key"] = EVENTFUL_KEY
        # params = {k: v for k, v in params.items() if v}
        params = dict((k, v) for (k, v) in params.iteritems() if v)
        params = dict((k, unicode(v).encode('utf-8')) for (k, v) in params.iteritems())
        url = "{base_url}{method}?{params}".format(base_url=BASE_URL,
                                                   method=method,
                                                   params=urllib.urlencode(params))
        return Utils.get_JSON_response(url=url,
                                       cache_days=cache_days)
