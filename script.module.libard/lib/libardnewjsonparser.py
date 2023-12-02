# -*- coding: utf-8 -*-
import json
import requests
import hashlib
import libardgraphqlqueries as q

apiUrl = 'https://api.ardmediathek.de/page-gateway'


headers = {'content-type':'application/json'}

class parser:
	def __init__(self):
		self.result = {'items':[], 'content':'movies', 'pagination':{'currentPage':0}}
		self.deviceType = 'pc'
		#self.deviceType = 'tv'
		#self.deviceType = 'responsive'
		#self.deviceType = 'mobile'
		#self.deviceType = 'amazon'
		#self.deviceType = 'tablet'
		#self.deviceType = 'phone'

	def setContend(self,content):
		self.result['content'] = content

	def setParams(self,params):
		self.params = params
		
	def setPlugin(self,plugin):
		self.plugin = plugin

	def parseDefaultPage(self,client):
		j = requests.get(f'{apiUrl}/pages/{client}/home',headers=headers).json()
		for widget in j['widgets']:
			d = {'type':'dir', 'params':{'mode':'libArdListWidget'}, 'metadata':{}}
			d['metadata']['name'] = widget['title']
			d['params']['widgetId'] = widget['id']
			d['params']['client'] = client
			if widget['type'] != 'stage' and d['metadata']['name'] != 'Livestreams':
				self.result['items'].append(d)
		return self.result

	def parseShows(self,client='ard'):
		j = requests.get(f'{apiUrl}/pages/{client}/editorial/experiment-a-z?embedded=true',headers=headers).json()
		for widget in j['widgets']:
			for teaser in widget['teasers']:
				self._grabTeaser(teaser,client)
		return self.result

	def parseShow(self,client='ard',showId=''):
		j = requests.get(f'{apiUrl}/pages/{client}/grouping/{showId}?seasoned=true&embedded=false',headers=headers).json()
		if len(j['widgets']) == 1:
			j = requests.get(f'{apiUrl}/widgets/{client}/asset/{showId}?pageNumber=0&pageSize=100&embedded=true&seasoned=false',headers=headers).json()
			for teaser in j['teasers']:
				self._grabTeaser(teaser,client)
		elif len(j['widgets']) > 1:
			for widget in j['widgets']:
				if 'seasonNumber' in widget:
					d = {'params':{}, 'metadata':{'art':{}}}
					d['metadata']['name'] = widget['title']
					if 'images' in widget:
						if 'aspect16x9' in widget['images']:
							d['metadata']['art']['thumb'] = widget['images']['aspect16x9']['src'].format(width='512')
						if 'aspect3x4' in widget['images']:
							d['metadata']['art']['poster'] = widget['images']['aspect3x4']['src'].format(width='512')
					d['params']['season'] = widget['seasonNumber']
					d['params']['client'] = client
					d['params']['showId'] = widget['id']
					d['params']['withAudiodescription'] = str(widget['withAudiodescription'])
					d['params']['withOriginalVersion'] = str(widget['withOriginalVersion'])
					d['params']['withOriginalWithSubtitle'] = str(widget['withOriginalWithSubtitle'])
					d['params']['withSignLanguage'] = str(widget['withSignLanguage'])
					d['params']['mode'] = 'libArdListEpisodes'
					d['type'] = 'dir'
					self.result['items'].append(d)
		return self.result

	def parseEpisodes(self,client='ard',showId='',season='1',withAudiodescription='false',withOriginalVersion='false',withOriginalWithSubtitle='false',withSignLanguage='false'):
		print(f'{apiUrl}/widgets/{client}/asset/{showId}?pageNumber=0&pageSize=100&embedded=true&seasoned=true&seasonNumber={season}&withAudiodescription={withAudiodescription}&withOriginalWithSubtitle={withOriginalWithSubtitle}&withAudiodescription={withAudiodescription}&withSignLanguage={withSignLanguage}')
		j = requests.get(f'{apiUrl}/widgets/{client}/asset/{showId}?pageNumber=0&pageSize=100&embedded=true&seasoned=true&seasonNumber={season}&withAudiodescription={withAudiodescription}&withOriginalWithSubtitle={withOriginalWithSubtitle}&withAudiodescription={withAudiodescription}&withSignLanguage={withSignLanguage}',headers=headers).json()
		for teaser in j['teasers']:
			self._grabTeaser(teaser,client)
		#self._grabPagination(j['data']['widget']['pagination'])
		return self.result

	def parseProgram(self,client='daserste',startDate='2019-08-30'):
		j = requests.get(f'{apiUrl}/compilations/{client}/pastbroadcasts?startDateTime={startDate}T00%3A00%3A00.000Z&endDateTime={startDate}T23%3A59%3A59.999Z&pageSize=200',headers=headers).json()
		#https://api.ardmediathek.de/page-gateway/compilations/alpha/pastbroadcasts?startDateTime=2021-05-06T04%3A30%3A00.000Z&endDateTime=2021-05-07T04%3A29%3A59.000Z&pageSize=200
		for teaser in j[0]['teasers']:
			self._grabTeaser(teaser)
		return self.result

	def parseWidget(self,widgetId='4o5DEpNx9uMOSmAceOCass',client='ard'):
		j = requests.get(f'{apiUrl}/widgets/{client}/editorials/{widgetId}?pageNumber=0&pageSize=20',headers=headers).json()
		for teaser in j['teasers']:
			self._grabTeaser(teaser,client)
		return self.result

	"""
	#disabled atm
	def parseMorePage(self,client,compilationId):
		j = self._getRequest({'query': q.queryMorePage + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"compilationId":"{compilationId}","client":"{client}"}}'})
		if j['data']['morePage']['widget']['teasers'] != None:
			for teaser in j['data']['morePage']['widget']['teasers']:
				self._grabTeaser(teaser)#,client)
		return self.result
	"""


	"""
	#disabled atm
	def parseSearchVOD(self,client='ard',text=''):
		j = self._getRequest({'query': q.querySearchPageVOD + q.fragmentTeaser + q.fragmentTeaserImages,'variables':f'{{"client":"{client}", "text":"{text}"}}'})
		for teaser in j['data']['searchPage']['vodResults']:
			self._grabTeaser(teaser,client)
		return self.result
	"""

	def parseVideo(self,clipId='Y3JpZDovL2JyLmRlL3ZpZGVvL2NkNzBjODMwLTM2ZTAtNDljNC1iMDJiLTQyNWNhMWIyZDg3NA',client="ard"):
		j = requests.get(f'{apiUrl}/mediacollection/{clipId}?devicetype={self.deviceType}',headers=headers).json()
		for item in j['_mediaArray'][0]['_mediaStreamArray']:
			if item['_quality'] == 'auto':
				url = item['_stream']
		if url.startswith('//'): 
			url = 'http:' + url
		d = {'media':[{'url':url, 'stream':'HLS'}]}
		if '_subtitleUrl' in j:
			d['subtitle'] = [{'url':j['_subtitleUrl'], 'type':'ttml', 'lang':'de', 'colour':True}]
		return d


	def _grabTeaser(self,teaser,client=False):
		d = {'params':{}, 'metadata':{'art':{}}}
		d['metadata']['name'] = teaser['shortTitle']
		d['metadata']['plotoutline'] = teaser['longTitle']
		if 'shortSynopsis' in teaser:
			d['metadata']['plotoutline'] = teaser['shortSynopsis']
		if 'synopsis' in teaser:
			d['metadata']['plot'] = teaser['synopsis']
		if 'duration' in teaser:
			d['metadata']['duration'] = teaser['duration']
		if 'images' in teaser:
			if 'aspect16x9' in teaser['images']:
				d['metadata']['art']['thumb'] = teaser['images']['aspect16x9']['src'].format(width='512')
			if 'aspect3x4' in teaser['images']:
				d['metadata']['art']['poster'] = teaser['images']['aspect3x4']['src'].format(width='512')
		if 'show' in teaser and teaser['show'] and 'images' in teaser['show'] and teaser['show']['images'] and '16x9' in teaser['show']['images']:
			d['metadata']['art']['fanart'] = teaser['show']['images']['16x9']['src'].format(width='512')
		if client:
			d['params']['client'] = client
		if teaser['type'] == 'compilation':
			d['params']['compilationId'] = teaser['links']['target']['id']
			d['type'] = 'dir'
			d['params']['mode'] = 'libArdListMorePage'
		elif teaser['type'] == 'show':
			d['params']['showId'] = teaser['links']['target']['id']
			d['type'] = 'dir'
			d['params']['mode'] = 'libArdListShow'
		elif teaser['type'] == 'poster':
			d['type'] = 'movie'
			d['params']['mode'] = 'libArdPlay'
		elif teaser['type'] == 'broadcastMainClip':
			d['type'] = 'date'
			d['params']['mode'] = 'libArdPlay'
		else:
			d['type'] = 'video'
			d['params']['mode'] = 'libArdPlay'

		if 'broadcastedOn' in teaser:
			d['metadata']['aired'] = {'ISO8601':teaser['broadcastedOn']}

		
		if 'subtitled' in teaser:
			d['metadata']['hassubtitles'] = True

		if 'links' in teaser and 'target' in teaser['links'] and 'id' in teaser['links']['target']:
			d['params']['id'] = teaser['links']['target']['id']
			self.result['items'].append(d)
		return

	def _grabPagination(self,p):
		return
		self.result['pagination']['currentPage'] = p['pageNumber']
		self.result['pagination']['pages'] = []
		lastPage = int((p['totalElements']-1)/20)
		for i in range(0,lastPage+1):
			d = self.params
			d['pageNumber'] = i
			self.result['pagination']['pages'].append(d)
		return


