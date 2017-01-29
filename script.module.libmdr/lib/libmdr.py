# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libmdrmetaparser as libMdrMetaParser
import libmdrhtmlparser as libMdrHtmlParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation
translationInternal = xbmcaddon.Addon(id='script.module.libmdr').getLocalizedString

def libMdrListMain():
	l = []
	l.append({'_name':translation(31030), 'mode':'libMdrListPlus', 'url':'http://www.mdr.de/mediathek/mediathek-neu-100-meta.xml', '_type':'dir'})
	l.append({'_name':translation(31031), 'mode':'libMdrListPlus', 'url':'http://www.mdr.de/mediathek/mediathek-meistgeklickt-100-meta.xml', '_type':'dir'})
	l.append({'_name':translation(31032), 'mode':'libMdrListShows', '_type':'dir'})
	l.append({'_name':translation(31033), 'mode':'libMdrListDate', '_type':'dir'})
	l.append({'_name':translation(31034), 'mode':'libMdrListRubrics', '_type':'dir'})
	return l

def libMdrListRubrics():
	l = [
	{'_name':translationInternal(32000),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/reportage/mediathek-reportagen-dokumentationen-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32001),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/sport/mediathek-sport-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32002),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/sachsen/mediathek-sachsen-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32003),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/sachsen-anhalt/mediathek-sachsen-anhalt-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32004),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/thueringen/mediathek-thueringen-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32005),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/kinder/mediathek-kinder-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32006),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/film-serie/mediathek-film-serien-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32007),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/magazine/mediathek-magazine-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32008),'mode':'libMdrListHtml','url':'http://www.mdr.de/mediathek/themen/nachrichten/mediathek-nachrichten-100_box--5390492834412829556_zc-4e12cc21.html', '_type':'dir'},
	{'_name':translationInternal(32009),'mode':'libMdrListPlus','url':'http://www.mdr.de/mediathek/livestreams/mdr-plus/mediathek-mdrplus-100-meta.xml', '_type':'dir'}
	]
	return l

def pDays():
	return libMdrMetaParser.parseDays()
	
def libMdrBroadcast():
	return libMdrMetaParser.parseBroadcast(params['url'])
	
def libMdrListHtml():
	return libMdrHtmlParser.testparse(params['url'])
	
def libMdrListLetters():
	libMediathek.populateDirAZ('libMdrListShows',ignore=['#'])
	return []
	
def libMdrListShows():
	libMediathek.sortAZ()
	return libMdrMetaParser.testparse()

def libMdrListPlus():
	return libMdrMetaParser.parseMdrPlus(params['url'])
	
def libMdrListVideos():
	return libMdrMetaParser.parseVideos(params['url'])
	
def libMdrListDate():
	return libMediathek.populateDirDate('libMdrListDateVideos')
	
def libMdrListDateVideos():
	return libMdrHtmlParser.parseDate(params['datum'])
	
def libMdrPlay():
	return libMdrMetaParser.parseVideo(params['url'])
	
	
def list():	
	modes = {
	'libMdrListMain': libMdrListMain,
	'libMdrBroadcast': libMdrBroadcast,
	'pDays': pDays,
	'libMdrListHtml': libMdrListHtml,
	'libMdrListRubrics': libMdrListRubrics,
	
	
	'libMdrListLetters': libMdrListLetters,
	'libMdrListShows': libMdrListShows,
	'libMdrListPlus': libMdrListPlus,
	'libMdrListVideos': libMdrListVideos,
	'libMdrListDate': libMdrListDate,
	'libMdrListDateVideos': libMdrListDateVideos,
	#'libMdrListDateChannels': libMdrListDateChannels,
	'libMdrPlay': libMdrPlay
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libMdrListMain')
	if mode == 'libMdrPlay':
		libMediathek.play(libMdrPlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	
