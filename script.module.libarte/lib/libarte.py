# -*- coding: utf-8 -*-
from libmediathek4 import lm4
import libartewebjsonparser

baseApi = 'http://www.arte.tv/hbbtvv2/services/web/index.php'


class libarte(lm4):
	def __init__(self):
		lm4.__init__(self)
		self.parser = libartewebjsonparser.APIParser()
		self.defaultMode = 'libArteListMain'

		self.modes.update({
			'libArteListMain': self.libArteListMain,
			'libArteListData': self.libArteListData,
			'libArteListCollection': self.libArteListCollection,
			'libArteListShows': self.libArteListShows,
			'libArteListVideos': self.libArteListVideos,
			
			'libArteThemes': self.libArteThemes,
			'libArteListDateVideos': self.libArteListDateVideos,
		})

		self.searchModes = {
			'libArteListSearch': self.libArteListSearch,
		}
		self.playbackModes = {
			'libArtePlay':self.libArtePlay,
			'libArtePlayWeb':self.libArtePlayWeb,
		}
		
	def libArteListMain(self):
		l = []
		l.append({'metadata':{'name':self.translation(32032)}, 'params':{'mode':'libArteListData', 'data':'VIDEO_LISTING', 'uriParams':'{"videoType":"MOST_RECENT"}'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32031)}, 'params':{'mode':'libArteListData', 'data':'VIDEO_LISTING', 'uriParams':'{"videoType":"MOST_VIEWED"}'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32132)}, 'params':{'mode':'libArteListData', 'data':'VIDEO_LISTING', 'uriParams':'{"videoType":"MAGAZINES"}'}, 'type':'dir'})
		if self.parser.langGuide in ['de','fr']:
			l.append({'metadata':{'name':self.translation(32133)}, 'params':{'mode':'libMediathekListDate', 'subParams':'{"mode":"libArteListDateVideos"}'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32033)}, 'params':{'mode':'libArteListData', 'data':'VIDEO_LISTING', 'uriParams':'{"videoType":"LAST_CHANCE"}'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'searchMode':'libArteListSearch'}, 'type':'dir'})
		return {'items':l,'name':'root'}
		

	def libArteListShows(self):
		return self.parser.parsePagesShows(self.params['uri'])

	def libArteListVideos(self):
		return self.parser.parsePagesVideos(self.params['uri'])

	def libArteListData(self):
		return self.parser.parseData(self.params['data'],self.params['uriParams'])

	def libArteListCollection(self):
		return self.parser.parseCollection(self.params['collectionId'])

	def libArteListDateVideos(self):
		return self.parser.parseDate(self.params['yyyymmdd'])

	def libArtePlayWeb(self):
		import libarteplayerjsonparser
		player = libarteplayerjsonparser.PlayerParser()
		return player.parseVideo(self.params['programId'])

	def libArteThemes(self):
		return self.parser.getPlaylists()
					
	def libArteListSearch(self,searchString):
		return self.parser.parseData('SEARCH_LISTING',f'{{"mainZonePage":"1", "query":"{searchString}"}}')
			
	def libArtePlay(self):
		return self.parser.getVideoUrlWeb(self.params['url'])

		