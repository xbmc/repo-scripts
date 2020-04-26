# -*- coding: utf-8 -*-
import requests
import re

#import dateutil.parser

base = 'http://www1.wdr.de'

def getAudio(id):
	response = requests.get(f'{base}/{id}~_format-mobile_variant-android.nimex').text
	if 'media:content' in response:
		audio = re.compile('<media:content url="(.+?)"').findall(response)[0]
		return {'media':[{'url':audio, 'type':'video', 'stream':'audio'}]}
	else:
		return {'media':[]}