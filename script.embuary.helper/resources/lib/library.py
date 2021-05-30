#!/usr/bin/python

########################

import xbmc
import xbmcgui

from time import gmtime, strftime
from resources.lib.json_map import *
from resources.lib.helper import *

########################

def add_items(li,json_query,type,searchstring=None):
    for item in json_query:
        if type == 'movie':
            handle_movies(li, item, searchstring)
        elif type ==  'tvshow':
            handle_tvshows(li, item, searchstring)
        elif type == 'season':
            handle_seasons(li, item)
        elif type == 'episode':
            handle_episodes(li, item)
        elif type == 'genre':
            handle_genre(li, item)
        elif type == 'cast':
            handle_cast(li, item)


def handle_movies(li,item,searchstring=None):
    genre = item.get('genre', '')
    studio = item.get('studio', '')
    country = item.get('country', '')
    director = item.get('director', '')
    writer = item.get('writer', '')

    li_item = xbmcgui.ListItem(item['title'], offscreen=True)
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
                                              'tag': item['tag'],
                                              'rating': str(float(item['rating'])),
                                              'userrating': str(float(item['userrating'])),
                                              'votes': item['votes'],
                                              'mpaa': item['mpaa'],
                                              'lastplayed': item['lastplayed'],
                                              'mediatype': 'movie',
                                              'trailer': item['trailer'],
                                              'dateadded': item['dateadded'],
                                              'premiered': item['premiered'],
                                              'path': item['file'],
                                              'playcount': item['playcount'],
                                              'set': item['set'],
                                              'setid': item['setid'],
                                              'top250': item['top250']
                                              })

    if 'cast' in item:
        cast_actors = _get_cast(item['cast'])
        li_item.setCast(item['cast'])
        _set_unique_properties(li_item,cast_actors[0],'cast')

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,genre,'genre')
    _set_unique_properties(li_item,studio,'studio')
    _set_unique_properties(li_item,country,'country')
    _set_unique_properties(li_item,director,'director')
    _set_unique_properties(li_item,writer,'writer')

    li_item.setProperty('resumetime', str(item['resume']['position']))
    li_item.setProperty('totaltime', str(item['resume']['total']))

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png'})

    hasVideo = False
    for key, value in iter(list(item['streamdetails'].items())):
        for stream in value:
            if 'video' in key:
                hasVideo = True
            li_item.addStreamInfo(key, stream)

    if not hasVideo: # if duration wasnt in the streaminfo try adding the scraped one
        stream = {'duration': item['runtime']}
        li_item.addStreamInfo('video', stream)

    if searchstring:
        li_item.setProperty('searchstring', searchstring)

    li.append((item['file'], li_item, False))


def handle_tvshows(li,item,searchstring=None):
    genre = item.get('genre', '')
    studio = item.get('studio', '')
    dbid = item['tvshowid']
    season = item['season']
    episode = item['episode']
    watchedepisodes = item['watchedepisodes']
    unwatchedepisodes = get_unwatched(episode,watchedepisodes)

    if not condition('Window.IsVisible(movieinformation)'):
        folder = True
        item['file'] = 'videodb://tvshows/titles/%s/' % dbid
    else:
        folder = False
        item['file'] = 'plugin://script.embuary.helper/?action=folderjump&type=tvshow&dbid=%s' % dbid

    li_item = xbmcgui.ListItem(item['title'], offscreen=True)
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
                                              'tag': item['tag'],
                                              'mediatype': 'tvshow',
                                              'dbid': dbid,
                                              'season': season,
                                              'episode': episode,
                                              'imdbnumber': item['imdbnumber'],
                                              'lastplayed': item['lastplayed'],
                                              'path': item['file'],
                                              'duration': item['runtime'],
                                              'dateadded': item['dateadded'],
                                              'playcount': item['playcount']
                                              })

    if 'cast' in item:
        cast_actors = _get_cast(item['cast'])
        li_item.setCast(item['cast'])
        _set_unique_properties(li_item,cast_actors[0],'cast')

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,genre,'genre')
    _set_unique_properties(li_item,studio,'studio')

    li_item.setProperty('totalseasons', str(season))
    li_item.setProperty('totalepisodes', str(episode))
    li_item.setProperty('watchedepisodes', str(watchedepisodes))
    li_item.setProperty('unwatchedepisodes', str(unwatchedepisodes))

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png'})

    if searchstring:
        li_item.setProperty('searchstring', searchstring)

    li.append((item['file'], li_item, folder))


def handle_seasons(li,item):
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

    if not condition('Window.IsVisible(movieinformation)'):
        folder = True
        file = 'videodb://tvshows/titles/%s/%s/' % (tvshowdbid, season)
    else:
        folder = False
        file = 'plugin://script.embuary.helper/?action=folderjump&type=season&dbid=%s&season=%s' % (tvshowdbid, season)

    li_item = xbmcgui.ListItem(title, offscreen=True)
    li_item.setInfo(type='Video', infoLabels={'title': title,
                                              'season': season,
                                              'episode': episode,
                                              'tvshowtitle': item['showtitle'],
                                              'playcount': item['playcount'],
                                              'mediatype': 'season',
                                              'dbid': item['seasonid']
                                              })

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png',
                    'fanart': item['art'].get('tvshow.fanart', '')
                    })

    li_item.setProperty('watchedepisodes', str(watchedepisodes))
    li_item.setProperty('unwatchedepisodes', str(unwatchedepisodes))
    li_item.setProperty('isspecial', special)
    li_item.setProperty('season_label', item.get('label', ''))

    li.append((file, li_item, folder))


def handle_episodes(li,item):
    director = item.get('director', '')
    writer = item.get('writer', '')

    if item['episode'] < 10:
      label = '0%s. %s' % (item['episode'], item['title'])
    else:
      label = '%s. %s' % (item['episode'], item['title'])

    if item['season'] == '0':
      label = 'S' + label
    else:
      label = '%sx%s' % (item['season'], label)

    li_item = xbmcgui.ListItem(label, offscreen=True)
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
                                              'path': item['file'],
                                              'dateadded': item['dateadded'],
                                              'mediatype': 'episode'
                                              })

    if 'cast' in item:
        cast_actors = _get_cast(item['cast'])
        li_item.setCast(item['cast'])
        _set_unique_properties(li_item,cast_actors[0],'cast')

    _set_ratings(li_item,item['ratings'])

    _set_unique_properties(li_item,director,'director')
    _set_unique_properties(li_item,writer,'writer')

    li_item.setProperty('resumetime', str(item['resume']['position']))
    li_item.setProperty('totaltime', str(item['resume']['total']))
    li_item.setProperty('season_label', item.get('season_label', ''))

    li_item.setArt({'icon': 'DefaultTVShows.png',
                    'fanart': item['art'].get('tvshow.fanart', ''),
                    'poster': item['art'].get('tvshow.poster', ''),
                    'banner': item['art'].get('tvshow.banner', ''),
                    'clearlogo': item['art'].get('tvshow.clearlogo') or item['art'].get('tvshow.logo') or '',
                    'landscape': item['art'].get('tvshow.landscape', ''),
                    'clearart': item['art'].get('tvshow.clearart', '')
                    })
    li_item.setArt(item['art'])

    hasVideo = False
    for key, value in iter(list(item['streamdetails'].items())):
        for stream in value:
            if 'video' in key:
                hasVideo = True
            li_item.addStreamInfo(key, stream)

    if not hasVideo: # if duration wasnt in the streaminfo try adding the scraped one
        stream = {'duration': item['runtime']}
        li_item.addStreamInfo('video', stream)

    if item['season'] == '0':
        li_item.setProperty('IsSpecial', 'true')

    li.append((item['file'], li_item, False))


def handle_cast(li,item):
    li_item = xbmcgui.ListItem(item['name'], offscreen=True)
    li_item.setLabel(item['name'])
    li_item.setLabel2(item['role'])
    li_item.setProperty('role', item['role'])

    li_item.setArt({'icon': 'DefaultActor.png',
                    'thumb': item.get('thumbnail', '')
                    })

    li.append(('', li_item, False))


def handle_genre(li,item):
    li_item = xbmcgui.ListItem(item['label'], offscreen=True)
    li_item.setInfo(type='Video', infoLabels={'title': item['label'],
                                              'dbid': str(item['genreid']),
                                              'path': item['url']
                                              })

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultGenre.png'})

    li.append((item['url'], li_item, True))


def get_unwatched(episode,watchedepisodes):
    if episode > watchedepisodes:
        unwatchedepisodes = episode - watchedepisodes
        return unwatchedepisodes
    else:
        return 0


def _get_cast(castData):
    listcast = []
    listcastandrole = []

    for castmember in castData:
        listcast.append(castmember['name'])
        listcastandrole.append((castmember['name'], castmember['role']))

    return [listcast, listcastandrole]


def _set_unique_properties(li_item,item,prop):
    try:
        i = 0
        for value in item:
            li_item.setProperty('%s.%s' % (prop,i), value)
            i += 1
    except Exception:
        pass

    return li_item


def _set_ratings(li_item,item):
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
