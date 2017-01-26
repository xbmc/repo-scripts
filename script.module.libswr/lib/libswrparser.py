# -*- coding: utf-8 -*-
import libmediathek3 as libMediathek
import re

baseUrl = 'http://swrmediathek.de'

def getList(url,type,mode):
	response = libMediathek.getUrl(url)
	return _findLiEntries(response,type,mode)
	
def getDate(d,type,mode):
	d = abs(int(d))
	response = libMediathek.getUrl('http://swrmediathek.de/app-2/svp.html')
	day = re.compile('<ul data-role="listview" data-theme="c" data-divider-theme="d">(.+?)</ul>', re.DOTALL).findall(response)[d]
	return _findLiEntries(day,type,mode)[::-1]
	
def _findLiEntries(response,type,mode):
	items = re.compile('<li data-icon="false">(.+?)</li>', re.DOTALL).findall(response)
	l = []
	for item in items:
		d = {}
		d['_name'] = re.compile('<h3>(.+?)</h3>', re.DOTALL).findall(item.replace(' class="teaserLink"',''))[0]
		uri = re.compile('href="(.+?)"', re.DOTALL).findall(item)[0]
		if not uri.startswith('/app-2/'):
			uri = '/app-2/' + uri
		d['url'] = baseUrl + uri
		if 'data-src' in item:
			d['_thumb'] = baseUrl + re.compile('data-src="(.+?)"', re.DOTALL).findall(item)[0]
		else:
			d['_thumb'] = baseUrl + re.compile('src="(.+?)"', re.DOTALL).findall(item)[0]
		
		if '<p>' in item:
			d['_plot'] = re.compile('<p>(.+?)</p>', re.DOTALL).findall(item)[0]
			s = d['_plot'].split(' vom ')
			DDMMYYYY,HHMM = s[1].split(' | ')
			dsplit = DDMMYYYY.split('.')
			d['_aired'] = dsplit[2] + '-' + dsplit[1] + '-'  + dsplit[0] 
			d['_airedtime'] = HHMM.replace(' Uhr','')
			if len(d['_airedtime']) == 4:
				d['_airedtime'] = '0' + d['_airedtime']
			if '| Spielfilm' in d['_name']:
				d['_tvshowtitle'] = 'Spielfilm'
			else:
				d['_tvshowtitle'] = s[0]
		
		d['_type'] = type
		d['mode'] = mode
		l.append(d)
	return l

def getVideo(url):
	d = {}
	response = libMediathek.getUrl(url)
	file = re.compile('"file":"(.+?)"').findall(response)[0]
	if file.endswith('.m3u8'):
		d['media'] = [{'url':file, 'type':'video', 'stream':'HLS'}]
	elif file.endswith('.m.mp4'):
		s = file.split('/')
		video = 'http://hls-ondemand.swr.de/i/swr-fernsehen/'+s[4]+'/'+s[5]+'/'+s[6]+'.,xl,l,ml,m,sm,s,.mp4.csmil/master.m3u8'
		d['media'] = [{'url':video, 'type':'video', 'stream':'HLS'}]
	elif file.endswith('.mp3'):
		d['media'] = [{'url':file, 'type':'audio', 'stream':'http'}]
		
	
	sub = re.compile("lucy2captionArray\((.+?)\)").findall(response)[0]
	if sub != "''":
		d['subtitle'] = [{'url':sub.replace("'",""), 'type': 'ttml', 'lang':'de'}]
	try:
		name = re.compile("title = '(.+?)'").findall(response)[-1]
		plot = re.compile("descl = '(.+?)'").findall(response)[-1]
		thumb = re.compile("image = '(.+?)'").findall(response)[-1]
		d['metadata'] = {'name':name, 'plot': plot, 'thumb':thumb}
	except: pass	
	return d
 
def startTimeToInt(s):
	HH,MM,SS = s.split(":")
	return int(HH) * 60 + int(MM)