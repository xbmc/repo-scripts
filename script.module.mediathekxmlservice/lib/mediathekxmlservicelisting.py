#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import urllib
import time
import libmediathek3 as libMediathek

#showSubtitles = xbmcaddon.Addon().getSetting('subtitle') == 'true'

def getXML(url,modePrefix,forcedType=False):
	baseUrl = url.split('/xmlservice')[0]
	l = []
	response = libMediathek.getUrl(url)
	
	if not '<teasers>' in response:
		return l
	
	teasers=re.compile('<teasers>(.+?)</teasers>', re.DOTALL).findall(response)[0]
	match_teaser=re.compile('<teaser(.+?)</teaser>', re.DOTALL).findall(teasers)
	for teaser in match_teaser:
		d = {}
		#match_member=re.compile('member="(.+?)"', re.DOTALL).findall(teaser)
		type = re.compile('<type>(.+?)</type>', re.DOTALL).findall(teaser)[0]
		if type == 'video':
			d['_thumb'] = chooseThumb(re.compile('<teaserimages>(.+?)</teaserimages>', re.DOTALL).findall(teaser)[0])
		else:
			d['_thumb'] = chooseThumb(re.compile('<teaserimages>(.+?)</teaserimages>', re.DOTALL).findall(teaser)[0],-1)
		d.update(getInfo(re.compile('<information>(.+?)</information>', re.DOTALL).findall(teaser)[0]))
		d.update(getDetails(re.compile('<details>(.+?)</details>', re.DOTALL).findall(teaser)[0]))
		#title = cleanTitle(title)
		if type == 'sendung' and d['_duration'] != '0':
			d['url'] = baseUrl+'/xmlservice/web/aktuellste?maxLength=50&id=' + d['_assetId']
			d['_fanart'] = d['_thumb']
			d['mode'] ='xmlListPage'
			if modePrefix:
				d['mode'] = modePrefix + 'XmlListPage'
			d['_type'] = 'shows'
			l.append(d)
		elif type == 'video':
			d['url'] = baseUrl+'/xmlservice/web/beitragsDetails?id=' + d['_assetId']
			d['mode'] = 'xmlPlay'
			if modePrefix:
				d['mode'] = modePrefix + 'XmlPlay'
			if forcedType:
				d['_type'] = forcedType
			else:
				d['_type'] = 'video'
			HH,MM = d['_airtime'].split(' ')[-1].split(':')
			d['_date'] = HH+':'+MM
			d['_time'] = str(int(HH)*60 + int(MM))
			l.append(d)
		elif type == 'rubrik' or type == 'thema':
			d['url'] = baseUrl+'/xmlservice/web/aktuellste?maxLength=50&id=' + d['_assetId']
			d['mode'] = 'xmlListPage'
			if modePrefix:
				d['mode'] = modePrefix + 'XmlListPage'
			d['_type'] = 'dir'
			l.append(d)
		else:
			libMediathek.log('unsupported item type "' + type + '"')
	
	nextPageUrl = _checkIfNextPageExists(url,response)
	if nextPageUrl:
		d = {}
		d['url'] = nextPageUrl
		d['_type'] = 'nextPage'
		d['mode'] = 'xmlListPage'
		l.append(d)
	
	return l
	
def _checkIfNextPageExists(url,response):
	offset = 0
	if '&offset=' in url:
		offset = url.split('&offset=')[-1]
		if '&' in offset:
			offset = offset.split('&')[0]
		url = url.replace('&offset='+offset,'')
		offset = int(offset)
		
	nextPage = False	
	if '<additionalTeaser>' in response:
		nextPage=re.compile('<additionalTeaser>(.+?)</additionalTeaser>', re.DOTALL).findall(response)[0] == 'true'
	elif '<batch>' in response:
		batch=re.compile('<batch>(.+?)</batch>', re.DOTALL).findall(response)[0]
		if int(batch) > offset:
			nextPage = True
	if nextPage:
		return url + '&offset=' + str(offset + 50)
	else:
		return False

def getInfo(infos):
	d = {}
	d['_name']=re.compile('<title>(.+?)</title>', re.DOTALL).findall(infos)[0].replace('<![CDATA[','').replace(']]>','')
	if '(' in d['_name']:
		s = d['_name'].split('(')
		for possibleEpisode in s:
			possibleEpisode = possibleEpisode.split(')')[0].replace(' ','')
			if '.Teil' in possibleEpisode:
				d['_episode'] = possibleEpisode.replace('.Teil','')
			elif '-' in possibleEpisode:
				if possibleEpisode.split('-')[0].isdigit() and possibleEpisode.split('-')[1].isdigit():
					d['_episode'] = possibleEpisode.split('-')[0]
					d['_season'] = possibleEpisode.split('-')[1]
			elif possibleEpisode.isdigit():
				d['_episode'] = possibleEpisode
	if not '_episode' in d and 'Teil' in d['_name']:
		possibleEpisode = d['_name'].split('Teil ')[-1].replace('.','')
		if possibleEpisode.isdigit():
			d['_episode'] = possibleEpisode
	try:
		d['_plot']=re.compile('<detail>(.+?)</detail>', re.DOTALL).findall(infos)[0].replace('<![CDATA[','').replace(']]>','')
	except: pass
		
	return d
	
def chooseThumb(images,maxW=476):
	thumb = ''
	height = 0
	width = 0
	match_images=re.compile('<teaserimage.+?key="(.+?)x(.+?)">(.+?)</teaserimage>', re.DOTALL).findall(images)
	for w,h,image in match_images:
		if not "fallback" in image:
			if int(h) > height or int(w) > width:
				if maxW == -1 or int(w) <= maxW:
					height = int(h)
					width = int(w)
					thumb = image
	return thumb

def getDetails(details):
	d = {}
	try:
		d['_assetId']=re.compile('<assetId>(.+?)</assetId>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_originChannelId']=re.compile('<originChannelId>(.+?)</originChannelId>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_tvshowtitle']=re.compile('<originChannelTitle>(.+?)</originChannelTitle>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_channel']=re.compile('<channel>(.+?)</channel>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_channelLogo']=re.compile('<channelLogoSmall>(.+?)</channelLogoSmall>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_airtime']=re.compile('<airtime>(.+?)</airtime>', re.DOTALL).findall(details)[0]
		d["_epoch"] = str(int(time.mktime(time.strptime(d['airtime'], '%d.%m.%Y %H:%M'))))
		s = d['_airtime'].split(' ')[0].split('.')
		d['_aired'] = s[2] + '-' + s[1] + '-' + s[0] 
		d['_airedtime'] = d['airtime'].split(' ')[1]
	except: pass
	try:
		d['_ttl']=re.compile('<timetolive>(.+?)</timetolive>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_fsk']=re.compile('<fsk>(.+?)</fsk>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_hasCaption']=re.compile('<hasCaption>(.+?)</hasCaption>', re.DOTALL).findall(details)[0]
	except: pass
	try:
		d['_url']=re.compile('<vcmsUrl>(.+?)</vcmsUrl>', re.DOTALL).findall(details)[0]
	except: pass
		
	try:
		if '<lengthSec>' in details:
			d['_duration'] = re.compile('<lengthSec>(.+?)</lengthSec>', re.DOTALL).findall(details)[0]
		elif '<length></length>' in details:
			d['_duration'] = '0'
		else:
			length=re.compile('<length>(.+?)</length>', re.DOTALL).findall(details)[0]
			if ' min ' in length:
				l = length.split(' min ')
				length = int(l[0]) * 60 + int(l[1])
			elif ' min' in length:
				l = length.replace(' min','')
				length = int(l) * 60
			elif '.000' in length:#get seconds
				length = length.replace('.000','')
				l = length.split(':')
				length = int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])
			d['_duration'] = str(length)
	except: pass
	
	return d
	
def toMin(s):
	m, s= divmod(int(s), 60)
	M = str(m)
	S = str(s)
	if len(M) == 1:
		M = '0'+M
	if len(S) == 0:
		S = '00'
	elif len(S) == 1:
		S = '0'+S
	return M+':'+S+' Min.'