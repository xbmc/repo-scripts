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
from statistics import mode, mean

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
	file = Path(config.addon_data + 'settings.xml')

	try:
		with open(file, 'r') as f:
			data = f.read()

		root = ET.fromstring(data)
	except:
		return dict
	else:
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

# Geolocation
def geoip(create=False):
	f = Path(f'{config.addon_data}/geoip')

	if create:
		with open(f, mode='w'):
			pass
	else:
		return f.is_file()

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
	elif arg == 'dayofyear':
		return datetime.today().timetuple().tm_yday

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
	xbmcgui.Window(12600).clearProperty(property)

def winprop(property):
	return xbmcgui.Window(12600).getProperty(property)

# Set Window property
def setprop(property, data, window=12600):
	xbmcgui.Window(window).setProperty(property, str(data))

# Set properties
def setprops():
	if config.addon.api:
		for i in sorted(config.loc.prop):
			setprop(f'weather.{i}', config.loc.prop[i], 10000)

			if config.addon.full and i in config.addon.mode:
				setprop(i, config.loc.prop[i])

	else:
		for i in sorted(config.loc.prop):
			setprop(i, config.loc.prop[i])

# Add property
def addprop(property, content):
	config.loc.prop[property] = content

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
	elif unit == 'seconds':
		m, s = divmod(int(content), 60)
		h, m = divmod(m, 60)
		content = f'{h:d}:{m:02d}'
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

	# Snow
	elif unit == 'snow':
		content = conv.snow(content)
	elif unit == 'unitsnow':
		content = conv.snow()

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

	# Season
	elif unit == 'season':
		content = conv.season(float(content))

	# Graphs
	elif unit == 'graph':
		idxnow    = index("now", data)
		type      = map[2][1]
		unit      = map[4]
		scaleneg  = False
		count     = 0 if config.addon.api else 1
		property  = f'{map[2][0]}.{count}.{map[2][1]}'
		content   = None
		alerting  = setting(f'alert_{type.split(".")[0]}_enabled', 'bool', True)

		# Data
		lv = []
		lt = []

		for idx in range(idxnow, idxnow+24):
			try:
				v = data[map[1][0]][map[1][1]][idx]
				t = data[map[1][0]]['time'][idx]
			except:
				continue
			else:
				lv.append(v)
				lt.append(t)

		# Unit
		lc   = [ conv.item(v, unit, False) for v in lv ]
		unit = conv.item(False, unit)

		addprop(f'{property}.unit', unit)

		# Neg
		scaleneg = bool([ v for v in lc if v < 0 ])

		# Scale
		scalemin = min(lc)
		scalemax = max(lc)
		scaleabs = max([ abs(v) for v in lc ])

		r = 1 if scalemin < 1 and scalemax < 1 else None
		a = scalemax/4
		s = (scalemax-scalemin)/4

		addprop(f'{property}.xaxis0', round(scalemax,r))
		addprop(f'{property}.xaxis1', round(scalemax-a,r))
		addprop(f'{property}.xaxis2', round(scalemax-a*2,r))
		addprop(f'{property}.xaxis3', round(scalemax-a*3,r))
		addprop(f'{property}.xaxis4', round(scalemax-a*4,r))

		addprop(f'{property}.scalexaxis0', round(scalemax,r))
		addprop(f'{property}.scalexaxis1', round(scalemax-s,r))
		addprop(f'{property}.scalexaxis2', round(scalemax-s*2,r))
		addprop(f'{property}.scalexaxis3', round(scalemax-s*3,r))
		addprop(f'{property}.scalexaxis4', round(scalemax-s*4,r))

		# Graph
		for idx in range(0,24):
			alert     = 0
			property  = f'{map[2][0]}.{count}.{map[2][1]}'

			try:
				time   = lt[idx]
				avalue = lv[idx]
				value  = lc[idx]

			except:
				continue
			else:
				negative = True if value < 0 else False

				if scalemax-scalemin == 0 or scaleabs == 0:
					percent = 0
				else:
					percent = round((value-scalemin)/(scalemax-scalemin)*100) if not negative else round(abs(value)/scaleabs*100)

				if scalemax == 0 or scaleabs == 0:
					percentabs = 0
				else:
					percentabs = round((value)/(scalemax)*100) if not negative else round(abs(value)/scaleabs*100)

				# Time
				addprop(f'{property}.time', conv.time('hour', time))

				# Value
				addprop(f'{property}.value', value)

				# Image
				if scaleneg:
					if negative:
						addprop(f'{property}.image', f'{config.addon_icons}/graph/{config.kodi.height}/bar_n{percent}n.png')
						addprop(f'{property}.code', f'n{percent}n')
					else:
						addprop(f'{property}.image', f'{config.addon_icons}/graph/{config.kodi.height}/bar_n{percent}p.png')
						addprop(f'{property}.code', f'n{percent}p')

				else:
					addprop(f'{property}.image', f'{config.addon_icons}/graph/{config.kodi.height}/bar_{percentabs}p.png')
					addprop(f'{property}.code', f'{percentabs}p')
					addprop(f'{property}.scaleimage', f'{config.addon_icons}/graph/{config.kodi.height}/bar_{percent}p.png')
					addprop(f'{property}.scalecode', f'{percent}p')

				# Alert
				if alerting:

					for c, d in [(x, y) for x in [ 3, 2, 1 ] for y in [ 'high', 'low', 'wmo' ] ]:
						last =  False

						try:
							if d == 'wmo':
								limit = list(config.alert.map[type][f'alert_{type.split(".")[0]}_{d}_{c}'].split(' '))
							else:
								limit = int(config.alert.map[type][f'alert_{type.split(".")[0]}_{d}_{c}'])
						except:
							continue

						if d == 'high':
							if avalue >= limit:
								if last and avalue > last:
									alert, last = c, avalue
								elif not last:
									alert, last = c, avalue
						elif d == 'low':
							if avalue <= limit:
								if last and avalue < last:
									alert, last = c, avalue
								elif not last:
									alert, last = c, avalue
						elif d == 'wmo':
							for wmo in limit:
								if avalue == int(wmo):
									if last and avalue > last:
										alert, last = c, avalue
									elif not last:
										alert, last = c, avalue
						if alert:
							break

				addprop(f'{property}.alert', alert)

				# Alert icon
				if alert == 0:
					addprop(f'{property}.alerticon', '')
				else:
					if type == 'condition.graph':
						icon  = f'{config.map_alert_condition.get(last)}{alert}'
						addprop(f'{property}.alerticon', f'{config.addon_icons}/alert/{icon}.png')
					else:
						addprop(f'{property}.alerticon', f'{config.addon_icons}/alert/{config.alert.map[type]["icon"]}{alert}.png')

				# Color
				if alert == 0:
					if negative:
						addprop(f'{property}.color', config.addon.cnegative)
						addprop(f'{property}.colornormal', config.addon.cnegative)
					else:
						addprop(f'{property}.color', config.addon.cdefault)
						addprop(f'{property}.colornormal', config.addon.cnormal)

				elif alert == 1:
					addprop(f'{property}.color', config.addon.cnotice)
					addprop(f'{property}.colornormal', config.addon.cnotice)

				elif alert == 2:
					addprop(f'{property}.color', config.addon.ccaution)
					addprop(f'{property}.colornormal', config.addon.ccaution)

				elif alert == 3:
					addprop(f'{property}.color', config.addon.cdanger)
					addprop(f'{property}.colornormal', config.addon.cdanger)

				count += 1

	# TimeOfDay
	elif unit == 'timeofday':
		idxnow  = index("now", data)
		idxmid  = index("mid", data)
		idxday  = index("mid", data)
		tod     = { 0: 'night', 1: 'morning', 2: 'afternoon', 3: 'evening' }
		start   = False
		content = 'true'
		idxtod  = 0 if config.addon.api else 1
		idxtod2 = 0 if config.addon.api else 1
		idxtod3 = 0 if config.addon.api else 1

		for d in range(0, config.maxdays):
			l   = []
			ll  = []

			# Daily
			for c in range(idxday, idxday+24):

				try:
					v  = data[map[1][0]][map[1][1]][c]
					vv = data[map[1][0]]['temperature_2m'][c]
				except:
					for i in [ 'date', 'shortdate', 'weekday', 'weekdayshort', 'condition', 'outlook', 'outlookicon', 'outlookiconwmo', 'temperature', 'maxoutlook', 'maxoutlookicon', 'maxoutlookiconwmo' ]:
						addprop(f'daily.{idxtod3}.overview.{i}', '')
					continue
				else:
					l.append(v)
					ll.append(vv)

			# Personalized forecast
			fcstart = config.map_fcstart.get(config.addon.fcstart)
			fcend   = config.map_fcend.get(config.addon.fcend)

			l = l[fcstart:][:fcend]

			# Properties
			date  = data[map[1][0]]['time'][idxday]
			code  = mode(sorted(l, reverse=True))
			mcode = max(l)
			temp  = conv.temp(mean(ll))

			addprop(f'daily.{idxtod3}.overview.date', dt('stamploc', date).strftime(config.kodi.date))
			addprop(f'daily.{idxtod3}.overview.shortdate', dt('stamploc', date).strftime(config.kodi.date))
			addprop(f'daily.{idxtod3}.overview.weekday', config.localization.weekday.get(dt('stamploc', date).strftime('%u')))
			addprop(f'daily.{idxtod3}.overview.weekdayshort', config.localization.weekdayshort.get(dt('stamploc', date).strftime('%u')))
			addprop(f'daily.{idxtod3}.overview.temperature', temp)
			addprop(f'daily.{idxtod3}.overview.outlook', config.localization.wmo.get(f'{code}d'))
			addprop(f'daily.{idxtod3}.overview.outlookicon', f'{config.map_wmo.get(f"{code}d")}.png')
			addprop(f'daily.{idxtod3}.overview.outlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{code}d.png')
			addprop(f'daily.{idxtod3}.overview.fanartcode', config.map_wmo.get(f"{code}d"))
			addprop(f'daily.{idxtod3}.overview.fanartcodewmo', f'{code}d')

			# Overwrite forecast (personalized)
			addprop(f'daily.{idxtod3}.condition', config.localization.wmo.get(f'{code}d'))
			addprop(f'daily.{idxtod3}.outlook', config.localization.wmo.get(f'{code}d'))
			addprop(f'daily.{idxtod3}.outlookicon', f'{config.map_wmo.get(f"{code}d")}.png')
			addprop(f'daily.{idxtod3}.outlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{code}d.png')
			addprop(f'daily.{idxtod3}.fanartcode', config.map_wmo.get(f"{code}d"))
			addprop(f'daily.{idxtod3}.fanartcodewmo', f'{code}d')

			if not config.addon.api:
				addprop(f'day{idxtod3-1}.condition', config.localization.wmo.get(f'{code}d'))
				addprop(f'day{idxtod3-1}.outlook', config.localization.wmo.get(f'{code}d'))
				addprop(f'day{idxtod3-1}.outlookicon', f'resource://resource.images.weathericons.default/{config.map_wmo.get(f"{code}d")}.png')
				addprop(f'day{idxtod3-1}.outlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{code}d.png')
				addprop(f'day{idxtod3-1}.fanartcode', config.map_wmo.get(f"{code}d"))
				addprop(f'day{idxtod3-1}.fanartcodewmo', f'{code}d')

			# Max outlook
			if mcode > code:
				addprop(f'daily.{idxtod3}.overview.maxoutlook', config.localization.wmo.get(f'{mcode}d'))
				addprop(f'daily.{idxtod3}.overview.maxoutlookicon', f'{config.map_wmo.get(f"{code}d")}.png')
				addprop(f'daily.{idxtod3}.overview.maxoutlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{mcode}d.png')

				addprop(f'daily.{idxtod3}.maxoutlook', config.localization.wmo.get(f'{mcode}d'))
				addprop(f'daily.{idxtod3}.maxoutlookicon', f'{config.map_wmo.get(f"{code}d")}.png')
				addprop(f'daily.{idxtod3}.maxoutlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{mcode}d.png')

			else:
				addprop(f'daily.{idxtod3}.overview.maxoutlook', '')
				addprop(f'daily.{idxtod3}.overview.maxoutlookicon', '')
				addprop(f'daily.{idxtod3}.overview.maxoutlookiconwmo', '')

				addprop(f'daily.{idxtod3}.maxoutlook', '')
				addprop(f'daily.{idxtod3}.maxoutlookicon', '')
				addprop(f'daily.{idxtod3}.maxoutlookiconwmo', '')

			idxday += 24
			idxtod3 += 1

			# Hourly
			for t in range(0,4):
				l   = []
				ll  = []
				lll = []
				llll = []
				now = ''

				for c in range(idxmid, idxmid+6):

					try:
						v   = data[map[1][0]][map[1][1]][c]
						vv  = data[map[1][0]]['is_day'][c]
						vvv = data[map[1][0]]['temperature_2m'][c]
						vvvv = data[map[1][0]]['time'][c]
					except:
						continue
					else:
						l.append(v)
						ll.append(vv)
						lll.append(vvv)
						llll.append(vvvv)

						if idxnow == c:
							start = True
							now   = 'true'

				date  = data[map[1][0]]['time'][idxmid]
				code  = mode(sorted(l, reverse=True))
				mcode = max(l)
				isday = mode(sorted(ll, reverse=False))
				isday = 'n' if isday == 0 else 'd'
				temp  = conv.temp(mean(lll))

				# TimeOfDay (List)
				if start:
					addprop(f'timeofday.{idxtod}.date', dt('stamploc', date).strftime(config.kodi.date))
					addprop(f'timeofday.{idxtod}.shortdate', dt('stamploc', date).strftime(config.kodi.date))
					addprop(f'timeofday.{idxtod}.weekday', config.localization.weekday.get(dt('stamploc', date).strftime('%u')))
					addprop(f'timeofday.{idxtod}.weekdayshort', config.localization.weekdayshort.get(dt('stamploc', date).strftime('%u')))
					addprop(f'timeofday.{idxtod}.time', config.localization.timeofday.get(t))
					addprop(f'timeofday.{idxtod}.outlook', config.localization.wmo.get(f'{code}{isday}'))
					addprop(f'timeofday.{idxtod}.outlookicon', f'{config.map_wmo.get(f"{code}{isday}")}.png')
					addprop(f'timeofday.{idxtod}.outlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{code}{isday}.png')
					addprop(f'timeofday.{idxtod}.fanartcode', config.map_wmo.get(f"{code}{isday}"))
					addprop(f'timeofday.{idxtod}.fanartcodewmo', f'{code}{isday}')
					addprop(f'timeofday.{idxtod}.temperature', temp)

					if mcode > code:
						addprop(f'timeofday.{idxtod}.maxoutlook', config.localization.wmo.get(f'{mcode}{isday}'))
						addprop(f'timeofday.{idxtod}.maxoutlookicon', f'{config.map_wmo.get(f"{mcode}{isday}")}.png')
						addprop(f'timeofday.{idxtod}.maxoutlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{mcode}{isday}.png')
					else:
						addprop(f'timeofday.{idxtod}.maxoutlook', '')
						addprop(f'timeofday.{idxtod}.maxoutlookicon', '')
						addprop(f'timeofday.{idxtod}.maxoutlookiconwmo', '')

					idxtod += 1

				# TimeOfDay (Daily)
				addprop(f'daily.{idxtod2}.{tod.get(t)}.date', dt('stamploc', date).strftime(config.kodi.date))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.shortdate', dt('stamploc', date).strftime(config.kodi.date))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.weekday', config.localization.weekday.get(dt('stamploc', date).strftime('%u')))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.weekdayshort', config.localization.weekdayshort.get(dt('stamploc', date).strftime('%u')))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.time', config.localization.timeofday.get(t))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.outlook', config.localization.wmo.get(f'{code}{isday}'))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.outlookicon', f'{config.map_wmo.get(f"{code}{isday}")}.png')
				addprop(f'daily.{idxtod2}.{tod.get(t)}.outlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{code}{isday}.png')
				addprop(f'daily.{idxtod2}.{tod.get(t)}.fanartcode', config.map_wmo.get(f"{code}{isday}"))
				addprop(f'daily.{idxtod2}.{tod.get(t)}.fanartcodewmo', f'{code}{isday}')
				addprop(f'daily.{idxtod2}.{tod.get(t)}.temperature', temp)

				if mcode > code:
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlook', config.localization.wmo.get(f'{mcode}{isday}'))
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlookicon', f'{config.map_wmo.get(f"{mcode}{isday}")}.png')
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlookiconwmo', f'{config.addon_icons}/{config.addon.icons}/{mcode}{isday}.png')
				else:
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlook', '')
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlookicon', '')
					addprop(f'daily.{idxtod2}.{tod.get(t)}.maxoutlookiconwmo', '')

				if d == 0:
					addprop(f'daily.{idxtod2}.{tod.get(t)}.now', now)

				idxmid  += 6

			idxtod2 += 1

	# Return data
	return content

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
	p = Path(config.addon_data)
	p.mkdir(parents=True, exist_ok=True)

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

