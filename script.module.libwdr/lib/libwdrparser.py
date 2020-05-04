# -*- coding: utf-8 -*-
import requests
import json
import re
#import dateutil.parser
base = 'http://www1.wdr.de'
	
	
def parseVideo(url,signLang=False):
	response = requests.get(url).text
	if 'mediaLink video' in response:
		j = json.loads(re.compile('<a href="javascript:void\(0\);" class="mediaLink video" data-extension=\'(.+?)\'', re.DOTALL).findall(response)[0])
		url = j['mediaObj']['url']
		return parseVideoJs(url,signLang)
	if 'mediaLink audio' in response:
		j = json.loads(re.compile('<a href="javascript:void\(0\);" class="mediaLink audio" data-extension=\'(.+?)\'', re.DOTALL).findall(response)[0])
		url = j['mediaObj']['url']
		return parseAudioJs(url)
	
def parseAudioJs(url):
	response = requests.get(url).text
	j = json.loads(response[38:-2])
	audio = j['mediaResource']['dflt']['audioURL']
	if audio.startswith('//'):
		audio = f'http:{audio}'
	return {'media':[{'url':audio, 'type':'video', 'stream':'audio'}]}

def parseVideoJs(url,signLang=False):
	response = requests.get(url).text
	j = json.loads(response[38:-2])
	
	videos = []
	subUrlTtml = False
	for type in j['mediaResource']:
		if type == 'dflt' or type == 'alt':
			if signLang and 'slVideoURL' in j['mediaResource'][type]:
				videos.append(j['mediaResource'][type]['slVideoURL'])
			else:
				videos.append(j['mediaResource'][type]['videoURL'])
		elif type == 'captionURL':
			subUrlTtml = j['mediaResource']['captionURL']
		elif type == 'captionsHash':
			if 'xml' in j['mediaResource']['captionsHash']:
				subUrlTtml = j['mediaResource']['captionsHash']['xml']
			if 'vtt' in j['mediaResource']['captionsHash']:
				subUrlVtt = j['mediaResource']['captionsHash']['vtt']
			if 'srt' in j['mediaResource']['captionsHash']:
				subUrlSrt = j['mediaResource']['captionsHash']['srt']
	video = False
	for vid in videos:
		if vid.startswith('//'):
			vid = 'http:' + vid
		if vid.endswith('.m3u8'):
			video = vid
		elif vid.endswith('.f4m') and (not video or video.endswith('.mp4')):
			video = vid.replace('manifest.f4m','master.m3u8').replace('adaptiv.wdr.de/z/','adaptiv.wdr.de/i/')
		elif vid.endswith('.mp4') and not video:
			video = vid
	d = {}
	d['media'] = []
	if video.endswith('m3u8'):
		d['media'].append({'url':video, 'type': 'video', 'stream':'HLS'})
	else:
		d['media'].append({'url':video, 'type': 'video', 'stream':'mp4'})
	if subUrlTtml:
		if subUrlTtml.startswith('//'):
			subUrlTtml = 'http:' + subUrlTtml
		d['subtitle'] = []
		d['subtitle'].append({'url':subUrlTtml, 'type': 'ttml', 'lang':'de'})
	return d
	
def startTimeToInt(s):
	HH,MM,SS = s.split(":")
	return int(HH) * 60 + int(MM)