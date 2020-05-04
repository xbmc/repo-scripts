# -*- coding: utf-8 -*-
import requests
import json

#https://player-v5-dev.arte.tv/static

preferedVideoDE = ['DE','UT','OV',]

class PlayerParser:
	def __init__(self):
		self.lang = 'de'
		self.langGuide = 'de'
		self.playerURL = 'https://api.arte.tv/api'
		self.playerURLPreprod = 'https://api-preprod.arte.tv/api'
		self.tokenPreprod = 'ZWU0ZWU0NDlmNTNkODcwNWZhNTYzOTc5MjExZTc4NjE4NzExYjE1OTM3YjFhOTQxMTJhNWJlNzYxNmM3MTdjYQ'
		#self.generalUrl = 'https://static-cdn.arte.tv/static/artevp/5.0.6/config/json/general.json'
		self.generalUrl = 'https://static-cdn.arte.tv/static/artevp/5.2.2/config/json/general.json'
		self.generalUrlPreprod = 'https://static-cdn.arte.tv/static-preprod/artevp/dev/5.2.2/config/json/general.json'
		
	def parseVideo(self,programId):
		d = {}
		j = requests.get(self.generalUrl).json()
		headers = {'Authorization': f'Bearer {j["apiplayer"]["token"]}'}
		j = requests.get(f'{self.playerURL}/player/v2/config/{self.langGuide}/{programId}', headers=headers).json()
		for item in j['data']['attributes']['streams']:
			if item['protocol'] == 'HLS':
				d[item['versions'][0]['shortLabel']] = item['url']
		
		for label in preferedVideoDE:
			if label in d:
				return {'media':[{'url':d[label], 'stream':'HLS'}]}
		return {'media':[{'url':j['data']['attributes']['streams'][0]['url'], 'stream':'HLS'}]}#fallback


