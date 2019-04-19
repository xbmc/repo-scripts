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

		if type == 'movies':
			parse_movies(li, item, searchstring, append)
		elif type ==  'tvshows':
			parse_tvshows(li, item, searchstring, append)
		elif type == 'seasons':
			parse_seasons(li, item, append)
		elif type == 'episodes':
			parse_episodes(li, item, append)
		elif type == 'genre':
			parse_genre(li, item, append)
		elif type == 'cast':
			parse_cast(li, item, append)


def _get_cast(castData):
		listCast = []
		listCastAndRole = []
		for castmember in castData:
			listCast.append(castmember['name'])
			listCastAndRole.append((castmember['name'], castmember['role']))
		return [listCast, listCastAndRole]


def _get_first_item(item):
		if len(item) > 0:
			item = item[0]
		else:
			item = ''
		return item


def _get_joined_items(item):
		if len(item) > 0:
			item = ' / '.join(item)
		else:
			item = ''
		return item


def parse_movies(li, item, searchstring=False, append=False):

	if 'cast' in item:
		cast = _get_cast(item['cast'])

	li_item = xbmcgui.ListItem(item['title'])
	li_item.setInfo(type='Video', infoLabels={'Title': item['title'],
											'OriginalTitle': item['originaltitle'],
											'Year': item['year'],
											'Genre': _get_joined_items(item.get('genre', '')),
											'Studio': _get_first_item(item.get('studio', '')),
											'Country': _get_first_item(item.get('country', '')),
											'Plot': item['plot'],
											'PlotOutline': item['plotoutline'],
											'dbid': item['movieid'],
											'imdbnumber': item['imdbnumber'],
											'Tagline': item['tagline'],
											'Rating': str(float(item['rating'])),
											'Votes': item['votes'],
											'MPAA': item['mpaa'],
											'lastplayed': item['lastplayed'],
											'Cast': cast[0],
											'CastAndRole': cast[1],
											'mediatype': 'movie',
											'Trailer': item['trailer'],
											'Playcount': item['playcount']})
	li_item.setProperty('resumetime', str(item['resume']['position']))
	li_item.setProperty('totaltime', str(item['resume']['total']))
	li_item.setArt(item['art'])
	li_item.setIconImage('DefaultVideo.png')

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
		cast = _get_cast(item['cast'])

	rating = str(round(item['rating'],1))
	dbid = str(item['tvshowid'])
	season = str(item['season'])
	episode = str(item['episode'])
	watchedepisodes = str(item['watchedepisodes'])

	if int(episode) > int(watchedepisodes):
		unwatchedepisodes = int(episode) - int(watchedepisodes)
		unwatchedepisodes = str(unwatchedepisodes)
	else:
		unwatchedepisodes = '0'

	year = str(item['year'])
	mpaa = item['year']

	if not visible('Window.IsVisible(movieinformation)'):
		folder = True
		item['file'] = 'videodb://tvshows/titles/%s/' % dbid
	else:
		folder = False
		item['file'] = 'plugin://script.embuary.helper/?action=jumptoshow&dbid=%s' % dbid

	li_item = xbmcgui.ListItem(item['title'])
	li_item.setInfo(type='Video', infoLabels={'Title': item['title'],
											'Year': year,
											'Genre': _get_joined_items(item.get('genre', '')),
											'Studio': _get_first_item(item.get('studio', '')),
											'Country': _get_first_item(item.get('country', '')),
											'Plot': item['plot'],
											'Rating': rating,
											'Votes': item['votes'],
											'Premiered': item['premiered'],
											'MPAA': mpaa,
											'Cast': cast[0],
											'CastAndRole': cast[1],
											'mediatype': 'tvshow',
											'dbid': dbid,
											'season': season,
											'episode': episode,
											'tvshowtitle': item['title'],
											'imdbnumber': str(item['imdbnumber']),
											'Path': item['file'],
											'DateAdded': item['dateadded'],
											'Playcount': item['playcount']})
	li_item.setProperty('TotalSeasons', season)
	li_item.setProperty('TotalEpisodes', episode)
	li_item.setProperty('WatchedEpisodes', watchedepisodes)
	li_item.setProperty('UnwatchedEpisodes', unwatchedepisodes)
	li_item.setArt(item['art'])
	li_item.setIconImage('DefaultVideo.png')

	if searchstring:
		li_item.setProperty('searchstring', searchstring)

	if append:
		li.append((item['file'], li_item, folder))


def parse_seasons(li, item, append=False):

	tvshowdbid = str(item['tvshowid'])
	seasonnr = str(item['season'])
	episode = str(item['episode'])
	watchedepisodes = str(item['watchedepisodes'])

	if seasonnr == '0':
		title = '%s' % (xbmc.getLocalizedString(20381))
	else:
		title = '%s %s' % (xbmc.getLocalizedString(20373), seasonnr)

	if int(episode) > int(watchedepisodes):
		unwatchedepisodes = int(episode) - int(watchedepisodes)
		unwatchedepisodes = str(unwatchedepisodes)
	else:
		unwatchedepisodes = '0'

	if not visible('Window.IsVisible(movieinformation)'):
		folder = True
		file = 'videodb://tvshows/titles/%s/%s/' % (tvshowdbid, seasonnr)
	else:
		folder = False
		file = 'plugin://script.embuary.helper/?action=jumptoseason&dbid=%s&season=%s' % (tvshowdbid, seasonnr)

	li_item = xbmcgui.ListItem(title)
	li_item.setInfo(type='Video', infoLabels={'Title': title,
											'season': seasonnr,
											'episode': episode,
											'tvshowtitle': item['showtitle'],
											'playcount': item['playcount'],
											'mediatype': 'season',
											'dbid': item['seasonid']})
	li_item.setArt(item['art'])
	li_item.setArt({'fanart': item['art'].get('tvshow.fanart', '')})
	li_item.setProperty('WatchedEpisodes', watchedepisodes)
	li_item.setProperty('UnwatchedEpisodes', unwatchedepisodes)
	li_item.setIconImage('DefaultVideo.png')

	if seasonnr == '0':
		li_item.setProperty('IsSpecial', 'true')

	if append:
		li.append((file, li_item, folder))


def parse_episodes(li, item, append=False):

	if 'cast' in item:
		cast = _get_cast(item['cast'])

	li_item = xbmcgui.ListItem(item['title'])
	li_item.setInfo(type='Video', infoLabels={'Title': item['title'],
											'Episode': item['episode'],
											'Season': item['season'],
											'Premiered': item['firstaired'],
											'Dbid': str(item['episodeid']),
											'Plot': item['plot'],
											'TVshowTitle': item['showtitle'],
											'lastplayed': item['lastplayed'],
											'Rating': str(float(item['rating'])),
											'Playcount': item['playcount'],
											'Director': _get_joined_items(item.get('director', '')),
											'Writer': _get_joined_items(item.get('writer', '')),
											'Cast': cast[0],
											'CastAndRole': cast[1],
											'mediatype': 'episode'})
	li_item.setProperty('resumetime', str(item['resume']['position']))
	li_item.setProperty('totaltime', str(item['resume']['total']))
	li_item.setArt({'fanart': item['art'].get('tvshow.fanart', ''), 'clearlogo': item['art'].get('tvshow.clearlogo', ''), 'landscape': item['art'].get('tvshow.landscape', ''), 'clearart': item['art'].get('tvshow.clearart', '')})
	li_item.setArt(item['art'])
	li_item.setIconImage('DefaultTVShows.png')

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
	li_item.setThumbnailImage(item.get('thumbnail', ''))
	li_item.setIconImage('DefaultActor.png')

	if append:
		li.append(('', li_item, False))


def parse_genre(li,item,append=False):

	li_item = xbmcgui.ListItem(item['label'])
	li_item.setInfo(type='Video', infoLabels={'Title': item['label'],
											'dbid': str(item['genreid']),
											'Path': item['file']})
	li_item.setArt(item['art'])
	li_item.setIconImage('DefaultGenre.png')

	if append:
		li.append((item['file'], li_item, True))
