
# -*- coding: utf-8 -*-
import json
import requests
import hashlib
import re
import random
import string
import copy

import libmediathek4utils as lm4utils

log = lm4utils.log

import libzdfjsonparser as jsonParser
parser = jsonParser.parser()

class parser2(jsonParser.parser):
	def _parsePageIndex2(self,j):
		for module in j['module']:
			if 'teaser' in module:
				for teaser in module['teaser']:
					self._grepItem(teaser)
		return self.result

	def _grepItem(self,target,forcedType=False):
		if target['profile'] in ['http://zdf.de/rels/not-found','http://zdf.de/rels/gone']:
			return False
		elif target['profile'] == 'http://zdf.de/rels/content/page-video-teaser-2':
			self._grepPageVideoTeaser2(target,forcedType)
		else:
			self._grepItemDefault(target,forcedType)

	def _grepPageVideoTeaser2(self,teaser,forcedType):

		self.d = copy.deepcopy(self.template)
		self.d['metadata']['name'] = teaser['title']
		self.d['metadata']['plot'] = teaser['text']
		if '384xauto' in teaser['image']['layouts']:
			self.d['metadata']['art']['thumb'] = teaser['image']['layouts']['384xauto']

		target = teaser['target']

		if target['contentType'] == 'episode':# or target['contentType'] == 'clip':
			if 'mainVideoContent' in target:
				content = target['mainVideoContent']['http://zdf.de/rels/target']
			else: return False
				
			if 'duration' in content:
				self.d['metadata']['duration'] = content['duration']

			if not 'http://zdf.de/rels/streams/ptmd-template' in content: return False
			self.d['params']['url'] = self.baseApi + content['http://zdf.de/rels/streams/ptmd-template'].replace('{playerId}',self.playerId)
			self.d['params']['mode'] = 'libZdfPlay'

			self.d['type'] = 'episode'
		else:
			log('Unknown target type: ' + target['contentType'])
			self.d = False
			
		if self.d:
			if forcedType:
				self.d['type'] = forcedType
			self.result['items'].append(self.d)
			return True
		else:
			return False
			