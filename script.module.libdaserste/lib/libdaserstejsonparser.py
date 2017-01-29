# -*- coding: utf-8 -*-
import json
import libmediathek3 as libMediathek
import urllib
import time

def getCategories():
	response = libMediathek.getUrl("http://www.daserste.de/dasersteapp/app/index~categories.json")
	j = json.loads(response)
	l = []
	for entry in j['result']:
		d = {}
		d['_name'] = entry['headline']
		try: d['thumb'] = _chooseThumb(entry['teaserImages'][0]['variantes'])
		except: pass #todo: make pretty
		d['url'] = 'http://www.daserste.de/dasersteapp/app/index~categories_pageSize-100_catVideo-'+entry['key']+'.json'
		d['_type'] = 'dir'
		d['mode'] = 'libDasErsteListVideos'
		l.append(d)
	return l
	
	
def getChars():
	response = libMediathek.getUrl("http://www.daserste.de/dasersteapp/app/index~series.json")
	j = json.loads(response)
	l = []
	for c in j['result']:
		if not c['hasContent']:
			l.append(c['charIndex'])
	return l
		
def getAZ():
	response = libMediathek.getUrl("http://www.daserste.de/dasersteapp/app/index~series_plain-false.json")
	j = json.loads(response)
	l = []
	for c in j['result']:
		if c['hasContent']:
			for show in c['content']:
				d = {}
				d['_name'] = show['headline']
				try: d['_thumb'] = _chooseThumb(show['imageUrls'][0]['variantes'])
				except: pass
				#d['url'] = 'http://www.daserste.de/dasersteapp/app/index~categories_series-'+show['serial']+'.json'
				
				d['url'] = 'http://www.daserste.de/dasersteapp/app/index~series_serial-'+show['serial'].encode('utf-8')+'_types-sendung,sendebeitrag_pageNumber-0_pageSize-100.json'
				d['_type'] = 'dir'
				d['mode'] = 'libDasErsteListVideos'
				l.append(d)
	return l		
	
def getDate(day):
	url = 'http://www.daserste.de/dasersteapp/app/index~program_pd-'+day+'.json'
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for r in j['result']:
		if r.has_key('entries'):
			for entry in r['entries']:
				if entry['hasVideo']:# or entry['videoAvailableSoon']:
					d = _parseVideo(entry,'date')
					l.append(d)
	return l
	
def getVideos(url,type='dir'):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	
	if j.has_key('entries'):
		for entry in j['entries']:
			if isinstance(entry, dict):
				l.append(_parseVideo(entry))
	return l
	
	
def _parseVideo(entry,t='video'):
	d = {}
	#d['plot'] = entry['teaserImages']['caption']
	try: d['thumb'] = _chooseThumb(entry['teaserImages'][0]['variantes'],True)
	except: pass #todo: make pretty
	if 'serialProgramName' in entry:
		d['_name'] = entry['serialProgramName']#.decode('utf-8')
		d['_name'] += ' - '
		d['_name'] += entry['headline']#.encode('utf-8')
		d['_name'] = d['_name'].replace('  ',' ')
		d['_tvshowtitle'] = entry['serialProgramName'].encode('utf-8')
	else:
		d['_name'] = entry['headline'].encode('utf-8')
		d['_tvshowtitle'] = entry['headline'].encode('utf-8')
		if 'subheadline' in entry:
			d['_name'] += ' - ' + entry['subheadline'].encode('utf-8')
	if 'teaserTextLong' in entry:
		d['_plot'] = entry['teaserTextLong']
	if 'fskRating' in entry:
		d['_mpaa'] = entry['fskRating'].encode('utf-8').replace('fsk','FSK ')
	if 'videoDuration' in entry:
		d['_duration'] = str(entry['videoDuration'])
	if 'referenceDate' in entry:
		d['_epoch'] = str(entry['referenceDate']/1000)
		d['_aired'] = time.strftime('%Y-%m-%d', time.gmtime(entry['referenceDate']/1000 + 3600))
		d['_airedtime'] = time.strftime('%H:%M', time.gmtime(entry['referenceDate']/1000 + 3600))
	d['url'] = 'http://www.daserste.de/dasersteapp/' + entry['id'] + '~full.json'
	d['_type'] = t
	d['mode'] = 'libDasErstePlay'
	
	return d
def getVideo(url):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	if not 'assets' in j:
		response = libMediathek.getUrl('http://www.daserste.de/dasersteapp/' + j['relatedContent'][0]['entries'][0]['id'] + '~full.json')
		j = json.loads(response)
	videoUrl = j['assets'][0]['urls'][0]['url']
	d = {}
	d['media'] = []
	d['media'].append({'url':videoUrl, 'type':'HLS'})
	try:
		d['metadata'] = {'name':j['headline'], 'plot': j['copytext'][0]['text'], 'thumb':j['teaserImages'][0]['variantes'][0]['url']}
	except: pass
	if 'subtitles' in j:
		d['subtitle'] = []
		#d['subtitle'].append({'url':j['subtitles']['subtitleSrt'], 'type':'srt', 'lang':'de'})
		d['subtitle'].append({'url':j['subtitles']['subtitleWebVTT'], 'type':'webvtt', 'lang':'de'})
	return d
	
	
def _chooseThumb(l,video=False):
	t = None
	for d in l:
		if video:
			if d['type'] == 'varm':
				t = d['url'].encode('utf-8')
		else:
			if d['type'] == 'varxl':
				t = d['url'].encode('utf-8')
		if d['type'] == 'varl':
			bak = d['url'].encode('utf-8')
	if t == None:
		return bak
	else:
		return t
	
