# -*- coding: utf-8 -*-
import xbmc
import json
import re
#import dateutil.parser
import libmediathek3 as libMediathek
base = 'http://www1.wdr.de'

def parseShows(letter):
	response = libMediathek.getUrl('http://www1.wdr.de/mediathek/video/sendungen-a-z/sendungen-'+letter.lower()+'-102.html')
	uls = re.compile('<ul  class="list">(.+?)</ul>', re.DOTALL).findall(response)
	l = []
	for ul in uls:
		lis = re.compile('<li >(.+?)</li>', re.DOTALL).findall(ul)
		for li in lis:
			d = {}

			d['url'] = base + re.compile('href="(.+?)"', re.DOTALL).findall(li)[0]
			d['_name'] = re.compile('<span>(.+?)</span>', re.DOTALL).findall(li)[0]
			thumb = re.compile('<img.+?src="(.+?)"', re.DOTALL).findall(li)[0].replace('~_v-ARDKleinerTeaser.jpg','~_v-original.jpg').replace('http//www','http://www')
			if thumb.startswith('http'):
				d['_thumb'] = thumb
			else:
				d['_thumb'] = base + thumb
			d['_type'] = 'dir'
			d['mode'] = 'libWdrListVideos'
			
			l.append(d)
		
	return l
	
def parseVideos(url):
	response = libMediathek.getUrl(url)
	typeA = re.compile('<div class="box".+?<a(.+?)>(.+?)</a>.+?<a(.+?)>(.+?)</a>', re.DOTALL).findall(response)
	l = []
	for href,show,href2,stuff in typeA:
		if '<div class="media mediaA video">' in stuff:
			d = {}
			d['url'] = base + re.compile('href="(.+?)"', re.DOTALL).findall(href2)[0]
			if '<h4' in stuff:
				d['_name'] = re.compile('<h4.+?>.+?<span class="hidden">Video:</span>(.+?)<', re.DOTALL).findall(stuff)[0].strip()
			else:
				d['_name'] = show.strip()
			if '<img' in stuff:
				d['_thumb'] = base + re.compile('<img.+?src="(.+?)"', re.DOTALL).findall(stuff)[0]
			d['_plot'] = re.compile('<p class="teasertext">(.+?)<', re.DOTALL).findall(stuff)[0]
			#TODO duration, ut
			d['_type'] = 'video'
			d['mode'] = 'libWdrPlay'
			
			l.append(d)
	return l
	
def parseVideo(url,signLang=False):
	response = libMediathek.getUrl(url)
	#'mediaObj': { 'url': 'http://deviceids-medp.wdr.de/ondemand/111/1114678.js'
	url2 = re.compile("'mediaObj': { 'url': '(.+?)'", re.DOTALL).findall(response)[0]
	response = libMediathek.getUrl(url2)
	import json
	j = json.loads(response[38:-2])
	
	videos = []
	subUrl = False
	for type in j['mediaResource']:
		xbmc.log(str(j['mediaResource'][type]))
		if type == 'dflt' or type == 'alt':
			if signLang and 'slVideoURL' in j['mediaResource'][type]:
				videos.append(j['mediaResource'][type]['slVideoURL'])
			else:
				videos.append(j['mediaResource'][type]['videoURL'])
		elif type == 'captionURL':
			subUrl = j['mediaResource']['captionURL']
	video = False
	for vid in videos:
		if vid.endswith('.m3u8'):
			video = vid
		elif vid.endswith('.f4m') and (not video or video.endswith('.mp4')):
			video = vid.replace('manifest.f4m','master.m3u8').replace('adaptiv.wdr.de/z/','adaptiv.wdr.de/i/')
		elif vid.endswith('.mp4') and not video:
			video = vid
	d = {}
	d['media'] = []
	d['media'].append({'url':video, 'type': 'video', 'stream':'HLS'})
	if subUrl:
		d['subtitle'] = []
		d['subtitle'].append({'url':subUrl, 'type': 'ttml', 'lang':'de'})
	return d
	
def startTimeToInt(s):
	HH,MM,SS = s.split(":")
	return int(HH) * 60 + int(MM)