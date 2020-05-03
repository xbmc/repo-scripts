#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import requests
import libmediathek4utils as lm4utils

bracketLookup = {
	'<c.textWhite>':   '<font color="#ffffff">',
	'<c.textYellow>':  '<font color="#ffff00">',
	'<c.textCyan>':    '<font color="#00ffff">',
	'<c.textRed>':     '<font color="#ff0000">',
	'<c.textGreen>':   '<font color="#00ff00">',
	'<c.textBlue>':    '<font color="#0000ff">',
	'<c.textMagenta>': '<font color="#ff00ff">',
	'<c.textMagenta>': '<font color="#ff00ff">',
	'</c>':            '</font>',
}
def webvtt2Srt(url):
	webvtt = requests.get(url).text
	webvtt = webvtt.replace('\r','')
	s = webvtt.split('\n\n')
	i = 1
	if s[1].strip() == '':
		i = 2
	srt = ''
	n = 1
	while i < len(s):
		j = 0
		for line in s[i].split('\n'):
			if j == 0:
				srt += f'{str(n)}\n'
				n += 1

			if j == 1:
				t = line.split('-->')
				srt += t[0].strip().replace('.',',') + ' --> ' + t[1].strip().replace('.',',') + '\n'
				
			if j > 1:
				for bracket in bracketLookup:
					line = line.replace(bracket,bracketLookup[bracket])
				srt += line + '\n'
			j += 1
		srt += '\n'
		i += 1
	
	subFile = lm4utils.pathUserdata('/webvtt.srt')
	lm4utils.f_write(subFile,srt)
	return subFile