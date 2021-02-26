import os
import sys
import urllib
import urllib.parse

import xbmcgui
import xbmcplugin
import xbmcaddon
from xbmc import log as xbmc_log

import requests
import yaml
import calendar
import time
from urllib.parse import parse_qsl
from datetime import datetime
import iso8601

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__icon__ = __addon__.getAddonInfo('icon')
__addonid__ = __addon__.getAddonInfo('id')

mode = args.get('mode', None)

imgIconResourcePath = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'resources','img','icon')
imgFanartResourcePath = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'resources','img','fanart')
fileHakaFavourites = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'hakaFavourites.yaml')
dummyWav = os.path.join(xbmcaddon.Addon().getAddonInfo('path'),'resources','1.wav')

haDomainNames = 		['automation','climate','group','light','scene','script','sensor','switch','vacuum','person']
haDomainSettings = 		[ False, False, False, False, False, False, False, False, False, False, False]
haDomainTranslations = 	[30005,30006,30007,30008,30009,30010,30011,30012,30013,30014,30019]

haServer = __addon__.getSetting('haServer')
haToken = __addon__.getSetting('haToken')

api_base = haServer + '/api'
headers = {'Authorization': 'Bearer ' + haToken, 'Content-Type': 'application/json'}

def build_url(query):
	return base_url + '?' + urllib.parse.urlencode(query)

def utc_to_local(utc_dt):
	# get integer timestamp to avoid precision lost
	timestamp = calendar.timegm(utc_dt.timetuple())
	local_dt = datetime.fromtimestamp(timestamp)
	assert utc_dt.resolution >= timedelta(microseconds=1)
	return local_dt.replace(microsecond=utc_dt.microsecond)

def parse_date(event_date):
	datetime_obj = iso8601.parse_date(event_date)
	datetime_obj = utc_to_local(datetime_obj)
	dateString = datetime_obj.strftime(xbmc.getRegion('dateshort'))
	return dateString

def parse_time(event_date):
	datetime_obj = iso8601.parse_date(event_date)
	datetime_obj = utc_to_local(datetime_obj)
	timeString = datetime_obj.strftime(xbmc.getRegion('time'))
	return timeString
	
def parse_dateTime(event_date):
	return parse_date(event_date) + ' ' + parse_time(event_date)

def have_credentials():
	return haServer and haToken

def show_dialog(message):
	xbmcgui.Dialog().ok(__addonname__, message)
	
def log(txt, loglevel=xbmc.LOGWARNING):
	if __addon__.getSetting( "logEnabled" ) == "true":
		message = u'%s: %s' % (__addonid__, txt)
		xbmc.log(msg=message, level=loglevel)

def read_favourites():
	favourites = []
	if os.stat(fileHakaFavourites).st_size > 0:
		try:
			file = open(fileHakaFavourites, 'r')
			favourites = yaml.load(file, Loader=yaml.BaseLoader)
			file.close() 
		except:
			log("Something went wrong opening or parsing hakaFavourites.yaml")
			show_dialog(__addon__.getLocalizedString(30056))
			favourites = []
	else:
		log("hakaFavourites.yaml seems to be 0 bytes")
		favourites = []
	return favourites
	
def write_favourite(entity_list, open_param):
	file = open(fileHakaFavourites, open_param)
	file.write(yaml.dump(entity_list))
	file.close()

def importDomainSettings():
	if __addon__.getSetting('importAutomation') == 'true':
		haDomainSettings[0] = True
	if __addon__.getSetting('importClimate') == 'true':
		haDomainSettings[1] = True
	if __addon__.getSetting('importGroups') == 'true':
		haDomainSettings[2] = True
	if __addon__.getSetting('importLights') == 'true':
		haDomainSettings[3] = True
	if __addon__.getSetting('importScenes') == 'true':
		haDomainSettings[4] = True
	if __addon__.getSetting('importScripts') == 'true':
		haDomainSettings[5] = True
	if __addon__.getSetting('importSensors') == 'true':
		haDomainSettings[6] = True
	if __addon__.getSetting('importSwitches') == 'true':
		haDomainSettings[7] = True
	if __addon__.getSetting('importVacuums') == 'true':
		haDomainSettings[8] = True
	if __addon__.getSetting('importPersons') == 'true':
		haDomainSettings[9] = True
	log('Domain settings imported: ' + str(haDomainSettings))

def getRequest(api_ext):
	try:
		log('Trying to make a get request to ' + api_base + api_ext)
		r = requests.get(api_base + api_ext, headers=headers)
		log(r.json())
		return r.json()
	except:
		log('Status code error is: ' + str(r.raise_for_status()))
		show_dialog(__addon__.getLocalizedString(30052)) #Unknown error: Check IP address or if server is online	
		log('GetRequest status code is: ' + str(r.status_code))		
		if r.status_code == 401:
			show_dialog(__addon__.getLocalizedString(30050)) #Error 401: Check your token
		elif r.status_code == 405:
			show_dialog(__addon__.getLocalizedString(30051)) #Error 405: Method not allowed
		elif r.status_code == 200:
			return r


def postRequest(api_ext, entity_id):
	try:
		payload = "{\"entity_id\": \"" + entity_id + "\"}"
		log('Trying to make a post request to ' + api_base + api_ext + ' with payload: ' + payload)
		r = requests.post(api_base + api_ext, headers=headers, data=payload)
		log('GetRequest status code is: ' + str(r.status_code))
		if r.status_code == 401:
			show_dialog(__addon__.getLocalizedString(30050)) #Error 401: Check your token
		elif r.status_code == 405:
			show_dialog(__addon__.getLocalizedString(30051)) #Error 405: Method not allowed
	except:
		show_dialog(__addon__.getLocalizedString(30052)) #Unknown error: Check IP address or if server is online
		
def browseByDomain():
	log('Browse by domain started')
	listing=[]
	isFolder = True

	#Test connection / get version
	response = getRequest('/config')
	if response is not None:
		log('Response from server: ' + str(response))
	else:
		log('Response from server is NONE!')

	#Compose folder list based on addon settings
	for d in range(len(haDomainSettings)):
		if haDomainSettings[d]:
			url = build_url({'mode': 'loadfolder', 'type': 'domain', 'domain': haDomainNames[d]})
			icon = os.path.join(imgIconResourcePath) + '\\' + haDomainNames[d] + '.png'
			li = xbmcgui.ListItem(__addon__.getLocalizedString(haDomainTranslations[d]))
			li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
			listing.append((url, li, isFolder))

	#Add the favourites folder
	if __addon__.getSetting('useFavourites') == 'true':
		url = build_url({'mode': 'loadfolder', 'type': 'favourites', 'domain': 'none'})
		icon = os.path.join(imgIconResourcePath, 'favourites.png')
		li = xbmcgui.ListItem('Favourites')
		li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
		listing.append((url, li, isFolder))

	#Add the version number as folder
	url = build_url({'mode': 'config'})
	icon = os.path.join(imgIconResourcePath, 'config.png')
	li = xbmcgui.ListItem(__addon__.getLocalizedString(30023) + ': ' + response['version'])
	li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
	listing.append((url, li, isFolder))

	xbmcplugin.addDirectoryItems(addon_handle, listing, len(listing))
	xbmcplugin.endOfDirectory(addon_handle)
	
def loadFolder(folderType, domain):
	response = getRequest('/states')

	searchKey = ''

	if folderType == 'domain':
		searchKey = domain + '.'
		createFolderList(searchKey, response, domain, folderType)

	if folderType == 'favourites' or folderType == 'widgets':
		favourites = read_favourites()
		if len(favourites) > 0:
			for entity in favourites:
				searchKey = entity['entity_id']
				domain = entity['domain']
				createFolderList(searchKey, response, domain, folderType)
		else:
			show_dialog(__addon__.getLocalizedString(30057))
			browseByDomain()
	if domain != 'vacuum':
		xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LABEL)
	xbmcplugin.endOfDirectory(addon_handle)


def createFolderList(searchKey, response, domain, folderType):
	listing=[]
	isFolder = False

	vacuumService = ['start', 'stop', 'return_to_base', 'locate']
	vacuumServiceTranslations = [30040, 30041, 30042, 30043]

	if folderType == 'widgets':
		markup = '[LIGHT] '
	else:
		markup = '[CR][LIGHT]'
	for entity in range(len(response)):
		if searchKey in response[entity]['entity_id']:
			contextMenuItems = []
			entity_id = response[entity]['entity_id']
			entity_state =response[entity]['state']
			label = response[entity]['attributes']['friendly_name']
			icon = os.path.join(imgIconResourcePath) + '\\' + domain + '.png'

			if domain == 'automation':
				if 'last_triggered' in response[entity]['attributes']:
					if response[entity]['attributes']['last_triggered'] is not None:
						label = label + markup + __addon__.getLocalizedString(30022) + str(parse_dateTime(response[entity]['attributes']['last_triggered'])) + '[/LIGHT]'
						if entity_state == 'off':
							icon = os.path.join(imgIconResourcePath,'automation_off.png')

			elif domain == 'climate':
				label = label + markup + entity_state + ' - '  + __addon__.getLocalizedString(30020) + str(response[entity]['attributes']['current_temperature']) + '[/LIGHT]'
				
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'climate_off.png')

			elif domain == 'group':
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'group_off.png')

			elif domain == 'light':
				if entity_state == 'on':
					if 'brightness' in response[entity]['attributes']:
						brightness = int(round(float(response[entity]['attributes']['brightness']) / 2.56))
						label = label + markup + __addon__.getLocalizedString(30021) + str(brightness) + '%[/LIGHT]'
				else:
					icon = os.path.join(imgIconResourcePath,'light_off.png')
					
			elif domain == 'person':
				if 'entity_picture' in response[entity]['attributes']:
					icon = str(haServer + response[entity]['attributes']['entity_picture'])
					if entity_state == 'home':
						label = label + markup + 'Home' + '[/LIGHT]'
					else:
						label = label + markup + 'Not home' + '[/LIGHT]'
					

			elif domain == 'scene':
				icon = os.path.join(imgIconResourcePath,'scene.png')
		
			elif domain == 'script':
				if 'last_triggered' in response[entity]['attributes']:
					if response[entity]['attributes']['last_triggered'] is not None:
						label = label  + markup + __addon__.getLocalizedString(30022) + str(parse_dateTime(response[entity]['attributes']['last_triggered'])) + '[/LIGHT]'

			elif domain == 'sensor':
				label = label + markup + entity_state + " "
				if 'device_class' in response[entity]['attributes']:
					if 'battery' in response[entity]['attributes']['device_class']:
						icon = os.path.join(imgIconResourcePath,'battery.png')
					elif 'connectivity' in response[entity]['attributes']['device_class']:
						if entity_state == 'on':
							icon = os.path.join(imgIconResourcePath,'connectivity.png')
						else:
							icon = os.path.join(imgIconResourcePath,'connectivity_off.png')
					elif 'humidity' in response[entity]['attributes']['device_class']:
						icon = os.path.join(imgIconResourcePath,'humidity.png')
					elif 'motion' in response[entity]['attributes']['device_class']:
						if 'last_changed' in response[entity]:
							if response[entity]['last_changed'] is not None:
								log(str(parse_dateTime(response[entity]['last_changed'])))
								label = label + "Last changed: " + str(parse_dateTime(response[entity]['last_changed']))
						icon = os.path.join(imgIconResourcePath,'motion.png')
					elif 'opening' in response[entity]['attributes']['device_class']:
						if entity_state == 'on':
							icon = os.path.join(imgIconResourcePath,'opening.png')
						else:
							icon = os.path.join(imgIconResourcePath,'opening_off.png')
					elif 'power' in response[entity]['attributes']['device_class']:
						if entity_state == 'on':
							icon = os.path.join(imgIconResourcePath,'power.png')
						else:
							icon = os.path.join(imgIconResourcePath,'power_off.png')
					elif 'temperature' in response[entity]['attributes']['device_class']:
						icon = os.path.join(imgIconResourcePath,'thermometer.png')
					elif 'window' in response[entity]['attributes']['device_class']:
						if entity_state == 'on':
							icon = os.path.join(imgIconResourcePath,'window.png')
						else:
							icon = os.path.join(imgIconResourcePath,'window_off.png')
				else:
					icon = os.path.join(imgIconResourcePath,'sensor.png')

				if 'unit_of_measurement' in response[entity]['attributes']:
					label = label + response[entity]['attributes']['unit_of_measurement']
				label = label +  '[/LIGHT]'

			elif domain == 'switch':
				if entity_state == 'off':
					icon = os.path.join(imgIconResourcePath,'switch_off.png')

			elif domain == 'vacuum': # Each for Start / Stop / Return to base / Locate
				label = '[B]' + label + '[/B][CR][LIGHT]State: ' + response[entity]['attributes']['status'] + ' - Battery: ' + str(response[entity]['attributes']['battery_level']) + '[/LIGHT]' 
				url = build_url({'mode': 'service', 'domain': domain, 'entity_id': entity_id, 'state' : entity_state, 'service': 'toggle'})
				li = xbmcgui.ListItem(label)
				li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
				li.setProperty('IsPlayable', 'false')
				listing.append((url, li, isFolder))

				for s in range(len(vacuumService)):
					controlIcon = vacuumService[s] + '.png'
					icon = os.path.join(imgIconResourcePath,controlIcon)
					labelService = '[LIGHT]' + __addon__.getLocalizedString(vacuumServiceTranslations[s]) + '[/LIGHT]' 
					url = build_url({'mode': 'service', 'domain': domain, 'entity_id': entity_id, 'state' : entity_state, 'service': vacuumService[s],})
					li = xbmcgui.ListItem(labelService)
					li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
					listing.append((url, li, isFolder))

			else:
				icon = os.path.join(imgIconResourcePath,'unknown.png')

			if domain != 'vacuum':
				url = build_url({'mode': 'service', 'domain': domain, 'entity_id': entity_id, 'state' : entity_state})
				li = xbmcgui.ListItem(label)

				if folderType == 'domain':
					cmd = 'RunPlugin({})'.format(build_url({'mode': 'addFav', 'name': (response[entity]['attributes']['friendly_name']).encode('utf-8'), 'entity_id': entity_id, 'domain': domain,}))
					contextMenuItems.append([__addon__.getLocalizedString(30070), cmd ])
				elif folderType == 'favourites' or folderType == 'widgets':
					cmd = 'RunPlugin({})'.format(build_url({'mode': 'remFav', 'name': (response[entity]['attributes']['friendly_name']).encode('utf-8'), 'entity_id': entity_id, 'domain': domain}))
					contextMenuItems.append([__addon__.getLocalizedString(30071), cmd ])
				li.addContextMenuItems(contextMenuItems)
				li.setProperty('IsPlayable', 'false')
				li.setArt({'icon': icon, 'fanart' : os.path.join(imgFanartResourcePath,'fanart.jpg')})
				listing.append((url, li, isFolder))
	xbmcplugin.addDirectoryItems(addon_handle, listing, len(listing))



#MAIN
log('HAKA Started')
importDomainSettings()

if not os.path.exists(fileHakaFavourites):
    open(fileHakaFavourites, 'w').close()

if not have_credentials():
	log('Credentials could not be read or are empty.')
	show_dialog(__addon__.getLocalizedString(30053))

if mode is None:
	browseByDomain()

else:
	params = dict(parse_qsl(sys.argv[2][1:]))
	log(params)

	if mode[0] == 'loadfolder':
		loadFolder(params['type'], params['domain'])

	elif mode[0] == 'addFav':
		favourites = read_favourites()
		does_exist = False
		if len(favourites) == 0:
			does_exist = False
		else:
			for idx,entity in enumerate(favourites):
				if params['entity_id'] in entity['entity_id']:
					does_exist = True
					show_dialog(params['name'] + __addon__.getLocalizedString(30058)) 
				else:
					does_exist = False

		if does_exist == False:
			write_favourite([{'entity_id': params['entity_id'], 'friendly_name': params['name'], 'domain': params['domain']}], 'a')
			show_dialog(params['name'] + __addon__.getLocalizedString(30054))


	elif mode[0] == 'remFav':
		favourites = read_favourites()

		for idx,entity in enumerate(favourites):
			if params['entity_id'] in entity['entity_id']:
				del favourites[idx]
				show_dialog(params['name'] + __addon__.getLocalizedString(30055))
		if len(favourites) > 0:
			write_favourite(favourites, 'w')
			loadFolder('favourites', 'None')
		else:
			open(fileHakaFavourites, 'w').close()
			browseByDomain()
		xbmc.executebuiltin("Container.Refresh")

	elif mode[0] == 'config':
		xbmcaddon.Addon().openSettings()

	elif mode[0] == 'service':
		if params['domain'] == 'automation':
			api_ext = '/services/automation/toggle'
			postRequest(api_ext, params['entity_id'])
			
		elif params['domain'] == 'climate':
			if params['state'] == 'off':
				api_ext = '/services/climate/turn_on'
			else:
				api_ext = '/services/climate/turn_off'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'group':
			if params['state'] == 'off':
				api_ext = '/services/homeassistant/turn_on'
			else:
				api_ext = '/services/homeassistant/turn_off'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'light':
			api_ext = '/services/light/toggle'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'scene':
			api_ext = '/services/scene/turn_on'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'script':
			api_ext = '/services/script/turn_on'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'switch':
			api_ext = '/services/homeassistant/toggle'
			postRequest(api_ext, params['entity_id'])

		elif params['domain'] == 'vacuum':
			api_ext = '/services/vacuum/' + params['service']
			postRequest(api_ext, params['entity_id'])

		#Play a dummy wav file to prevent errors when starting a service as widget
		xbmcplugin.setResolvedUrl(addon_handle, True, xbmcgui.ListItem(path=dummyWav)) 
		loadFolder('domain', params['domain'])
		xbmc.executebuiltin("Container.Refresh")