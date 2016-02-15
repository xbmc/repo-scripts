# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
from Utils import *

LAST_FM_API_KEY = 'd942dd5ca4c9ee5bd821df58cf8130d4'
GOOGLE_MAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?api_key=%s&format=json&' % (LAST_FM_API_KEY)


def handle_events(results):
    events = []
    if not results:
        return []
    if "error" in results:
        notify("Error", results["message"])
        return []
    if "@attr" not in results["events"]:
        return []
    if not isinstance(results['events']['event'], list):
        results['events']['event'] = [results['events']['event']]
    for event in results['events']['event']:
        artists = event['artists']['artist']
        if isinstance(artists, list):
            my_arts = ' / '.join(artists)
        else:
            my_arts = artists
        try:
            location = event['venue']['location']
            if location['geo:point']['geo:long']:
                search_str = location['geo:point']['geo:lat'] + "," + location['geo:point']['geo:long']
            elif location['street']:
                search_str = location['city'] + " " + location['street']
            elif location['city']:
                search_str = location['city'] + " " + event['venue']['name']
            else:
                search_str = event['venue']['name']
        except:
            search_str = ""
        if xbmc.getCondVisibility("System.HasAddon(script.maps.browser)"):
            builtin = 'RunScript(script.maps.browser,info=eventinfo,id=%s)' % (event['id'])
        else:
            builtin = "Notification(Please install script.maps.browser)"
        params = {"sensor": "false",
                  "scale": 2,
                  "maptype": "roadmap",
                  "center": search_str,
                  "zoom": 13,
                  "markers": search_str,
                  "size": "640x640",
                  "key": GOOGLE_MAPS_KEY}
        map_url = 'http://maps.googleapis.com/maps/api/staticmap?&%s' % (urllib.urlencode(params))
        event = {'date': event['startDate'][:-3],
                 'name': event['venue']['name'],
                 'id': event['venue']['id'],
                 'venue_id': event['venue']['id'],
                 'event_id': event['id'],
                 'street': location['street'],
                 'eventname': event['title'],
                 'website': event['website'],
                 'description': clean_text(event['description']),
                 'postalcode': location['postalcode'],
                 'city': location['city'],
                 'country': location['country'],
                 'lat': location['geo:point']['geo:lat'],
                 'lon': location['geo:point']['geo:long'],
                 'artists': my_arts,
                 'googlemap': map_url,
                 'path': "plugin://script.extendedinfo/?info=action&&id=" + builtin,
                 'artist_image': event['image'][-1]['#text'],
                 'thumb': event['image'][-1]['#text'],
                 'venue_image': event['venue']['image'][-1]['#text'],
                 'headliner': event['artists']['headliner']}
        events.append(event)
    return events


def handle_albums(results):
    albums = []
    if not results:
        return []
    if 'topalbums' in results and "album" in results['topalbums']:
        for album in results['topalbums']['album']:
            album = {'artist': album['artist']['name'],
                     'mbid': album.get('mbid', ""),
                     'thumb': album['image'][-1]['#text'],
                     'name': album['name']}
            albums.append(album)
    return albums


def handle_shouts(results):
    shouts = []
    if not results:
        return []
    for item in results['shouts']['shout']:
        shout = {'comment': item['body'],
                 'author': item['author'],
                 'date': item['date'][4:]}
        shouts.append(shout)
    return shouts


def handle_artists(results):
    artists = []
    if not results:
        return []
    for artist in results['artist']:
        if 'name' not in artist:
            continue
        artist = {'title': artist['name'],
                  'name': artist['name'],
                  'mbid': artist['mbid'],
                  'thumb': artist['image'][-1]['#text'],
                  'Listeners': format(int(artist.get('listeners', 0)), ",d")}
        artists.append(artist)
    return artists


def get_events(mbid, past_events=False):
    if not mbid:
        return []
    if past_events:
        method = "Artist.getPastEvents"
    else:
        method = "Artist.getEvents"
    results = get_data(method=method,
                       params={"mbid": mbid},
                       cache_days=1)
    return handle_events(results)


def get_artist_podcast(artist):  # todo
    results = get_data(method="Artist.getPodcast",
                       params={"limit": "100"})
    return handle_artists(results['artists'])


def get_hyped_artists():
    results = get_data(method="Chart.getHypedArtists",
                       params={"limit": "100"})
    return handle_artists(results['artists'])


def get_top_artists():
    results = get_data(method="Chart.getTopArtists",
                       params={"limit": "100"})
    return handle_artists(results['artists'])


def get_album_shouts(artist_name, album_title):
    if not artist_name or not album_title:
        return []
    params = {"artist": artist_name,
              "album": album_title}
    results = get_data(method="Album.getShouts", params=params)
    return handle_shouts(results)


def get_artist_shouts(artist_name):
    if not artist_name:
        return []
    results = get_data(method="Artist.GetShouts",
                       params={"artist": artist_name})
    return handle_shouts(results)


def get_artist_images(artist_mbid):
    if not artist_mbid:
        return []
    results = get_data(method="Artist.getImages",
                       params={"mbid": artist_mbid},
                       cache_days=5)
    return handle_events(results)


def get_track_shouts(artist_name, track_title):
    if not artist_name or not track_title:
        return []
    params = {"artist": artist_name,
              "track": track_title}
    results = get_data(method="Track.getShouts", params=params)
    return handle_shouts(results)


def get_event_shouts(event_id):
    if not event_id:
        return []
    results = get_data(method="event.GetShouts",
                       params={"event": event_id})
    return handle_shouts(results)


def get_venue_id(venue_name=""):
    if not venue_name:
        return []
    results = get_data(method="Venue.search",
                       params={"venue": venue_name})
    if "results" in results:
        matches = results["results"]["matches"]
        if "venue" in matches and matches["venue"]:
            if isinstance(matches["venue"], list):
                return matches["venue"][0]["id"]
            else:
                return matches["venue"]["id"]
    return []


def get_artist_albums(artist_mbid):
    if not artist_mbid:
        return []
    results = get_data(method="Artist.getTopAlbums",
                       params={"mbid": artist_mbid})
    return handle_albums(results)


def get_similar_artists(artist_mbid):
    if not artist_mbid:
        return []
    params = {"mbid": artist_mbid,
              "limit": "400"}
    results = get_data(method="Artist.getSimilar", params=params)
    if results and "similarartists" in results:
        return handle_artists(results['similarartists'])


def get_near_events(tag=False, festivals_only=False, lat="", lon="", location="", distance=""):
    if not location and not lat:
        return []
    params = {"festivalsonly": int(bool(festivals_only)),
              "limit": "40",
              "tag": tag,
              "lat": lat,
              "long": lon,
              "location": location,
              "distance": distance}
    results = get_data(method="geo.getEvents", params=params)
    return handle_events(results)


def get_venue_events(venue_id=""):
    if not venue_id:
        return []
    results = get_data(method="Venue.getEvents",
                       params={"venue": venue_id})
    return handle_events(results)


def get_track_info(artist_name="", track=""):
    if not artist_name or not track:
        return []
    params = {"artist": artist_name,
              "track": track_title}
    results = get_data(method="track.getInfo", params=params)
    if not results:
        return {}
    if "wiki" in results['track']:
        summary = clean_text(results['track']['wiki']['summary'])
    else:
        summary = ""
    track_info = {'playcount': str(results['track']['playcount']),
                  'thumb': str(results['track']['playcount']),
                  'summary': summary}
    return track_info


def get_data(method, params={}, cache_days=0.5):
    params["method"] = method
    # params = {k: v for k, v in params.items() if v}
    params = dict((k, v) for (k, v) in params.iteritems() if v)
    params = dict((k, unicode(v).encode('utf-8')) for (k, v) in params.iteritems())
    url = "{base_url}{params}".format(base_url=BASE_URL,
                                      params=urllib.urlencode(params))
    return get_JSON_response(url=url,
                             cache_days=cache_days,
                             folder="LastFM")
