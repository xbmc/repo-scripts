# -*- coding: utf-8 -*-

import sys
import urllib
import urllib.parse
import json
from datetime import date, timedelta
import time

import xbmcaddon
import xbmcgui
import xbmcplugin



class lm4:
	def __init__(self):
		self.modes = {
			'libMediathekListDate':self.libMediathekListDate,
			'libMediathekListLetters':self.libMediathekListLetters,
			'libMediathekSearch':self.libMediathekSearch,
		}	
		self.playbackModes = {
			'libMediathekPlayDirect':self.libMediathekPlayDirect
		}
		self.defaultMode = ''

		self.params = {}

	def translation(self,id,addonid=False):
		#return str(id)
		if addonid:
			return xbmcaddon.Addon(id=addonid).getLocalizedString(id)
		elif id < 32000:
			return xbmcaddon.Addon().getLocalizedString(id)
		else:
			return xbmcaddon.Addon(id='script.module.libmediathek4').getLocalizedString(id)

	def sortAZ(self):
		xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE)

	def setSetting(self,k,v):
		return xbmcplugin.setSetting(int(sys.argv[1]), k, v)
		
	def getSetting(self,k):
		return xbmcplugin.getSetting(int(sys.argv[1]), id=k)
		
	def endOfDirectory(self):
		xbmcplugin.endOfDirectory(int(sys.argv[1]),cacheToDisc=True)

	def _buildUri(self,d):
		return d.get('pluginpath', sys.argv[0]) + '?' + urllib.parse.urlencode(d)
	
	def addEntries(self,d):
		lists = []
		for item in d['items']:
			u = self._buildUri(item['params'])
			metadata = item['metadata']
			name = metadata.get('name','')
			ilabels = {}



			if 'type' in item:
				if item['type'] in ['video', 'live', 'clip']:
					ilabels['mediatype'] = 'video'
				elif item['type'] in ['date']:
					ilabels['mediatype'] = 'video'
					if 'aired' in metadata:
						if 'ISO8601' in metadata['aired']:
							if metadata['aired']['ISO8601'].endswith('Z'):
								t = time.strptime(metadata['aired']['ISO8601'],'%Y-%m-%dT%H:%M:%SZ')
							else:
								t = time.strptime(metadata['aired']['ISO8601'],'%Y-%m-%dT%H:%M:%S%z')
							ilabels['aired'] = time.strftime('%Y-%m-%d',t)
							name = f'({time.strftime("%H:%M",t)}) {name}'

				elif item['type'] in ['tvshow']:
					ilabels['mediatype'] = 'tvshow'
				elif item['type'] in ['shows', 'season']:
					ilabels['mediatype'] = 'season'
				elif item['type'] in ['episode']:
					ilabels['mediatype'] = 'episode'
				elif item['type'] in ['movie']:
					ilabels['mediatype'] = 'movie'
				elif item['type'] in ['sport']:
					ilabels['mediatype'] = 'sport'
				else:
					ilabels['mediatype'] = 'video'
				
			
			ilabels.update({
				"Title": 				name,
				"Plot": 				metadata.get('plot',metadata.get('plotoutline','')),
				"Plotoutline": 	metadata.get('plotoutline',''),
				"Duration": 		str(metadata.get('duration','')),
				"Mpaa": 				metadata.get('mpaa',''),
				"Studio": 			metadata.get('channel',''),
				"episode": 			metadata.get('episode',''),
				"season": 			metadata.get('season',''),
				"tvshowtitle": 	metadata.get('tvshowtitle',''),
				"rating": 			metadata.get('rating',''),
				"director": 		metadata.get('directors',''),
				"artist": 			metadata.get('artists',[]),
				"writer": 			metadata.get('writers',''),
				"credits": 			metadata.get('credits',''),
				"genre": 				metadata.get('genres',''),
				"year": 				metadata.get('year',''),
				"premiered": 		metadata.get('premiered',''),
				"premiered": 		metadata.get('originaltitle',''),
				})

			liz=xbmcgui.ListItem(name)

			if 'art' in metadata:
				liz.setArt(metadata['art'])
			if 'episode' in metadata:
				liz.setArt(metadata['episode'])
			if 'season' in metadata:
				liz.setArt(metadata['season'])

			
			if 'subtitles' in metadata:#TODO
				liz.addStreamInfo('subtitle', {'language': 'deu'})

			if 'actors' in metadata:
				liz.setCast(metadata['actors'])
					
			ok=True

			if item['type'] in ['audio','songs']:
				liz.setInfo( type="music", infoLabels=ilabels)
			else:
				liz.setInfo( type="Video", infoLabels=ilabels)
				
			if item.get('type',None) in ['video', 'live', 'date', 'clip', 'episode', 'audio', 'sport', 'sports', 'movie', 'song']:
				liz.setProperty('IsPlayable', 'true')
				lists.append([u,liz,False])
			else:
				lists.append([u,liz,True])

		if 'content' in d:
			xbmcplugin.setContent(handle=int(sys.argv[1]), content=d['content'] )
		else:
			xbmcplugin.setContent(handle=int(sys.argv[1]), content="files" )
		
		xbmcplugin.addDirectoryItems(int(sys.argv[1]), lists)

	def play(self,d,external=False):
		if not 'media' in d or len(d['media']) == 0:#TODO: add error msg
			listitem = xbmcgui.ListItem(path='')
			pluginhandle = int(sys.argv[1])
			xbmcplugin.setResolvedUrl(pluginhandle, False, listitem)
			return

		listitem,url = self._chooseBitrate(d['media'])	
				
		if 'subtitle' in d:
			subs = []
			for subtitle in d['subtitle']:
				if subtitle['type'] == 'srt':
					subs.append(subtitle['url'])
				elif subtitle['type'] == 'ttml':
					import libmediathek4ttml2srt
					subFile = libmediathek4ttml2srt.ttml2Srt(subtitle['url'])
					subs.append(subFile)
				elif subtitle['type'] == 'webvtt':
					import libmediathek4webvtt2srt 
					subFile = libmediathek4webvtt2srt.webvtt2Srt(subtitle['url'])
					subs.append(subFile)
				else:
					log('Subtitle format not supported: ' + subtitle['type'])
			listitem.setSubtitles(subs)
		
		if 'metadata' in d:
			ilabels = {}
			if 'plot' in d['metadata']:
				ilabels['Plot'] = d['metadata']['plot']
			if 'name' in d['metadata']:
				ilabels['Title'] = d['metadata']['name']
			listitem.setInfo( type="Video", infoLabels=ilabels)
			
			art = {}
			if 'thumb' in d['metadata']:
				art['thumb'] = d['metadata']['thumb']
			listitem.setArt(art)
			
		if 'header' in d['media']:
			listitem.setProperty('inputstream.adaptive.stream_headers',d['media']['header'])
		
		if external:
			xbmc.Player().play(url, listitem)
		else:
			pluginhandle = int(sys.argv[1])
			xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
			
	def _chooseBitrate(self,l):
		bitrate = 0
		url = False
		streamType = False
		for item in l:
			if item.get('stream','').lower() == 'hls':#prefer hls
				url = item['url']
				streamType = 'HLS'
				break
			if item.get('stream','').lower() == 'dash':
				url = item['url']
				streamType = 'DASH'
			if item.get('stream','').lower() == 'mp4' and item.get('bitrate',0) >= bitrate:
				bitrate = item.get('bitrate',0)
				url = item['url']
				streamType = 'MP4'
			if item.get('stream','').lower() == 'audio':
				url = item['url']
				streamType = 'AUDIO'
		listitem = xbmcgui.ListItem(path=url)
		if streamType == 'DASH':
			listitem.setProperty('inputstreamaddon', 'inputstream.adaptive')
			listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
			if 'licenseserverurl' in item:
				listitem.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
				listitem.setProperty('inputstream.adaptive.license_key', item['licenseserverurl'])
			listitem.setMimeType('application/dash+xml')
			listitem.setContentLookup(False)
		elif streamType == 'HLS':
			listitem.setMimeType('application/vnd.apple.mpegurl')
			listitem.setProperty('inputstream', 'inputstream.adaptive')
			listitem.setProperty('inputstream.adaptive.manifest_type', 'hls')
			listitem.setContentLookup(False)

		return listitem,url

	def action(self):	
		self.params = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
		mode = self.params.get('mode',self.defaultMode)
		if mode in self.playbackModes:
			self.play(self.playbackModes[mode]())
		else:
			l = self.modes[mode]()
			self.addEntries(l)
			self.endOfDirectory()	

			
	def libMediathekSearch(self):
		sString = xbmcgui.Dialog().input(self.translation(32139))
		if sString == '':
			xbmcplugin.endOfDirectory(int(sys.argv[1]),succeeded=False)
			return
		return self.searchModes[self.params['searchMode']](urllib.parse.quote(sString))
			
	def libMediathekListLetters(self):
		import string
		result = {'items':[]}
		ignore = self.params.get('ignore','').split(',')
		letters = ['#']
		letters.extend(list(string.ascii_lowercase))
		for letter in letters:
			if not letter in ignore:
				d = {'params':json.loads(self.params['subParams']), 'metadata':{}, 'type':'dir'}
				d['metadata']['name'] = letter.upper()
				d['params']['letter'] = letter
				result['items'].append(d)
		return result
			
	def libMediathekListDate(self):
		result = {'items':[]}
		weekdayDict = { 
			'0': self.translation(32013),
			'1': self.translation(32014),
			'2': self.translation(32015),
			'3': self.translation(32016),
			'4': self.translation(32017),
			'5': self.translation(32018),
			'6': self.translation(32019),
			}
		
		i = 0
		while i <= 6:
			day = date.today() - timedelta(i)
		
			d = {'params':json.loads(self.params['subParams']), 'metadata':{}, 'type':'dir'}
			d['params']['datum'] = str(i)
			d['params']['yyyymmdd'] = self._calcyyyymmdd(i)
			d['params']['ddmmyyyy'] = self._calcddmmyyyy(i)
			
			if i == 0:
				d['metadata']['name'] = self.translation(32020)
			elif i == 1:
				d['metadata']['name'] = self.translation(32021)
			else:
				d['metadata']['name'] = weekdayDict[day.strftime("%w")]

			result['items'].append(d)
			i += 1

		#if self.params.get('datePicker',False) == True:
		#	d = {'params':{'mode': mode}, 'metadata':{'name': self.translation(32022)}, 'type':'dir'}
		#	if channel: d['params']['channel'] = channel
		#	result['items'].append(d)
		return result

	def libMediathekPlayDirect(self):
		return {'media':[{'url':self.params['url'], 'stream':self.params['stream']}]}

	def _calcyyyymmdd(self,d):
		day = date.today() - timedelta(d)
		return day.strftime('%Y-%m-%d')

	def _calcddmmyyyy(self,d):
		day = date.today() - timedelta(d)
		return day.strftime('%d-%m-%Y')