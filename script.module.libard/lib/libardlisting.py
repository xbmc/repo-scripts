#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import urllib
import libardrssparser
import libmediathek3 as libMediathek
import HTMLParser

h = HTMLParser.HTMLParser()
useThumbAsFanart = True
baseUrl = "http://www.ardmediathek.de"
defaultThumb = baseUrl+"/ard/static/pics/default/16_9/default_webM_16_9.jpg"
defaultBackground = "http://www.ard.de/pool/img/ard/background/base_xl.jpg"
icon = ''#todo
showDateInTitle = False

def listRSS(url,page=0):
	if page > 1:
		url += '&mcontents=page.'+str(page)

	response = libMediathek.getUrl(url)
	data = libardrssparser.parser(response)
	if page == 0:
		return data
	else:
		if len(data) == 50:
			return data,True
		else:
			return data,False
		

def getAZ(letter):
	if letter == '#':
		letter = '0-9'
	l = []
	if letter == 'X' or letter == 'Y':
		return l
	content = libMediathek.getUrl(baseUrl+"/tv/sendungen-a-z?buchstabe="+letter)
	
	#r = requests.get(baseUrl+"/tv/sendungen-a-z?buchstabe="+letter)
	#content = r.text.decode('utf-8')
	
	spl = content.split('<div class="teaser" data-ctrl')
	for i in range(1, len(spl), 1):
		d = {}
		entry = spl[i]
		url = re.compile('href="(.+?)"', re.DOTALL).findall(entry)[0]
		url = url.replace("&amp;","&")
		d['url'] = baseUrl+url+'&m23644322=quelle.tv&rss=true'
		d['name'] = re.compile('class="headline">(.+?)<', re.DOTALL).findall(entry)[0]
		d['channel'] = re.compile('class="subtitle">(.+?)<', re.DOTALL).findall(entry)[0]
		thumbId = re.compile('/image/(.+?)/16x9/', re.DOTALL).findall(entry)[0]
		d['thumb'] = baseUrl+"/image/"+thumbId+"/16x9/0"
		d['fanart'] = d['thumb']
		bcastId = url.split('bcastId=')[-1]
		if '&' in bcastId:
			bcastId = bcastId.split('&')[0]
		d['plot'] = libArdBcastId2Desc.toDesc(bcastId)
		d["mode"] = "libArdListVideos"
		l.append(d)
	return l
	
def getVideosXml(videoId):
	l = []
	content = libMediathek.getUrl(baseUrl+'/ard/servlet/export/collection/collectionId='+videoId+'/index.xml')
	match = re.compile('<content>(.+?)</content>', re.DOTALL).findall(content)
	for item in match:
		clip = re.compile('<clip(.+?)>', re.DOTALL).findall(item)[0]
		if 'isAudio="false"' in clip:
			name = re.compile('<name>(.+?)</name>', re.DOTALL).findall(item)[0]
			length = re.compile('<length>(.+?)</length>', re.DOTALL).findall(item)[0]
			if not '<mediadata:images/>' in item:
				thumb = re.compile('<image.+?url="(.+?)"', re.DOTALL).findall(item)[-1]
			else:
				thumb = ''
			id = re.compile(' id="(.+?)"', re.DOTALL).findall(clip)[0]
			l.append([name, id, thumb, length])
	return l
	

	
	
def listDate(url):
	l =[]
	response = libMediathek.getUrl(url)
	videos = response.split('<span class="date">')
	videos = videos[1:]
	for video in videos:
		time = video[:5]
		titel = re.compile('<span class="titel">(.+?)</span>', re.DOTALL).findall(video)[0]
		match = re.compile('<div class="media mediaA">.+?<a href="(.+?)" class="mediaLink">.+?urlScheme&#039;:&#039;(.+?)##width##.+?<h4 class="headline">(.+?)</h4>.+?<p class="subtitle">(.+?)</p>', re.DOTALL).findall(video)
		#http://www.ardmediathek.de/ard/servlet/image/00/32/75/15/44/1547339463/16x9/320
		for url,thumb,name,plot in match:
			d = {}
			d['_time'] = time
			d['_date'] = time
			length = plot.split(' ')[0]
			#if ':' in length:
			#	length = length.split(':')
			#	d['duration'] = str(int(length[0])*60+int(length[1]))
			#else:
			#	d['duration'] = str(int(length)*60)
			if name in titel:
				d['_name'] = titel
			elif titel in name:
				d['_name'] = name
			else:
				d['_name'] = titel+' - '+name
			HH,MM = time.split(':')
			d['_time'] = str(int(HH)*60 + int(MM))
			d['_thumb'] = 'http://www.ardmediathek.de/ard/servlet'+thumb+'0'
			d['_plot'] = plot
			d['url'] = baseUrl+url.replace('&amp;','&')
			d['_name'] = d['_name'].decode('utf-8')
			d['_name'] = h.unescape(d['_name'])
			d['_name'] = d['_name'].encode('utf-8')
			d['documentId'] = d['url'].encode('utf-8').split("documentId=")[-1]
			d['mode'] = 'libArdPlay'
			d['_type'] = 'date'
			l.append(d)
	return l	
	
def listVideos(url,page=1):
	l =[]
	content = libMediathek.getUrl(url)
	spl = content.split('<div class="teaser" data-ctrl')
	for i in range(1, len(spl), 1):
		d ={}
		entry = spl[i]
		d["url"] = baseUrl + re.compile('<a href="(.+?)" class="mediaLink">', re.DOTALL).findall(entry)[0].replace("&amp;","&")
		d["name"] = cleanTitle(re.compile('class="headline">(.+?)<', re.DOTALL).findall(entry)[0])
		
		match = re.compile('class="dachzeile">(.+?)<', re.DOTALL).findall(entry)
		if match:
			d["showname"] = match[0]
		
		match = re.compile('<p class="subtitle">(.+?)</p>', re.DOTALL).findall(entry)
		if match:
			subtitle = match[0].split(" | ")
			d["date"] = subtitle[0]
			try:
				d["duration"] = int(subtitle[1].replace(" Min.",""))*60
			except: pass
			d["channel"] = subtitle[2]
			if len(subtitle) > 3:
				if subtitle[3] == "UT":
					d["subtitle"] = True
			
		
		match = re.compile('/image/(.+?)/16x9/', re.DOTALL).findall(entry)
		if match:
			d['thumb'] = baseUrl+"/image/"+match[0]+"/16x9/448"
		d["type"] = 'video'
		d['mode'] = 'libArdPlay'
		d["documentId"] = d["url"].split("documentId=")[-1]
		l.append(d)
		
	return l
	

def cleanTitle(title):
	title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#034;", "\"").replace("&#039;", "'").replace("&quot;", "\"").replace("&szlig;", "ß").replace("&ndash;", "-")
	title = title.replace("&Auml;", "Ä").replace("&Uuml;", "Ü").replace("&Ouml;", "Ö").replace("&auml;", "ä").replace("&uuml;", "ü").replace("&ouml;", "ö").replace("&eacute;", "é").replace("&egrave;", "è")
	title = title.replace("&#x00c4;","Ä").replace("&#x00e4;","ä").replace("&#x00d6;","Ö").replace("&#x00f6;","ö").replace("&#x00dc;","Ü").replace("&#x00fc;","ü").replace("&#x00df;","ß")
	title = title.replace("&apos;","'").strip()
	return title
	