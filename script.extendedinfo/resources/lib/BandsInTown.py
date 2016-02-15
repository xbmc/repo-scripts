# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
from Utils import *

# TVRAGE_KEY = 'VBp9BuIr5iOiBeWCFRMG'
API_KEY = 'xbmc_open_source_media_center'
BASE_URL = "http://api.bandsintown.com/events/search?format=json&api_version=2.0&app_id=%s&" % API_KEY


def handle_events(results):
    events = []
    for event in results:
        venue = event['venue']
        artists = ''
        for art in event["artists"]:
            artists = artists + ' / ' + art['name']
            artists = artists.replace(" / ", "", 1)
        events.append({'date': event['datetime'].replace("T", " - ").replace(":00", "", 1),
                       'city': venue['city'],
                       'lat': venue['latitude'],
                       'lon': venue['longitude'],
                       'id': venue['id'],
                       'url': venue['url'],
                       'name': venue['name'],
                       'region': venue['region'],
                       'country': venue['country'],
                       'artists': artists})
    return events


def get_near_events(artists):  # not possible with api 2.0
    arts = []
    for art in artists[:50]:
        try:
            arts.append(urllib.quote(art['artist']))
        except:
            arts.append(urllib.quote(art['artist'].encode("utf-8")))
    artist_str = 'artists[]=' + '&artists[]='.join(arts)
    url = BASE_URL + 'location=use_geoip&radius=50&per_page=100&%s' % (artist_str)
    results = get_JSON_response(url, folder="BandsInTown")
    if results:
        return handle_events(results)
    return []
