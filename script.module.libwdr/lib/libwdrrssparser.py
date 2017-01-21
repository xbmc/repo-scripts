# -*- coding: utf-8 -*-
import xbmc
import json
import libmediathek3 as libMediathek
import re
#import dateutil.parser

base = 'http://www1.wdr.de'

def parseVideos(url):#TODO remove "mehr"
	if not url.endswith('index.html'):
		l = len(url.split('/')[-1])
		url = url[:-l] + 'index.html'
	response = libMediathek.getUrl(url).decode('utf-8')
	feed = re.compile('<link rel="alternate".+?href="(.+?)"').findall(response)[0]
	feed = base + feed.replace('.feed','~_format-mp111_type-rss.feed')
	return parseFeed(feed)
	
def parseFeed(feed,type=False):
	response = libMediathek.getUrl(feed)
	items = re.compile('<item>(.+?)</item>', re.DOTALL).findall(response)
	l = []
	for item in items:
		d = {}
		dctype = re.compile('<dc:type>(.+?)</dc:type>', re.DOTALL).findall(item)[0]
		if 'Video' in dctype:# or (dctype == 'Sportnachricht - sportschau.de' and '<title>' in item):
			d['_name'] = re.compile('<title>(.+?)</title>', re.DOTALL).findall(item)[0]
			d['url'] = re.compile('<link>(.+?)</link>', re.DOTALL).findall(item)[0]
			if '<content:encoded>' in item:
				d['_plot'] = re.compile('<content:encoded>(.+?)</content:encoded>', re.DOTALL).findall(item)[0].replace('\n ','\n')
			d['_channel'] = re.compile('<dc:creator>(.+?)</dc:creator>', re.DOTALL).findall(item)[0]
			d['_tvshowtitle'] = re.compile('<mp:topline>(.+?)</mp:topline>', re.DOTALL).findall(item)[0]
			d['_thumb'] = _chooseThumb(re.compile('<mp:image>(.+?)</mp:image>', re.DOTALL).findall(item))
			
			dcdate = re.compile('<dc:date>(.+?)</dc:date>', re.DOTALL).findall(item)[0]#TODO
			s = dcdate.split('T')
			d['_aired'] = s[0]
			t = s[1].replace('Z','').split(':')
			d['_airedtime'] = str(int(t[0])+2) + ':' + t[1]
			d['sort'] = s[1].replace('Z','').replace(':','')
			if len(d['_airedtime']) == 4:
				d['_airedtime'] = '0' + d['_airedtime']
			if type:
				d['_type'] = type
			else:
				d['_type'] = 'video'
			d['mode'] = 'libWdrPlay'
			l.append(d)
	return l

def _chooseThumb(thumbs):
	for thumb in thumbs:
		w = re.compile('<mp:width>(.+?)</mp:width>', re.DOTALL).findall(thumb)[0]
		h = re.compile('<mp:height>(.+?)</mp:height>', re.DOTALL).findall(thumb)[0]
		if w == '310' and h == '174':
			return re.compile('<mp:data>(.+?)</mp:data>', re.DOTALL).findall(thumb)[0]