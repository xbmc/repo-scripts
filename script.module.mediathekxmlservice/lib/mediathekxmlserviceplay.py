#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import sys
import urllib
import libmediathek3 as utils

videoQuality = 10
zdfMetaEnabled = False#True
expertEnabled = False
forceHttp = False
rtspEnabled = False
threegpEnabled = False
wmv3Enabled = False
httpEnabled = True
preferHttp = False
m3u8Enabled = True

qualityDict = { 'low':		0,
				'med':		1,
				'high':		2,
				'veryhigh': 3,
				'hd' :		4}

def getVideoUrl(url):
	baseVideoUrl = "http://nrodl.zdf.de/de"
	content = utils.getUrl(url)
	#_saveBookmarks(content)
	match = re.compile('<formitaet basetype="(.+?)" isDownload=".+?">(.+?)</formitaet>', re.DOTALL).findall(content)
	subtitleUrl = False
	offset = '0'
	if '<caption>' in content:
		try:
			caption = re.compile('<caption>(.+?)</caption>', re.DOTALL).findall(content)[0]
			subtitleUrl = re.compile('<url>(.+?)</url>', re.DOTALL).findall(caption)[0]
			if '<offset>' in caption:
				offset = re.compile('<offset>(.+?)</offset>', re.DOTALL).findall(caption)[0]
			else:
				offset = '0'
		except: pass
	if '<default-stream-url>' in content:
		url = re.compile('<default-stream-url>(.+?)</default-stream-url>', re.DOTALL).findall(content)[0]
	elif '<type>livevideo</type>' in content:
		url = re.compile('<formitaet basetype="h264_aac_ts_http_m3u8_http" isDownload="false">.+?<quality>high</quality>.+?<url>(.+?)</url>', re.DOTALL).findall(content)[0]
	else:
		lastBr = 0
		m3u8 = False
		qualityM3u8 = 0
		for basetype,entry in match:
			possibleUrl = False
			facet = re.compile('<facet>(.+?)</facet>', re.DOTALL).findall(entry)
			#if not facet or facet[0] != 'podcast':
			if True:
				videoUrl = re.compile('<url>(.+?)</url>', re.DOTALL).findall(entry)[0]
				quality = re.compile('<quality>(.+?)</quality>', re.DOTALL).findall(entry)[0]
				videoBitrate = int(re.compile('<videoBitrate>(.+?)</videoBitrate>', re.DOTALL).findall(entry)[0])
				if   basetype == 'h264_aac_mp4_rtsp_mov_http'		and rtspEnabled:
					possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet)
				elif basetype == 'h264_aac_3gp_http_na_na'			and threegpEnabled:
					possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet)
				elif basetype == 'wmv3_wma9_asf_mms_asx_http'		and wmv3Enabled:
					possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet)
				elif basetype == 'h264_aac_mp4_rtmp_zdfmeta_http'	and zdfMetaEnabled:
					possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet)
				elif basetype == 'h264_aac_ts_http_m3u8_http'		and m3u8Enabled:
					#possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet)
					if qualityDict[quality] >= qualityM3u8:
						m3u8 = videoUrl
						qualityM3u8 = qualityDict[quality]
				elif basetype == 'h264_aac_mp4_http_na_na'			and httpEnabled:
					possibleUrl, possibleBr = _chooseVideo(videoUrl,videoBitrate,lastBr,facet) 
					if forceHttp:
						if not facet or facet[0] != 'hbbtv':
							baseVideoUrl = videoUrl.split('/zdf/')[0]#die basis ist nicht immer gleich

				if possibleUrl:
					if possibleBr > lastBr or basetype == 'h264_aac_mp4_http_na_na' and preferHttp and possibleBr == lastBr:
						url = possibleUrl
						lastBr = possibleBr

	if m3u8:# and lastBr < 2200000:
		url = m3u8
	if url.endswith('.meta'):
		meta = utils.getUrl(url)
		url = re.compile('<default-stream-url>(.+?)</default-stream-url>', re.DOTALL).findall(meta)[0]
		if forceHttp and 'mp4:' in url:
			url = baseVideoUrl+'/'+url.split('mp4:')[-1]
	
	d = {}
	d['media'] = []
	if subtitleUrl:
		d['subtitle'] = [{'url':subtitleUrl, 'type':'ttml', 'lang':'de', 'offset':offset}]
	d['media'] = [{'url':url, 'type': 'video', 'stream':'HLS'}]
	return d
	

def _chooseVideo(videoUrl,videoBitrate,lastBr,facet):
	url = False
	if lastBr == 0:
		url = videoUrl
		lastBr = videoBitrate
	elif videoQuality == 0:#low
		if videoBitrate <= 1300000:
			if not facet or facet[0] != 'hbbtv':
				url = videoUrl
				lastBr = videoBitrate
	elif videoQuality == 1:#medium
		if int(videoBitrate) <= 1500000:
			if not facet or facet[0] != 'hbbtv':
				url = videoUrl
				lastBr = videoBitrate
	elif videoQuality == 2:#high 25p
		if not facet or facet[0] != 'hbbtv':
			if '1456k_p13v11.mp4' in videoUrl:
				url = videoUrl.replace('1456k_p13v11.mp4','2256k_p14v11.mp4')
				lastBr = 2200000
			else:
				url = videoUrl
				lastBr = videoBitrate
	elif videoQuality == 3:#high 50i
		if not facet or facet[0] != 'hbbtv':
			if '1456k_p13v11.mp4' in videoUrl:
				url = videoUrl.replace('1456k_p13v11.mp4','2328k_p35v11.mp4')
				lastBr = 2200000
			else:
				url = videoUrl
				lastBr = videoBitrate
	return url,lastBr
	