# -*- coding: utf-8 -*-
import xbmc
import json
import urllib

import libmediathek3 as libMediathek

pluginpath = 'plugin://script.module.libArd/'
chan = {"BR":"channel_28107",
		"br":"channel_28107",
		"ARD-Alpha":"channel_28487",
		"ardalpha":"channel_28487"}

def _parseMain():
	response = libMediathek.getUrl("http://www.br.de/system/halTocJson.jsp")
	j = json.loads(response)
	url = j["medcc"]["version"]["1"]["href"]
	response = libMediathek.getUrl(url)
	return json.loads(response)
	
def parseShows(letter):
	j = _parseMain()
	url = j["_links"]["broadcastSeriesAz"]["href"]
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	url = j['az']['_links'][letter.lower()]['href']
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	for show in j["_embedded"]["teasers"]:
		#xbmc.log(str(show))
		d = {}
		d['url'] = show["_links"]["self"]["href"]
		d['_name'] = show["headline"]
		d['_tvshowtitle'] = show["topline"]
		if 'br-core:teaserText' in show["documentProperties"]:
			d['_plot'] = show["documentProperties"]["br-core:teaserText"]
		try: d['_thumb'] = show['teaserImage']['_links']['original']['href']
		except: pass
		d['_type'] = 'shows'
		d['mode'] = 'libBrListVideos'
		
		l.append(d)
	return l
	
def search(searchString):
	j = _parseMain()
	url = j["_links"]["search"]["href"].replace('{term}',urllib.quote_plus(searchString))
	return parseLinks(url)
	
def parseVideos(url):
	if not 'latestVideos' in url:
		response = libMediathek.getUrl(url)
		j = json.loads(response)
		if "_links" in j and 'latestVideos' in j["_links"]:
			url = j["_links"]["latestVideos"]["href"]
		else: return []
	return parseLinks(url)
	
def parseLinks(url):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	l = []
	if not '_embedded' in j:
		return l
	for show in j["_embedded"]["teasers"]:
		d = {}
		d['url'] = show["_links"]["self"]["href"]
		d['_name'] = show["topline"]
		if 'headline' in show:
			d['_name'] += ' - ' + show['headline']
			d['_tvshowtitle'] = show['topline']
			
		d['_subtitle'] = show["topline"]
		d['_plot'] = show["teaserText"]
		d['_channel'] = show["channelTitle"]
		duration = show['documentProperties']["br-core:duration"].split(':')
		d['_duration'] = str(int(duration[0]) * 3600 + int(duration[1]) * 60 + int(duration[2]))
		
		xbmc.log(str(show["teaserImage"]["_links"]))#image512
		if 'image512' in show["teaserImage"]["_links"]:
			d['_thumb'] = show["teaserImage"]["_links"]["image512"]["href"]
		elif 'image256' in show["teaserImage"]["_links"]:
			d['_thumb'] = show["teaserImage"]["_links"]["image256"]["href"]
		try:
			if show['hasSubtitle']:
				d['_hasSubtitle'] = 'true'
				#d['plot'] += '\n\nUntertitel'
		except:pass
		d['_type'] = 'video'
		d['mode'] = 'libBrPlay'
		
		l.append(d)
	try:
		d = {}
		d['_type'] = 'nextPage'
		d['url'] = j['_embedded']['_links']['next']['href']
		l.append(d)
	except: pass
	return l
	
def parseDate(date,channel='BR'):
	import time
	j = _parseMain()
	#xbmc.log(str(j))
	url = j["_links"]["epg"]["href"]
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	url = j["epgDays"]["_links"][date]["href"]#date: 2016-12-30
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	#xbmc.log(str(j))
	l = []
	broadcasts = j["channels"][chan[channel]]["broadcasts"]
	for b in broadcasts:
		if "_links" in b and "video" in b["_links"]:
			xbmc.log(str(b))
			d = {}
			d["_name"] = b["headline"]
			if len(b["subTitle"]) > 0:
				d['_name'] += ' - ' + b["subTitle"]
			d["_plot"] = b["subTitle"]
			d["_tvshowtitle"] = b["hasSubtitle"]
			d["url"] = b["_links"]["video"]["href"]
			#2016-10-14T08:50:00+02:00
			d["_epoch"] = int(time.mktime(time.strptime(b["broadcastStartDate"].split('+')[0], '%Y-%m-%dT%H:%M:%S')))
			d["_epoch"] = str(d["_epoch"])
			d["_time"] = startTimeToInt(b["broadcastStartDate"][11:19])
			d['_date'] = b["broadcastStartDate"][11:16]
			d['_duration'] = (startTimeToInt(b["broadcastEndDate"][11:19]) - startTimeToInt(b["broadcastStartDate"][11:19])) * 60
			if d['_duration'] < 0:
				d['_duration'] = 86400 - abs(d['_duration'])
			#TODO: rest of properties
			if b['hasSubtitle']:
				d['_hasSubtitle'] = 'true'
				#d['_plot'] += '\n\nUntertitel'
			d['_type'] = 'date'
			d['mode'] = 'libBrPlay'
			l.append(d)
	return l
			
	
def parse(url):
	l = []
	response = libMediathek.getUrl(url)
	j = json.loads(response)

def parseVideo(url):#TODO grep the plot and other metadata from here
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	d = {}
	d['media'] = []
	assets = j["assets"]
	if 'dataTimedTextUrl' in j['_links']:
		d['subtitle'] = [{'url':j['_links']['dataTimedTextUrl']['href'], 'type':'ttml', 'lang': 'de'}]
		
	for asset in assets:
		if "type" in asset and asset["type"] == "HLS_HD":
			d['media'].append({'url':asset["_links"]["stream"]["href"], 'type': 'video', 'stream':'HLS'})
			return d
	for asset in assets:
		if "type" in asset and asset["type"] == "HLS":
			d['media'].append({'url':asset["_links"]["stream"]["href"], 'type': 'video', 'stream':'HLS'})
			return d
def startTimeToInt(s):
	HH,MM,SS = s.split(":")
	return int(HH) * 60 + int(MM)