import os
import io
import socket
import json
import requests
import xbmc
import xbmcgui

from PIL import Image
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry

from . import config
from . import utils
from . import weather

# DNS cache
old_getaddrinfo = socket.getaddrinfo

def new_getaddrinfo(*args):
	try:
		return config.dnscache[args]
	except KeyError:
		r = old_getaddrinfo(*args)
		config.dnscache[args] = r
		return r

socket.getaddrinfo = new_getaddrinfo

# Requests
r = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
s = requests.Session()
s.headers.update(config.addon_ua)
s.mount('https://', HTTPAdapter(max_retries=r))

# Network
def network():
	if config.neterr > 10:
		return False
	else:
		return True

# Get url
def geturl(url, head=False):

	# Network timeout
	if network():
		timeout = 6
	else:
		timeout = 1

	# Download
	try:
		if head:
			utils.log(f'Checking: {url}', 3)
			r = s.head(url, timeout=timeout)
		else:
			utils.log(f'Download: {url}', 3)
			r = s.get(url, timeout=timeout)

	except Exception as e:
		utils.log(f'Download: {url} ({e})', 3)
		config.dnscache = {}
		config.neterr  += 1
		return None

	else:
		config.neterr = 0

		if r.ok:
			utils.log(f'Download: {url} ({r.status_code})', 3)
			return r.content
		else:
			utils.log(f'Download: {url} ({r.status_code})', 2)
			config.dnscache = {}
			return None

# Get data
def getdata(type, loc, map=None):

	# URL
	if type == 'weather':
		url = config.map_api.get(type).format(map[0], map[1], config.maxdays)
	elif type == 'airquality':
		url = config.map_api.get(type).format(map[0], map[1])
	elif type == 'sun':
		url = config.map_api.get(type).format(map[0], map[1], map[2])
	elif type == 'moon':
		url = config.map_api.get(type).format(map[0], map[1], map[2])

	# Weather
	file = f'{config.addon_cache}/{loc}/{type}.json'
	data = geturl(url)

	if data:
		with open(Path(file), 'wb') as f:
			f.write(data)

# Get Map ( 0:loc, 1:type, 2:count, 3:z, 4:x, 5:y, 6:xtile 7:ytile, 8:path, 9:time, 10-13 bbox )
def getmap(map, head=False):

	if map[1] == 'osm':
		url = config.map_api.get(map[1]).format(map[3], map[4], map[5])
	elif map[1] == 'rvradar':
		url = config.map_api.get(map[1]).format(map[8], map[3], map[4], map[5])
	elif map[1] == 'rvsatellite':
		url = config.map_api.get(map[1]).format(map[8], map[3], map[4], map[5])
	elif map[1] == 'gctemp':
		url = config.map_api.get(map[1]).format(map[10], map[11], map[12], map[13])
	elif map[1] == 'gcwind':
		url = config.map_api.get(map[1]).format(map[10], map[11], map[12], map[13])

	# HEAD
	if head:
		data = geturl(url, head=True)
		return data

	# GET
	data = geturl(url)

	if data:
		config.mapcache[map[1]][map[2]] = data
	else:
		with open(Path(f'{config.addon_path}/resources/tile.png'), 'rb') as f:
			tile = f.read()

		config.mapcache[map[1]][map[2]] = tile

# Map merge
def mapmerge(map):
	image = Image.new("RGBA", (756, 756), None)

	for item in map:

		try:
			tile = Image.open(io.BytesIO(config.mapcache[item[1]][item[2]]))
		except:
			tile = Image.open(f'{config.addon_path}/resources/tile.png')
		else:
			image.paste( tile, (item[6], item[7]))

	if map[0][1] == 'osm':
		image.save(f'{config.addon_cache}/{map[0][0]}/{map[0][1]}.png')
	else:
		image.save(f'{config.addon_cache}/{map[0][0]}/{map[0][1]}_{map[0][9]}.png')

# Get rvdata
def getrvindex(type):
	try:
		data = json.loads(geturl(config.map_api.get('rvindex')))
		map  = config.map_layers.get(type)
		time = data[map[0]][map[1]][-1]['time']
		path = data[map[0]][map[1]][-1]['path']
	except:
		return None, None
	else:
		return time, path

# Get location (GeoIP)
def getloc(locid):
	utils.log(f'Geolocation ...')

	# Get location
	try:
		data    = json.loads(geturl(config.map_api.get('geoip')))
		city    = data['city']
		region  = data.get('region_name')
		country = data.get('country_code')

		# Search
		data     = json.loads(geturl(config.map_api.get('search').format(city)))
		location = data['results'][0]

		for item in data['results']:

			if country and region:
				if country in location['country_code'] and region in location['admin1']:
					location = item
					break

			if country:
				if country in location['country_code']:
					location = item
					break
	except Exception as e:
		utils.log(f'Geolocation: Unknown ({e})')
	else:
		utils.log(f'Geolocation: {location["name"]}, {location["admin1"]}, {location["country_code"]} [{location["latitude"]}, {location["longitude"]}]')
		utils.setsetting(f'loc{locid}', f'{location["name"]}, {location["admin1"]}, {location["country_code"]}')
		utils.setsetting(f'loc{locid}lat', str(location["latitude"]))
		utils.setsetting(f'loc{locid}lon', str(location["longitude"]))
		utils.setsetting(f'loc{locid}tz', str(location["timezone"]))

# Clear location
def clearloc(locid, last=False):
	if last:
		utils.setsetting(f'loc{locid}data', '321318000')
		utils.setsetting(f'loc{locid}map', '321318000')
		utils.setsetting(f'loc{locid}rv', '321318000')
		utils.setsetting(f'loc{locid}gc', '321318000')
	else:
		utils.setsetting(f'loc{locid}', '')
		utils.setsetting(f'loc{locid}user', '')
		utils.setsetting(f'loc{locid}alert', 'true')
		utils.setsetting(f'loc{locid}utz', 'false')
		utils.setsetting(f'loc{locid}tz', '')
		utils.setsetting(f'loc{locid}lat', '0')
		utils.setsetting(f'loc{locid}lon', '0')

# Set location
def setloc (locid):
	utils.log(f'Search dialog ...')

	dialog   = xbmcgui.Dialog()
	input    = utils.setting(f'loc{locid}')
	keyboard = xbmc.Keyboard(input, utils.loc(14024), False)
	keyboard.doModal()

	if keyboard.isConfirmed():
		search = keyboard.getText()

		# No changes
		if search == input:
			utils.log(f'[LOC{locid}] No changes')

		# Remove location
		elif search == '':
			check = utils.setting(f'loc{int(locid)+1}')

			if not check:
				utils.log(f'[LOC{locid}] Removed')
				clearloc(locid)
				clearloc(locid, True)

		# Search location
		else:
			try:
				locs   = []
				url    = config.map_api.get('search').format(search)
				data   = json.loads(geturl(url))['results']
			except:
				utils.log('[LOC{locid}] No results')
				dialog.ok('Open-meteo', utils.loc(284))
			else:
				for item in data:
					li = xbmcgui.ListItem(f'{item.get("name")}, {item.get("admin1")}, {item.get("country_code")} (Lat: {item.get("latitude")}, Lon: {item.get("longitude")})')
					locs.append(li)

				select = dialog.select(utils.loc(396), locs, useDetails=True)

				if select != -1:

					# Cleanup cache dir
					dir   = f'{config.addon_cache}/{locid}'
					files = sorted(list(Path(dir).glob('*')))

					for file in files:
						os.remove(file)

					# Set location
					utils.log(f'Location {locid}: {data[select].get("name")}, {data[select].get("admin1")}, {data[select].get("country_code")} {data[select].get("latitude")} {data[select].get("longitude")}')
					utils.setsetting(f'loc{locid}', f'{data[select].get("name")}, {data[select].get("admin1")}, {data[select].get("country_code")}')
					utils.setsetting(f'loc{locid}lat', data[select]["latitude"])
					utils.setsetting(f'loc{locid}lon', data[select]["longitude"])
					utils.setsetting(f'loc{locid}tz', data[select]["timezone"])

					# Wait for settings dialog
					while xbmcgui.getCurrentWindowDialogId() == 10140:
						utils.log(f'Waiting for settings dialog ...')
						utils.monitor.waitForAbort(1)

						if utils.monitor.abortRequested():
							return

					# Cleanup lastupdate
					clearloc(locid, True)

					# Refresh
					if int(utils.settingrpc("weather.currentlocation")) == int(locid):
						weather.Main(str(locid), mode='download')
						weather.Main(str(locid), mode='update')
					else:
						weather.Main(str(locid), mode='download')
						weather.Main(str(locid), mode='updatelocs')

