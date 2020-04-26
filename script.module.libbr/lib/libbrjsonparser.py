# -*- coding: utf-8 -*-
import json
import urllib
import time
import requests

import copy

import libbrgraphqlqueries
import libbrgraphqlqueriesnew as q

#graphqlUrl = 'https://proxy-base.master.mango.express/graphql'
graphqlUrl = 'https://api.mediathek.br.de/graphql'
headers = {'Content-Type':'application/json', 'Accept-Encoding':'gzip, deflate'}
	
class parser:
	def __init__(self):
		self.result = {'items':[],'pagination':{'currentPage':0}}
		self.template = {'params':{}, 'metadata':{'art':{}}, 'type':'video'}
		
		self.boards = [
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-film-krimi',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-kabarett-comedy',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-doku-reportage',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-news-politik',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-natur-tiere',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-wissen',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-berge',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-kultur',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-heimat',
			'Board:http://ard.de/ontologies/mangoLayout#discover2',
			'Board:http://ard.de/ontologies/mangoLayout#discover1',
			'Board:http://ard.de/ontologies/mangoLayout#entdecken-kinder',]

	def parseSeries(self):
		p = json.dumps({'query': q.querySeries})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['allSeries']['edges']:
			d = {'type':'dir', 'params':{'mode':'libBrListEpisodes'}, 'metadata':{'art':{}}}
			node = edge['node']
			d['metadata']['name'] = node['title']
			d['metadata']['tvshowtitle'] = node['kicker']
			d['metadata']['plotoutline'] = node['kicker']
			d['metadata']['plot'] = node['kicker']
			if node['shortDescription'] is not None:
				d['metadata']['plotoutline'] = node['shortDescription']
				d['metadata']['plot'] = node['shortDescription']
			if node['description'] is not None:
				d['metadata']['plot'] = node['description']
			try:
				d['metadata']['thumb'] = node['defaultTeaserImage']['imageFiles']['edges'][0]['node']['publicLocation']
			except: pass
			d['metadata']['channel'] = 'BR'#TODO: add ARD-Alpha
			d['params']['id'] = node['id']
			self.result['items'].append(d)
		return self.result
		
	def parseEpisodes(self,id):
		p = json.dumps({'query': q.queryEpisodes + q.fragmentVideoItems_programme ,'variables':{'id':id,'day':time.strftime('%Y-%m-%dT%H:%M:%S.000Z')}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['series']['episodes']['edges']:
			node = edge['node']
			self._buildVideoDict(node)
		return self.result
		
	def parseBoards(self):
		p = json.dumps({'query': libbrgraphqlqueries.getCats(),'variables':{'nodes':self.boards}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for node in j['data']['nodes']:
			d = {'type':'dir', 'params':{'mode':'libBrListBoard'}, 'metadata':{'art':{}}}
			d['metadata']['name'] = node['title'].title()
			if 'shortDescription' in node and node['shortDescription'] is not None:
				d['metadata']['plotoutline'] = node['shortDescription']
				d['metadata']['plot'] = node['shortDescription']
			if 'description' in node and node['description'] is not None:
				d['metadata']['plot'] = node['description']
			d['params']['boardId'] = node['id']
			self.result['items'].append(d)
		return self.result
		
	def parseBoard(self,boardId):
		p = json.dumps({'query': q.queryBoard + q.fragmentClip,'variables':{'boardId':boardId}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['board']['sections']['edges']:
			for edge2 in edge['node']['contents']['edges']:
				self._buildVideoDict(edge2['node']['represents'])
		return self.result

	def parseCategories(self):
		p = json.dumps({'query': q.queryCategories})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['allCategories']['edges']:
			d = {'type':'dir', 'params':{'mode':'libBrListCategory'}, 'metadata':{'art':{}}}
			node = edge['node']
			d['metadata']['name'] = node['label']
			d['params']['id'] = node['id']
			self.result['items'].append(d)
		return self.result
		
	def parseCategory(self,category):
		filter = {"categories": {"contains": category}}
		return self._parseAllClips(filter)

	def parseGenres(self):
		p = json.dumps({'query': q.queryGenres})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['allGenres']['edges']:
			d = {'type':'dir', 'params':{'mode':'libBrListGenre'}, 'metadata':{'art':{}}}
			node = edge['node']
			d['metadata']['name'] = node['label']
			d['params']['id'] = node['id']
			self.result['items'].append(d)
		return self.result
		
	def parseGenre(self,genre):
		filter = {'genres':{'contains':genre}}
		return self._parseAllClips(filter)
		
	def parseSections(self):
		p = json.dumps({'query': q.querySections})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['allSections']['edges']:
			d = {'type':'dir', 'params':{'mode':'libBrListSection'}, 'metadata':{'art':{}}}
			node = edge['node']
			if node['title'] is not None:
				d['metadata']['name'] = node['title']
				d['params']['id'] = node['id']
				self.result['items'].append(d)
		return self.result
		
	def parseSection(self,id):
		p = json.dumps({'query': q.queryBoard + q.fragmentClip,'variables':{'id':id}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for edge in j['data']['viewer']['section']['contents']['edges']:
			self._buildVideoDict(edge['node']['represents'])
		return self.result
		

	def parseDate(self,day,channel):
		p = json.dumps({'query': q.queryDate,'variables':{"slots": ["MORNING","NOON","EVENING","NIGHT"], "day": day, "broadcasterId":f"av:http://ard.de/ontologies/ard#{channel}"}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()

		for epg in j['data']['viewer']['allLivestreams']['edges'][0]['node']['epg']:
			broadcastEvent = epg['broadcastEvent']
			if broadcastEvent != None:
				publicationOf = broadcastEvent['publicationOf']
				if len(publicationOf['essences']['edges']) != 0:
					self.template['metadata']['aired'] = {'ISO8601':broadcastEvent['start'].replace('.000','')}
					self.template['type'] = 'date'
					self._buildVideoDict(publicationOf)
		return self.result
		
	def parseSearch(self,term):
		filter = {"term":term,"audioOnly":{"eq":False},"essences":{"empty":{"eq":False}},"status":{"id":{"eq":"av:http://ard.de/ontologies/lifeCycle#published"}}}
		return self._parseAllClips(filter)
		
		
	def parseVideo(self,id):
		p = json.dumps({'query': q.queryVideo,'variables':{'clipId':id}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		
		node = j['data']['viewer']['clip']['videoFiles']['edges'][0]['node']
		d = {'media': []}
		d['media'] = []
		d['media'].append({'url':node['publicLocation'], 'stream':'HLS'})
		try:
			sub = node['subtitles']['edges'][0]['node']['timedTextFiles']['edges'][0]['node']['publicLocation']
			d['subtitle'] = [{'url':sub, 'type': 'ttml', 'lang':'de'}]
		except: pass
		return d
		
	def _parseAllClips(self,filter):
		p = json.dumps({'query': q.query_allClips + q.fragmentVideoItems_clip + q.fragmentClip,'variables':{'filter':filter}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for edge in j['data']['viewer']['allClips']['edges']:
			self._buildVideoDict(edge['node'])
		return self.result
		
	def _buildVideoDict(self,node):
		if node == {}:
			return
		d = copy.deepcopy(self.template)
		d['metadata']['name'] = node['title']
		d['metadata']['tvshowtitle'] = node['kicker']
		d['metadata']['plotoutline'] = node['kicker']
		d['metadata']['plot'] = node['kicker']
		if node['shortDescription'] is not None and node['shortDescription'] != '':
			d['metadata']['plotoutline'] = node['shortDescription']
			d['metadata']['plot'] = node['shortDescription']
		if node['description'] is not None and node['description'] != '':
			d['metadata']['plot'] = node['description']
		if 'duration' in node:
			d['metadata']['duration'] = node['duration']
		try:
			d['metadata']['art']['thumb'] = node['defaultTeaserImage']['imageFiles']['edges'][0]['node']['publicLocation'] + '?w=600&q=70'
		except: pass
		d['params']['id'] = node['id']
		d['params']['mode'] = 'libBrPlay'
		self.result['items'].append(d)
		return 		
		
	def parseNew(self,boardId='l:http://ard.de/ontologies/mangoLayout#mainBoard_web',itemCount=50):
		#variables = {'boardId':boardId,"itemCount":itemCount}
		p = json.dumps({'query': q.queryBoard + q.fragmentClip,'variables':{'boardId':boardId}})
		j = requests.post(graphqlUrl,headers=headers,data=p).json()
		for edge in j['data']['viewer']['board']['stageTeaserSection']['edges'][2]['node']['verticalSectionContents']['edges']:
			self._buildVideoDict(edge['node']['represents'])
		return self.result
		