# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib

from kodi65 import utils
from kodi65 import ItemList
from kodi65 import VideoItem

# TVRAGE_KEY = 'VBp9BuIr5iOiBeWCFRMG'
API_KEY = 'xbmc_open_source_media_center'
BASE_URL = "http://api.bandsintown.com/events/search?format=json&api_version=2.0&app_id=%s&" % API_KEY


def handle_events(results):
    events = ItemList()
    for event in results:
        venue = event['venue']
        item = VideoItem(label=venue['name'])
        item.set_properties({'date': event['datetime'].replace("T", " - ").replace(":00", "", 1),
                             'city': venue['city'],
                             'lat': venue['latitude'],
                             'lon': venue['longitude'],
                             'id': venue['id'],
                             'url': venue['url'],
                             'region': venue['region'],
                             'country': venue['country'],
                             'artists': " / ".join([art for art in event["artists"]])})
        events.append(item)
    return events


def get_near_events(artists):  # not possible with api 2.0
    arts = [urllib.quote(art['artist'].encode("utf-8")) for art in artists[:50]]
    artist_str = 'artists[]=' + '&artists[]='.join(arts)
    url = BASE_URL + 'location=use_geoip&radius=50&per_page=100&%s' % (artist_str)
    results = utils.get_JSON_response(url, folder="BandsInTown")
    if results:
        return handle_events(results)
    return []
