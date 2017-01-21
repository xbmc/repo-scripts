# -*- coding: utf-8 -*-
import xbmc
import json
import libmediathek3 as libMediathek
import re
#import dateutil.parser

base = 'http://www1.wdr.de'

#channels:
#10 - wdr fernsehen
#34 - one
def getDate(d):
	l = parseEpg(d)

	return l
	
def parseEpg(url,channels=[10]):
	l = []
	#url = 'http://www.wdr.de/programmvorschau/ajax/alle/uebersicht/2016-09-18/'
	response = libMediathek.getUrl(url)#.decode('utf-8')
	j = json.loads(response)
	for sender in j['sender']:
		if sender['senderId'] in channels:
			for sendung in sender['sendungen']:
				if sendung['mediathek'] or True:
					d = {}	
					d['_channel'] = sender['senderName']
					d['_start'] = str(sendung['start'])[:-3]
					#d['_date'] = str(sendung['start'])[:-3]
					d['_airedtime'] = sendung['startHHMM'].replace('.',':')
					d['_end'] = str(sendung['ende'])[:-3]
					d['_duration'] = str(sendung['ende'] - sendung['start'])[:-3]
					d['_name'] = sendung['hauptTitel']
					if sendung['mediathek']:
						d['url'] = sendung['mediathekUrl']
					else:
						d['url'] = ' '
					d['mode'] = 'libWdrPlay'
					d['type'] = 'video'
					#d['plot'] = #unterTitel
					#d[''] =
					l.append(d)
	return l