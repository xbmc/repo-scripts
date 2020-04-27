#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import requests
import html
import libmediathek4utils as lm4utils

def ttml2Srt(url):
	content = requests.get(url).text
	content = content.replace('\0','').replace('<tt:','<').replace('</tt:','</')
	if content:
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
				part = ''.join([l.strip() + '\n' for l in part.splitlines()])
				part = re.sub('(\n){2,}','\n',part)
				part = html.unescape(part)
				buffer += str(i) + '\n'
				buffer += begin+" --> "+end+"\n"
				buffer += part.strip() + '\n\n'
				i+=1

		subFile = lm4utils.pathUserdata('/ttml.srt')
		lm4utils.f_write(subFile,buffer)
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

