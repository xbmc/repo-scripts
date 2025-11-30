import os
import sys
import xbmc
import xbmcgui
import xbmcaddon
import math
import json
import time
import xml.etree.ElementTree as ET

from datetime import datetime
from pytz import timezone
from pathlib import Path

from . import config
from . import conv
from . import weather
from . import monitor

# Monitor
monitor = monitor.Main()

# Logging
def log(msg, level=0):
	if level == 1:
		xbmc.log(msg=f'[weather.openmeteo]: [W] {msg}', level=xbmc.LOGINFO)
	elif level == 2:
		xbmc.log(msg=f'[weather.openmeteo]: [E] {msg}', level=xbmc.LOGINFO)
	elif level == 3:
		if config.addon.debug:
			xbmc.log(msg=f'[weather.openmeteo]: [D] {msg}', level=xbmc.LOGINFO)
	elif level == 4:
		if config.addon.verbose:
			xbmc.log(msg=f'[weather.openmeteo]: [V] {msg}', level=xbmc.LOGINFO)
	else:
		xbmc.log(msg=f'[weather.openmeteo]: [I] {msg}', level=xbmc.LOGINFO)

# Setting
def setting(arg, type='str', cache=False):

	# Cache
	if cache:
		try:
			value = config.addon.settings[arg]
		except:
			value = xbmcaddon.Addon().getSetting(arg)
	else:
		value = xbmcaddon.Addon().getSetting(arg)

	# Type
	if type == 'int':
		return int(value)

	elif type == 'float':
		return float(value)

	elif type == 'bool':

		if value == 'true':
			return True
		else:
			return False

	else:
		return str(value)

def setsetting(arg, value):
	xbmcaddon.Addon().setSetting(arg, str(value))

def settingrpc(setting):
	try:
		r = json.loads(xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"Settings.GetSettingValue", "params": {{"setting": "{}"}} }}'.format(setting)))
	except:
		return None
	else:
		return r.get('result').get('value')

def settings(changed=False):
	dict = {}
	skip = [ 'alert_notification', 'service', 'geoip' ]

	try:
		tree = ET.parse(f'{config.addon_data}settings.xml')
	except:
		return dict
	else:
		root = tree.getroot()

		for item in root:
			id = item.attrib['id']

			if changed:
				if not 'loc' in id and not id in skip:
					dict[id] = item.text
			else:
				dict[id] = item.text

		return dict

def region(arg):
	return xbmc.getRegion(arg)

# Localization
def loc(arg):
	return xbmc.getLocalizedString(arg)

def locaddon(arg):
	return xbmcaddon.Addon().getLocalizedString(arg)

# Notification
def notification(header, msg, icon, locid):
	log(f'[LOC{locid}] Notification: {header} - {msg}')

	duration = (int(setting('alert_duration')) - 2) * 1000
	xbmcgui.Dialog().notification(header, msg, icon, int(duration))

# Datetime
def dt(arg, stamp=0):

	if arg == 'stamputc':
		return datetime.fromtimestamp(int(stamp), tz=timezone('UTC'))
	elif arg == 'stamploc':
		if config.loc.utz:
			return datetime.fromtimestamp(int(stamp), tz=timezone('UTC')).astimezone(config.loc.tz)
		else:
			return datetime.fromtimestamp(int(stamp), tz=timezone('UTC')).astimezone()
	elif arg == 'nowutc':
		return datetime.now(tz=timezone('UTC'))
	elif arg == 'nowutcstamp':
		return int(datetime.now(tz=timezone('UTC')).timestamp())
	elif arg == 'nowloc':
		if config.loc.utz:
			return datetime.now(tz=timezone('UTC')).astimezone(config.loc.tz)
		else:
			return datetime.now(tz=timezone('UTC')).astimezone()
	elif arg == 'isoutc':
		return datetime.fromisoformat(stamp)
	elif arg == 'isoloc':
		if config.loc.utz:
			return datetime.fromisoformat(stamp).astimezone(config.loc.tz)
		else:
			return datetime.fromisoformat(stamp).astimezone()

# Last update
def lastupdate(arg):
	try:
		time1 = setting(arg)
		time2 = dt('nowutcstamp')
		return int(time2) - int(time1)
	except:
		return 321318000

def setupdate(arg):
	setsetting(arg, dt('nowutcstamp'))

# Window property
def clrprop(property):
	log(f'CLR: {property}', 4)
	xbmcgui.Window(12600).clearProperty(property)

def winprop(property):
	log(f'GET: {property}', 4)
	return xbmcgui.Window(12600).getProperty(property)

# Window property (Set)
def setprop(property, data):
	log(f'SET: {property} = {data}', 4)
	xbmcgui.Window(12600).setProperty(property, str(data))

# Window property (Get)
def getprop(data, map, idx, count):

	# Content
	if len(map[1]) == 1:
		if idx is not None:
			content = data[map[1][0]][idx]
		else:
			content = data[map[1][0]]
	elif len(map[1]) == 2:
		if idx is not None:
			content = data[map[1][0]][map[1][1]][idx]
		else:
			content = data[map[1][0]][map[1][1]]
	elif len(map[1]) == 3:
		if idx is not None:
			content = data[map[1][0]][map[1][1]][map[1][2]][idx]
		else:
			content = data[map[1][0]][map[1][1]][map[1][2]]

	if content is None:
		raise TypeError('No data')

	# Unit
	unit = map[3]

	# WMO (isday)
	if unit.startswith('wmo') or unit == 'image' or unit == 'code':
		if idx:
			try:
				if data[map[1][0]]['is_day'][idx] == 1:
					isday = 'd'
				else:
					isday = 'n'
			except:
				isday = 'd'
		else:
			try:
				if data[map[1][0]]['is_day'] == 1:
					isday = 'd'
				else:
					isday = 'n'
			except:
				isday = 'd'

	# Tools
	if unit == 'round':
		content = int(round(content))
	elif unit == 'roundpercent':
		content = f'{int(round(content))}%'
	elif unit == 'round2':
		content = round(content, 2)
	elif unit == 'wmocond':
		content = config.localization.wmo.get(f'{content}{isday}')
	elif unit == 'wmoimage':
		content = f'{config.addon_icons}/{config.addon.icons}/{content}{isday}.png'
	elif unit == 'wmocode':
		content = f'{content}{isday}'
	elif unit == 'image':
		# KODI workaround for DayX.OutlookIcon, add "resource://resource.images.weathericons.default" to path
		if map[2][0] == 'day':
			content = f'resource://resource.images.weathericons.default/{config.map_wmo.get(f"{content}{isday}")}.png'
		else:
			content = f'{config.map_wmo.get(f"{content}{isday}")}.png'
	elif unit == 'code':
		content = config.map_wmo.get(f'{content}{isday}')
	elif unit == 'date':
		content = dt('stamploc', content).strftime(config.kodi.date)
	elif unit == 'time':
		content = conv.time('time', content)
	elif unit == 'timeiso':
		content = conv.time('timeiso', content)
	elif unit == 'hour':
		content = conv.time('hour', content)
	elif unit == 'weekday':
		content = config.localization.weekday.get(dt('stamploc', content).strftime('%u'))
	elif unit == 'weekdayshort':
		content = config.localization.weekdayshort.get(dt('stamploc', content).strftime('%u'))
	elif unit == '%':
		content = f'{content}%'

	# Temperature
	elif unit == 'temperature':
		content = conv.temp(content)
	elif unit == 'temperaturekodi':
		content = conv.temp(content, True)
	elif unit == 'temperatureunit':
		content = f'{conv.temp(content)}{conv.temp()}'
	elif unit == 'unittemperature':
		content = conv.temp()

	# Speed
	elif unit == 'speed':
		content = conv.speed(content)
	elif unit == 'unitspeed':
		content = conv.speed()

	# Precipitation
	elif unit == 'precipitation':
		content = conv.precip(content)
	elif unit == 'unitprecipitation':
		content = conv.precip()

	# Distance
	elif unit == 'distance':
		content = conv.distance(content)
	elif unit == 'unitdistance':
		content = conv.distance()

	# UVIndex
	elif unit == 'uvindex':
		content = conv.dp(content, config.addon.uvindexdp)

	# Particles
	elif unit == 'particles':
		content = conv.dp(content, config.addon.particlesdp)
	elif unit == 'unitparticles':
		content = 'μg/m³'

	# Pollen
	elif unit == 'pollen':
		content = conv.dp(content, config.addon.pollendp)
	elif unit == 'unitpollen':
		content = f'{locaddon(32456)}/m³'

	# Radiation
	elif unit == 'radiation':
		content = conv.dp(content, config.addon.radiationdp)
	elif unit == 'unitradiation':
		content = 'W/m²'

	# Pressure
	elif unit == 'pressure':
		content = conv.pressure(content)
	elif unit == 'unitpressure':
		content = conv.pressure()

	# Direction
	elif unit == 'direction':
		content = conv.direction(content)

	# Percent
	elif unit == 'unitpercent':
		content = '%'

	# Wind
	elif unit == 'windkodi':
		speed     = round(conv.speed(data['current']['wind_speed_10m']), True)
		unit      = conv.speed(False, True)
		direction = conv.direction(data['current']['wind_direction_10m'])
		content   = loc(434).format(direction, int(speed), unit)

	# Moonphase
	elif unit == 'moonphase':
		content = conv.moonphase(int(content))

	elif unit == 'moonphaseimage':
		content = f'{config.addon_icons}/moon/{conv.moonphaseimage(int(content))}'

	# Graphs
	elif unit == 'graph':
		property = f'{map[2][0]}.{count}.{map[2][1]}'
		time     = map[2][0]
		type     = map[2][1]
		mscale   = map[4]
		alert    = 0
		scale    = 0
		scaleneg = False

		# Content
		try:
			calc = map[5]
		except:
			calc = False
		else:
			if calc == 'temperature':

				if conv.temp() == '°F':
					mscale = '100'

			elif calc == 'divide10':
				content = content/10

			elif calc == 'divide1000':
				content = content/1000

			elif calc == 'pressure':
				content = config.map_pressure.get(int(content),0)

		# Autoscale
		try:
			ascale = config.addon.scalecache[f'{time}{type}']
			nscale = config.addon.scalecache[f'{time}{type}neg']
		except:
			_idx_ = idx

			for _count_ in range(0,25):

				if calc == 'temperature':
					v = conv.temp(data[map[1][0]][map[1][1]][_idx_+_count_], True)

					# Negative temperature
					if v < 0:
						scaleneg = True

					check = abs(v)

				elif calc == 'divide10':
					check = abs(data[map[1][0]][map[1][1]][_idx_+_count_]/10)
				elif calc == 'divide1000':
					check = abs(data[map[1][0]][map[1][1]][_idx_+_count_]/1000)
				elif calc == 'pressure':
					check = abs(config.map_pressure.get(int(data[map[1][0]][map[1][1]][_idx_+_count_])))
				else:
					check = abs(data[map[1][0]][map[1][1]][_idx_+_count_])

				if check > scale:
					scale = check

			if scale < 1:
				config.addon.scalecache[f'{time}{type}'] = 1
			elif scale >= 101 and scale <= 150:
				config.addon.scalecache[f'{time}{type}'] = 150
			elif scale >= 151 and scale <= 200:
				config.addon.scalecache[f'{time}{type}'] = 200
			else:
				config.addon.scalecache[f'{time}{type}'] = math.ceil(scale/10.0)*10

			# Negative values
			config.addon.scalecache[f'{time}{type}neg'] = scaleneg

			# Set cache
			ascale = config.addon.scalecache[f'{time}{type}']
			nscale = config.addon.scalecache[f'{time}{type}neg']

			log(f'Scale {type} ({time}) = {ascale}', 4)

		# Alert
		for _alert_ in config.alert.map[type]:

			if not 'alert' in _alert_:
				continue

			if 'wmo' in _alert_:
				limit = list(config.alert.map[type][_alert_].split(' '))
			else:
				limit = float(config.alert.map[type][_alert_])

			if not limit:
				continue

			if 'high' in _alert_:
				if content >= int(limit):
					alert = int(_alert_[-1])
			elif 'low' in _alert_:
				if content <= int(limit):
					alert = int(_alert_[-1])
			elif 'wmo' in _alert_:
				for wmo in limit:
					if content == int(wmo):
						alert = int(alert[-1])

		setprop(f'{property}alert', alert)

		# Content
		if calc == 'temperature':
			content = conv.temp(content, True)

		if ascale == 1:
			content = round(content,1)
		else:
			content = round(content)

		# Set properties
		if nscale:
			setprop(f'{property}image', f'{config.addon_icons}/graph/{config.kodi.height}/scaleneg{mscale}_{content}.png')
			setprop(f'{property}imagescale', f'{config.addon_icons}/graph/{config.kodi.height}/scaleneg{ascale}_{content}.png')
			setprop(f'{property}scale', f'{ascale}n')
		else:
			setprop(f'{property}image', f'{config.addon_icons}/graph/{config.kodi.height}/scale{mscale}_{content}.png')
			setprop(f'{property}imagescale', f'{config.addon_icons}/graph/{config.kodi.height}/scale{ascale}_{content}.png')
			setprop(f'{property}scale', f'{ascale}')

		# Color
		if alert == 0:
			if content < 0:
				setprop(f'{property}color', config.addon.cnegative)
				setprop(f'{property}colornormal', config.addon.cnegative)
			else:
				setprop(f'{property}color', config.addon.cdefault)
				setprop(f'{property}colornormal', config.addon.cnormal)

		elif alert == 1:
			setprop(f'{property}color', config.addon.cnotice)
			setprop(f'{property}colornormal', config.addon.cnotice)

		elif alert == 2:
			setprop(f'{property}color', config.addon.ccaution)
			setprop(f'{property}colornormal', config.addon.ccaution)

		elif alert == 3:
			setprop(f'{property}color', config.addon.cdanger)
			setprop(f'{property}colornormal', config.addon.cdanger)

	# Return data
	return content

# Set alert
def setalert(data, map, idx, locid, curid, loc, mode):
	winprops = [ 'name', 'value', 'icon', 'unit', 'time', 'hours', 'status' ]
	type   = map[2][1]
	prop   = config.alert.map[type]['type']
	name   = locaddon(config.alert.map[type]['loc'])
	shours = config.addon.alerthours
	hours  = { '1': 0, '2': 0, '3': 0 }
	code   = 0
	value  = 0
	unit   = ''

	log(f'[LOC{locid}] Checking alert: {prop}', 3)

	for index in range(idx, idx+shours):

		try:
			content = int(data[map[1][0]][map[1][1]][index])
		except:
			if locid == curid:
				setprop(f'alert.{prop}', 0)
				for winprop in winprops:
					setprop(f'alert.{prop}.{winprop}', '')

			return

		# Alert
		for alert in config.alert.map[type]:

			if not 'alert' in alert:
				continue

			if 'wmo' in alert:
				limit = list(config.alert.map[type][alert].split(' '))
			else:
				limit = int(config.alert.map[type][alert])

			if not limit:
				continue

			if 'high' in alert:
				if content >= limit:
					hours[f'{alert[-1]}'] += 1
				if content >= value:
					if content >= limit:
						code  = int(alert[-1])
						value = content
						stamp = data[map[1][0]]['time'][index]

			elif 'low' in alert:
				if content <= limit:
					hours[f'{alert[-1]}'] += 1
				if content <= value:
					if content <= limit:
						code  = int(alert[-1])
						value = content
						stamp = data[map[1][0]]['time'][index]

			elif 'wmo' in alert:
				for wmo in limit:
					if content == int(wmo):
						hours[f'{alert[-1]}'] += 1

						if content > value:
							code  = int(alert[-1])
							value = content
							stamp = data[map[1][0]]['time'][index]

	# Check alert code
	if code != 0:
		icon = f'{prop}{code}'
		time = conv.time('time', stamp)

		if prop == 'temperature':
			value = conv.temp(value)
			unit  = conv.temp()
		elif prop == 'windspeed' or prop == 'windgust':
			value = conv.speed(value)
			unit  = conv.speed()
		elif prop == 'condition':
			icon  = f'condition{config.map_alert_condition.get(value)}{code}'
			value = config.localization.wmo.get(f'{value}d')

		# Set alert properties for current location
		if locid == curid:

			if setting(f'alert_{prop}_enabled', 'bool'):
				log(f'[LOC{locid}] Updating alert: {prop} = {code}', 3)
				config.addon.alerts += 1

				setprop(f'alert.{prop}', code)
				setprop(f'alert.{prop}.name', name)
				setprop(f'alert.{prop}.time', time)
				setprop(f'alert.{prop}.hours', hours[str(code)])
				setprop(f'alert.{prop}.icon', f'{config.addon_icons}/alert/{icon}.png')
				setprop(f'alert.{prop}.value', value)
				setprop(f'alert.{prop}.unit', unit)
				if code == 1:
					setprop(f'alert.{prop}.status', locaddon(32340))
				elif code == 2:
					setprop(f'alert.{prop}.status', locaddon(32341))
				elif code == 3:
					setprop(f'alert.{prop}.status', locaddon(32342))
			else:
				setprop(f'alert.{prop}', '')
				for winprop in winprops:
					setprop(f'alert.{prop}.{winprop}', '')

		# Notification
		if mode == 'msgqueue':
			if code == 1 and setting(f'alert_{prop}_notice', 'bool'):
				config.addon.msgqueue.append([ f'{loc} - {locaddon(32340)} ({hours[str(code)]} {locaddon(32288)})', f'({time}) {name}: {value} {unit}', f'{config.addon_icons}/alert/{icon}.png' ])
			elif code == 2 and setting(f'alert_{prop}_caution', 'bool'):
				config.addon.msgqueue.append([ f'{loc} - {locaddon(32341)} ({hours[str(code)]} {locaddon(32288)})', f'({time}) {name}: {value} {unit}', f'{config.addon_icons}/alert/{icon}.png' ])
			elif code == 3 and setting(f'alert_{prop}_danger', 'bool'):
				config.addon.msgqueue.append([ f'{loc} - {locaddon(32342)} ({hours[str(code)]} {locaddon(32288)})', f'({time}) {name}: {value} {unit}', f'{config.addon_icons}/alert/{icon}.png' ])

	else:
		if locid == curid:
			setprop(f'alert.{prop}', 0)
			for winprop in winprops:
				setprop(f'alert.{prop}.{winprop}', '')

# Get file
def getfile(file):
	try:
		# Note: Changing language throws an exception without enforcing utf8
		with open(Path(f'{config.addon_cache}/{file}'), 'r', encoding='utf8') as f:
			data = json.load(f)

	except Exception as e:
		log(f'{e}', 2)
		return None

	else:
		return data

# Index
def index(arg, data):
	if arg == 'now':
		match = dt('nowloc').strftime('%Y-%m-%d %H')
	elif arg == 'mid':
		match = dt('nowloc').strftime('%Y-%m-%d 00')
	elif arg == 'day':
		match = dt('nowloc').strftime('%Y-%m-%d')

	for idx in range(config.mindata, config.maxdata):

		try:
			if arg == 'day':
				timecheck = dt('stamploc', data['daily']['time'][idx]).strftime('%Y-%m-%d')
			else:
				timecheck = dt('stamploc', data['hourly']['time'][idx]).strftime('%Y-%m-%d %H')
		except:
			return None
		else:
			if timecheck == match:
				return idx

# Directory
def createdir():
	file = config.addon_data + 'w.txt'

	try:
		os.makedirs(config.addon_cache, exist_ok=True)
		with open(file, 'w') as f:
			f.write('w')
	except Exception as e:
		log(f'Addon data directory not writeable: {config.addon_data} {e}', 2)
		xbmcgui.Dialog().notification('Weather Open-Meteo', 'Weather data directory not writeable, check log ...', xbmcgui.NOTIFICATION_ERROR, 15000)
		sys.exit(1)
	else:
		os.remove(file)

# Locations
def locations():
	locs = 0
	for count in range(1,6):
		loc = setting(f'loc{count}')
		if loc:
			setprop(f'location{count}', loc)
			locs += 1

	setprop('locations', locs)

# LatLon2Coords
def lat2coords(lat_deg, lon_deg, zoom):
	lat_rad = math.radians(lat_deg)
	n = 1 << zoom
	xtile = int((lon_deg + 180.0) / 360.0 * n)
	ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
	return xtile, ytile

def numTiles(z):
	return(pow(2,z))

def latEdges(y,z):
	n = numTiles(z)
	unit = 1 / n
	relY1 = y * unit
	relY2 = relY1 + unit
	lat1 = mercatorToLat(math.pi * (1 - 2 * relY1))
	lat2 = mercatorToLat(math.pi * (1 - 2 * relY2))
	return(lat1,lat2)

def lonEdges(x,z):
	n = numTiles(z)
	unit = 360 / n
	lon1 = -180 + x * unit
	lon2 = lon1 + unit
	return(lon1,lon2)

def mercatorToLat(mercatorY):
	return(math.degrees(math.atan(math.sinh(mercatorY))))

def coords2bbox(x,y,z):
	lat1,lat2 = latEdges(y,z)
	lon1,lon2 = lonEdges(x,z)
	return((lat2, lon1, lat1, lon2)) # S,W,N,E

