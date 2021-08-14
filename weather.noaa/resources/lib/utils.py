# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from future import standard_library
import math
import time

import xbmc, xbmcaddon

from dateutil.parser import parse
import socket, urllib.request
import json

standard_library.install_aliases()


ADDON		= xbmcaddon.Addon()
ADDONID		= ADDON.getAddonInfo('id')
LANGUAGE	= ADDON.getLocalizedString

DEBUG		= ADDON.getSetting('Debug')
TEMPUNIT	= xbmc.getRegion('tempunit')
SPEEDUNIT	= xbmc.getRegion('speedunit')
DATEFORMAT	= xbmc.getRegion('dateshort')
TIMEFORMAT	= xbmc.getRegion('meridiem')


def log(txt):
	if DEBUG == 'true':
		message = u'%s: %s' % (ADDONID, txt)
		xbmc.log(msg=message, level=xbmc.LOGDEBUG)




def get_url_JSON(url):
	try:
		xbmc.log('fetching url: %s' % url,level=xbmc.LOGDEBUG)
		try:
			timeout = 10
			socket.setdefaulttimeout(timeout)
			# this call to urllib.request.urlopen now uses the default timeout
			# we have set in the socket module
			req = urllib.request.Request(url)
			req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
			response = urllib.request.urlopen(req)

			#responsedata = decode_utf8(urlopen(url, timeout=25).read())
			responsedata = response.read()
			data = json.loads(responsedata)
			log('data: %s' % data)
			# Happy path, we found and parsed data
			return data
		except:
			xbmc.log('failed to parse json: %s' % url,level=xbmc.LOGERROR)
			xbmc.log('data: %s' % data,level=xbmc.LOGERROR)
	except:
		xbmc.log('failed to fetch : %s' % url,level=xbmc.LOGERROR)
	return None



def get_url_response(url):
	try:
		xbmc.log('fetching url: %s' % url,level=xbmc.LOGDEBUG)
		timeout = 10
		socket.setdefaulttimeout(timeout)
		# this call to urllib.request.urlopen now uses the default timeout
		# we have set in the socket module
		req = urllib.request.Request(url)
		req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
		response = urllib.request.urlopen(req)

		responsedata = response.read()
		log('data: %s' % responsedata)
		# Happy path, we found and parsed data
		return responsedata
	except:
		xbmc.log('failed to fetch : %s' % url,level=xbmc.LOGERROR)
	return None

def get_url_image(url,destination):
	try:
		urllib.request.urlretrieve(url, destination)
		return destination
	except:
		xbmc.log('failed to fetch : %s' % url,level=xbmc.LOGERROR)
	return None






WEATHER_CODES = {
		'skc':		'34', #'Fair/clear'
		'few':		'30', #'A few clouds'
		'sct':		'30', #'Partly cloudy'
		'bkn':		'28', #'Mostly cloudy'
		'ovc':		'26', #'Overcast'
		'wind_skc':	'24', #'Fair/clear and windy'
		'wind_few':	'26', #'A few clouds and windy'
		'wind_sct':	'26', #'Partly cloudy and windy'
		'wind_bkn':	'28', #'Mostly cloudy and windy'
		'wind_ovc':	'26', #'Overcast and windy'
		'snow':		'16', #'Snow'
		'rain_snow':	'5', #'Rain/snow'
		'rain_sleet':	'6', #'Rain/sleet'
		'snow_sleet':	'7', #'Rain/sleet'
		'fzra':		'10', #'Freezing rain'
		'rain_fzra':	'10', #'Rain/freezing rain'
		'snow_fzra':	'10', #'Freezing rain/snow'
		'sleet':	'18', #'Sleet'
		'rain':		'40', #'Rain'
		'rain_showers':	'11', #'Rain showers (high cloud cover)'
		'rain_showers_hi':	'12', #'Rain showers (low cloud cover)'
		'tsra':		'38', #'Thunderstorm (high cloud cover)'
		'tsra_sct':	'39', #'Thunderstorm (medium cloud cover)'
		'tsra_hi':	'38', #'Thunderstorm (low cloud cover)'
		'tornado':	'0', #'Tornado'
		'hurricane':	'2', #'Hurricane conditions'
		'tropical_storm':	'1', #'Tropical storm conditions'
		'dust':		'19', #'Dust'
		'smoke':	'22', #'Smoke'
		'haze':		'21', #'Haze'
		'hot':		'36', #'Hot'
		'cold':		'25', #'Cold'
		'blizzard':	'15', #'Blizzard'
		'fog':		'20', #'Fog/mist'
		''		: 'na' }
MONTH_NAME_LONG = { '01' : 21,
		'02' : 22,
		'03' : 23,
		'04' : 24,
		'05' : 25,
		'06' : 26,
		'07' : 27,
		'08' : 28,
		'09' : 29,
		'10' : 30,
		'11' : 31,
		'12' : 32 
				}

MONTH_NAME_SHORT = { '01' : 51,
		'02' : 52,
		'03' : 53,
		'04' : 54,
		'05' : 55,
		'06' : 56,
		'07' : 57,
		'08' : 58,
		'09' : 59,
		'10' : 60,
		'11' : 61,
		'12' : 62 
	}

WEEK_DAY_LONG = { '0' : 17,
		'1' : 11,
		'2' : 12,
		'3' : 13,
		'4' : 14,
		'5' : 15,
		'6' : 16 
	}

WEEK_DAY_SHORT = { '0' : 47,
		'1' : 41,
		'2' : 42,
		'3' : 43,
		'4' : 44,
		'5' : 45,
		'6' : 46 
	}

FORECAST = { 'thunderstorm with light rain': LANGUAGE(32201),
		'thunderstorm with rain': LANGUAGE(32202),
		'thunderstorm with heavy rain': LANGUAGE(32203),
		'light thunderstorm': LANGUAGE(32204),
		'thunderstorm': LANGUAGE(32205),
		'heavy thunderstorm': LANGUAGE(32206),
		'ragged thunderstorm': LANGUAGE(32207),
		'thunderstorm with light drizzle': LANGUAGE(32208),
		'thunderstorm with drizzle': LANGUAGE(32209),
		'thunderstorm with heavy drizzle': LANGUAGE(32210),
		'light intensity drizzle': LANGUAGE(32211),
		'drizzle': LANGUAGE(32212),
		'heavy intensity drizzle': LANGUAGE(32213),
		'light intensity drizzle rain': LANGUAGE(32214),
		'drizzle rain': LANGUAGE(32215),
		'heavy intensity drizzle rain': LANGUAGE(32216),
		'shower rain And drizzle': LANGUAGE(32217),
		'heavy shower rain and drizzle': LANGUAGE(32218),
		'shower drizzle': LANGUAGE(32219),
		'light rain': LANGUAGE(32220),
		'moderate rain': LANGUAGE(32221),
		'heavy intensity rain': LANGUAGE(32222),
		'very heavy rain': LANGUAGE(32223),
		'extreme rain': LANGUAGE(32224),
		'freezing rain': LANGUAGE(32225),
		'light intensity shower rain': LANGUAGE(32226),
		'shower rain': LANGUAGE(32227),
		'heavy intensity shower rain': LANGUAGE(32228),
		'ragged shower rain': LANGUAGE(32229),
		'light snow': LANGUAGE(32230),
		'snow': LANGUAGE(32231),
		'heavy snow': LANGUAGE(32232),
		'sleet': LANGUAGE(32233),
		'shower sleet': LANGUAGE(32234),
		'light rain and snow': LANGUAGE(32235),
		'rain and snow': LANGUAGE(32236),
		'light shower snow': LANGUAGE(32237),
		'shower snow': LANGUAGE(32238),
		'heavy shower snow': LANGUAGE(32239),
		'mist': LANGUAGE(32240),
		'smoke': LANGUAGE(32241),
		'haze': LANGUAGE(32242),
		'sand, dust whirls': LANGUAGE(32243),
		'fog': LANGUAGE(32244),
		'sand': LANGUAGE(32245),
		'dust': LANGUAGE(32246),
		'volcanic ash': LANGUAGE(32247),
		'squalls': LANGUAGE(32248),
		'tornado': LANGUAGE(32249),
		'clear sky': LANGUAGE(32250),
		'few clouds': LANGUAGE(32251),
		'scattered clouds': LANGUAGE(32252),
		'broken clouds': LANGUAGE(32253),
		'overcast clouds': LANGUAGE(32254),
		'tornado': LANGUAGE(32255),
		'tropical storm': LANGUAGE(32256),
		'hurricane': LANGUAGE(32257),
		'cold': LANGUAGE(32258),
		'hot': LANGUAGE(32259),
		'windy': LANGUAGE(32260),
		'hail': LANGUAGE(32261),
		'calm': LANGUAGE(32262),
		'light breeze': LANGUAGE(32263),
		'gentle breeze': LANGUAGE(32264),
		'moderate breeze': LANGUAGE(32265),
		'fresh breeze': LANGUAGE(32266),
		'strong breeze': LANGUAGE(32267),
		'high wind, near gale': LANGUAGE(32268),
		'gale': LANGUAGE(32269),
		'severe gale': LANGUAGE(32270),
		'storm': LANGUAGE(32271),
		'violent storm': LANGUAGE(32272),
		'hurricane': LANGUAGE(32273),
		'clear': LANGUAGE(32274),
		'clouds': LANGUAGE(32275),
		'rain': LANGUAGE(32276) 
	}

def SPEED(mps):
	try:
		val = float(mps)
	except:
		return ''

	if SPEEDUNIT == 'km/h':
		speed = mps * 3.6
	elif SPEEDUNIT == 'm/min':
		speed = mps * 60
	elif SPEEDUNIT == 'ft/h':
		speed = mps * 11810.88
	elif SPEEDUNIT == 'ft/min':
		speed = mps * 196.84
	elif SPEEDUNIT == 'ft/s':
		speed = mps * 3.281
	elif SPEEDUNIT == 'mph':
		speed = mps * 2.237
	elif SPEEDUNIT == 'knots':
		speed = mps * 1.944
	elif SPEEDUNIT == 'Beaufort':
		speed = KPHTOBFT(mps* 3.6)
	elif SPEEDUNIT == 'inch/s':
		speed = mps * 39.37
	elif SPEEDUNIT == 'yard/s':
		speed = mps * 1.094
	elif SPEEDUNIT == 'Furlong/Fortnight':
		speed = mps * 6012.886
	else:
		speed = mps
	return str(int(round(speed)))


def FtoC(Fahrenheit):
	try:
		Celsius = (float(Fahrenheit) - 32.0) * 5.0/9.0 
		return str(int(round(Celsius))) 
	except:
		return
		
def CtoF(Celsius):
	try:
		Fahrenheit = (float(Celsius) * 9.0/5.0) + 32.0
		return str(int(round(Fahrenheit))) 
	except:
		return
def TEMP(deg):
	if TEMPUNIT == u'\N{DEGREE SIGN}'+'F':
		temp = deg * 1.8 + 32
	elif TEMPUNIT == u'K':
		temp = deg + 273.15
	elif TEMPUNIT == u'°Ré':
		temp = deg * 0.8
	elif TEMPUNIT == u'°Ra':
		temp = deg * 1.8 + 491.67
	elif TEMPUNIT == u'°Rø':
		temp = deg * 0.525 + 7.5
	elif TEMPUNIT == u'°D':
		temp = deg / -0.667 + 150
	elif TEMPUNIT == u'°N':
		temp = deg * 0.33
	else:
		temp = deg
	return str(int(round(temp)))

def WIND_DIR(deg):
	if deg >= 349 or deg <= 11:
		return 71
	elif deg >= 12 and deg <= 33:
		return 72
	elif deg >= 34 and deg <= 56:
		return 73
	elif deg >= 57 and deg <= 78:
		return 74
	elif deg >= 79 and deg <= 101:
		return 75
	elif deg >= 102 and deg <= 123:
		return 76
	elif deg >= 124 and deg <= 146:
		return 77
	elif deg >= 147 and deg <= 168:
		return 78
	elif deg >= 169 and deg <= 191:
		return 79
	elif deg >= 192 and deg <= 213:
		return 80
	elif deg >= 214 and deg <= 236:
		return 81
	elif deg >= 237 and deg <= 258:
		return 82
	elif deg >= 259 and deg <= 281:
		return 83
	elif deg >= 282 and deg <= 303:
		return 84
	elif deg >= 304 and deg <= 326:
		return 85
	elif deg >= 327 and deg <= 348:
		return 86

def KPHTOBFT(spd):
	if (spd < 1.0):
		bft = '0'
	elif (spd >= 1.0) and (spd < 5.6):
		bft = '1'
	elif (spd >= 5.6) and (spd < 12.0):
		bft = '2'
	elif (spd >= 12.0) and (spd < 20.0):
		bft = '3'
	elif (spd >= 20.0) and (spd < 29.0):
		bft = '4'
	elif (spd >= 29.0) and (spd < 39.0):
		bft = '5'
	elif (spd >= 39.0) and (spd < 50.0):
		bft = '6'
	elif (spd >= 50.0) and (spd < 62.0):
		bft = '7'
	elif (spd >= 62.0) and (spd < 75.0):
		bft = '8'
	elif (spd >= 75.0) and (spd < 89.0):
		bft = '9'
	elif (spd >= 89.0) and (spd < 103.0):
		bft = '10'
	elif (spd >= 103.0) and (spd < 118.0):
		bft = '11'
	elif (spd >= 118.0):
		bft = '12'
	else:
		bft = ''
	return bft

def FEELS_LIKE(Ts, Vs=0, Rs=0, ext=True):
	T=float(Ts)
	V=float(Vs)
	R=float(Rs)
	
	if T <= 10.0 and V >= 8.0:
		FeelsLike = WIND_CHILL(T, V)
	elif T >= 26.0:
		FeelsLike = HEAT_INDEX(T, R)
	else:
		FeelsLike = T
	if ext:
		return TEMP( FeelsLike )
	else:
		return str(int(round(FeelsLike)))

#### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
def WIND_CHILL(Ts, Vs):
	T=float(Ts)
	V=float(Vs)
	
	FeelsLike = ( 13.12 + ( 0.6215 * T ) - ( 11.37 * V**0.16 ) + ( 0.3965 * T * V**0.16 ) )
	return FeelsLike

### https://en.wikipedia.org/wiki/Heat_index
def HEAT_INDEX(Ts, Rs):
	T=float(Ts)
	R=float(Rs)
	T = T * 1.8 + 32.0 # calaculation is done in F
	FeelsLike = -42.379 + (2.04901523 * T) + (10.14333127 * R) + (-0.22475541 * T * R) + (-0.00683783 * T**2) + (-0.05481717 * R**2) + (0.00122874 * T**2 * R) + (0.00085282 * T * R**2) + (-0.00000199 * T**2 * R**2)
	FeelsLike = (FeelsLike - 32.0) / 1.8 # convert to C
	return FeelsLike

#### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
def DEW_POINT(Tc=0, RH=93.0, ext=True, minRH=( 0, 0.075 )[ 0 ]):
	Es = 6.11 * 10.0**( 7.5 * Tc / ( 237.7 + Tc ) )
	RH = RH or minRH
	E = ( RH * Es ) / 100
	try:
		DewPoint = ( -430.22 + 237.7 * math.log( E ) ) / ( -math.log( E ) + 19.08 )
	except ValueError:
		DewPoint = 0
	if ext:
		return TEMP( DewPoint )
	else:
		return str(int(round(DewPoint)))


## a couple functions from itertools
def repeat_x(object_x, times=None):
	# repeat(10, 3) --> 10 10 10
	if times is None:
		while True:
			yield object_x
	else:
		for i in range(times):
			yield object_x

def zip_x(fill, *args):
	# zip_longest('ABCD', 'xy', fillvalue='-') --> Ax By C- D-
	iterators = [iter(it) for it in args]
	num_active = len(iterators)
	if not num_active:
		return
	while True:
		values = []
		for i, it in enumerate(iterators):
			try:
				value = next(it)
			except StopIteration:
				num_active -= 1
				if not num_active:
					return
				iterators[i] = repeat_x(fill)
				value = fill
			values.append(value)
		yield tuple(values)

def get_timestamp(datestr):
	#"2019-04-29T16:00:00-04:00"
	#iso_fmt = '%Y-%m-%dT%H:%M:%S%z'
	datestamp=parse(datestr)
	return time.mktime(datestamp.timetuple())


def convert_date(stamp):
	if str(stamp).startswith('-'):
		return ''
	date_time = time.localtime(stamp)
	if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
		localdate = time.strftime('%d-%m-%Y', date_time)
	elif DATEFORMAT[1] == 'm' or DATEFORMAT[0] == 'M':
		localdate = time.strftime('%m-%d-%Y', date_time)
	else:
		localdate = time.strftime('%Y-%m-%d', date_time)

	if TIMEFORMAT != '/':
		localtime = time.strftime('%I:%M%p', date_time)
	else:
		localtime = time.strftime('%H:%M', date_time)
	return localtime + '	' + localdate

def get_time(stamp):
	date_time = time.localtime(stamp)
	if TIMEFORMAT != '/':
		localtime = time.strftime('%I:%M%p', date_time)
	else:
		localtime = time.strftime('%H:%M', date_time)
	return localtime

def get_weekday(stamp, form):
	date_time = time.localtime(stamp)
	weekday = time.strftime('%w', date_time)
	if form == 's':
		return xbmc.getLocalizedString(WEEK_DAY_SHORT[weekday])
	elif form == 'l':
		return xbmc.getLocalizedString(WEEK_DAY_LONG[weekday])
	else:
		return int(weekday)

def get_month(stamp, form):
	date_time = time.localtime(stamp)
	month = time.strftime('%m', date_time)
	day = time.strftime('%d', date_time)
	if form == 'ds':
		label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_SHORT[month])
	elif form == 'dl':
		label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_LONG[month])
	elif form == 'ms':
		label = xbmc.getLocalizedString(MONTH_NAME_SHORT[month]) + ' ' + day
	elif form == 'ml':
		label = xbmc.getLocalizedString(MONTH_NAME_LONG[month]) + ' ' + day
	return label

# Satellite Imagery paths

MAPSECTORS = {
	"conus-e":	{"name":LANGUAGE(32360),"path":"GOES16/ABI/CONUS/%s/1250x750.jpg"},
	"conus-w":	{"name":LANGUAGE(32361),"path":"GOES17/ABI/CONUS/%s/1250x750.jpg"},
	"glm-e":	{"name":LANGUAGE(32362),"path":"GOES16/GLM/CONUS/EXTENT/1250x750.jpg"},
	"glm-w":	{"name":LANGUAGE(32363),"path":"GOES17/GLM/CONUS/EXTENT/1250x750.jpg"},
	"ak":		{"name":LANGUAGE(32364),"path":"GOES17/ABI/SECTOR/ak/%s/1000x1000.jpg"},
	"cak":		{"name":LANGUAGE(32365),"path":"GOES17/ABI/SECTOR/cak/%s/1200x1200.jpg"},
	"sea":		{"name":LANGUAGE(32366),"path":"GOES17/ABI/SECTOR/sea/%s/1200x1200.jpg"},
	"np":		{"name":LANGUAGE(32367),"path":"GOES17/ABI/SECTOR/np/%s/900x540.jpg"},
	"wus":		{"name":LANGUAGE(32368),"path":"GOES17/ABI/SECTOR/wus/%s/1000x1000.jpg"},
	"pnw-w":	{"name":LANGUAGE(32369),"path":"GOES17/ABI/SECTOR/pnw/%s/1200x1200.jpg"},
	"pnw-e":	{"name":LANGUAGE(32370),"path":"GOES16/ABI/SECTOR/pnw/%s/1200x1200.jpg"},
	"psw-w":	{"name":LANGUAGE(32371),"path":"GOES17/ABI/SECTOR/psw/%s/1200x1200.jpg"},
	"psw-e":	{"name":LANGUAGE(32371),"path":"GOES16/ABI/SECTOR/psw/%s/1200x1200.jpg"},
	"nr":		{"name":LANGUAGE(32373),"path":"GOES16/ABI/SECTOR/nr/%s/1200x1200.jpg"},
	"sr":		{"name":LANGUAGE(32374),"path":"GOES16/ABI/SECTOR/sr/%s/1200x1200.jpg"},
	"sp":		{"name":LANGUAGE(32375),"path":"GOES16/ABI/SECTOR/sp/%s/1200x1200.jpg"},
	"umv":		{"name":LANGUAGE(32376),"path":"GOES16/ABI/SECTOR/umv/%s/1200x1200.jpg"},
	"smv":		{"name":LANGUAGE(32377),"path":"GOES16/ABI/SECTOR/smv/%s/1200x1200.jpg"},
	"can":		{"name":LANGUAGE(32378),"path":"GOES16/ABI/SECTOR/can/%s/1125x560.jpg"},
	"cgl":		{"name":LANGUAGE(32379),"path":"GOES16/ABI/SECTOR/cgl/%s/1200x1200.jpg"},
	"eus":		{"name":LANGUAGE(32380),"path":"GOES16/ABI/SECTOR/eus/%s/1000x1000.jpg"},
	"ne":		{"name":LANGUAGE(32381),"path":"GOES16/ABI/SECTOR/ne/%s/1200x1200.jpg"},
	"na":		{"name":LANGUAGE(32382),"path":"GOES16/ABI/SECTOR/na/%s/900x540.jpg"},
	"se":		{"name":LANGUAGE(32383),"path":"GOES16/ABI/SECTOR/se/%s/1200x1200.jpg"},
	"car":		{"name":LANGUAGE(32384),"path":"GOES16/ABI/SECTOR/car/%s/1000x1000.jpg"},
	"pr":		{"name":LANGUAGE(32385),"path":"GOES16/ABI/SECTOR/pr/%s/1200x1200.jpg"},
	"gm":		{"name":LANGUAGE(32386),"path":"GOES16/ABI/SECTOR/gm/%s/1000x1000.jpg"},
	"taw":		{"name":LANGUAGE(32387),"path":"GOES16/ABI/SECTOR/taw/%s/900x540.jpg"},
	"mex":		{"name":LANGUAGE(32388),"path":"GOES16/ABI/SECTOR/mex/%s/1000x1000.jpg"},
	"hi":		{"name":LANGUAGE(32389),"path":"GOES17/ABI/SECTOR/hi/%s/1200x1200.jpg"},
	"tpw":		{"name":LANGUAGE(32390),"path":"GOES17/ABI/SECTOR/tpw/%s/900x540.jpg"},
	"tsp":		{"name":LANGUAGE(32391),"path":"GOES17/ABI/SECTOR/tsp/%s/900x540.jpg"},
	"eep":		{"name":LANGUAGE(32392),"path":"GOES16/ABI/SECTOR/eep/%s/900x540.jpg"},
	"cam":		{"name":LANGUAGE(32393),"path":"GOES16/ABI/SECTOR/cam/%s/1000x1000.jpg"},
	"nsa":		{"name":LANGUAGE(32394),"path":"GOES16/ABI/SECTOR/nsa/%s/900x540.jpg"},
	"ssa":		{"name":LANGUAGE(32395),"path":"GOES16/ABI/SECTOR/ssa/%s/900x540.jpg"}
	}


MAPTYPES = {
	"GEOCOLOR":	LANGUAGE(32400),
	"EXTENT":	LANGUAGE(32401),
	"Sandwich":	LANGUAGE(32402),
	"AirMass":	LANGUAGE(32404),
	"DayCloudPhase":LANGUAGE(32405),   
	"NightMicrophysics":LANGUAGE(32406),  
	"DMW":		LANGUAGE(32407),
	"Dust":		LANGUAGE(32408),
	"01":		LANGUAGE(32409),
	"02":		LANGUAGE(32410),
	"03":		LANGUAGE(32411),
	"04":		LANGUAGE(32412), 
	"05":		LANGUAGE(32413), 
	"06":		LANGUAGE(32414), 
	"07":		LANGUAGE(32415), 
	"08":		LANGUAGE(32416),
	"09":		LANGUAGE(32417),
	"10":		LANGUAGE(32418),
	"11":		LANGUAGE(32419),
	"12":		LANGUAGE(32420),
	"13":		LANGUAGE(32421),
	"14":		LANGUAGE(32422),
	"15":		LANGUAGE(32423),
	"16":		LANGUAGE(32424)		
	}


