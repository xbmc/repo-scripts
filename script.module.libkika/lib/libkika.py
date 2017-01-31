# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
import urllib
import libkikajsonparser as libKikaJsonParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation

#http://hbbtv.sr-mediathek.de/inc/SearchJSON.php

def libKikaListMain():
	libMediathek.searchWorkaroundRemove()
	l = []
	l.append({'name':translation(31032), 'mode':'libKikaListShows', 'url':'http://itv.mit-xperts.com/kikamediathek/kika/api.php/videos/hbbtv/sendungen/sendereihen-hbbtv-100-hbbtv.json', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'libKikaListDate', '_type':'dir'})
	l.append({'name':translation(31039), 'mode':'libKikaSearch', '_type':'dir'})
	return l
	
def libKikaListDate():
	return libMediathek.populateDirDate('libKikaListDateVideos')

def libKikaListDateVideos():
	return libKikaJsonParser.getVideos('http://itv.mit-xperts.com/kikamediathek/kika/api.php/videos/hbbtv/suche/hbbtv-search-100-hbbtv.json?day=-'+params['datum'],type='date')
	
def libKikaListShows():
	libMediathek.sortAZ()
	return libKikaJsonParser.getShows(params['url'])
		
def libKikaListVideos():
	return libKikaJsonParser.getVideos(params['url'])


def libKikaSearch():
	if libMediathek.searchWorkaroundExists():
		d = libMediathek.searchWorkaroundRead()
	else:
		dialog = xbmcgui.Dialog()
		d = dialog.input(translation(31039),type=xbmcgui.INPUT_ALPHANUM)
		libMediathek.searchWorkaroundWrite(d)
	search_string = urllib.quote_plus(d)
	return libKikaJsonParser.getVideos('http://itv.mit-xperts.com/kikamediathek/kika/api.php/videos/hbbtv/suche/hbbtv-search-100-hbbtv.json?searchText='+search_string)
	

def list():	
	modes = {
	'libKikaListMain': libKikaListMain,
	'libKikaListShows': libKikaListShows,
	'libKikaListVideos': libKikaListVideos,
	'libKikaListDate': libKikaListDate,
	'libKikaListDateVideos': libKikaListDateVideos,
	'libKikaSearch': libKikaSearch,
	
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libKikaListMain')
	if mode == 'libMdrPlay':
		import libmdr
		libmdr.list()
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
