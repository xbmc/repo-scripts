# -*- coding: utf-8 -*-
import time
import re,random,datetime
import sys
from datetime import date, timedelta

import libardnewjsonparser

from libmediathek4 import lm4


o = libardnewjsonparser.parser()

channels = {
			  'ARD-alpha':'5868',
			  'BR':'2224',
			  #['Einsfestival', :'673348' ],
			  #['EinsPlus',     :'4178842'],
			  'Das Erste':'208',
			  'HR':'5884',
			  'MDR':'5882',
			  'MDR Thüringen':'1386988',
			  'MDR Sachsen':'1386804',
			  'MDR Sachsen-Anhalt':'1386898',
			  'NDR Fernsehen':'5906',
			  'One':'673348',
			  'RB':'5898',
			  'RBB':'5874',
			  'SR':'5870',
			  'SWR Fernsehen':'5310',
			  'SWR Rheinland-Pfalz':'5872',
			  'SWR Baden-Württemberg':'5904',
			  'tagesschau24':'5878',
			  'WDR':'5902',}
			
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
		l.append({'metadata':{'name':self.translation(32139)}, 'params':{'mode':'libMediathekSearch', 'client':'ard', 'searchMode':'libArdListSearch'}, 'type':'dir'})
		return {'items':l,'name':'root'}
		
	def libArdListShows(self):
		return o.parseShows(self.params['client'])

	def libArdListShow(self):
		return o.parseShow(self.params['client'],self.params['showId'])

	def libArdListDefaultPage(self):
		if 'content' in self.params:
			o.setContend(self.params['content'])
		return o.parseDefaultPage(self.params['client'],self.params['name'])
		
	def libArdListWidget(self):
		return o.parseWidget(self.params['widgetId'],self.params.get('client','ard'))

	def libArdListMorePage(self):
		return o.parseMorePage(self.params['client'],self.params['compilationId'])

	def libArdListChannelHome(self):
		channels = o.parseChannels()
		for channel in channels['items']:
			channel['params']['mode'] = 'libArdListDefaultPage'
			channel['params']['client'] = channel['params']['channel']
			channel['params']['name'] = 'home'
		return channels
		
	def libArdListChannel(self):
		channels = o.parseChannels()
		for channel in channels['items']:
			channel['params']['mode'] = 'libMediathekListDate'
			channel['params']['subParams'] = f'{{"mode":"libArdListChannelDateVideos","channel":"{channel["params"]["channel"]}"}}'
		return channels
			
	def libArdListChannelDateVideos(self):
		return o.parseProgram(self.params['channel'],self.params['yyyymmdd'])

	def libArdPlay(self):
		return o.parseVideo(self.params['id'])

	def libArdListSearch(self,searchString):
		return o.parseSearchVOD(self.params['client'],searchString)
		