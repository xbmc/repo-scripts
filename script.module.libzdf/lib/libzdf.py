# -*- coding: utf-8 -*-
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
import urllib
import sys
import libmediathek3 as libMediathek
import libzdfjsonparser as libZdfJsonParser
from datetime import date, timedelta

translation = libMediathek.getTranslation


#https://api.zdf.de/content/documents/zdf-startseite-100.json?profile=default
#https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=teaser
#https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=default
#https://api.zdf.de/content/documents/sendungen-100.json?profile=default
#api.zdf.de/search/documents?hasVideo=true&q=*&types=page-video&sender=ZDFneo&paths=%2Fzdf%2Fcomedy%2Fneo-magazin-mit-jan-boehmermann%2Ffilter%2C%2Fzdf%2Fcomedy%2Fneo-magazin-mit-jan-boehmermann&sortOrder=desc&limit=1&editorialTags=&sortBy=date&contentTypes=episode&exclEditorialTags=&allEditorialTags=false
#api.zdf.de/search/documents?hasVideo=true&q=*&types=page-video&sender=ZDFneo&paths=%2Fzdf%2Fnachrichten%2Fzdfspezial%2Ffilter%2C%2Fzdf%nachrichten%2Fzdfspezial&sortOrder=desc&limit=1&editorialTags=&sortBy=date&contentTypes=episode&exclEditorialTags=&allEditorialTags=false
#https://api.zdf.de/cmdm/epg/broadcasts?from=2016-10-28T05%3A30%3A00%2B02%3A00&to=2016-10-29T05%3A29%3A00%2B02%3A00&limit=500&profile=teaser
#https://api.zdf.de/cmdm/epg/broadcasts?from=2016-10-28T05%3A30%3A00%2B02%3A00&to=2016-10-29T05%3A29%3A00%2B02%3A00&limit=500&profile=teaser&tvServices=ZDF

channels = 	['ZDF','ZDFinfo','ZDFneo',]

def getMostViewed():#used in unithek
	return libZdfJsonParser.parsePage('https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=default')

def libZdfListMain():
	libMediathek.searchWorkaroundRemove()
	l = []
	l.append({'_name':translation(31031), 'mode':'libZdfListPage', '_type': 'dir', 'url':'https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=default'})
	l.append({'_name':translation(31032), 'mode':'libZdfListAZ', '_type': 'dir'})
	l.append({'_name':translation(31033), 'mode':'libZdfListChannel', '_type': 'dir'})
	l.append({'_name':translation(31034), 'mode':'libZdfListPage', '_type': 'dir', 'url':'https://api.zdf.de/search/documents?q=%2A&contentTypes=category'})
	l.append({'_name':translation(31039), 'mode':'libZdfSearch',   '_type': 'dir'})
	return l
	
def libZdfListAZ():
	libMediathek.sortAZ()
	return libZdfJsonParser.getAZ()
	
def libZdfListPage():
	return libZdfJsonParser.parsePage(params['url'])
	
def libZdfListVideos():
	return libZdfJsonParser.getVideos(params['url'])

def libZdfPlay():
	return libZdfJsonParser.getVideoUrl(params['url'])
	
def libZdfListChannel():
	l = []
	for channel in channels:
		d = {}
		d['mode'] = 'libZdfListChannelDate'
		d['_name'] = channel
		d['_type'] = 'dir'
		d['channel'] = channel
		l.append(d)
	return l

def libZdfListChannelDate():
	return libMediathek.populateDirDate('libZdfListChannelDateVideos',params['channel'],True)
	
def libZdfListChannelDateVideos():
	if 'datum' in params:
		datum = params['datum']
		day = date.today() - timedelta(int(datum))
		yyyymmdd = day.strftime('%Y-%m-%d')
	else:
		ddmmyyyy = libMediathek.dialogDate()
		yyyymmdd = ddmmyyyy[4:8] + '-' + ddmmyyyy[2:4] + '-' + ddmmyyyy[0:2]
	l = []
	params['url'] = 'https://api.zdf.de/cmdm/epg/broadcasts?from='+yyyymmdd+'T00%3A00%3A00%2B02%3A00&to='+yyyymmdd+'T23%3A59%3A59%2B02%3A00&limit=500&profile=teaser&tvServices='+params['channel']

	return libZdfListPage()
	
def libZdfSearch():
	if libMediathek.searchWorkaroundExists():
		d = libMediathek.searchWorkaroundRead()
	else:
		dialog = xbmcgui.Dialog()
		d = dialog.input(translation(31039),type=xbmcgui.INPUT_ALPHANUM)
		libMediathek.searchWorkaroundWrite(d)
	search_string = urllib.quote_plus(d)
	params['url'] = "https://api.zdf.de/search/documents?q="+search_string
	return libZdfListPage()
		
def libZdfGetVideoHtml(url):
	import re
	response = libMediathek.getUrl(url)
	return libZdfJsonParser.getVideoUrl(re.compile('"contentUrl": "(.+?)"', re.DOTALL).findall(response)[0])

def list():	
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	
	mode = params.get('mode','libZdfListMain')
	if mode == 'libZdfPlay':
		libMediathek.play(libZdfPlay())
		
	else:
		l = modes.get(mode,libZdfListMain)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
	
modes = {
	'libZdfListMain':libZdfListMain,
	'libZdfListAZ':libZdfListAZ,
	'libZdfListVideos':libZdfListVideos,
	#'libZdfListDate':libZdfListDate,
	#'libZdfListDateChannels':libZdfListDateChannels,
	
	'libZdfListChannel':libZdfListChannel,
	'libZdfListChannelDate':libZdfListChannelDate,
	'libZdfListChannelDateVideos':libZdfListChannelDateVideos,
	'libZdfSearch':libZdfSearch,
	'libZdfListPage':libZdfListPage,
	'libZdfPlay':libZdfPlay,
	}	