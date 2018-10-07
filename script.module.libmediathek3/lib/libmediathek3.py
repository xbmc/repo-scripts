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
		if item.get('stream','').lower() == 'audio':
			url = item['url']
			streamType = 'AUDIO'
	listitem = xbmcgui.ListItem(path=url)
	if streamType == 'DASH':
		listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
		listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
		#listitem.setProperty('inputstream.adaptive.stream_headers','User-Agent=Mozilla%2F5.0%20%28Windows%20NT%206.1%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F63.0.3239.84%20Safari%2F537.36')
		listitem.setMimeType('application/dash+xml')
		listitem.setContentLookup(False)
	elif streamType == 'HLS':
		listitem.setMimeType('application/vnd.apple.mpegurl')
		listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
		listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
		listitem.setContentLookup(False)
	#elif streamType == 'MP4':
	#	listitem.setMimeType('application/dash+xml')
	#	listitem.setContentLookup(False)

	return listitem,url

def play(d,external=False):
	#listitem = xbmcgui.ListItem(path=url)
	listitem,url = _chooseBitrate(d['media'])	
	
	i = 0
	if 'subtitle' in d:
		subs = []
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
		listitem.setSubtitles(subs)
	
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
		
	if 'header' in d['media']:
		#listitem.setProperty('media_headers',d['media']['header'])
		#listitem.setProperty('inputstream.adaptive.media_headers',d['media']['header'])
		listitem.setProperty('inputstream.adaptive.stream_headers',d['media']['header'])
	
	if external:
		xbmc.Player().play(url, listitem)
	else:
		pluginhandle = int(sys.argv[1])
		xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
