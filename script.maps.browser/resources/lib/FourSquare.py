# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

# code for FourSquare Scraping based on script.maps by a.a.alsaleh. credits to him.

import xbmcgui
import xbmcaddon
import urllib
import Utils
import googlemaps

ADDON = xbmcaddon.Addon()
FOURSQUARE_ID = "OPLZAEBJAWPE5F4LW0QGHHSJDF0K3T5GVJAAICXUDHR11GPS"
FOURSQUARE_SECRET = "0PIG5HGE0LWD3Z5TDSE1JVDXGCVK4AJYHL50VYTJ2CFPVPAC"
BING_KEY = 'Ai8sLX5R44tf24_2CGmbxTYiIX6w826dsCVh36oBDyTmH21Y6CxYEqtrV9oYoM6O'
BASE_URL = "https://api.foursquare.com/v2/"


class FourSquare():

    def __init__(self):
        pass

    def handle_places(self, results):
        self.pins = ""
        places = list()
        letter = ord('A')
        for count, venue in enumerate(results):
            try:
                photo_node = venue['venue']['photos']['groups'][0]['items'][0]
                photo = photo_node['prefix'] + str(photo_node['height']) + photo_node['suffix']
            except:
                photo = ""
            if "name" not in venue:
                venue = venue["venue"]
            if venue['categories']:
                icon = venue['categories'][0]['icon']
                icon = icon['prefix'] + "88" + icon['suffix']
            else:
                icon = ""
            if 'formattedAddress' in venue['location']:
                formattedAddress = "[CR]".join(filter(None, venue['location']['formattedAddress']))
            lat = str(venue['location']['lat'])
            lon = str(venue['location']['lng'])
            googlemap = googlemaps.get_static_map(lat=lat,
                                                  lon=lon)
            props = {"id": str(venue['id']),
                     "foursquare_id": str(venue['id']),
                     "distance": str(venue['location']['distance']),
                     "visited": str(venue['stats']['usersCount']),
                     "twitter": venue['contact'].get('twitter', ""),
                     "eventname": venue['location']['address'],
                     "description": formattedAddress,
                     "name": venue['name'],
                     "label": venue['name'],
                     "label2": venue['name'],
                     "icon": icon,
                     "photo": photo,
                     "thumb": photo,
                     "Venue_Image": icon,
                     "GoogleMap": googlemap,
                     "letter": chr(letter + count),
                     "lat": lat,
                     "lon": lon,
                     "phone": venue['contact'].get('phone', ""),
                     "comments": str(venue['stats']['tipCount'])}
            self.pins = self.pins + "&markers=color:blue%7Clabel:" + chr(letter + count) + "%7C" + lat + "," + lon
            places.append(props)
        return places, self.pins

    def get_places(self, lat, lon, query="", category_id=""):
        params = {"limit": 26,
                  "ll": '%.8f,%.8f' % (lat, lon),
                  "query": query,
                  "categoryId": category_id}
        results = self.get_data(method="venues/search",
                                params=params,
                                cache_days=7)
        if results and 'meta' in results:
            if results['meta']['code'] == 200:
                return self.handle_places(results['response']['venues'])
            elif results['meta']['code'] == 400:
                Utils.notify("Error", "LIMIT EXCEEDED")
            else:
                Utils.notify("ERROR", "Could not get requested information")
        else:
            Utils.log("ERROR")
        return [], ""

    def get_places_by_section(self, lat, lon, placetype):
        params = {"venuePhotos": 1,
                  "ll": '%.8f,%.8f' % (float(lat), float(lon)),
                  "section": placetype}
        results = self.get_data(method="venues/explore",
                                params=params,
                                cache_days=7)
        if not results or 'meta' not in results:
            return [], ""
        if results['meta']['code'] == 200:
            if results['response']['groups'][0]['items']:
                return self.handle_places(results['response']['groups'][0]['items'])
            else:
                Utils.notify("Error", "No results found near the selected area.")
        elif results['meta']['code'] == 400:
            Utils.log("LIMIT EXCEEDED")
        else:
            Utils.log("ERROR" + str(results['meta']['code']))
        return [], ""

    def select_category(self):
        results = self.get_data(method="venues/categories",
                                cache_days=7)
        modeselect = [Utils.LANG(32122)]
        modeselect += [Utils.cleanText(item["name"]) for item in results["categories"]]
        index = xbmcgui.Dialog().select(Utils.LANG(32123), modeselect)
        if index > 0:
            return results["categories"][index - 1]["id"]
        elif index > -1:
            return ""

    def select_section(self):
        sections = {"topPicks": Utils.LANG(32005),
                    "food": Utils.LANG(32006),
                    "drinks": Utils.LANG(32007),
                    "coffee": Utils.LANG(32008),
                    "shops": Utils.LANG(32009),
                    "arts": Utils.LANG(32010),
                    "outdoors": Utils.LANG(32011),
                    "sights": Utils.LANG(32012),
                    "trending": Utils.LANG(32013),
                    "specials": Utils.LANG(32014),
                    "nextVenues": Utils.LANG(32015)}
        modeselect = [Utils.LANG(32120)]
        modeselect += [value for value in sections.itervalues()]
        index = xbmcgui.Dialog().select(Utils.LANG(32121), modeselect)
        if index > 0:
            return sections.keys()[index - 1]
        elif index > -1:
            return ""

    def get_data(self, method, params={}, cache_days=0.5):
        params["client_id"] = FOURSQUARE_ID
        params["client_secret"] = FOURSQUARE_SECRET
        params["v"] = 20130815
        # params = {k: v for k, v in params.items() if v}
        params = dict((k, v) for (k, v) in params.iteritems() if v)
        params = dict((k, unicode(v).encode('utf-8')) for (k, v) in params.iteritems())
        url = "{base_url}{method}?{params}".format(base_url=BASE_URL,
                                                   method=method,
                                                   params=urllib.urlencode(params))
        return Utils.get_JSON_response(url=url,
                                       cache_days=cache_days)
