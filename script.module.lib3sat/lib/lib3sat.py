# -*- coding: utf-8 -*-
import sys
import xbmcgui
import xbmcplugin
import urllib
import libmediathek3 as libMediathek
import mediathekxmlservice as xmlservice

from datetime import date, timedelta

translation = libMediathek.getTranslation

baseXml = 'http://www.3sat.de/mediathek'
modePrefix = 'lib3sat'
	
def lib3satListMain():
	libMediathek.searchWorkaroundRemove()
	l = []
	l.append({'name':translation(31030), 'mode':'lib3satListNew', '_type':'dir'})
	l.append({'name':translation(31031), 'mode':'lib3satListMV', '_type':'dir'})
	l.append({'name':translation(31032), 'mode':'lib3satListLetters', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'lib3satListDate', '_type':'dir'})
	l.append({'name':translation(31039), 'mode':'lib3satSearch', '_type':'dir'})
	return l
	
def lib3satListNew():
	return xmlservice.getNew(baseXml,modePrefix)
	
def lib3satListMV():
	return xmlservice.getMostViewed(baseXml,modePrefix)

def lib3satListLetters():
	return libMediathek.populateDirAZ('lib3satListShows',['d','e','g','i','j','l','o','p','q','r','u','x','y','z'])
		
def lib3satListShows():
	letter = params['name'].replace('#','0%2D9')
	return xmlservice.getXML('http://www.3sat.de/mediathek/xmlservice/web/sendungenAbisZ?characterRangeEnd='+letter+'&detailLevel=2&characterRangeStart='+letter)
	
def lib3satListDate():
	l = libMediathek.populateDirDate('lib3satListDateVideos',False,True)
	return l
	
def lib3satListDateVideos():
	if 'datum' in params:
		from datetime import date, timedelta
		day = date.today() - timedelta(int(params['datum']))
		ddmmyy = day.strftime('%d%m%y')
	else:
		ddmmyyyy = libMediathek.dialogDate()
		ddmmyy = ddmmyyyy[0:2] + ddmmyyyy[2:4] + ddmmyyyy[6:8]
	url = 'http://www.3sat.de/mediathek/xmlservice/web/sendungVerpasst?startdate='+ddmmyy+'&enddate='+ddmmyy+'&maxLength=50'
	return xmlservice.getXML(url,type='date')[::-1]
	
def lib3satListRubrics():#not supported by the mediathek
	return xmlservice.getRubrics(baseXml)
	
def lib3satListTopics():#not supported by the mediathek
	return xmlservice.getTopics(baseXml)
	
def lib3satSearch():
	if libMediathek.searchWorkaroundExists():
		d = libMediathek.searchWorkaroundRead()
	else:
		dialog = xbmcgui.Dialog()
		d = dialog.input(translation(31039),type=xbmcgui.INPUT_ALPHANUM)
		libMediathek.searchWorkaroundWrite(d)
	search_string = urllib.quote_plus(d)
	return xmlservice.getXML(baseXml + "/xmlservice/web/detailsSuche?maxLength=50&types=Video&properties=HD%2CUntertitel%2CRSS&searchString="+search_string)
	
def lib3satXmlListPage():
	return xmlservice.getXML(params['url'])
	
def lib3satXmlPlay():
	return xmlservice.getVideoUrl(params['url'])
	
def list():
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	import xbmc
	xbmc.log(str(params))
	mode = params.get('mode','lib3satListMain')
	if mode == 'lib3satXmlPlay' or mode == 'xmlPlay':
		libMediathek.play(lib3satXmlPlay())
	else:
		#l = modes.get(mode,lib3satListMain)()
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	

modes = {
	'lib3satListMain': lib3satListMain,
	'lib3satListNew': lib3satListNew,
	'lib3satListMV': lib3satListMV,
	'xmlListPage': lib3satXmlListPage,
	'lib3satXmlListPage': lib3satXmlListPage,
	'xmlPlay': lib3satXmlPlay,
	'lib3satXmlPlay': lib3satXmlPlay,
	'lib3satListRubrics': lib3satListRubrics,
	'lib3satListTopics': lib3satListTopics,
	'lib3satListLetters': lib3satListLetters,
	'lib3satListShows': lib3satListShows,
	'lib3satListDate': lib3satListDate,
	'lib3satListDateVideos': lib3satListDateVideos,
	'lib3satSearch': lib3satSearch,
	}
views = {
	'lib3satListShows': 'shows',
	'lib3satListVideos': 'videos',
	'lib3satListDate': 'videos',
	'lib3satListDateVideos': 'videos',
	'lib3satListSearch': 'videos'
	}
