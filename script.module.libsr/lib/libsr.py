# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libsrjsonparser as libSrJsonParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation

#http://hbbtv.sr-mediathek.de/inc/SearchJSON.php

def libSrListMain():
	l = []
	l.append({'name':translation(31030), 'mode':'libSrListVideos', 'url':'http://hbbtv.sr-mediathek.de/inc/TeaserJSON.php', '_type':'dir'})
	l.append({'name':translation(31032), 'mode':'libSrListShows', 'url':'http://hbbtv.sr-mediathek.de/inc/SndazJSON.php', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'libSrListDate', '_type':'dir'})
	return l
	
def libSrListDate():
	return libMediathek.populateDirDate('libSrListDateVideos')

def libSrListDateVideos():
	return libSrJsonParser.getDate(params['datum'])
	
def libSrListShows():
	libMediathek.sortAZ()
	return libSrJsonParser.getShows()
		
def libSrListVideos():
	return libSrJsonParser.getVideos(params['url'])
	
def libSrPlay():
	d = {}
	url = params['url']
	d['media'] = [{'url':url, 'type':'video', 'stream':'HLS'}]
	return d

def list():	
	modes = {
	'libSrListMain': libSrListMain,
	'libSrListShows': libSrListShows,
	'libSrListVideos': libSrListVideos,
	'libSrListDate': libSrListDate,
	'libSrListDateVideos': libSrListDateVideos,
	'libSrPlay': libSrPlay,
	#'libSrSearch': libSrSearch,
	
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libSrListMain')
	if mode == 'libSrPlay':
		libMediathek.play(libSrPlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
