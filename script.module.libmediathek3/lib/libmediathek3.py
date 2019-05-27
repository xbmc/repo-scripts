# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import sys

from libmediathek3utils import *
from libmediathek3listing import *
from libmediathek3ttml2srt import *
from libmediathek3premadedirs import *
from libmediathek3dialogs import *
	
#translation = xbmcaddon.Addon(id='script.module.libmediathek3').getLocalizedString
"""
prefererdLang = ['de','en','fr']
prefererdSub = ['de','en','fr']
subtitleenabled = False
subtitleenabled = True
"""

def _chooseBitrate(l):
	bitrate = 0
	url = False
	streamType = False
	for item in l:
		if item.get('stream','').lower() == 'hls':#prefer hls
			url = item['url']
			streamType = 'HLS'
			break
		if item.get('stream','').lower() == 'dash':
			url = item['url']
			streamType = 'DASH'
		if item.get('stream','').lower() == 'mp4' and item.get('bitrate',0) >= bitrate:
			bitrate = item.get('bitrate',0)
			url = item['url']
			streamType = 'MP4'
	listitem = xbmcgui.ListItem(path=url)
	if streamType == 'DASH':
		listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
		listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
	return listitem,url

def play(d,external=False):
	"""
	if 'lang' in d['media'][0]:
		url = _chooseBitrate(d['media'])
		#""
		languageFound = False
		l = []
		lsubtitles = []
		for lang in prefererdLang:
			for item in d['media']:
				if lang == item['lang']:
					if 'subtitlelang' in item:
						lsubtitles.append(item)
					else:
						l.append(item)
					languageFound = True
			if languageFound:
				log('###############')
				if subtitleenabled and len(lsubtitles) > 0:
					url = _chooseBitrate(lsubtitles)
				elif len(l) == 0 and len(lsubtitles) > 0:
					url = _chooseBitrate(lsubtitles)
				elif lang != prefererdLang and len(lsubtitles) > 0:
					url = _chooseBitrate(lsubtitles)
				else:
					url = _chooseBitrate(l)
				break
		#""
		if not languageFound:
			url = _chooseBitrate(d['media'])
	else:
		url = _chooseBitrate(d['media'])
	"""	
			
	#listitem = xbmcgui.ListItem(path=url)
	listitem,url = _chooseBitrate(d['media'])	
	
	subs = []
	i = 0
	if 'subtitle' in d:
		for subtitle in d['subtitle']:
			if subtitle['type'] == 'srt':
				subs.append(subtitle['url'])
			elif subtitle['type'] == 'ttml':
				subFile = ttml2Srt(subtitle['url'])
				subs.append(subFile)
			elif subtitle['type'] == 'webvtt':
				import libmediathek3webvtt2srt 
				subFile = libmediathek3webvtt2srt.webvtt2Srt(subtitle['url'])
				subs.append(subFile)
			else:
				log('Subtitle format not supported: ' + subtitle['type'])
	
	if 'metadata' in d:
		ilabels = {}
		if 'plot' in d['metadata']:
			ilabels['Plot'] = d['metadata']['plot']
		if 'name' in d['metadata']:
			ilabels['Title'] = d['metadata']['name']
		listitem.setInfo( type="Video", infoLabels=ilabels)
		
		art = {}
		if 'thumb' in d['metadata']:
			art['thumb'] = d['metadata']['thumb']
		listitem.setArt(art)
	listitem.setSubtitles(subs)
	
	
	if external:
		xbmc.Player().play(url, listitem)
	else:
		pluginhandle = int(sys.argv[1])
		xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
