# -*- coding: utf-8 -*-
import requests
import re

base = 'http://www1.wdr.de'

def parseVideos(url):#TODO remove "mehr"
	if not url.endswith('index.html'):
		l = len(url.split('/')[-1])
		url = url[:-l] + 'index.html'
	response = libMediathek.getUrl(url).decode('utf-8')
	feed = re.compile('<link rel="alternate".+?href="(.+?)"').findall(response)[0]
	feed = base + feed.replace('.feed','~_format-mp111_type-rss.feed')
	return parseFeed(feed)
	
def parseId(id):
	return parseFeed(f'{base}/{id}~_format-mp111_type-rss.feed')

def parseFeed(feed,type='video'):
	requests.head(feed)
	response = requests.get(feed).text
	items = re.compile('<item>(.+?)</item>', re.DOTALL).findall(response)
	result = {'items':[],'pagination':{'currentPage':0}}
	for item in items:
		dctype = re.compile('<dc:type>(.+?)</dc:type>', re.DOTALL).findall(item)[0]
		WLdctypes = ['Video','Radio','Audio']
		if any(WLdctype in dctype for WLdctype in WLdctypes):
			if 'Video' in dctype or 'Audio' in dctype:
				d = {'type':type, 'params':{'mode':'libWdrPlay'}, 'metadata':{'art':{}}}
			if 'Radio' in dctype:
				d = {'type':'audio', 'params':{'mode':'libWdrPlayNimex'}, 'metadata':{'art':{}}}
			d['metadata']['name'] = re.compile('<title>(.+?)</title>', re.DOTALL).findall(item)[0].replace('&amp;','&')
			d['params']['url'] = re.compile('<link>(.+?)</link>', re.DOTALL).findall(item)[0]
			d['params']['id'] = re.compile('<link>(.+?)</link>', re.DOTALL).findall(item)[0].split('/')[-1].split('.')[0]
			if '<content:encoded>' in item:
				d['metadata']['plot'] = re.compile('<content:encoded>(.+?)</content:encoded>', re.DOTALL).findall(item)[0].replace('\n ','\n')
			d['metadata']['channel'] = re.compile('<dc:creator>(.+?)</dc:creator>', re.DOTALL).findall(item)[0]
			d['metadata']['tvshowtitle'] = re.compile('<mp:topline>(.+?)</mp:topline>', re.DOTALL).findall(item)[0]
			if '<mp:expires>' in item:
				d['metadata']['ttl'] = re.compile('<mp:expires>(.+?)</mp:expires>', re.DOTALL).findall(item)[0]
			d['metadata']['art']['thumb'] = _chooseThumb(re.compile('<mp:image>(.+?)</mp:image>', re.DOTALL).findall(item))
			
			dcdate = re.compile('<dc:date>(.+?)</dc:date>', re.DOTALL).findall(item)[0]#TODO
			s = dcdate.split('T')
			d['metadata']['aired'] = s[0]
			t = s[1].replace('Z','').split(':')
			d['metadata']['airedtime'] = str(int(t[0])+2) + ':' + t[1]
			d['metadata']['sort'] = s[1].replace('Z','').replace(':','')
			if len(d['metadata']['airedtime']) == 4:
				d['metadata']['airedtime'] = '0' + d['metadata']['airedtime']
			result['items'].append(d)
	return result

def _chooseThumb(thumbs):
	for thumb in thumbs:
		w = re.compile('<mp:width>(.+?)</mp:width>', re.DOTALL).findall(thumb)[0]
		h = re.compile('<mp:height>(.+?)</mp:height>', re.DOTALL).findall(thumb)[0]
		if w == '310' and h == '174':
			return re.compile('<mp:data>(.+?)</mp:data>', re.DOTALL).findall(thumb)[0]