# -*- coding: utf-8 -*-
import xbmc
import json
import libmediathek3 as libMediathek

def getVideo(id):
	response = libMediathek.getUrl('http://www.ndr.de/'+id+'-ppjson.json')
	j = json.loads(response)
	d = {}
	d['media'] = []
	for item in j['playlist']:
		if item != 'config' and 'type' in j['playlist'][item] and j['playlist'][item]['type'] == 'application/x-mpegURL':
			d['media'].append({'url':j['playlist'][item]['src'], 'type': 'video', 'stream':'HLS'})

	#if 'tracks' in j['playlist']['config']:
	#	d['subtitle'] = [{'url':'http://www.ndr.de' + j['playlist']['config']['tracks'][0]['src'], 'type':'ttml', 'lang':'de', 'colour':True}]
	return d

	