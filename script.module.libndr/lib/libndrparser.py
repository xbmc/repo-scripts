# -*- coding: utf-8 -*-
import libmediathek3 as libMediathek
import re

baseUrl = 'http://ndr.de'
	
def getDate(yyyymmdd):
	l = []
	response = libMediathek.getUrl('http://www.ndr.de/mediathek/sendung_verpasst/epg1490_date-'+yyyymmdd+'_display-onlyvideo.html')
	
	response = response.split('<div id="program_schedule">')[-1]
	videos = re.compile('<li\nclass="program hasVideo ">(.+?)</li>', re.DOTALL).findall(response.replace('<li><span class="icon icon_favorit"></span></li>',''))
	for video in videos:
		d = {}#TODO rating
		d['_thumb'] = re.compile('<img src="(.+?)"', re.DOTALL).findall(video)[0]
		if not 'www.' in d['_thumb']:
			d['_thumb'] = 'http://www.ndr.de' + d['_thumb'] 
			
		d['_name'] = re.compile('title="(.+?)"', re.DOTALL).findall(video)[2]
		d['id'] = re.compile('<a href=".+?,(.+?)\.html"', re.DOTALL).findall(video)[1]
		
		d['_airedtime'] = re.compile('<strong class="time">(.+?)</strong>', re.DOTALL).findall(video)[0]
		d['_plot'] = re.compile('<div class="subtitle">(.+?)<', re.DOTALL).findall(video)[0].replace('<div class="rating_wrapper">','')#Bodge
		MM,SS = re.compile('<span class="icon icon_video" aria-label="L&auml;nge"></span>(.+?)</div>', re.DOTALL).findall(video)[0].split(':')
		d['_duration'] = str(int(MM) * 60 + int(SS))
		d['mode'] = 'libNdrPlay'
		d['_type'] = 'date'
		l.append(d)
	return l
 
def parseShows():
	response = libMediathek.getUrl('http://www.ndr.de/mediathek/sendungen_a-z/index.html')
	videos = re.compile('<section class="columnedlist">(.+?)<div id="footer">', re.DOTALL).findall(response)[0]
	l = []
	match = re.compile('<a href="(.+?)".+?>(.+?)</a>', re.DOTALL).findall(videos)
	for url,name in match:
		d = {}
		d['url'] = baseUrl + url
		d['_name'] = name
		d['_type'] = 'dir'
		d['mode'] = 'libNdrListVideos'
		l.append(d)
	return l
	
def parseVideos(url):
	response = libMediathek.getUrl(url)
	s = response.split('<div class="pagepadding">')
	s2 = s[-1].split('<div class="pagination">')
	
	videos = re.compile('<div class="modulepadding">.+?<img src="(.+?)".+?<span class="icon icon_video"></span>(.+?)<.+?<a href="(.+?)".+?>(.+?)</a>.+?<p>(.+?)<', re.DOTALL).findall(s2[0])
	l = []
	for thumb,duration,url,name,plot in videos:
		d = {}
		MM,SS = duration.split(' ')[0].split(':')
		d['_duration'] = str(int(MM) * 60 + int(SS))
		d['id'] = url.replace('.html','').split(',')[-1]
		d['_name'] = name
		d['_thumb'] = baseUrl + thumb.replace('-einspaltig.jpg','-zweispaltig.jpg')
		d['_plot'] = plot
		d['_type'] = 'video'
		d['mode'] = 'libNdrPlay'
			
		l.append(d)
	
	if len(s2) > 1 and '<a title="weiter" href="' in s2[1]:
		d = {}
		d['url'] = baseUrl + re.compile('<a title="weiter" href="(.+?)"', re.DOTALL).findall(s2[1])[0]
		d['_type'] = 'nextPage'
		d['mode'] = 'libNdrListVideos'
		l.append(d)
		
	return l
	