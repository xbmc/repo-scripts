# -*- coding: utf-8 -*-
import json
import libmediathek3 as libMediathek

def getShows(url):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for entry in j['result']['serialPrograms']:
		show = _getShow(entry)
		l.append(show)
	return l
	
def _getShow(jsonDict):
	d = {}
	d['_name'] = jsonDict['headline']
	if 'serialProgramId' in jsonDict:
		d['url'] = 'http://itv.mit-xperts.com/kikamediathek/kika/api.php/videos/hbbtv/suche/hbbtv-search-100-hbbtv.json?serialProgram=' + jsonDict['serialProgramId']
	elif 'bundleUrl' in jsonDict:
		d['url'] = 'http://itv.mit-xperts.com/kikamediathek/kika/api.php' + jsonDict['bundleUrl']
	if 'description' in jsonDict:
		d['_plot'] = jsonDict['description']
	d['_thumb'] = jsonDict['images'][0]['imageUrls']['varhbbtvm']
	d['mode'] = 'libKikaListVideos'
	d['_type'] = 'dir'	
	return d
	
def getVideos(url,type='video'):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for entry in j['result']['videos']:
		vid = _getDictVideos(entry,type)
		l.append(vid)
	return l
	
def _getDictVideos(jsonDict,type='video'):#TODO: ttl
	d = {}
	d['_name'] = jsonDict['headline']
	if 'teaserText' in jsonDict:
		d['_plot'] = jsonDict['teaserText']
	if 'serialProgram' in jsonDict:
		d['_tvshowtitle'] = jsonDict['serialProgram']['serialProgramName']
	HH,MM,SS = jsonDict['videoDuration'].split(':')
	d['_duration'] = str(int(HH) * 3600 + int(MM) * 60 + int(SS))
	d['url'] = 'http://www.kika.de/' + jsonDict['id'] + '-avCustom.xml'
	d['_thumb'] = jsonDict['images'][0]['imageUrls']['varhbbtvm']
	d['_mpaa'] = jsonDict['fskRating']
	if 'referenceDate' in jsonDict:
		d['_airedISO8601'] = jsonDict['referenceDate']
	
	d['mode'] = 'libMdrPlay'
	d['_type'] = type
	
	return d