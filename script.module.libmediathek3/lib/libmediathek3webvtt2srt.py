#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import xbmc
import re
import libmediathek3utils as utils
import xbmcaddon
import HTMLParser
import xbmcvfs

subFile = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'/webvtt.srt').decode('utf-8')

bracketLookup = {
	'<c.textWhite>':	'<font color="#ffffff">',
	'<c.textYellow>':	'<font color="#ffff00">',
	'<c.textCyan>':		'<font color="#00ffff">',
	'<c.textRed>':		'<font color="#ff0000">',
	'<c.textGreen>':	'<font color="#00ff00">',
	'<c.textBlue>':		'<font color="#0000ff">',
	'<c.textMagenta>':	'<font color="#ff00ff">',
	'<c.textMagenta>':	'<font color="#ff00ff">',
	'</c>':				'</font>',
}
def webvtt2Srt(url):
	if xbmcvfs.exists(subFile):
		xbmcvfs.delete(subFile)
	
	webvtt = utils.getUrl(url)
	s = webvtt.split('\n\n')
	i = 1
	srt = ''
	while i < len(s):
		j = 0
		for line in s[i].split('\n'):
			if j == 0:
				srt += line + '\n'
			elif j == 1:
				t = line.split(' ')
				srt += t[0][:-1].replace('.',',') + ' --> ' + t[2][:-1].replace('.',',') + '\n'
			else:
				for bracket in bracketLookup:
					line = line.replace(bracket,bracketLookup[bracket])
				srt += line + '\n'
			j += 1
		srt += '\n'
		i += 1
	
	f = xbmcvfs.File(subFile, 'w')
	f.write(srt)
	f.close()
	return subFile