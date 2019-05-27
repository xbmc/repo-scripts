#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import xbmc
import re
import libmediathek3utils as utils
import xbmcaddon
import HTMLParser
import xbmcvfs

subFile = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')+'/ttml.srt').decode('utf-8')

def ttml2Srt(url):
	return _newSubtitle(url)

def _createProfilePath():
	if utils.f_exists(xbmcaddon.Addon().getAddonInfo('profile')):
		return
	else:
		utils.f_mkdir(xbmcaddon.Addon().getAddonInfo('profile'))
		return
def _newSubtitle(url):
	_createProfilePath()
	if xbmcvfs.exists(subFile):
		xbmcvfs.delete(subFile)
	#content = utils.getUrl(url)
	try:
		content = utils.getUrl(url)
	except:
		content = ""
	content = content.replace('\0','').replace('<tt:','<').replace('</tt:','</')
	if content:
		#utils.log(str(content))
		d = _stylesSetup(re.compile('<styling>(.+?)</styling>', re.DOTALL).findall(content)[0])
		div = re.compile('<div.+?>(.+?)</div>', re.DOTALL).findall(content)[0]
		p = re.compile('<(.+?)</p>', re.DOTALL).findall(div)
		i = 1
		buffer = ''
		for part in p:
			if '<span' in part:
				part = part.replace('begin="1','begin="0').replace('end="1','end="0').replace('\n','').replace('<br/>','\n')
				begin = re.compile('begin="(.+?)"').findall(part)[0]
				begin = begin.replace(".",",")[:-1]
				end = re.compile('end="(.+?)"').findall(part)[0]
				end = end.replace(".",",")[:-1]
				s = part.split('>')[0]
				part = part.replace(s+'>','')
				part = part.replace('<br />','\n')
				if 'style=' in s:
					style = re.compile('style="(.+?)"').findall(s)[0]
					if d[style]:
						part = '<font color="'+d[style]+'">'+part+'</font>'
				match = re.compile('<(.+?)>').findall(part)
				for entry in match:
					if entry.startswith('span'):
						if 'style' in entry:
							style = re.compile('style="(.+?)"').findall(entry)[0]
							part = part.replace('<'+entry+'>','<font color="'+d[style]+'">')
						else:
							part = part.replace('<'+entry+'>','')
					elif entry.startswith('/span'):
						part = part.replace('</span>','</font>')
					else:
						part = part.replace('<'+entry+'>','')
				

				buffer += str(i) + '\n'
				buffer += begin+" --> "+end+"\n"
				buffer += part + '\n\n'
				i+=1
		buffer = buffer.replace('            ','').replace('           ','').replace('  ',' ').replace(' \n','\n')
		utils.f_write(subFile,buffer)
		utils.log(subFile)
		return subFile


def _stylesSetup(styles):
	d = {}
	styles = styles.replace('tt:','').replace('xml:','')
	match_styles = re.compile('<style(.+?)>', re.DOTALL).findall(styles)
	for style in match_styles:
		id = re.compile('id="(.+?)"', re.DOTALL).findall(style)[0]
		if 'color=' in style:
			color = re.compile('color="(.+?)"', re.DOTALL).findall(style)[0]
		else:
			color = False
		d[id] = color
	return d

"""
def _newSubtitle(url):
	if xbmcvfs.exists(subFile):
		xbmcvfs.delete(subFile)
	try:
		content = utils.getUrl(url)
	except:
		content = ""
	if content:
		d = _stylesSetup(re.compile('<tt:styling>(.+?)</tt:styling>', re.DOTALL).findall(content)[0])
		div = re.compile('<tt:div.+?>(.+?)</tt:div>', re.DOTALL).findall(content)[0]
		p = re.compile('<tt:p(.+?)</tt:p>', re.DOTALL).findall(div)
		i = 1
		buffer = ''
		for part in p:
			if '<tt:span' in part:
				part = part.replace('begin="1','begin="0').replace('end="1','end="0').replace('\n','').replace('<tt:br/>','\n')
				begin = re.compile('begin="(.+?)"').findall(part)[0]
				begin = begin.replace(".",",")[:-1]
				end = re.compile('end="(.+?)"').findall(part)[0]
				end = end.replace(".",",")[:-1]
				s = part.split('>')[0]
				part = part.replace(s+'>','')
				part = part.replace('<tt:br />','\n')
				if 'style=' in s:
					style = re.compile('style="(.+?)"').findall(s)[0]
					if d[style]:
						part = '<font color="'+d[style]+'">'+part+'</font>'
				match = re.compile('<(.+?)>').findall(part)
				for entry in match:
					if entry.startswith('tt:span'):
						if 'style' in entry:
							style = re.compile('style="(.+?)"').findall(entry)[0]
							part = part.replace('<'+entry+'>','<font color="'+d[style]+'">')
						else:
							part = part.replace('<'+entry+'>','')
					elif entry.startswith('tt:/span'):
						part = part.replace('</tt:span>','</font>')
					else:
						part = part.replace('<'+entry+'>','')
				

				buffer += str(i) + '\n'
				buffer += begin+" --> "+end+"\n"
				buffer += part + '\n\n'
				i+=1
		buffer = buffer.replace('            ','').replace('           ','').replace('  ',' ').replace(' \n','\n')
		utils.f_write(subFile,buffer)
		return subFile


def _stylesSetup(styles):
	d = {}
	styles = styles.replace('tt:','').replace('xml:','')
	match_styles = re.compile('<style(.+?)>', re.DOTALL).findall(styles)
	for style in match_styles:
		id = re.compile('id="(.+?)"', re.DOTALL).findall(style)[0]
		if 'color=' in style:
			color = re.compile('color="(.+?)"', re.DOTALL).findall(style)[0]
		else:
			color = False
		d[id] = color
	return d
"""

def _cleanTitle(title,html=True):
	if html:
		title = HTMLParser.HTMLParser().unescape(title)
		return title.encode("utf-8")
	else:
		title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#034;", "\"").replace("&#039;", "'").replace("&quot;", "\"").replace("&szlig;", "ß").replace("&ndash;", "-")
		title = title.replace("&Auml;", "Ä").replace("&Uuml;", "Ü").replace("&Ouml;", "Ö").replace("&auml;", "ä").replace("&uuml;", "ü").replace("&ouml;", "ö").replace("&eacute;", "é").replace("&egrave;", "è")
		title = title.replace("&#x00c4;","Ä").replace("&#x00e4;","ä").replace("&#x00d6;","Ö").replace("&#x00f6;","ö").replace("&#x00dc;","Ü").replace("&#x00fc;","ü").replace("&#x00df;","ß")
		title = title.replace("&apos;","'").strip()
		return title