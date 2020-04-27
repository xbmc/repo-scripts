# -*- coding: utf-8 -*-
import requests
import re

#import dateutil.parser

base = 'http://www1.wdr.de/'

def parsePodcasts(id):
	response = requests.get(f'{base}/{id}.podcast').text
	items = re.compile('<item>(.+?)</item>', re.DOTALL).findall(response)
	fanart = re.compile('<itunes:image href="(.+?)"', re.DOTALL).findall(response)[0]
	result = {'items':[],'pagination':{'currentPage':0}}
	for item in items:
		d = {'type':'audio', 'params':{'mode':'libWdrPlayDirect','stream':'audio'}, 'metadata':{'art':{}}}
		d['metadata']['name'] = re.compile('<title>(.+?)</title>', re.DOTALL).findall(item)[0]
		d['metadata']['plot'] = re.compile('<description>(.+?)</description>', re.DOTALL).findall(item)[0]
		d['params']['url'] = re.compile('url="(.+?)"', re.DOTALL).findall(item)[0]#.replace('https://','http://')
		d['metadata']['art']['thumb'] = re.compile('href="(.+?)"', re.DOTALL).findall(item)[0]
		d['metadata']['art']['fanart'] = fanart
		result['items'].append(d)
	return result