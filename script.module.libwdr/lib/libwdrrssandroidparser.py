# -*- coding: utf-8 -*-
import json
import requests
import re
#import dateutil.parser

base = 'http://www1.wdr.de'


def parseShows(id):
	response = requests.get(f'{base}/{id}~_variant-android.mobile').text
	items = re.compile('<mp:additionallink>(.+?)</mp:additionallink>', re.DOTALL).findall(response)
	#creator = re.compile('<dc:creator>(.+?)</dc:creator>', re.DOTALL).findall(response)[0]
	result = {'items':[],'pagination':{'currentPage':0}}
	for item in items:
		#print(item)
		if 'WDR Audiothek' in re.compile('<category>(.+?)</category>', re.DOTALL).findall(response):
			d = {'type':'dir', 'params':{'mode':'libWdrListPodcast'}, 'metadata':{'art':{}}}
		else:
			d = {'type':'dir', 'params':{'mode':'libWdrListId'}, 'metadata':{'art':{}}}
		d['metadata']['name'] = re.compile('<mp:label>(.+?)</mp:label>', re.DOTALL).findall(item)[0]
		#if len(l) != 0 and d['name'] == l[-1]['name']: continue
		#d['id'],extension = re.compile('<mp:link>(.+?)</mp:link>', re.DOTALL).findall(item)[0].split('/')[-1].split('~')
		d['params']['id'] = re.compile('<mp:link>(.+?)</mp:link>', re.DOTALL).findall(item)[0].split('/')[-1].split('~')[0]
		d['metadata']['art']['thumb'] = _chooseThumb(re.compile('<mp:image>(.+?)</mp:image>', re.DOTALL).findall(item))
		result['items'].append(d)
	return result

def _chooseThumb(thumbs):
	for thumb in thumbs:
		w = re.compile('<mp:width>(.+?)</mp:width>', re.DOTALL).findall(thumb)[0]
		h = re.compile('<mp:height>(.+?)</mp:height>', re.DOTALL).findall(thumb)[0]
		if w == '310' and h == '174':
			return re.compile('<mp:data>(.+?)</mp:data>', re.DOTALL).findall(thumb)[0]