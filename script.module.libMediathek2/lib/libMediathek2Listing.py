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

from libMediathek2Utils import clearString

icon = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')+'/icon.png').decode('utf-8')
fanart = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')+'/fanart.jpg').decode('utf-8')

def addEntries(l):
	lists = []
	for dict in l:
		u = _buildUri(dict)
		newdict = {}
		for key in dict:
			if key.startswith('_'):
				if isinstance(dict[key], unicode):
					dict[key] = dict[key].encode('utf-8', 'ignore')
				newdict[key[1:]] = dict[key]
				newdict[key[1:]] = dict[key]
			elif isinstance(dict[key], unicode):
				newdict[key] = dict[key].encode('utf-8', 'ignore')
			else:
				newdict[key] = dict[key]
		dict = newdict
		if 'type' in dict and dict['type'] == 'nextPage':
			dict['name'] = translation(31040)
			if not 'mode' in dict:
				dict['mode'] = get_params()['mode']
		if isinstance(dict["name"], unicode):
			dict["name"] = dict["name"].encode('utf-8')
		dict["name"] = clearString(dict["name"])
		if 'airedISO8601' in dict or 'airedISO8601A' in dict:
			dict['aired'],dict['airedtime'] = _airedISO8601(dict)
			
		if 'type' in dict and dict['type'] == 'date' and 'airedtime' in dict:
			dict["name"] = '(' + str(dict["airedtime"]) + ') ' + dict["name"]
		elif 'type' in dict and dict['type'] == 'date' and 'time' in dict:
			dict["name"] = '(' + str(dict["date"]) + ') ' + dict["name"]
			
		ilabels = {
			"Title": clearString(dict.get('name','')),
			"Plot": clearString(dict.get('plot','')),
			"Plotoutline": clearString(dict.get('plot','')),
			"Duration": dict.get('duration',''),
			"Mpaa": dict.get('mpaa',''),
			"Aired": dict.get('aired',''),
			"Studio": dict.get('channel',''),
			}
		if 'episode' in dict: 
			ilabels['Episode'] = dict['episode']
		if 'Season' in dict: 
			ilabels['Season'] = dict['season']
		if 'tvshowtitle' in dict: 
			ilabels['tvshowtitle'] = dict['tvshowtitle']
			ilabels['tagline'] = dict['tvshowtitle']
			ilabels['album'] = dict['tvshowtitle']
		if 'rating' in dict:
			ilabels['rating'] = dict['rating']
		ok=True
		liz=xbmcgui.ListItem(clearString(dict.get('name','')))
			
		liz.setInfo( type="Video", infoLabels=ilabels)
		liz.addStreamInfo('subtitle', {'language': 'deu'})
		art = {}
		art['thumb'] = dict.get('thumb')
		art['landscape'] = dict.get('thumb')
		art['poster'] = dict.get('thumb')
		art['fanart'] = dict.get('fanart',dict.get('thumb',fanart))
		art['icon'] = dict.get('channelLogo','')
		liz.setArt(art)
		if 'type' in dict:
			if dict['type'] == 'clip':
				xbmc.log('ignoring clip')
			elif dict.get('type',None) == 'video' or dict.get('type',None) == 'live' or dict.get('type',None) == 'date':
				xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="episodes" )
				liz.setProperty('IsPlayable', 'true')
				lists.append([u,liz,False])
			elif 'type' in dict and dict['type'] == 'nextPage':
				lists.append([u,liz,True])
			elif dict['type'] == 'shows':
				xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="tvshows" )
				lists.append([u,liz,True])
			else:
				xbmcplugin.setContent( handle=int( sys.argv[ 1 ] ), content="files" )
				lists.append([u,liz,True])
		else:
			lists.append([u,liz,True])
			
	xbmcplugin.addDirectoryItems(int(sys.argv[1]), lists)

def _buildUri(dict):
	u = dict.get('pluginpath',sys.argv[0])+'?'
	i = 0
	for key in dict.keys():
		if not key.startswith('_'):
			if i > 0:
				u += '&'
			u += key + '=' + urllib.quote_plus(dict[key])
			i += 1
	return u
	
def _airedISO8601(dict):
	iso = dict['airedISO8601']			
	try:
		tempdate = datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S')
	except TypeError:#workaround:
		tempdate = datetime(*(time.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S')[0:6]))
	offset = iso.replace(':','')[-5:]
	HH = offset[1:3]
	MM = offset[4:5]
	delta = timedelta(hours=int(HH),minutes=int(MM))
	if offset.startswith('+'):
		tempdate += delta
	else:
		tempdate -= delta
	return tempdate.strftime('%Y-%m-%d'), tempdate.strftime('%H:%S')
	
	
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