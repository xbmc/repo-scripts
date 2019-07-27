#!/usr/bin/python

########################

import xbmc
import xbmcgui

from time import gmtime, strftime
from resources.lib.json_map import *
from resources.lib.helper import *

########################

def append_items(li, json_query, type, searchstring=False, append=True):

    for item in json_query:
        if type == 'movie':
            parse_movies(li, item, searchstring, append)
        elif type ==  'tvshow':
            parse_tvshows(li, item, searchstring, append)
        elif type == 'season':
            parse_seasons(li, item, append)
        elif type == 'episode':
            parse_episodes(li, item, append)
        elif type == 'genre':
            parse_genre(li, item, append)
        elif type == 'cast':
            parse_cast(li, item, append)


def get_cast(castData):
    listcast = []
    listcastandrole = []
    for castmember in castData:
        listcast.append(castmember['name'])
        listcastandrole.append((castmember['name'], castmember['role']))

    return [listcast, listcastandrole]


def get_first_item(item):
    if len(item) > 0:
        item = item[0]
    else:
        item = ''

    return item


def get_joined_items(item):
    if len(item) > 0:
        item = ' / '.join(item)
    else:
        item = ''

    return item


def get_unwatched(episode,watchedepisodes):
    if episode > watchedepisodes:
        unwatchedepisodes = episode - watchedepisodes
        return unwatchedepisodes
    else:
        return 0


def _set_unique_properties(li_item,item,prop):
    try:
        i = 0
        for value in item:
            li_item.setProperty('%s.%s' % (prop,i), value)
            i += 1
    except Exception:
        pass

    return li_item


def _set_ratings(li_item,item,properties=False):
    for key in item:
        try:
            rating = item[key]['rating']
            votes = item[key]['votes'] or 0
            default = True if key == 'default' or len(item) == 1 else False

            ''' Kodi only supports floats up to 10.0. But Rotten Tomatoes is using 0-100.
                To get the values correctly set it's required to transform the value.
            '''
            if rating > 100:
                raise Exception
            elif rating > 10:
                rating = rating / 10

            li_item.setRating(key, float(rating), votes, default)

        except Exception:
            pass

    return li_item


def parse_movies(li, item, searchstring=False, append=False):

    if 'cast' in item:
        cast = get_cast(item['cast'])

    genre = item.get('genre', '')
    studio = item.get('studio', '')
    country = item.get('country', '')
    director = item.get('director', '')
    writer = item.get('writer', '')

    li_item = xbmcgui.ListItem(item['title'])
    li_item.setInfo(type='Video', infoLabels={'title': item['title'],
                                            'originaltitle': item['originaltitle'],
                                            'sorttitle': item['sorttitle'],
                                            'year': item['year'],
                                            'genre': get_joined_items(genre),
                                            'studio': get_joined_items(studio),
                                            'country': get_joined_items(country),
                                            'director': get_joined_items(director),
                                            'writer': get_joined_items(writer),
                                            'plot': item['plot'],
                                            'plotoutline': item['plotoutline'],
                                            'dbid': item['movieid'],
                                            'imdbnumber': item['imdbnumber'],
                                            'tagline': item['tagline'],
                                            'rating': str(float(item['rating'])),
                                            'userrating': str(float(item['userrating'])),
                                            'votes': item['votes'],
                                            'mpaa': item['mpaa'],
                                            'lastplayed': item['lastplayed'],
                                            'cast': cast[0],
                                            'castandrole': cast[1],
                                            'mediatype': 'movie',
                                            'trailer': item['trailer'],
                                            'dateadded': item['dateadded'],
                                            'path': item['file'],
                                            'playcount': item['playcount']})

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,genre,'genre')
    _set_unique_properties(li_item,studio,'studio')
    _set_unique_properties(li_item,country,'country')
    _set_unique_properties(li_item,director,'director')
    _set_unique_properties(li_item,writer,'writer')
    _set_unique_properties(li_item,cast[0],'cast')

    li_item.setProperty('resumetime', str(item['resume']['position']))
    li_item.setProperty('totaltime', str(item['resume']['total']))

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png'})

    hasVideo = False

    for key, value in iter(item['streamdetails'].items()):
        for stream in value:
            if 'video' in key:
                hasVideo = True
            li_item.addStreamInfo(key, stream)

    if not hasVideo: # if duration wasnt in the streaminfo try adding the scraped one
        stream = {'duration': item['runtime']}
        li_item.addStreamInfo('video', stream)

    if searchstring:
        li_item.setProperty('searchstring', searchstring)

    if append:
        li.append((item['file'], li_item, False))


def parse_tvshows(li, item, searchstring=False, append=False):

    if 'cast' in item:
        cast = get_cast(item['cast'])

    genre = item.get('genre', '')
    studio = item.get('studio', '')

    dbid = item['tvshowid']
    season = item['season']
    episode = item['episode']
    watchedepisodes = item['watchedepisodes']
    unwatchedepisodes = get_unwatched(episode,watchedepisodes)

    if not visible('Window.IsVisible(movieinformation)'):
        folder = True
        item['file'] = 'videodb://tvshows/titles/%s/' % dbid
    else:
        folder = False
        item['file'] = 'plugin://script.embuary.helper/?action=folderjump&type=tvshow&dbid=%s' % dbid

    li_item = xbmcgui.ListItem(item['title'])
    li_item.setInfo(type='Video', infoLabels={'title': item['title'],
                                            'year': item['year'],
                                            'tvshowtitle': item['title'],
                                            'sorttitle': item['sorttitle'],
                                            'originaltitle': item['originaltitle'],
                                            'genre': get_joined_items(genre),
                                            'studio': get_joined_items(studio),
                                            'plot': item['plot'],
                                            'rating': str(float(item['rating'])),
                                            'userrating': str(float(item['userrating'])),
                                            'votes': item['votes'],
                                            'premiered': item['premiered'],
                                            'mpaa': item['mpaa'],
                                            'cast': cast[0],
                                            'castandrole': cast[1],
                                            'mediatype': 'tvshow',
                                            'dbid': dbid,
                                            'season': season,
                                            'episode': episode,
                                            'imdbnumber': item['imdbnumber'],
                                            'lastplayed': item['lastplayed'],
                                            'path': item['file'],
                                            'duration': item['runtime'],
                                            'dateadded': item['dateadded'],
                                            'playcount': item['playcount']})

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,genre,'genre')
    _set_unique_properties(li_item,studio,'studio')
    _set_unique_properties(li_item,cast[0],'cast')

    li_item.setProperty('Totalseasons', str(season))
    li_item.setProperty('Totalepisodes', str(episode))
    li_item.setProperty('Watchedepisodes', str(watchedepisodes))
    li_item.setProperty('Unwatchedepisodes', str(unwatchedepisodes))

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png'})

    if searchstring:
        li_item.setProperty('searchstring', searchstring)

    if append:
        li.append((item['file'], li_item, folder))


def parse_seasons(li, item, append=False):

    tvshowdbid = item['tvshowid']
    season = item['season']
    episode = item['episode']
    watchedepisodes = item['watchedepisodes']
    unwatchedepisodes = get_unwatched(episode,watchedepisodes)

    if season == 0:
        title = '%s' % (xbmc.getLocalizedString(20381))
        special = 'true'
    else:
        title = '%s %s' % (xbmc.getLocalizedString(20373), season)
        special = 'false'

    if not visible('Window.IsVisible(movieinformation)'):
        folder = True
        file = 'videodb://tvshows/titles/%s/%s/' % (tvshowdbid, season)
    else:
        folder = False
        file = 'plugin://script.embuary.helper/?action=folderjump&type=season&dbid=%s&season=%s' % (tvshowdbid, season)

    li_item = xbmcgui.ListItem(title)
    li_item.setInfo(type='Video', infoLabels={'title': title,
                                            'season': season,
                                            'episode': episode,
                                            'tvshowtitle': item['showtitle'],
                                            'playcount': item['playcount'],
                                            'mediatype': 'season',
                                            'dbid': item['seasonid']})
    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png', 'fanart': item['art'].get('tvshow.fanart', '')})
    li_item.setProperty('Watchedepisodes', str(watchedepisodes))
    li_item.setProperty('Unwatchedepisodes', str(unwatchedepisodes))
    li_item.setProperty('IsSpecial', special)

    if append:
        li.append((file, li_item, folder))


def parse_episodes(li, item, append=False):

    if 'cast' in item:
        cast = get_cast(item['cast'])

    director = item.get('director', '')
    writer = item.get('writer', '')

    li_item = xbmcgui.ListItem(item['title'])
    li_item.setInfo(type='Video', infoLabels={'title': item['title'],
                                            'episode': item['episode'],
                                            'season': item['season'],
                                            'premiered': item['firstaired'],
                                            'dbid': item['episodeid'],
                                            'plot': item['plot'],
                                            'tvshowtitle': item['showtitle'],
                                            'originaltitle': item['originaltitle'],
                                            'lastplayed': item['lastplayed'],
                                            'rating': str(float(item['rating'])),
                                            'userrating': str(float(item['userrating'])),
                                            'votes': item['votes'],
                                            'playcount': item['playcount'],
                                            'director': get_joined_items(director),
                                            'writer': get_joined_items(writer),
                                            'cast': cast[0],
                                            'path': item['file'],
                                            'dateadded': item['dateadded'],
                                            'castandrole': cast[1],
                                            'mediatype': 'episode'})

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,director,'director')
    _set_unique_properties(li_item,writer,'writer')
    _set_unique_properties(li_item,cast[0],'cast')

    li_item.setProperty('resumetime', str(item['resume']['position']))
    li_item.setProperty('totaltime', str(item['resume']['total']))

    li_item.setArt({'icon': 'DefaultTVShows.png', 'fanart': item['art'].get('tvshow.fanart', ''), 'clearlogo': item['art'].get('tvshow.clearlogo', ''), 'landscape': item['art'].get('tvshow.landscape', ''), 'clearart': item['art'].get('tvshow.clearart', '')})
    li_item.setArt(item['art'])

    hasVideo = False

    for key, value in iter(item['streamdetails'].items()):
        for stream in value:
            if 'video' in key:
                hasVideo = True
            li_item.addStreamInfo(key, stream)

    if not hasVideo: # if duration wasnt in the streaminfo try adding the scraped one
        stream = {'duration': item['runtime']}
        li_item.addStreamInfo('video', stream)

    if item['season'] == '0':
        li_item.setProperty('IsSpecial', 'true')

    if append:
        li.append((item['file'], li_item, False))


def parse_cast(li,item,append=False):

    li_item = xbmcgui.ListItem(item['name'])
    li_item.setLabel(item['name'])
    li_item.setLabel2(item['role'])
    li_item.setArt({'icon': 'DefaultActor.png', 'thumb': item.get('thumbnail', '')})

    if append:
        li.append(('', li_item, False))


def parse_genre(li,item,append=False):

    li_item = xbmcgui.ListItem(item['label'])
    li_item.setInfo(type='Video', infoLabels={'title': item['label'],
                                            'dbid': str(item['genreid']),
                                            'path': item['file']})
    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultGenre.png'})

    if append:
        li.append((item['file'], li_item, True))
