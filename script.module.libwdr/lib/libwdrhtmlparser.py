# -*- coding: utf-8 -*-
import xbmc
import json
import libmediathek3 as libMediathek
import re
#import dateutil.parser

base = 'http://www1.wdr.de'


def parse(url):
	response = libMediathek.getUrl(url)
	s = response.split('<h2 class="headline">Suchergebnis</h2>')[-1]
	#xbmc.log(response)
	videos = s.split('<div class="media mediaA">')[1:]
	l = []
	for video in videos:
		d = {}
		#xbmc.log(video)
		d['_name'] = re.compile('<h3 class="headline">.+?>(.+?)<', re.DOTALL).findall(video)[0]
		d['_plot'] = re.compile('<p class="teasertext">.+?>(.+?)<', re.DOTALL).findall(video)[0]
		#d['date'] = re.compile('<p class="dachzeile">.+?>(.+?)<', re.DOTALL).findall(video)[0].replace('<strong>Video</strong>','')
		d['_thumb'] = re.compile('<img.+?src="(.+?)"', re.DOTALL).findall(video)[0]
		d['url'] = re.compile('<a href="(.+?)"', re.DOTALL).findall(video)[0]
		
		d['_type'] = 'video'
		d['mode'] = 'libWdrPlay'
		#xbmc.log(str(d))
		l.append(d)
		
	pages = re.compile('<div class="entry" data-ctrl-load_avsuche100-source=".+?<a href="(.+?)">(.+?)</a>', re.DOTALL).findall(response)
	xbmc.log(str(pages))
	nextPage = str(int(url.split('pageNumber=')[-1].split('&')[0]) + 1)
	for url,page in pages:
		if page == nextPage:
			l.append({'_type':'nextPage','url':base+url,'mode':'libWdrListSearch'})
		
	return l