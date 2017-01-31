# -*- coding: utf-8 -*-
import json
import libmediathek3 as libMediathek

def getShows(url='http://hbbtv.sr-mediathek.de/inc/SndazJSON.php'):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for letterNumber in j:
		for entry in j[letterNumber]:
			show = _getDictShows(entry)
			if show['_entries'] != '0':
				l.append(show)
	return l
	
def getVideos(url):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for entry in j:
		vid = _getDictVideos(entry)
		l.append(vid)
	return l
	
def getDate(day):
	response = libMediathek.getUrl('http://hbbtv.sr-mediathek.de/inc/SndvrpJSON.php')
	j = json.loads(response)
	l = []
	for entry in j[int(day)]:
		vid = _getDictVideos(entry,'date')
		l.append(vid)
	return l[::-1]
	
def _getDictShows(jsonDict):
	d = {}
	d['_name'] = jsonDict['s_name']
	d['_entries'] = jsonDict['s_anzahl']
	d['url'] = 'http://hbbtv.sr-mediathek.de/inc/sendungJSON.php?sid=' + jsonDict['s_id']
	d['_plot'] = jsonDict['s_beschreibung']
	d['_thumb'] = jsonDict['bild']
	d['mode'] = 'libSrListVideos'
	d['_type'] = 'dir'
	
	return d
	
def _getDictVideos(jsonDict,type='video'):
	d = {}
	d['_name'] = jsonDict['ueberschrift']
	d['url'] = 'http://sr_hls_od-vh.akamaihd.net/i/' + jsonDict['media_url_firetv']
	d['_plot'] = jsonDict['kompletttext']
	d['_mpaa'] = jsonDict['fsk']
	d['_thumb'] = jsonDict['bild']
	d['_aired'] = jsonDict['start'][:4] + '-' + jsonDict['start'][4:6] + '-' + jsonDict['start'][6:8]
	d['_airedtime'] = jsonDict['start'][8:10] + ':' + jsonDict['start'][10:12]
	#d['start'] = jsonDict['start']
	if 'playtime_hh' in jsonDict:
		d['_duration'] = str(int(jsonDict['playtime_hh']) * 3600 + int(jsonDict['playtime_mm']) * 60 + int(jsonDict['playtime_ss']))
	d['mode'] = 'libSrPlay'
	d['_type'] = type
	
	return d