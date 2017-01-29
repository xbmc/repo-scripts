# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libbrjsonparser as libBrJsonParser
import libmediathek3 as libMediathek
from datetime import date, timedelta

translation = libMediathek.getTranslation

def getDate(date,channel='BR'):
	return libBrJsonParser.parseDate(date,channel)
def search(searchString):
	return libBrJsonParser.search(searchString)
def getVideoUrl(url):
	return libBrJsonParser.parseVideo(url)
def play(dict):
	url,sub = getVideoUrl(dict["url"])
	#listitem = xbmcgui.ListItem(label=video["name"],thumbnailImage=video["thumb"],path=url)
	#listitem = xbmcgui.ListItem(label=dict["name"],path=url)
	listitem = xbmcgui.ListItem(label='TODO',path=url)
	xbmc.Player().play(url, listitem)	
	

	
def libBrListMain():
	l = []
	l.append({'name':translation(31031), 'mode':'libBrListVideos2', 'url':'http://www.br.de/mediathek/video/suche/tag-suche-mediathek-100~hal_vt-medcc1_-bff08c03fe069a9ee9013704adcbd4855992ad2a.json?t=social&q=mostViewed', '_type':'dir'})
	l.append({'name':translation(31032), 'mode':'libBrListLetters', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'libBrListChannel', '_type':'dir'})
	l.append({'name':translation(31039), 'mode':'libBrSearch', '_type':'dir'})
	return l
	
	
	
def libBrListLetters():
	return libMediathek.populateDirAZ('libBrListShows')
	
def libBrListShows():
	return libBrJsonParser.parseShows(params['name'])
	
def libBrListVideos():
	return libBrJsonParser.parseVideos(params['url'])
def libBrListVideos2():
	return libBrJsonParser.parseLinks(params['url'])

	
def libBrListChannel():
	l = []
	l.append({'name':'ARD-Alpha', 'mode':'libBrListChannelDate','channel':'ARD-Alpha'})
	l.append({'name':'BR', 'mode':'libBrListChannelDate','channel':'BR'})
	return l

def libBrListChannelDate():
	return libMediathek.populateDirDate('libBrListChannelDateVideos',params['channel'],True)
	
def libBrListChannelDateVideos():
	datum = date.today() - timedelta(int(params['datum']))
	xbmc.log(datum.strftime('%Y-%m-%d'))
	return libBrJsonParser.parseDate(datum.strftime('%Y-%m-%d'),params['channel'])#params['datum'] =yyyy-mm-dd
	
def libBrSearch():
	dialog = xbmcgui.Dialog()
	d = dialog.input(translation(31039),type=xbmcgui.INPUT_ALPHANUM)
	search_string = urllib.quote_plus(d)
	return libBrListSearch(search_string)

def libBrListSearch(searchString=False):
	if not searchString:
		searchString = params['searchString']
	return search(searchString)
	
def libBrPlay():
	return libBrJsonParser.parseVideo(params['url'])
	
	
def list():	
	modes = {
	'libBrListMain': libBrListMain,
	'libBrListLetters': libBrListLetters,
	'libBrListShows': libBrListShows,
	'libBrListVideos': libBrListVideos,
	'libBrListVideos2': libBrListVideos2,
	'libBrListChannel': libBrListChannel,
	'libBrListChannelDate': libBrListChannelDate,
	'libBrListChannelDateVideos': libBrListChannelDateVideos,
	'libBrSearch': libBrSearch,
	'libBrListSearch': libBrListSearch,
	'libBrPlay': libBrPlay
	}
	views = {
	'libBrListShows': 'shows',
	'libBrListVideos': 'videos',
	'libBrListDate': 'videos',
	'libBrListDateVideos': 'videos',
	'libBrListSearch': 'videos'
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libBrListMain')
	xbmc.log(mode)
	if mode == 'libBrPlay':
		libMediathek.play(libBrPlay())
	else:
		xbmc.log
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
	