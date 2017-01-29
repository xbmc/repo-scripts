# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib
import libdaserstejsonparser as libDasErsteJsonParser
import libmediathek3 as libMediathek
from datetime import date, timedelta

translation = libMediathek.getTranslation
#http://www.daserste.de/dasersteapp/app/daserste/mehr/index.json
#http://www.daserste.de/dasersteapp/app/index~categories.json
#http://www.daserste.de/dasersteapp/app/index~series.json
#http://www.daserste.de/dasersteapp/app/index~series_plain-false.json
#http://www.daserste.de/dasersteapp/app/index~program_pd20161010.json
#http://www.daserste.de/dasersteapp/app/daserste/start/index.json

#http://www.daserste.de/dasersteapp/app/index~categories_pageSize-20_catVideo-Film.json
#http://www.daserste.de/dasersteapp/app/index~categories_series-akteex.json
#http://www.daserste.de/dasersteapp/app/index~categories_series-tatort.json
#http://www.daserste.de/dasersteapp/app/index~series_serial-akteex_types-sendung,sendebeitrag_pageNumber-0.json
#types: making%5BU%5Dof,support,interview,trailer,bestof,precap,recap

#http://www.daserste.de/dasersteapp/wer-weiss-denn-sowas-folge-75-100~full.json
#http://www.daserste.de/dasersteapp/die-realistin-folge-60-100~full.json
#http://www.daserste.de/dasersteapp/Folge-60-die-realistin-100~full.json

	
def libDasErsteListMain():
	l = []
	l.append({'name':translation(31032), 'mode':'libDasErsteListShows', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'libDasErsteListDate', '_type':'dir'})
	l.append({'name':translation(31035), 'mode':'libDasErsteListCategories', '_type':'dir'})
	#l.append({'name':translation(31039), 'mode':'libDasErsteSearch', '_type':'dir'})
	return l
	
def libDasErsteListShows():
	return libDasErsteJsonParser.getAZ()

def libDasErsteListCategories():
	return libDasErsteJsonParser.getCategories()
	
def libDasErsteListVideos():
	return libDasErsteJsonParser.getVideos(params['url'])
	
def libDasErsteListDate():
	return libMediathek.populateDirDate('libDasErsteListDateVideos')
	
def libDasErsteListDateVideos():
	datum = date.today() - timedelta(int(params['datum']))
	return libDasErsteJsonParser.getDate(datum.strftime('%Y%m%d'))
	
def libDasErsteSearch():
	keyboard = xbmc.Keyboard('', translation(31039))
	keyboard.doModal()
	if keyboard.isConfirmed() and keyboard.getText():
		search_string = keyboard.getText()
		libDasErsteListSearch(search_string)

def libDasErsteListSearch(searchString=False):
	if not searchString:
		searchString = params['searchString']
	return search(searchString)
	
def libDasErstePlay():
	return libDasErsteJsonParser.getVideo(params['url'])
	
def libDasErstePvrPlay():
	videoUrl = libDasErsteJsonParser.getVideo(params['url'])
	listitem = xbmcgui.ListItem(label=params['name'],thumbnailImage=params["thumb"],path=videoUrl)
	xbmc.Player().play(videoUrl, listitem)

	
def list():	
	modes = {
	'libDasErsteListMain': libDasErsteListMain,
	'libDasErsteListShows': libDasErsteListShows,
	'libDasErsteListCategories': libDasErsteListCategories,
	'libDasErsteListVideos': libDasErsteListVideos,
	'libDasErsteListDate': libDasErsteListDate,
	'libDasErsteListDateVideos': libDasErsteListDateVideos,
	'libDasErstePlay': libDasErstePlay,
	}
	views = {
	'libDasErsteListShows': 'shows',
	'libDasErsteListVideos': 'videos',
	'libDasErsteListDate': 'videos',
	'libDasErsteListDateVideos': 'videos',
	'libDasErsteListSearch': 'videos'
	}
	global params
	params = libMediathek.get_params()
	global pluginhandle
	pluginhandle = int(sys.argv[1])
	mode = params.get('mode','libDasErsteListMain')
	if mode == 'libDasErstePlay':
		libMediathek.play(libDasErstePlay())
	else:
		l = modes.get(mode)()
		libMediathek.addEntries(l)
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	