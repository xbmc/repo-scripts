# -*- coding: utf-8 -*-
import urllib
import urllib2
import socket
import sys
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import re
from datetime import datetime,timedelta
import time

from libmediathek3utils import clearString
from libmediathek3utils import getTranslation as translation

icon = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('icon'))
fanart = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('fanart'))

def sortAZ():
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)

def addEntries(l):
	lists = []
	doneList = []
	
	for d in l:
		if str(d) in doneList:#primitive methode to filter duplicated entries
			continue
		doneList.append(str(d))
		
		if '_overridepath' in d:
			u = d['_overridepath']
		else:
			u = _buildUri(d)
		newd = {}
		for key in d:
			if key.startswith('_'):
				if isinstance(d[key], unicode):
					d[key] = d[key].encode('utf-8', 'ignore')
				newd[key[1:]] = d[key]
			elif isinstance(d[key], unicode):
				newd[key] = d[key].encode('utf-8', 'ignore')
			else:
				newd[key] = d[key]
		d = newd
		
		if 'type' in d and d['type'] == 'nextPage':
			d['name'] = translation(31040)
			if not 'mode' in d:
				d['mode'] = get_params()['mode']
		if isinstance(d["name"], unicode):
			d["name"] = d["name"].encode('utf-8')
		d["name"] = clearString(d["name"])
		if 'airedISO8601' in d or 'airedISO8601A' in d:
			d['aired'],d['airedtime'] = _airedISO8601(d)
			
		if 'type' in d and d['type'] == 'date' and 'airedtime' in d:
			d["name"] = '(' + str(d["airedtime"]) + ') ' + d["name"]
		elif 'type' in d and d['type'] == 'date' and 'time' in d:
			d["name"] = '(' + str(d["date"]) + ') ' + d["name"]
			
		ilabels = {
			"Title": clearString(d.get('name','')),
			"Plot": clearString(d.get('plot','')),
			"Plotoutline": clearString(d.get('plot','')),
			"Duration": d.get('duration',''),
			"Mpaa": d.get('mpaa',''),
			"Aired": d.get('aired',''),
			"Studio": d.get('channel',''),
			}
		if 'epoch' in d: 
			ilabels['aired'] = time.strftime("%Y-%m-%d", time.gmtime(float(d['epoch'])))
		if 'episode' in d: 
			ilabels['episode'] = d['episode']
		if 'season' in d: 
			ilabels['season'] = d['season']
		if 'tvshowtitle' in d: 
			ilabels['tvshowtitle'] = d['tvshowtitle']
			ilabels['tagline'] = d['tvshowtitle']
			ilabels['album'] = d['tvshowtitle']
		if 'rating' in d:
			ilabels['rating'] = d['rating']
		if 'type' in d and d['type'] != 'nextPage':
			if d['type'] == 'video' or d['type'] == 'live' or d['type'] == 'date' or d['type'] == 'clip':
				ilabels['mediatype'] = 'video'
			elif d['type'] == 'shows' or d['type'] == 'season':
				ilabels['mediatype'] = 'season'
			elif d['type'] == 'episode':
				ilabels['mediatype'] = 'episode'
			else:
				ilabels['mediatype'] = 'video'
				
		ok=True
		liz=xbmcgui.ListItem(clearString(d.get('name','')))
		if d['type'] == 'audio':
			liz.setInfo( type="music", infoLabels=ilabels)
		else:
			liz.setInfo( type="Video", infoLabels=ilabels)
		liz.addStreamInfo('subtitle', {'language': 'deu'})
		art = {}
		art['thumb'] = d.get('thumb')
		art['landscape'] = d.get('thumb')
		art['poster'] = d.get('thumb')
		art['fanart'] = d.get('fanart',d.get('thumb',fanart))
		art['icon'] = d.get('channelLogo','')
		liz.setArt(art)
		
		if 'customprops' in d:
			for prop in d['customprops']:
				liz.setProperty(prop, d['customprops'][prop])
				
		if d.get('type',None) == 'video' or d.get('type',None) == 'live' or d.get('type',None) == 'date' or d.get('type',None) == 'clip' or d.get('type',None) == 'episode' or d.get('type',None) == 'audio':
			#xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="episodes" )
			liz.setProperty('IsPlayable', 'true')
			lists.append([u,liz,False])
		else:
			lists.append([u,liz,True])
		

	if len(l) > 0:
		type = l[0]['_type']
		if type == 'video' or type == 'live' or type == 'date' or type == 'clip' or type == 'episode':
			xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="episodes" )
		elif type == 'shows' or type == 'season':
			xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="tvshows" )
		else:
			xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="files" )
			
	xbmcplugin.addDirectoryItems(int(sys.argv[1]), lists)
	
def endOfDirectory():
	xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)	

def _buildUri(d):
	u = d.get('pluginpath',sys.argv[0])+'?'
	i = 0
	for key in d.keys():
		if not key.startswith('_'):
			if i > 0:
				u += '&'
			try:
				u += key + '=' + urllib.quote_plus(d[key])
			except:
				u += key + '=' + urllib.quote_plus(d[key].encode('utf-8'))
			i += 1
	return u
	
def _airedISO8601(d):
	iso = d['airedISO8601']
	try:
		tempdate = datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S')
	except TypeError:#workaround:
		tempdate = datetime(*(time.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S')[0:6]))
	offset = iso.replace(':','')[-5:]
	HH = offset[1:3]
	MM = offset[4:5]
	delta = timedelta(hours=int(HH),minutes=int(MM))
	#if offset.startswith('+'):
	#	tempdate += delta
	#else:
	#	tempdate -= delta
	return tempdate.strftime('%Y-%m-%d'), tempdate.strftime('%H:%M')
	
	
def get_params():
	param={}
	paramstring=sys.argv[2]
	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')
		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]= urllib.unquote_plus(splitparams[1])

	return param