# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import sys

from libMediathek2Utils import *
from libMediathek2Listing import *
from libMediathek2Ttml2Srt import *
from libMediathek2PremadeDirs import *
	
translation = xbmcaddon.Addon(id='script.module.libMediathek2').getLocalizedString


def play(d):
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
			#elif subtitle['type'] == 'vtt':
			#	subFile = vtt2Srt(subtitle['url'])
			#	subs.append(subFile)
			else:
				log('Subtitle format not supported: ' + subtitle['type'])
	if 'metadata' in d:
		if 'plot' in d['metadata']:
			listitem.setInfo( type="Video", infoLabels={'Plot':d['metadata']['plot']})
	listitem.setSubtitles(subs)
	pluginhandle = int(sys.argv[1])
	xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
