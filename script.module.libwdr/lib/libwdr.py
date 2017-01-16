# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libwdrparser as libWdrParser
import libwdrjsonparser as libWdrJsonParser
import libwdrrssparser as libWdrRssParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation

def libWdrListMain():
	libMediathek.searchWorkaroundRemove()
	l = []
	l.append({'_name':translation(31030), 'mode':'libWdrListFeed', 'url':'http://www1.wdr.de/mediathek/video/sendungverpasst/sendung-verpasst-100~_format-mp111_type-rss.feed', '_type':'dir'})
	l.append({'_name':translation(31032), 'mode':'libWdrListLetters', '_type':'dir'})
	l.append({'_name':translation(31033), 'mode':'libWdrListDate', '_type':'dir'})
	#l.append({'name':'Videos in Gebärdensprache', 'mode':'libWdrListFeed', 'url':'http://www1.wdr.de/mediathek/video/sendungen/videos-dgs-100~_format-mp111_type-rss.feed', '_type':'dir'})
	#l.append({'name':'Videos mit Untertiteln', 'mode':'libWdrListFeed', 'url':'http://www1.wdr.de/mediathek/video/sendungen/videos-untertitel-100~_format-mp111_type-rss.feed', '_type':'dir'})
	l.append({'_name':translation(31039), 'mode':'libWdrSearch', '_type':'dir'})
	return l
	
def libWdrListLetters():
	return libMediathek.populateDirAZ('libWdrListShows',ignore=['#'])
	
def libWdrListShows():
	return libWdrParser.parseShows(params['name'])
	
def libWdrListVideos():
	return libWdrRssParser.parseVideos(params['url'])
	
def libWdrListFeed():
	return libWdrRssParser.parseFeed(params['url'])

def libWdrListDate():
	return libMediathek.populateDirDate('libWdrListDateVideos',False,True)
	
def libWdrListDateVideos():
	if 'datum' in params:
		from datetime import date, timedelta
		day = date.today() - timedelta(int(params['datum']))
		ddmmyyyy = day.strftime('%d%m%Y')
	else:
		ddmmyyyy = libMediathek.dialogDate()
	url = 'http://www1.wdr.de/mediathek/video/sendungverpasst/sendung-verpasst-100~_tag-'+ddmmyyyy+'_format-mp111_type-rss.feed'
	return libWdrRssParser.parseFeed(url,'video')
	
def libWdrSearch():
	import libwdrhtmlparser as libWdrHtmlParser
	search_string = libMediathek.getSearchString()
	return libWdrHtmlParser.parse("http://www1.wdr.de/mediathek/video/suche/avsuche100~suche_parentId-videosuche100.html?pageNumber=1&sort=date&q="+search_string)
	
def libWdrListSearch():
	import libwdrhtmlparser as libWdrHtmlParser
	return libWdrHtmlParser.parse(params['url'])
	
def libWdrPlay():
	return libWdrParser.parseVideo(params['url'])
	
	
def list():	
	modes = {
	'libWdrListMain': libWdrListMain,
	'libWdrListLetters': libWdrListLetters,
	'libWdrListShows': libWdrListShows,
	'libWdrListVideos': libWdrListVideos,
	'libWdrListFeed': libWdrListFeed,
	'libWdrListDate': libWdrListDate,
	'libWdrListDateVideos': libWdrListDateVideos,
	'libWdrSearch': libWdrSearch,
	'libWdrListSearch': libWdrListSearch,
	'libWdrPlay': libWdrPlay
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libWdrListMain')
	if mode == 'libWdrPlay':
		libMediathek.play(libWdrPlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	