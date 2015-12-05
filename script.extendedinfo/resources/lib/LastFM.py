# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
from Utils import *

LAST_FM_API_KEY = 'd942dd5ca4c9ee5bd821df58cf8130d4'
GOOGLE_MAPS_KEY = 'AIzaSyBESfDvQgWtWLkNiOYXdrA9aU-2hv_eprY'
BASE_URL = 'http://ws.audioscrobbler.com/2.0/?api_key=%s&format=json&' % (LAST_FM_API_KEY)


def handle_lastfm_events(results):
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
            if event['venue']['location']['geo:point']['geo:long']:
                lon = event['venue']['location']['geo:point']['geo:long']
                lat = event['venue']['location']['geo:point']['geo:lat']
                search_str = lat + "," + lon
            elif event['venue']['location']['street']:
                search_str = url_quote(event['venue']['location']['city'] + " " + event['venue']['location']['street'])
            elif event['venue']['location']['city']:
                search_str = url_quote(event['venue']['location']['city'] + " " + event['venue']['name'])
            else:
                search_str = url_quote(event['venue']['name'])
        except:
            search_str = ""
        if xbmc.getCondVisibility("System.HasAddon(script.maps.browser)"):
            builtin = 'RunScript(script.maps.browser,info=eventinfo,id=%s)' % (str(event['id']))
        else:
            builtin = "Notification(Please install script.maps.browser)"
        googlemap = 'http://maps.googleapis.com/maps/api/staticmap?&sensor=false&scale=2&maptype=roadmap&center=%s&zoom=13&markers=%s&size=640x640&key=%s' % (search_str, search_str, GOOGLE_MAPS_KEY)
        event = {'date': event['startDate'][:-3],
                 'name': event['venue']['name'],
                 'id': event['venue']['id'],
                 'venue_id': event['venue']['id'],
                 'event_id': event['id'],
                 'street': event['venue']['location']['street'],
                 'eventname': event['title'],
                 'website': event['website'],
                 'description': clean_text(event['description']),
                 'postalcode': event['venue']['location']['postalcode'],
                 'city': event['venue']['location']['city'],
                 'country': event['venue']['location']['country'],
                 'lat': event['venue']['location']['geo:point']['geo:lat'],
                 'lon': event['venue']['location']['geo:point']['geo:long'],
                 'artists': my_arts,
                 'googlemap': googlemap,
                 'path': "plugin://script.extendedinfo/?info=action&&id=" + builtin,
                 'artist_image': event['image'][-1]['#text'],
                 'thumb': event['image'][-1]['#text'],
                 'venue_image': event['venue']['image'][-1]['#text'],
                 'headliner': event['artists']['headliner']}
        events.append(event)
    return events


def handle_lastfm_albums(results):
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
    else:
        log("No Info in JSON answer:")
        prettyprint(results)
    return albums


def handle_lastfm_shouts(results):
    shouts = []
    if not results:
        return []
    for shout in results['shouts']['shout']:
        newshout = {'comment': shout['body'],
                    'author': shout['author'],
                    'date': shout['date'][4:]}
        shouts.append(newshout)
    return shouts


def handle_lastfm_tracks(results):
    if not results:
        return {}
    if "wiki" in results['track']:
        summary = clean_text(results['track']['wiki']['summary'])
    else:
        summary = ""
    TrackInfo = {'playcount': str(results['track']['playcount']),
                 'thumb': str(results['track']['playcount']),
                 'summary': summary}
    return TrackInfo


def handle_lastfm_artists(results):
    artists = []
    if not results:
        return []
    for artist in results['artist']:
        try:
            if 'name' in artist:
                listeners = int(artist.get('listeners', 0))
                artist = {'title': artist['name'],
                          'name': artist['name'],
                          'mbid': artist['mbid'],
                          'thumb': artist['image'][-1]['#text'],
                          'Listeners': format(listeners, ",d")}
                artists.append(artist)
        except:
            prettyprint(artist)
    return artists


def get_events(id, past_events=False):
    if past_events:
        url = 'method=Artist.getPastEvents&mbid=%s' % (id)
    else:
        url = 'method=Artist.getEvents&mbid=%s' % (id)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=1,
                                folder="LastFM")
    return handle_lastfm_events(results)


def get_artist_podcast(artist):  # todo
    results = get_JSON_response(url=BASE_URL + "method=Artist.getPodcast&limit=100",
                                folder="LastFM")
    return handle_lastfm_artists(results['artists'])


def get_hyped_artists():
    results = get_JSON_response(url=BASE_URL + "method=Chart.getHypedArtists&limit=100",
                                folder="LastFM")
    return handle_lastfm_artists(results['artists'])


def get_top_artists():
    results = get_JSON_response(url=BASE_URL + "method=Chart.getTopArtists&limit=100",
                                folder="LastFM")
    return handle_lastfm_artists(results['artists'])


def get_album_shouts(artist_name, album_title):
    url = 'method=Album.getShouts&artist=%s&album=%s' % (url_quote(artist_name), url_quote(album_title))
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_shouts(results)


def get_artist_shouts(artist_name):
    url = 'method=Artist.GetShouts&artist=%s' % (url_quote(artist_name))
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_shouts(results)


def get_artist_images(artist_mbid):
    url = 'method=Artist.getImages&mbid=%s' % (artist_mbid)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0,
                                folder="LastFM")
    return handle_lastfm_events(results)


def get_track_shouts(artist_name, track_title):
    url = 'method=Track.getShouts&artist=%s&track=%s' % (url_quote(artist_name), url_quote(track_title))
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_shouts(results)


def get_event_shouts(event_id):
    url = 'method=event.GetShouts&event=%s' % (event_id)
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_shouts(results)


def get_venue_id(venue_name=""):
    url = '&method=Venue.search&venue=%s' % (url_quote(venue_name))
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    if "results" in results:
        matches = results["results"]["matches"]
        if "venue" in matches and matches["venue"]:
            if isinstance(matches["venue"], list):
                return matches["venue"][0]["id"]
            else:
                return matches["venue"]["id"]
    return []


def get_artist_albums(artist_mbid):
    url = 'method=Artist.getTopAlbums&mbid=%s' % (artist_mbid)
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_albums(results)


def get_similar_artists(artist_mbid):
    url = 'method=Artist.getSimilar&mbid=%s&limit=400' % (artist_mbid)
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    if results is not None and "similarartists" in results:
        return handle_lastfm_artists(results['similarartists'])


def get_near_events(tag=False, festivals_only=False, lat="", lon="", location="", distance=""):
    if festivals_only:
        festivals_only = "1"
    else:
        festivals_only = "0"
    url = 'method=geo.getEvents&festivalsonly=%s&limit=40' % (festivals_only)
    if tag:
        url += '&tag=%s' % (url_quote(tag))
    if lat and lon:
        url += '&lat=%s&long=%s' % (str(lat), str(lon))  # &distance=60
    if location:
        url += '&location=%s' % (url_quote(location))
    if distance:
        url += '&distance=%s' % (distance)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0.5,
                                folder="LastFM")
    return handle_lastfm_events(results)


def get_venue_events(venueid=""):
    url = 'method=Venue.getEvents&venue=%s' % (venueid)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0.5,
                                folder="LastFM")
    return handle_lastfm_events(results)


def get_track_info(artist="", track=""):
    url = 'method=track.getInfo&artist=%s&track=%s' % (url_quote(artist), url_quote(track))
    results = get_JSON_response(url=BASE_URL + url,
                                folder="LastFM")
    return handle_lastfm_tracks(results)
