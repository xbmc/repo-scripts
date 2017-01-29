# -*- coding: utf-8 -*-
import xbmc
import json
import libmediathek3 as libMediathek
import re
from operator import itemgetter
#import xml.etree.ElementTree as ET

	
def getDate(yyyymmdd):
	l = []
	response = libMediathek.getUrl('http://www.hr-online.de/website/fernsehen/sendungen/')
	match = re.compile("<div class='dayDate' id='(.+?)' style='cursor:pointer;'>(.+?)</div>", re.DOTALL).findall(response)
	
	yyyy,mm,dd = yyyymmdd.split('-')
	if mm.startswith('0'):
		mm = mm[1:]
	if dd.startswith('0'):
		dd = dd[1:]
	
	url = False
	for id,date in match:
		if date == dd + '. ' + mm + '.':
			id = 0 - int(id)
			url = re.compile("loadPlayItems\('(.+?)'\);", re.DOTALL).findall(response)[id]
			
	if not url:
		return []
	
	response = libMediathek.getUrl(url).decode('cp1252').encode('utf-8')
	items = re.compile('<item>(.+?)</item>', re.DOTALL).findall(response)
	for item in items:
		#TODO showname
		d = {}
		d['_name'] = re.compile('<title>(.+?)</title>', re.DOTALL).findall(item)[0].replace(' - ganze Sendung','')
		if '<description>' in item:
			d['_plot'] = re.compile('<description>(.+?)</description>', re.DOTALL).findall(item)[0]
		d['url'] = re.compile('<jwplayer:source.+?file="(.+?)"', re.DOTALL).findall(item)[0]
		if '<jwplayer:track kind="captions"' in item:
			d['subUrl'] = re.compile('<jwplayer:track.+?file="(.+?)"', re.DOTALL).findall(item)[0]
		d['thumb'] = re.compile('<!\[CDATA\[(.+?)\]\]>', re.DOTALL).findall(item)[0].strip()
		HH,MM,SS = re.compile('duration="(.+?)"', re.DOTALL).findall(item)[0].split(':')
		d['_duration'] = str(int(HH) * 3600 + int(MM) * 60 + int(SS))
		day,time = re.compile('<jwplayer:date>(.+?)</jwplayer:date>', re.DOTALL).findall(item)[0].split(' ')
		d['_aired'] = day.replace('.','-')
		d['_airedtime'] = time
		#d['_'] = re.compile('<jwplayer:author>(.+?)</jwplayer:author>', re.DOTALL).findall(item)[0]
		d['_type'] = 'date'
		d['mode'] = 'libHrPlay'
		l.append(d)
	l = sorted(l, key=itemgetter('_airedtime')) 
	return l