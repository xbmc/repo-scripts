# -*- coding: utf-8 -*-
import time
import re,random,datetime
import sys
from datetime import date, timedelta

import libardnewjsonparser

from libmediathek4 import lm4


o = libardnewjsonparser.parser()

channels = {
			  'ARD-alpha':'alpha',
			  'ARTE':'arte',
			  'BR':'br',
			  'Das Erste':'daserste',
			  'funk':'funk',
			  'HR':'hr',
			  'MDR':'mdr',
			  'NDR ':'ndr',
			  'ONE':'one',
			  'phoenix':'phoenix',
			  'Radio Bremen':'radiobremen',
			  'RBB':'rbb',
			  'SR':'sr',
			  'SWR':'swr',
			  'tagesschau24':'tagesschau24',
			  'WDR':'wdr',}
			  
			
class libard(lm4):
	def __init__(self):
		lm4.__init__(self)
		self.defaultMode = 'libArdListMain'

		self.modes.update({
			'libArdListMain':self.libArdListMain,
			'libArdListDefaultPage':self.libArdListDefaultPage,
			'libArdListWidget':self.libArdListWidget,
			'libArdListMorePage':self.libArdListMorePage,
			'libArdListShows':self.libArdListShows,
			'libArdListShow':self.libArdListShow,
			'libArdListEpisodes':self.libArdListEpisodes,
			'libArdListChannelHome':self.libArdListChannelHome,
			'libArdListChannel':self.libArdListChannel,
			'libArdListChannelDateVideos':self.libArdListChannelDateVideos,
		})
		
		self.searchModes = {
			'libArdListSearch': self.libArdListSearch,
		}

		self.playbackModes = {
			'libArdPlay':self.libArdPlay,
		}

	def libArdListMain(self):
		l = []
		l.append({'metadata':{'name':self.translation(32030)}, 'params':{'mode':'libArdListWidget', 'widgetId':'4o5DEpNx9uMOSmAceOCass'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32132)}, 'params':{'mode':'libArdListShows', 'client':'ard'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32133)}, 'params':{'mode':'libArdListChannel'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32144)}, 'params':{'mode':'libArdListWidget', 'widgetId':'16tmBoMKT0iqkyc4ycwgIE', 'content':'movies'}, 'type':'dir'})
		l.append({'metadata':{'name':self.translation(32145)}, 'params':{'mode':'libArdListChannelHome'}, 'type':'dir'})
		#l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'client':'ard', 'searchMode':'libArdListSearch'}, 'type':'dir'})#TODO: reimplement
		return {'items':l,'name':'root'}
		
	def libArdListShows(self):
		return o.parseShows(self.params['client'])

	def libArdListShow(self):
		return o.parseShow(self.params['client'],self.params['showId'])

	def libArdListEpisodes(self):
		return o.parseEpisodes(self.params['client'],self.params['showId'],self.params['season'],self.params['withAudiodescription'],self.params['withOriginalVersion'],self.params['withOriginalWithSubtitle'],self.params['withSignLanguage'])

	def libArdListDefaultPage(self):
		if 'content' in self.params:
			o.setContend(self.params['content'])
		return o.parseDefaultPage(self.params['client'])
		
	def libArdListWidget(self):
		return o.parseWidget(self.params['widgetId'],self.params.get('client','ard'))

	def libArdListMorePage(self):
		return o.parseMorePage(self.params['client'],self.params['compilationId'])

	def libArdListChannelHome(self):
		result = {'items':[], 'content':'movies', 'pagination':{'currentPage':0}}
		for channel in channels:
			d = {'type':'dir', 'params':{'mode':'libArdListDefaultPage'}, 'metadata':{}}
			d['params']['client'] = channels[channel]
			d['metadata']['name'] = channel
			result['items'].append(d)
		return result
		
	def libArdListChannel(self):
		result = {'items':[], 'content':'movies', 'pagination':{'currentPage':0}}
		for channel in channels:
			d = {'type':'dir', 'params':{'mode':'libMediathekListDate', 'subParams':f'{{"client":"{channels[channel]}", "mode":"libArdListChannelDateVideos"}}'}, 'metadata':{}}
			d['metadata']['name'] = channel
			result['items'].append(d)
		return result
			
	def libArdListChannelDateVideos(self):
		return o.parseProgram(self.params['client'],self.params['yyyymmdd'])

	def libArdPlay(self):
		return o.parseVideo(self.params['id'])

	def libArdListSearch(self,searchString):
		return o.parseSearchVOD(self.params['client'],searchString)
		