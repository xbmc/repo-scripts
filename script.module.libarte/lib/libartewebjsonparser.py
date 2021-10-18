# -*- coding: utf-8 -*-
import requests
import json 
import libmediathek4utils as lm4utils


headers = {'Authorization':'Bearer YTEwZWE3M2UxMTVmYmRjZmE0YTdmNjA4ZTI2NDczZDU3YjdjYmVmMmRmNGFjOTM3M2RhNTM5ZjIxYmI3NTc1Zg'}


class APIParser:
	def __init__(self):
		self.result = {'items':[],'pagination':{'currentPage':0}}
		self.baseURL = 'https://www.arte.tv/api/rproxy/emac/v3'
		self.baseURLGuide = 'https://www.arte.tv/api/emac/v3'
		self.baseURLApp = 'https://api-cdn.arte.tv/api/emac/v3/'
		self.token = 'YTEwZWE3M2UxMTVmYmRjZmE0YTdmNjA4ZTI2NDczZDU3YjdjYmVmMmRmNGFjOTM3M2RhNTM5ZjIxYmI3NTc1Zg'
		self.baseURLAppPreprod = 'https://api-preprod.arte.tv/api/emac/v3/'
		self.tokenPreprod = 'MWZmZjk5NjE1ODgxM2E0MTI2NzY4MzQ5MTZkOWVkYTA1M2U4YjM3NDM2MjEwMDllODRhMjIzZjQwNjBiNGYxYw'
		self.baseURLAppDev = 'https://emac-dev.arte.tv/api/emac/v3'
		self.tokenDev = ''
		self.playerURL = 'https://api.arte.tv/api'
		self.generalUrl = 'https://static-cdn.arte.tv/static/artevp/5.0.6/config/json/general.json'
		self._setLang()

	def parseHome(self):
		j = requests.get(f'{self.baseURL}/{self.lang}/web/HOME/').json()
		for zone in j['zones']:
			d = {'type':'dir', 'params':{'mode':'libArteListData'}, 'metadata':{'art':{}}}
			if zone['code']['name'] != None:
				d['metadata']['name'] = zone['title']
				d['params']['code'] = zone['code']['name']
				self.result['items'].append(d)
		return self.result
		

	def parseDataCode(self,code='playlists_HOME',data='MANUAL_TEASERS'):
		return self._getData(f'{self.baseURL}/{self.lang}/web/data/{data}/?imageFormats=square,landscape,banner,portrait&code={code}&page=1&limit=100')

	def parseData(self,data,uriParams):
		url = f'{self.baseURL}/{self.lang}/web/data/{data}/?imageFormats=square,landscape,banner,portrait&page=1&limit=100'
		for k,v in json.loads(uriParams).items():
			url += f'&{k}={v}'
		return self._getData(url)

	def _getData(self,url):
		j = requests.get(url, headers=headers).json()
		for item in j['data']:
			if item['kind']['code'] == 'SHOW' or item['kind']['code'] == 'BONUS':
				d = {'type':'video', 'params':{'mode':'libArtePlayWeb'}, 'metadata':{'art':{}}}
				d['metadata']['duration'] = item['duration']
				d['metadata']['mpaa'] = item['ageRating']
				d['params']['programId'] = item['programId']
			elif item['kind']['code'] == 'LIVE_EVENT':
				d = {'type':'video', 'params':{'mode':'libArtePlayWeb'}, 'metadata':{'art':{}}}
				d['metadata']['mpaa'] = item['ageRating']
				d['params']['programId'] = item['programId']
			else:
				d = {'type':'dir', 'params':{'mode':'libArteListData', 'data':'COLLECTION_VIDEOS'}, 'metadata':{'art':{}}}
				d['params']['uriParams'] = f'{{"collectionId":"{item["programId"]}"}}'
			#d['metadata']['name'] = item['title']
			d['metadata']['tvshowtitle'] = item['title']
			if item['subtitle'] != None:
				d['metadata']['name'] = item['subtitle']
			else:
				d['metadata']['name'] = item['title']
			d['metadata']['plot'] = item['shortDescription']
			d['metadata']['plotoutline'] = item['subtitle']
			if item['images']['landscape'] != None:
				d['metadata']['art']['thumb'] = item['images']['landscape']['resolutions'][2]['url']
				d['metadata']['art']['fanart'] = item['images']['landscape']['resolutions'][2]['url']
			if item['images']['banner'] != None:
				d['metadata']['art']['banner'] = item['images']['banner']['resolutions'][2]['url']
			if item['images']['square'] != None:
				d['metadata']['art']['icon'] = item['images']['square']['resolutions'][2]['url']
			if item['images']['portrait'] != None:
				d['metadata']['art']['poster'] = item['images']['portrait']['resolutions'][1]['url']

			self.result['items'].append(d)
		return self.result

		
	def parseCollection(self,collectionId):
		url = f'{self.baseURL}/{self.lang}/web/data/COLLECTION_VIDEOS/?collectionId={collectionId}&page=1&limit=100'
		self._getData(url)
		return self.result

	def _getShows(self,j):
		for item in j['data']:
			d = {'type':'video', 'params':{'mode':'libArtePlayWeb'}, 'metadata':{'art':{}}}
			
			d['metadata']['tvshowtitle'] = item['title']
			if item['subtitle'] != None:
				d['metadata']['name'] = item['subtitle']
			else:
				d['metadata']['name'] = item['title']

			d['metadata']['duration'] = item['duration']
			d['metadata']['mpaa'] = item['ageRating']
			d['metadata']['art']['thumb'] = item['images']['landscape']['resolutions'][2]['url']

			d['params']['programId'] = item['programId']
			self.result['items'].append(d)

		

	def parsePagesShows(self,uri):
		self.result['content'] = 'tvshows'
		j = requests.get(f'{self.baseURL}/{self.lang}/web/pages/{uri}').json()
		for item in j['zones'][0]['data']:
			d = {'type':'dir', 'params':{'mode':'libArteListCollection'}, 'metadata':{'art':{}}}
			
			d['metadata']['name'] = item['title']
			d['metadata']['plotoutline'] = item['subtitle']
			d['metadata']['plot'] = item['shortDescription']
			d['metadata']['art']['thumb'] = item['images']['landscape']['resolutions'][2]['url']

			d['params']['programId'] = item['programId']
			d['params']['collectionId'] = item['programId']
			self.result['items'].append(d)

		return self.result

	def parsePagesVideos(self,uri,content='videos'):
		self.result['content'] = content
		j = requests.get(f'{self.baseURL}/{self.lang}/web/pages/{uri}').json()
		for item in j['zones'][0]['data']:
			if item['type'] == 'teaser':
				d = {'type':'video', 'params':{'mode':'libArtePlayWeb'}, 'metadata':{'art':{}}}
			else:
				d = {'type':'dir', 'params':{'mode':'libArteListCollection'}, 'metadata':{'art':{}}}
			
			d['metadata']['name'] = item['title']
			d['metadata']['plot'] = item['shortDescription']
			d['metadata']['duration'] = item['duration']
			d['metadata']['mpaa'] = item['ageRating']
			d['metadata']['art']['thumb'] = item['images']['landscape']['resolutions'][2]['url']

			d['params']['programId'] = item['programId']
			d['params']['collectionId'] = item['programId']
			self.result['items'].append(d)

		return self.result


	def parseDate(self,date='2020-01-30'):
		j = requests.get(f'{self.baseURL}/{self.langGuide}/web/pages/TV_GUIDE/?day={date}').json()
		for item in j['zones'][1]['data']:
			d = {'type':'date', 'params':{'mode':'libArtePlayWeb'}, 'metadata':{'art':{}}}
			
			d['metadata']['name'] = item['title']
			d['metadata']['duration'] = item['duration']
			d['metadata']['mpaa'] = item['ageRating']
			d['metadata']['plot'] = item['shortDescription']
			d['metadata']['art']['thumb'] = item['images']['landscape']['resolutions'][2]['url']
			if len(item['broadcastDates']) > 0:
				d['metadata']['aired'] = {'ISO8601':item['broadcastDates'][0]}

			d['params']['programId'] = item['programId']
			d['params']['collectionId'] = item['programId']
			self.result['items'].append(d)
		return self.result


	def _setLang(self):
		availableLanguages = ['en','de','es','fr','it','pl',]
		s = lm4utils.getSetting('language')
		if s == 'system' or s == '':
			l = lm4utils.getISO6391()
			if l in availableLanguages:
				self.lang = l
				self.langGuide = l
			else:
				self.lang = 'en'
				self.langGuide = 'en'
		else:
			self.lang = s
			self.langGuide = s

