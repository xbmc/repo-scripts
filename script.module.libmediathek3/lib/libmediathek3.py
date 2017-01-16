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


def play(d,external=False):
	listitem = xbmcgui.ListItem(path=d['media'][0]['url'])
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
		if 'plot' in d['metadata']:
			listitem.setInfo( type="Video", infoLabels={'Plot':d['metadata']['plot']})
	
	listitem.setSubtitles(subs)
	
	if external:
		xbmc.Player().play(d['media'][0]['url'], listitem)
	else:
		pluginhandle = int(sys.argv[1])
		xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
