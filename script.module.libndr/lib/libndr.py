# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libndrparser as libNdrParser
import libndrjsonparser as libNdrJsonParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation




def libNdrListMain():
	l = []
	l.append({'_name':translation(31032), 'mode':'libNdrListDir', '_type':'dir'})
	l.append({'_name':translation(31033), 'mode':'libNdrListDate', '_type':'dir'})
	return l

def libNdrListDir():
	return libNdrParser.parseShows()
	
def libNdrListVideos():
	return libNdrParser.parseVideos(params['url'])
	
def libNdrListDate():
	return libMediathek.populateDirDate('libNdrListDateVideos')
		
def libNdrListDateVideos():
	return libNdrParser.getDate(params['yyyymmdd'])
	

def libNdrSearch():
	keyboard = xbmc.Keyboard('', translation(31039))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = urllib.quote_plus(keyboard.getText())
		url = 'http://swrmediathek.de/app-2/suche/' + search_string
		return libNdrParser.getList(url,'video','libNdrPlay')
	
def libNdrPlay():
	return libNdrJsonParser.getVideo(params['id'])
		
def libNdrListLetters():
	libMediathek.populateDirAZ('libNdrListShows',ignore=['#'])
	return []
	
def libNdrListShows():
	return libNdrParser.parseShows(params['name'])
	

def list():	
	modes = {
	'libNdrListMain': libNdrListMain,
	'libNdrListDir': libNdrListDir,
	'libNdrListVideos': libNdrListVideos,
	'libNdrListDate': libNdrListDate,
	'libNdrListDateVideos': libNdrListDateVideos,
	
	'libNdrSearch': libNdrSearch,
	
	'libNdrPlay': libNdrPlay,
	
	
	'libNdrListLetters': libNdrListLetters,
	'libNdrListShows': libNdrListShows,
	#'libNdrListDateChannels': libNdrListDateChannels,
	}
	
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libNdrListMain')
	if mode == 'libNdrPlay':
		libMediathek.play(libNdrPlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
