# -*- coding: utf-8 -*-

from libmediathek4 import lm4


#https://api.zdf.de/content/documents/zdf-startseite-100.json?profile=default
#https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=teaser
#https://api.zdf.de/content/documents/meist-gesehen-100.json?profile=default
#https://api.zdf.de/content/documents/sendungen-100.json?profile=default
#api.zdf.de/search/documents?hasVideo=true&q=*&types=page-video&sender=ZDFneo&paths=%2Fzdf%2Fcomedy%2Fneo-magazin-mit-jan-boehmermann%2Ffilter%2C%2Fzdf%2Fcomedy%2Fneo-magazin-mit-jan-boehmermann&sortOrder=desc&limit=1&editorialTags=&sortBy=date&contentTypes=episode&exclEditorialTags=&allEditorialTags=false
#api.zdf.de/search/documents?hasVideo=true&q=*&types=page-video&sender=ZDFneo&paths=%2Fzdf%2Fnachrichten%2Fzdfspezial%2Ffilter%2C%2Fzdf%nachrichten%2Fzdfspezial&sortOrder=desc&limit=1&editorialTags=&sortBy=date&contentTypes=episode&exclEditorialTags=&allEditorialTags=false
#https://api.zdf.de/cmdm/epg/broadcasts?from=2016-10-28T05%3A30%3A00%2B02%3A00&to=2016-10-29T05%3A29%3A00%2B02%3A00&limit=500&profile=teaser
#https://api.zdf.de/cmdm/epg/broadcasts?from=2016-10-28T05%3A30%3A00%2B02%3A00&to=2016-10-29T05%3A29%3A00%2B02%3A00&limit=500&profile=teaser&tvServices=ZDF
#https://api.3sat.de/content/documents/zdf/programm?profile=video-app&maxResults=200&airtimeDate=2019-06-09T12:00:00.000Z&includeNestedObjects=true


class libzdf(lm4):
	def __init__(self):
		lm4.__init__(self)
		self.defaultMode = 'libZdfListMain'

		self.modes.update({
			'libZdfListMain':self.libZdfListMain,
			'libZdfListShows':self.libZdfListShows,
			'libZdfListVideos':self.libZdfListVideos,
			'libZdfListChannel':self.libZdfListChannel,
			'libZdfListChannelDateVideos':self.libZdfListChannelDateVideos,
			'libZdfListPage':self.libZdfListPage,
			})

		self.searchModes = {
			'libZdfListSearch': self.libZdfListSearch,
		}

		self.playbackModes = {
			'libZdfPlay':self.libZdfPlay,
			'libZdfPlayById':self.libZdfPlayById,
			}

		if self.apiVersion == 1:
			import libzdfjsonparser as jsonParser
			self.parser = jsonParser.parser()
		elif self.apiVersion == 2:
			import libzdfjsonparser2 as jsonParser
			self.parser = jsonParser.parser2()

		self.parser.baseApi = self.baseApi
		self.parser.userAgent = self.userAgent
		self.parser.tokenUrl = self.tokenUrl
		self.parser.API_CLIENT_ID = self.API_CLIENT_ID
		self.parser.API_CLIENT_KEY = self.API_CLIENT_KEY

	def libZdfListMain(self):
		l = []
		l.append({'metadata':{'name':self.translation(32031)}, 'params':{'mode':'libZdfListPage','url':f'{self.baseApi}/content/documents/meist-gesehen-100.json?profile=default'}, 'type':'dir'})
		#l.append({'metadata':{'name':self.translation(32031)}, 'params':{'mode':'libZdfListPage','url':f'{self.baseApi}/content/documents/filter-meist-gesehen-100.json?profile=page-video_episode_vod&limit=50'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32132)}, 'params':{'mode':'libZdfListShows'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32133)}, 'params':{'mode':'libZdfListChannel'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32134)}, 'params':{'mode':'libZdfListPage', 'url':f'{self.baseApi}/search/documents?q=%2A&contentTypes=category'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'searchMode':'libZdfListSearch'}, 'type':'dir'})
		return {'items':l,'name':'root'}
	def libZdfListShows(self):
		if 'uri' in self.params:
			return self.parser.getAZ(self.params['uri'])
		else:
			return self.parser.getAZ()
				
	def libZdfListPage(self):
		return self.parser.parsePage(self.params['url'])
		
	def libZdfListVideos(self):
		return self.parser.getVideos(self.params['url'])

	def libZdfPlay(self):
		return self.parser.getVideoUrl(self.params['url'])
		
	def libZdfPlayById(self):
		return self.parser.getVideoUrlById(self.params['id'])
		
	def libZdfListChannel(self):
		l = []
		for channel in self.channels:
			l.append({'metadata':{'name':channel}, 'params':{'mode':'libMediathekListDate','subParams':f'{{"mode":"libZdfListChannelDateVideos","channel":"{channel}"}}'}, 'type':'dir'})
		return {'items':l,'name':'libZdfListChannel'}
		
	def libZdfListChannelDateVideos(self):
		self.params['url'] = f"{self.baseApi}/cmdm/epg/broadcasts?from={self.params['yyyymmdd']}T00%3A00%3A00%2B02%3A00&to={self.params['yyyymmdd']}T23%3A59%3A59%2B02%3A00&limit=500&profile=teaser&tvServices={self.params['channel']}"
		return self.libZdfListPage()
		
	def libZdfListSearch(self,searchString):
		self.params['url'] = f'{self.baseApi}/search/documents?q={searchString}'
		return self.libZdfListPage()
			