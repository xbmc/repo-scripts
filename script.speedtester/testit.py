#!/usr/bin/env python
############################################################################
#							  /T /I										   #
#							   / |/ | .-~/								   #
#						   T\ Y	 I	|/	/  _							   #
#		  /T			   | \I	 |	I  Y.-~/							   #
#		 I l   /I		T\ |  |	 l	|  T  /								   #
#	  T\ |	\ Y l  /T	| \I  l	  \ `  l Y								   #
# __  | \l	 \l	 \I l __l  l   \   `  _. |								   #
# \ ~-l	 `\	  `\  \	 \ ~\  \   `. .-~	|								   #
#  \   ~-. "-.	`  \  ^._ ^. "-.  /	 \	 |								   #
#.--~-._  ~-  `	 _	~-_.-"-." ._ /._ ." ./								   #
# >--.	~-.	  ._  ~>-"	  "\   7   7   ]								   #
#^.___~"--._	~-{	 .-~ .	`\ Y . /	|								   #
# <__ ~"-.	~		/_/	  \	  \I  Y	  : |								   #
#	^-.__			~(_/   \   >._:	  | l______							   #
#		^--.,___.-~"  /_/	!  `-.~"--l_ /	   ~"-.						   #
#			   (_/ .  ~(   /'	  "~"--,Y	-=b-. _)					   #
#				(_/ .  \	Dr0idGuy  / l	   c"~o \					   #
#				 \ /	`.	  .		.^	 \_.-~"~--.	 )					   #
#				  (_/ .	  `	 /	   /	   !	   )/					   #
#				   / / _.	'.	 .':	  /		   '					   #
#				   ~(_/ .	/	 _	`  .-<_								   #
#					 /_/ . ' .-~" `.  / \  \		  ,z=.				   #
#					 ~( /	'  :   | K	 "-.~-.______//					   #
#					   "-,.	   l   I/ \_	__{--->._(==.				   #
#						//(		\  <	~"~"	 //						   #
#					   /' /\	 \	\	  ,v=.	((						   #
#					 .^. / /\	  "	 }__ //===-	 `						   #
#					/ / ' '	 "-.,__ {---(==-							   #
#				  .^ '		 :	T  ~"	ll								   #
#				 / .  .	 . : | :!		 \								   #
#				(_/	 /	 | | j-"		  ~^							   #
#				  ~-<_(_.^-~"											   #
#																		   #
#																		   #
#					   original speedtest-cli DEV						   #
#			 Matt Martz (https://github.com/sivel/speedtest-cli)		   #
#																		   #
#																		   #
# Licensed under the Apache License, Version 2.0 (the "License"); you may  #
# not use this file except in compliance with the License. You may obtain  #
# a copy of the License at												   #
#																		   #
#	   http://www.apache.org/licenses/LICENSE-2.0						   #
#																		   #
# Unless required by applicable law or agreed to in writing, software	   #
# distributed under the License is distributed on an "AS IS" BASIS,WITHOUT #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the #
# License for the specific language governing permissions and limitations  #
# under the License.													   #
############################################################################

import xbmc ,xbmcgui, xbmcaddon
import os
import re
import sys
import math
import signal
import socket
import timeit
import platform
import threading

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
ART = xbmc.translatePath(os.path.join(ADDON.getAddonInfo('path'),'resources', 'skins', 'Default', 'media'))

source = None
shutdown_event = None
socket_socket = socket.socket
ua_tuple = ('Mozilla/5.0', '(%s; U; %s; en-us)'
		% (platform.system(), platform.architecture()[0]),
		'Python/%s' % platform.python_version(),
		'(KHTML, like Gecko)')
		
user_agent = ' '.join(ua_tuple)

#py2 imports except py3 ver
if sys.version_info.major==3:
	try:
		import xml.etree.ElementTree as ET
	except ImportError:
		from xml.dom import minidom as DOM
		ET = None
	from urllib.request import urlopen, Request, HTTPError, URLError
	from http.client import HTTPConnection, HTTPSConnection
	from queue import Queue
	from urllib.parse import urlparse
	try:
		from urllib.parse import parse_qs
	except ImportError:
		from cgi import parse_qs
	from hashlib import md5
if sys.version_info.major==2:
	import xml.etree.cElementTree as ET
	from xml.dom import minidom as DOM
	from urllib2 import urlopen, Request, HTTPError, URLError
	from httplib import HTTPConnection, HTTPSConnection
	from Queue import Queue
	from urlparse import urlparse
	from urlparse import parse_qs
	from md5 import md5


class SpeedtestCliServerListError(Exception):
	"""
"""

def bound_socket(*args, **kwargs):

	global source
	sock = socket_socket(*args, **kwargs)
	sock.bind((source, 0))
	return sock

def distance(origin, destination):
	(lat1, lon1) = origin
	(lat2, lon2) = destination
	radius = 6371  # km

	dlat = math.radians(lat2 - lat1)
	dlon = math.radians(lon2 - lon1)
	a = math.sin(dlat / 2) * math.sin(dlat / 2) \
		+ math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) \
		* math.sin(dlon / 2) * math.sin(dlon / 2)
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	d = radius * c

	return d

def build_request(url, data=None, headers={}):
	if url[0] == ':':
		schemed_url = '%s%s' % (scheme, url)
	else:
		schemed_url = url
	headers['User-Agent'] = user_agent
	return Request(schemed_url, data=data, headers=headers)

def catch_request(request):
	try:
		uh = urlopen(request)
		return uh
	except (HTTPError, URLError, socket.error):
		e = sys.exc_info()[1]
		return (None, e)

class FileGetter(threading.Thread):

	def __init__(self, url, start):
		self.url = url
		self.result = None
		self.starttime = start
		threading.Thread.__init__(self)

	def run(self):
		self.result = [0]
		try:
			if timeit.default_timer() - self.starttime <= 10:
				request = build_request(self.url)
				f = urlopen(request)
				while 1 and not shutdown_event.isSet():
					self.result.append(len(f.read(10240)))
					if self.result[-1] == 0:
						break
				f.close()
		except IOError:
			pass

class FilePutter(threading.Thread):

	def __init__(
		self,
		url,
		start,
		size,
		):
		self.url = url
		chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
		data = chars * int(round(int(size) / 36.0))
		self.data = ('content1=%s' % data[0:int(size) - 9]).encode()
		del data
		self.result = None
		self.starttime = start
		threading.Thread.__init__(self)

	def run(self):
		try:
			if timeit.default_timer() - self.starttime <= 10 \
				and not shutdown_event.isSet():
				request = build_request(self.url, data=self.data)
				f = urlopen(request)
				f.read(11)
				f.close()
				self.result = len(self.data)
			else:
				self.result = 0
		except IOError:
			self.result = 0

def getAttributesByTagName(dom, tagName):
	elem = dom.getElementsByTagName(tagName)[0]
	return dict(list(elem.attributes.items()))

def getConfig():
	request = \
		build_request('http://www.speedtest.net/speedtest-config.php')
	uh = catch_request(request)
	if uh is False:
		xbmc.log('Could not retrieve speedtest.net configuration: %s' % e,xbmc.LOGDEBUG)
		sys.exit(1)
	configxml = []
	while 1:
		configxml.append(uh.read(10240))
		if len(configxml[-1]) == 0:
			break
	if int(uh.code) != 200:
		return None
	uh.close()
	try:
		try:
			root = ET.fromstring(''.encode().join(configxml))
			config = {
				'client': root.find('client').attrib,
				'times': root.find('times').attrib,
				'download': root.find('download').attrib,
				'upload': root.find('upload').attrib,
				}
		except Exception:

						   # Python3 branch

			root = DOM.parseString(''.join(configxml))
			config = {
				'client': getAttributesByTagName(root, 'client'),
				'times': getAttributesByTagName(root, 'times'),
				'download': getAttributesByTagName(root, 'download'),
				'upload': getAttributesByTagName(root, 'upload'),
				}
	except SyntaxError:
		xbmc.log('Failed to parse speedtest.net configuration',xbmc.LOGDEBUG)
		sys.exit(1)
	del root
	del configxml
	return config


def closestServers(client, all=False):

	urls = [
		'https://www.speedtest.net/speedtest-servers-static.php',
		'http://c.speedtest.net/speedtest-servers-static.php',
	]
	errors = []
	servers = {}
	for url in urls:
		try:
			request = build_request(url)
			uh = catch_request(request)
			if uh is False:
				errors.append('%s' % e)
				raise SpeedtestCliServerListError
			serversxml = []
			while not xbmc.Monitor().abortRequested():
				serversxml.append(uh.read(10240))
				if len(serversxml[-1]) == 0:
					break
			if int(uh.code) != 200:
				uh.close()
				raise SpeedtestCliServerListError
			uh.close()
			try:
				try:
					root = ET.fromstring(''.encode().join(serversxml))
					elements = root.getiterator('server')
				except Exception:

								# Python3 branch

					root = DOM.parseString(''.join(serversxml))
					elements = root.getElementsByTagName('server')
			except SyntaxError:
				raise SpeedtestCliServerListError
			for server in elements:
				try:
					attrib = server.attrib
				except AttributeError:
					attrib = dict(list(server.attributes.items()))
				d = distance([float(client['lat']), float(client['lon'
							])], [float(attrib.get('lat')),
							float(attrib.get('lon'))])
				attrib['d'] = d
				if d not in servers:
					servers[d] = [attrib]
				else:
					servers[d].append(attrib)
			del root
			del serversxml
			del elements
		except SpeedtestCliServerListError:
			continue
		if servers:
			break
	if not servers:
		xbmc.log('Failed to retrieve list of speedtest.net servers:%s'% '\n'.join(errors),xbmc.LOGDEBUG)
		sys.exit(1)
	closest = []
	for d in sorted(servers.keys()):
		for s in servers[d]:
			closest.append(s)
			if len(closest) == 5 and not all:
				break
		else:
			continue
		break
	del servers
	return closest


def getBestServer(servers):
	results = {}
	for server in servers:
		cum = []
		url = '%s/latency.txt' % os.path.dirname(server['url'])
		urlparts = urlparse(url)
		for i in range(0, 3):
			try:
				if urlparts[0] == 'https':
					h = HTTPSConnection(urlparts[1])
				else:
					h = HTTPConnection(urlparts[1])
				headers = {'User-Agent': user_agent}
				start = timeit.default_timer()
				h.request('GET', urlparts[2], headers=headers)
				r = h.getresponse()
				total = timeit.default_timer() - start
			except (HTTPError, URLError, socket.error):
				cum.append(3600)
				continue
			text = r.read(9)
			if int(r.status) == 200 and text == 'test=test'.encode():
				cum.append(total)
			else:
				cum.append(3600)
			h.close()
		avg = round(sum(cum) / 6 * 1000, 3)
		results[avg] = server
	fastest = sorted(results.keys())[0]
	best = results[fastest]
	best['latency'] = fastest
	return best


class animation(xbmcgui.WindowXMLDialog):
	def __init__(self,*args, **kwargs):
		super(xbmcgui.WindowXMLDialog, self).__init__()
		self.doModal()

class DG_Speed_Test(animation):
	def __init__(self,*args, **kwargs):
		if sys.version_info.major==2:
			xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
			self.doModal()
		if sys.version_info.major==3:
			super().__init__(*args, **kwargs)

	def onInit(self):
		self.testRun = False

		self.screenx = 1920
		self.screeny = 1080

		self.image_dir = ART
		self.image_background = self.image_dir + '/bg_screen.jpg'
		self.image_shadow = self.image_dir + '/shadowframe.png'
		self.image_progress = self.image_dir + '/ajax-loader-bar.gif'
		self.image_ping = self.image_dir + '/ping_progress_bg.png'
		self.image_ping_glow = self.image_dir + '/ping_progress_glow.png'
		self.image_gauge = self.image_dir + '/gauge_bg.png'
		self.image_gauge_arrow = self.image_dir + '/gauge_ic_arrow.png'
		self.image_button_run = self.image_dir + '/btn_start_bg.png'
		self.image_button_run_glow = self.image_dir + '/btn_start_glow_active.png'
		self.image_speedtestresults = self.image_dir + '/speedtest_results_wtext.png'
		self.image_centertext_testingping = self.image_dir + '/testing_ping.png'
		self.image_result = self.image_speedtestresults
		self.textbox = xbmcgui.ControlTextBox(50, 50, 880, 500, textColor='0xFFFFFFFF')
		self.addControl(self.textbox)
		self.displayButtonRun()
		self.displayButtonClose()
		self.setFocus(self.button_run)

	def onAction(self, action):
		if action == 10 or action == 92:
			self.saveClose()

	def displayButtonRun(self, function="true"):
		if (function == "true"):
			button_run_glowx = int((self.screenx / 3) - (300 / 2))
			button_run_glowy = int((self.screeny / 3) - (122 / 2) + 50)

			self.button_run_glow = xbmcgui.ControlImage(button_run_glowx, button_run_glowy, 300, 122, '', aspectRatio=0)
			self.addControl(self.button_run_glow)
			self.button_run_glow.setVisible(False)
			self.button_run_glow.setImage(self.image_button_run_glow)
			self.button_run_glow.setAnimations([
				('conditional', 'effect=fade start=0 time=1000 condition=true pulse=true')
			])

			self.button_run = xbmcgui.ControlButton(button_run_glowx, button_run_glowy, 300, 122, "[B]Run Speedtest[/B]",focusTexture=self.image_button_run,noFocusTexture=self.image_button_run, alignment=2 | 4,textColor='0xFF000000', focusedColor='0xFF000000',shadowColor='0xFFCCCCCC', disabledColor='0xFF000000')

			self.addControl(self.button_run)
			self.setFocus(self.button_run)
			self.button_run.setVisible(False)
			self.button_run.setAnimations([
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.button_run.getId())
			])
			self.button_run_ID = self.button_run.getId()
			self.button_run.setEnabled(True)
			self.button_run.setVisible(True)
			self.button_run_glow.setEnabled(True)
			self.button_run_glow.setVisible(True)
		else:
			self.button_run.setEnabled(False)
			self.button_run.setVisible(False)
			self.button_run_glow.setEnabled(False)
			self.button_run_glow.setVisible(False)


	def displayButtonClose(self, function="true"):
		if (function == "true"):
			self.button_close_glow = xbmcgui.ControlImage(880, 418, 300, 122, '', aspectRatio=0)
			self.addControl(self.button_close_glow)
			self.button_close_glow.setVisible(False)
			self.button_close_glow.setImage(self.image_button_run_glow)
			self.button_close_glow.setAnimations([
				('conditional',
				'effect=fade start=0 time=1000 delay=2000 pulse=true condition=Control.IsVisible(%d)' % self.button_close_glow.getId())
			])

			self.button_close = xbmcgui.ControlButton(99999, 99999, 300, 122, "[B]Close[/B]",focusTexture=self.image_button_run,noFocusTexture=self.image_button_run, alignment=2 | 4,textColor='0xFF000000', focusedColor='0xFF000000',shadowColor='0xFFCCCCCC', disabledColor='0xFF000000')

			self.addControl(self.button_close)
			self.button_close.setVisible(False)
			self.button_close.setPosition(880, 418)
			self.button_close_ID = self.button_close.getId()
			self.button_close.setAnimations([
				('conditional',
				'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.button_close.getId())
			])
		elif (function == "visible"):
			self.button_close.setVisible(True)
			self.button_close_glow.setVisible(True)
			self.setFocus(self.button_close)
		else:
			self.button_close.setVisible(False)
			self.button_close_glow.setVisible(False)


	def displayPingTest(self, function="true"):
		if (function == "true"):
			imgCentertextx = int((self.screenx / 3) - (320 / 2))
			imgCentertexty = int((self.screeny / 3) - (130 / 2) + 50)
			self.imgCentertext = xbmcgui.ControlImage(imgCentertextx, imgCentertexty, 320, 130, ' ', aspectRatio=0)
			self.addControl(self.imgCentertext)

			imgPingx = int((self.screenx / 3) - (600 / 2))
			imgPingy = int((self.screeny / 3) - (400 / 2))
			self.imgPing = xbmcgui.ControlImage(imgPingx, imgPingy, 600, 400, '', aspectRatio=1)
			self.imgPing_glow = xbmcgui.ControlImage(imgPingx, imgPingy, 600, 400, '', aspectRatio=1)
			self.addControl(self.imgPing)
			self.addControl(self.imgPing_glow)
			self.imgPing.setVisible(False)
			self.imgPing_glow.setVisible(False)
			self.imgPing.setImage(self.image_ping)
			self.imgPing_glow.setImage(self.image_ping_glow)
			self.imgPing.setAnimations([
				('conditional',
				'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.imgPing.getId()),
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.imgPing.getId())
			])
			self.imgPing_glow.setAnimations([
				('conditional',
				'effect=fade start=0 time=1000 pulse=true condition=Control.IsEnabled(%d)' % self.imgPing_glow.getId()),
				('conditional',
				'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.imgPing_glow.getId()),
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.imgPing_glow.getId())
			])
			self.imgCentertext.setAnimations([
				('conditional', 'effect=fade start=70 time=1000 condition=true pulse=true')
			])
		elif (function == "visible"):
			self.imgPing.setVisible(True)
			self.imgPing_glow.setVisible(True)
		else:
			self.imgPing.setVisible(False)
			self.imgPing_glow.setVisible(False)

			self.imgCentertext.setVisible(False)

	def displayGaugeTest(self, function="true"):
		if (function == "true"):

			imgGaugex = int((self.screenx / 3) - (548 / 2))
			imgGaugey = int((self.screeny / 3) - (400 / 2))

			imgGauge_arrowx = int((self.screenx / 3) - (66 / 2) - 5)
			imgGauge_arrowy = int((self.screeny / 3) - (260 / 2) - 60)
			self.imgGauge = xbmcgui.ControlImage(imgGaugex, imgGaugey, 548, 400, '', aspectRatio=0)
			self.imgGauge_arrow = xbmcgui.ControlImage(imgGauge_arrowx, imgGauge_arrowy, 66, 260, '', aspectRatio=0)
			self.addControl(self.imgGauge)
			self.addControl(self.imgGauge_arrow)
			self.imgGauge.setVisible(False)
			self.imgGauge_arrow.setVisible(False)
			self.imgGauge.setImage(self.image_gauge)
			self.imgGauge_arrow.setImage(self.image_gauge_arrow)
			self.imgGauge.setAnimations([
				('conditional',
				'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.imgGauge.getId()),
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.imgGauge.getId())
			])
			self.imgGauge_arrow.setAnimations([
				('conditional',
				'effect=fade start=0 end=100 time=1000 condition=Control.IsVisible(%d)' % self.imgGauge_arrow.getId()),
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.imgGauge_arrow.getId())
			])

			dlul_prog_textboxx = int((self.screenx / 3) - (200 / 2))
			dlul_prog_textboxy = int((self.screeny / 3) - (50 / 2) + 170)
			self.dlul_prog_textbox = xbmcgui.ControlLabel(dlul_prog_textboxx, dlul_prog_textboxy, 200, 50, label='',
														textColor='0xFFFFFFFF', font='font30', alignment=2 | 4)
			self.addControl(self.dlul_prog_textbox)
		elif (function == "visible"):
			self.imgGauge.setEnabled(True)
			self.imgGauge.setVisible(True)
			self.imgGauge_arrow.setEnabled(True)
			self.imgGauge_arrow.setVisible(True)
		else:
			self.imgGauge.setEnabled(False)
			self.imgGauge.setVisible(False)
			self.imgGauge_arrow.setEnabled(False)
			self.imgGauge_arrow.setVisible(False)
			self.dlul_prog_textbox.setLabel('')

	def displayProgressBar(self, function="true"):
		if (function == "true"):
			self.imgProgress = xbmcgui.ControlImage(340, 640, 600, 20, '', aspectRatio=0, colorDiffuse="0xFF00AACC")
			self.addControl(self.imgProgress)
			self.imgProgress.setVisible(False)
			self.imgProgress.setImage(self.image_progress)
			self.imgProgress.setAnimations([
				('conditional',
				'effect=fade start=0 end=100 time=500 condition=Control.IsVisible(%d)' % self.imgProgress.getId()),
				('conditional',
				'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.imgProgress.getId())
			])
			self.imgProgress.setVisible(True)
			imgProgressx = int((self.screenx / 3) - (200 / 2))
			imgProgressy = int((self.screeny / 3) - (50 / 2) + 270)
			self.please_wait_textbox = xbmcgui.ControlLabel(imgProgressx, imgProgressy, 200, 50,
															label='Please wait...', textColor='0xFFFFFFFF',
															alignment=2 | 4)
			self.addControl(self.please_wait_textbox)
		elif (function == "visible"):
			self.please_wait_textbox.setVisible(True)
			self.imgProgress.setEnabled(True)
			self.imgProgress.setVisible(True)
		else:
			self.please_wait_textbox.setVisible(False)
			self.imgProgress.setEnabled(False)
			self.imgProgress.setVisible(False)

	def displayResults(self, function="true"):
		if (function == "true"):
			self.imgResults = xbmcgui.ControlImage(932, 40, 320, 144, '', aspectRatio=0)
			self.addControl(self.imgResults)
			self.imgResults.setVisible(False)
			self.imgResults.setImage(self.image_speedtestresults)
			self.imgResults.setAnimations([
				('conditional',
				'effect=fade start=100 end=0 time=300 delay=1000 condition=!Control.IsEnabled(%d)' % self.imgResults.getId())
			])
			self.imgResults.setVisible(True)

			self.ping_textbox = xbmcgui.ControlLabel(955, 133, 75, 50, label='', textColor='0xFFFFFFFF')
			self.addControl(self.ping_textbox)

			self.dl_textbox = xbmcgui.ControlLabel(1035, 133, 75, 50, label='', textColor='0xFFFFFFFF')
			self.addControl(self.dl_textbox)

			self.ul_textbox = xbmcgui.ControlLabel(1153, 133, 75, 50, label='',textColor='0xFFFFFFFF')
			self.addControl(self.ul_textbox)
			
		elif (function == "visible"):
			self.imgResults.setEnabled(True)
			self.imgResults.setVisible(True)
		else:
			self.imgResults.setEnabled(False)
			self.dl_textbox.setLabel('')
			self.ul_textbox.setLabel('')
			self.ping_textbox.setLabel('')

	def showEndResult(self):
		self.imgFinalResults = xbmcgui.ControlImage(932, 40, 320, 144, '', aspectRatio=0)
		self.addControl(self.imgFinalResults)
		self.imgFinalResults.setVisible(False)
		self.imgFinalResults.setEnabled(False)

		self.imgFinalResults.setImage(image_result)
		self.imgFinalResults.setAnimations([
			('conditional',
			'effect=fade start=0 end=100 time=1000 delay=100 condition=Control.IsVisible(%d)' % self.imgFinalResults.getId()),
			('conditional',
			'effect=zoom end=175 start=100 center=%s time=2000 delay=3000 condition=Control.IsVisible(%d)' % (
			"auto", self.imgFinalResults.getId())),
			('conditional',
			'effect=slide end=-100,25 time=2000 delay=3000 tween=linear easing=in condition=Control.IsVisible(%d)' % self.imgFinalResults.getId())
		])
		self.imgFinalResults.setVisible(True)
		self.imgFinalResults.setEnabled(True)

	def showEndResultSP(self):
		self.rec_speed = xbmcgui.ControlTextBox(325,475,600,300, textColor='0xFFFFFFFF')
		self.addControl(self.rec_speed)
		self.rec_speed.setVisible(False)
		self.rec_speed.setEnabled(False)
		self.rec_speed.setText("".join("[B]Recomenended Speeds for Streaming! \n3 to 5 Mb/s for viewing standard definition 480p video \n5 to 10 Mb/s for viewing high-def 720p video \n10+ Mb/s or more for the best  1080p experience \n10+ Mb/s for the best Live TV Streaming experience \n25 to 50+ Mb/s 4K streaming \nAll Speeds are based on the device not what speed you pay for![/B]"))
		self.rec_speed.setAnimations([
			('conditional',
			'effect=fade start=0 end=100 time=1000 delay=100 condition=Control.IsVisible(%d)' % self.rec_speed.getId()),
		])
		self.rec_speed.setVisible(True)
		self.rec_speed.setEnabled(True)

	def onAction(self, action):
		if action == 10 or action == 92:
			self.saveClose()

	def onClick(self, control):
		if control == self.button_run_ID:
			self.testRun = True
			self.displayButtonRun(False)
			self.displayResults()
			self.displayProgressBar()
			self.displayPingTest()
			self.displayGaugeTest()
			self.speedtest(share=True, simple=True)
			self.displayProgressBar(False)
			self.displayPingTest(False)
			self.displayGaugeTest(False)
			self.displayResults(False)
			self.showEndResult()
			self.showEndResultSP()
			self.displayButtonClose("visible")
		if control == self.button_close_ID:
			self.saveClose()

	def saveClose(self):
		self.close()

	def update_textbox(self, text):
		self.textbox.setText("\n".join(text))

	def error(self, message):
		self.imgProgress.setImage(' ')
		self.button_close.setVisible(True)
		self.setFocus(self.button_close)

	def configGauge(self, speed, last_speed=0, time=1000):
		if last_speed == 0:
			last_speed = 122
		CurrentS = 0
		if speed <= 1:
			CurrentS = 122 - float((float(speed) - float(0))) * float(
				(float(31) / float(1)))
		elif speed <= 2:
			CurrentS = 90 - float((float(speed) - float(1))) * float(
				(float(31) / float(1)))
		elif speed <= 3:
			CurrentS = 58 - float((float(speed) - float(2))) * float(
				(float(29) / float(1)))
		elif speed <= 5:
			CurrentS = 28 - float((float(speed) - float(3))) * float(
				(float(28) / float(2)))
		elif speed <= 10:
			CurrentS =		float((float(speed) - float(5))) * float(
				(float(28) / float(5)))
		elif speed <= 20:
			CurrentS = 29 + float((float(speed) - float(10))) * float(
				(float(29) / float(10)))
		elif speed <= 30:
			CurrentS = 59 + float((float(speed) - float(20))) * float(
				(float(31) / float(10)))
		elif speed <= 50:
			CurrentS = 91 + float((float(speed) - float(30))) * float(
				(float(31) / float(20)))
		elif speed > 50:
			CurrentS = 122
		SpeedN = "%.0f" % float(CurrentS)
		if speed > 5:
			SpeedN = '-' + str(SpeedN)

		imgGauge_arrowx = (self.screenx / 3) - (66 / 2) + 28
		imgGauge_arrowy = (self.screeny / 3) + (260 / 2) - 88
		self.imgGauge_arrow.setAnimations([
			('conditional', 'effect=rotate start=%d end=%d center=%d,%d condition=Control.IsVisible(%d) time=%d' % (
			int(last_speed), int(SpeedN), imgGauge_arrowx, imgGauge_arrowy, self.imgGauge.getId(), time))
		])
		return SpeedN

	def downloadSpeed(self, files, quiet=False):
		start = timeit.default_timer()
		def producer(q, files):
			for file in files:
				thread = FileGetter(file, start)
				thread.start()
				q.put(thread, True)

				if not quiet and not shutdown_event.isSet():
					sys.stdout.write('.')
					sys.stdout.flush()
		finished = []
		def consumer(q, total_files):
			speed_dl = 0
			while len(finished) < total_files:
				thread = q.get(True)
				while thread.isAlive():
					thread.join(timeout=0.1)
				finished.append(sum(thread.result))
				speedF = ((sum(finished) / (timeit.default_timer() - start)) / 1000 / 1000) * 8
				speed_dl = self.configGauge(speedF, speed_dl)
				self.dlul_prog_textbox.setLabel('%.02f Mbps ' % speedF)
				del thread

		q = Queue(6)
		prod_thread = threading.Thread(target=producer, args=(q, files))
		cons_thread = threading.Thread(target=consumer, args=(q,
									len(files)))
		start = timeit.default_timer()
		prod_thread.start()
		cons_thread.start()
		while prod_thread.isAlive():
			prod_thread.join(timeout=0.1)
		while cons_thread.isAlive():
			cons_thread.join(timeout=0.1)
		return sum(finished) / (timeit.default_timer() - start)

	def uploadSpeed(self, url, sizes, quiet=False):
		start = timeit.default_timer()

		def producer(q, sizes):
			for iI in sizes:
				thread = FilePutter(url, start, iI)
				thread.start()
				q.put(thread, True)
				if not quiet and not shutdown_event.isSet():
					sys.stdout.write('.')
					sys.stdout.flush()
		finished = []
		def consumer(q, total_sizes):
			speed_dl = 0
			while len(finished) < total_sizes:
				thread = q.get(True)
				while thread.isAlive():
					thread.join(timeout=0.1)
				finished.append(thread.result)
				speedF = ((sum(finished) / (timeit.default_timer() - start)) / 1000 / 1000) * 8
				speed_dl = self.configGauge(speedF, speed_dl)
				self.dlul_prog_textbox.setLabel('%.02f Mbps ' % speedF)
				del thread

		q = Queue(6)
		prod_thread = threading.Thread(target=producer, args=(q, sizes))
		cons_thread = threading.Thread(target=consumer, args=(q,
										len(sizes)))
		start = timeit.default_timer()
		prod_thread.start()
		cons_thread.start()
		while prod_thread.isAlive():
			prod_thread.join(timeout=0.1)
		while cons_thread.isAlive():
			cons_thread.join(timeout=0.1)
		return sum(finished) / (timeit.default_timer() - start)

	def speedtest(self, list=False, mini=None, server=None, share=False, simple=False, src=None, timeout=10,
	units=('bit', 8), version=False):
		self.imgPing.setVisible(True)
		self.imgPing_glow.setVisible(True)
		startST = ['Executed Speed Test Script']

		global shutdown_event, source
		shutdown_event = threading.Event()

		socket.setdefaulttimeout(timeout)

		if src:
			source = src
			socket.socket = bound_socket

		startST.append('Retrieving speedtest.net configuration')
		self.update_textbox(startST)
		try:
			config = getConfig()
		except URLError:
			return False

		startST.append('Retrieving speedtest.net server list')
		self.update_textbox(startST)
		self.imgCentertext.setImage(self.image_centertext_testingping)

		servers = closestServers(config['client'])

		startST.append('Testing from %(isp)s (%(ip)s)' % config['client'])
		self.update_textbox(startST)

		best = getBestServer(servers)

		try:
			startST.append('Selecting best server based on latency')
			self.update_textbox(startST)
		except:pass
		try:
			startST.append('Hosted by: %(sponsor)s' % best)
			self.update_textbox(startST)
		except:pass
		try:
			startST.append('Host Server: %(host)s' % best)
			self.update_textbox(startST)
		except:pass
		try:
			startST.append('Country: %(country)s' % best)
			self.update_textbox(startST)
		except:pass
		try:
			startST.append('City , State: %(name)s' % best)
			self.update_textbox(startST)
		except:pass
		try:
			km2mi = 0.62
			km = '%(d)0.2f ' % best
			Distance = float(km)
			miles = Distance * km2mi
			startST.append('Distance: %s mi' % miles)
			self.update_textbox(startST)
		except:pass
		try:
			startST.append('Ping: %(latency)s ms' % best)
			self.update_textbox(startST)
			self.ping_textbox.setLabel("%.0f" % float(best['latency']))
		except:pass
		self.imgCentertext.setImage(' ')
		self.imgPing.setEnabled(False)
		self.imgPing_glow.setEnabled(False)

		sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
		urls = []
		for size in sizes:
			for i in range(0, 4):
				urls.append('%s/random%sx%s.jpg' %
									(os.path.dirname(best['url']), size, size))
		self.imgGauge.setVisible(True)
		xbmc.Monitor().waitForAbort(1)
		self.configGauge(0)
		self.imgGauge_arrow.setVisible(True)

		startST.append('Testing download speed')
		self.update_textbox(startST)
		dlspeed = self.downloadSpeed(urls, simple)
		startST.append('Download: %0.2f M%s/s' % ((dlspeed / 1000 / 1000) * units[1], units[0]))
		self.update_textbox(startST)
		self.dl_textbox.setLabel("%.2f" % float((dlspeed / 1000 / 1000) * units[1]))

		sizesizes = [int(.25 * 1000 * 1000), int(.5 * 1000 * 1000)]
		sizes = []
		for size in sizesizes:
			for i in range(0, 25):
				sizes.append(size)

		startST.append('Testing upload speed')
		self.update_textbox(startST)
		ulspeed = self.uploadSpeed(best['url'], sizes, simple)
		startST.append('Upload: %0.2f M%s/s' % ((ulspeed / 1000 / 1000) * units[1], units[0]))
		self.update_textbox(startST)
		self.ul_textbox.setLabel("%.2f" % float((ulspeed / 1000 / 1000) * units[1]))
		self.configGauge(0, (ulspeed / 1000 / 1000) * 8, time=3000)
		xbmc.Monitor().waitForAbort(2)

		if share:
			dlspeedk = int(round((dlspeed / 1000) * 8, 0))
			ping = int(round(best['latency'], 0))
			ulspeedk = int(round((ulspeed / 1000) * 8, 0))

			apiData = [
				'download=%s' % dlspeedk,
				'ping=%s' % ping,
				'upload=%s' % ulspeedk,
				'promo=',
				'startmode=%s' % 'pingselect',
				'recommendedserverid=%s' % best['id'],
				'accuracy=%s' % 1,
				'serverid=%s' % best['id'],
				'hash=%s' % md5(('%s-%s-%s-%s' %
								(ping, ulspeedk, dlspeedk, '297aae72'))
								.encode()).hexdigest()]

			headers = {'Referer': 'https://c.speedtest.net/flash/speedtest.swf'}
			request = build_request('https://www.speedtest.net/api/api.php',
										data='&'.join(apiData).encode(),
										headers=headers)
			f = catch_request(request)
			if f is False:
				xbmc.log('Could not submit results to speedtest.net',xbmc.LOGDEBUG)
				return False
			response = f.read()
			code = f.code
			f.close()

			if int(code) != 200:
				xbmc.log('Could not submit results to speedtest.net',xbmc.LOGDEBUG)
				return False

			qsargs = parse_qs(response.decode())
			resultid = qsargs.get('resultid')
			if not resultid or len(resultid) != 1:
				xbmc.log('Could not submit results to speedtest.net',xbmc.LOGDEBUG)
				return False
				
			global image_result
			image_result = 'https://www.speedtest.net/result/%s.png' % resultid[0]

if __name__ == '__main__':
	Dr0idGuy = DG_Speed_Test("script-speedtester_main.xml", ADDON.getAddonInfo('path'), "Default")
	del Dr0idGuy