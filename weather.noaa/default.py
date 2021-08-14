# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()

import os, glob, sys, time
import xbmc, xbmcgui, xbmcvfs, xbmcaddon

from resources.lib.utils import FtoC, CtoF, log, ADDON, LANGUAGE,MAPSECTORS,MAPTYPES
from resources.lib.utils import WEATHER_CODES, FORECAST, FEELS_LIKE, SPEED, WIND_DIR, SPEEDUNIT, zip_x 
from resources.lib.utils import get_url_JSON, get_url_image 
from resources.lib.utils import get_month, get_timestamp, get_weekday, get_time


WEATHER_WINDOW  = xbmcgui.Window(12600)
WEATHER_ICON	= xbmcvfs.translatePath('%s.png')
DATEFORMAT	= xbmc.getRegion('dateshort')
TIMEFORMAT	= xbmc.getRegion('meridiem')
MAXDAYS		= 10
TEMPUNIT	= xbmc.getRegion('tempunit')

def set_property(name, value):
	WEATHER_WINDOW.setProperty(name, value)

def clear_property(name):
	WEATHER_WINDOW.clearProperty(name)

def clear():
	set_property('Current.Condition'	, 'N/A')
	set_property('Current.Temperature'	, '0')
	set_property('Current.Wind'		, '0')
	set_property('Current.WindDirection'	, 'N/A')
	set_property('Current.Humidity'		, '0')
	set_property('Current.FeelsLike'	, '0')
	set_property('Current.UVIndex'		, '0')
	set_property('Current.DewPoint'		, '0')
	set_property('Current.OutlookIcon'	, 'na.png')
	set_property('Current.FanartCode'	, 'na')
	for count in range (0, MAXDAYS+1):
		set_property('Day%i.Title'	% count, 'N/A')
		set_property('Day%i.HighTemp'	% count, '0')
		set_property('Day%i.LowTemp'	% count, '0')
		set_property('Day%i.Outlook'	% count, 'N/A')
		set_property('Day%i.OutlookIcon' % count, 'na.png')
		set_property('Day%i.FanartCode'	% count, 'na')

def refresh_locations():
	locations = 0
	for count in range(1, 6):
		LatLong = ADDON.getSetting('Location%sLatLong' % count)
		loc_name = ADDON.getSetting('Location%s' % count)
		if LatLong:
			locations += 1
			if not loc_name:
				loc_name = 'Location %s' % count
			set_property('Location%s' % count, loc_name)

		else:
			set_property('Location%s' % count, '')

		#set_property('Location%s' % count, loc_name)

	set_property('Locations', str(locations))
	log('available locations: %s' % str(locations))

def get_initial(loc):
	url = 'https://api.weather.gov/points/%s' % loc
	log("url:"+url)
	responsedata=get_url_JSON(url)	
	return responsedata
	
def code_from_icon(icon):
	if icon:
		if '?' in icon:
			icon=icon.rsplit('?', 1)[0]
		if '/' in icon:	
			code=icon.rsplit('/',1)[1]
		else:
			code=icon
		thing=code.split(",")
		if len(thing) > 1:
			rain=thing[1]
			code=thing[0]
			return code, rain
		else:
			code=thing[0]
			return code, ''
		

########################################################################################
##  Dialog for getting Latitude and Longitude
########################################################################################

def enterLocation(num):	
##	log("argument: %s" % (sys.argv[1]))
	text = ADDON.getSetting("Location"+num+"LatLong")
	Latitude=""
	Longitude=""
	if text and "," in text:
		thing=text.split(",")
		Latitude=thing[0]
		Longitude=thing[1]

	dialog = xbmcgui.Dialog()
	
	Latitude=dialog.input(LANGUAGE(32341),defaultt=Latitude,type=xbmcgui.INPUT_ALPHANUM)
	
#	xbmc.Keyboard(line, heading, hidden)
#	keyboard = xbmc.Keyboard(Latitude, 32341, False)
#	keyboard.doModal()
#	if (keyboard.isConfirmed()):
#		Latitude= keyboard.getText()
	if not Latitude:
		ADDON.setSetting("Location"+num+"LatLong","")
		return False

	Longitude=dialog.input(heading=LANGUAGE(32342),defaultt=Longitude,type=xbmcgui.INPUT_ALPHANUM)

#	keyboard = xbmc.Keyboard(Longitude, 32342, False)
#	keyboard.doModal()
#	if (keyboard.isConfirmed()):
#		Longitude= keyboard.getText()
	if not Longitude:
		ADDON.setSetting("Location"+num+"LatLong","")
		return False
	LatLong=Latitude+","+Longitude
	ADDON.setSetting("Location"+num+"LatLong",LatLong)
	fetchLocation(num,LatLong)
	return

########################################################################################
##  fetches location data (weather grid point, station, etc, for lattitude,logngitude
########################################################################################

def fetchLocation(num,LatLong):
	prefix="Location"+num
	log('searching for location: %s' % LatLong)
	data = get_initial(LatLong)
	log('location data: %s' % data)
	if not data:
		log('failed to retrieve location data')
		return None
	if data and 'properties' in data:

		city	=	data['properties']['relativeLocation']['properties']['city']
		state =		data['properties']['relativeLocation']['properties']['state']
		locationName=	city+", "+state
		ADDON.setSetting(prefix, locationName)

		gridX=data['properties']['gridX']
		ADDON.setSetting(prefix+'gridX',str(gridX))
		
		gridY=data['properties']['gridY']
		ADDON.setSetting(prefix+'gridY',str(gridY))
		
		cwa=data['properties']['cwa']
		ADDON.setSetting(prefix+'cwa',	cwa)

		forecastZone=data['properties']['forecastZone']
		zone=forecastZone.rsplit('/',1)[1]
		ADDON.setSetting(prefix+'Zone',	zone)

		forecastCounty=data['properties']['county']
		county=forecastCounty.rsplit('/',1)[1]
		ADDON.setSetting(prefix+'County', county)
		
		forecastGridData_url =	data['properties']['forecastGridData']
		ADDON.setSetting(prefix+'forecastGrid_url', forecastGridData_url)

		forecastHourly_url =	data['properties']['forecastHourly']
		ADDON.setSetting(prefix+'forecastHourly_url', forecastHourly_url)

		forecast_url =		data['properties']['forecast']
		ADDON.setSetting(prefix+'forecast_url',	forecast_url)

		radarStation =		data['properties']['radarStation']
		ADDON.setSetting(prefix+'radarStation',	radarStation)
		

		stations_url =	data['properties']['observationStations']
		odata = get_url_JSON(stations_url)

		if odata and 'features' in odata:
			stations={}
			stationlist=[]
			
			for count,item in enumerate(odata['features']):
				stationId=item['properties']['stationIdentifier']
				stationName=item['properties']['name']
				stationlist.append(stationName)
				stations[stationName]=stationId

			dialog = xbmcgui.Dialog()
			i=dialog.select(LANGUAGE(32331),stationlist)
			# clean up reference to dialog object
			del dialog


			ADDON.setSetting(prefix+'Station',stations[stationlist[i]])
			ADDON.setSetting(prefix+'StationName',stationlist[i])

		


########################################################################################
##  fetches daily weather data
########################################################################################

def fetchDaily(num):

	url=ADDON.getSetting('Location'+str(num)+'forecast_url')		
	if 'F' in TEMPUNIT:
		url="%s?units=us" % url		
	elif 'C' in TEMPUNIT:
		url="%s?units=si" % url		

	log('forecast url: %s' % url)

	daily_weather = get_url_JSON(url)

	if daily_weather and 'properties' in daily_weather:
		data=daily_weather['properties']
	else:
		#api.weather.gov is acting up, so fall back to alternate api
		xbmc.log('failed to find weather data from : %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % daily_weather,level=xbmc.LOGERROR)
		return fetchAltDaily(num)

	for count, item in enumerate(data['periods']):
		icon = item['icon']
		#https://api.weather.gov/icons/land/night/ovc?size=small
		if icon and '?' in icon:
			icon=icon.rsplit('?', 1)[0]
		code, rain=code_from_icon(icon)

		weathercode = WEATHER_CODES.get(code)
		starttime=item['startTime']
		startstamp=get_timestamp(starttime)
		set_property('Day%i.isDaytime'		% (count),str(item['isDaytime']))
		set_property('Day%i.Title'		% (count), item['name'])

		if item['isDaytime'] == True:
			##Since we passed units into api, we may need to convert to C, or may not
			if 'F' in TEMPUNIT:
				set_property('Day%i.HighTemp'	% (count), str(FtoC(item['temperature'])))
				set_property('Day%i.LowTemp'	% (count), str(FtoC(item['temperature'])))
			elif 'C' in TEMPUNIT:
				set_property('Day%i.HighTemp'	% (count), str(item['temperature']))
				set_property('Day%i.LowTemp'	% (count), str(item['temperature']))
		if item['isDaytime'] == False:
			if 'F' in TEMPUNIT:
				set_property('Day%i.HighTemp'	% (count), str(FtoC(item['temperature'])))
				set_property('Day%i.LowTemp'	% (count), str(FtoC(item['temperature'])))
			elif 'C' in TEMPUNIT:
				set_property('Day%i.HighTemp'	% (count), str(item['temperature']))
				set_property('Day%i.LowTemp'	% (count), str(item['temperature']))
		set_property('Day%i.Outlook'		% (count), item['shortForecast'])
		set_property('Day%i.OutlookIcon'	% (count), weathercode)
		set_property('Day%i.RemoteIcon'		% (count), icon)

		# NOTE: Day props are 0 based, but Daily/Hourly are 1 based
		set_property('Daily.%i.isDaytime'	% (count+1),str(item['isDaytime']))
		set_property('Daily.%i.Outlook'		% (count+1), item['detailedForecast'])
		set_property('Daily.%i.ShortOutlook'	% (count+1), item['shortForecast'])
		
		set_property('Daily.%i.RemoteIcon'	% (count+1), icon)
		set_property('Daily.%i.OutlookIcon'	% (count+1), WEATHER_ICON % weathercode)
		set_property('Daily.%i.FanartCode'	% (count+1), weathercode)
		set_property('Daily.%i.WindDirection'	% (count+1), item['windDirection'])
		set_property('Daily.%i.WindSpeed'	% (count+1), item['windSpeed'])

		if item['isDaytime'] == True:
			set_property('Daily.%i.LongDay'		% (count+1), item['name'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (d)")
				#set_property('Daily.%i.TempDay'		% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
				#set_property('Daily.%i.HighTemperature'	% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))

			## we passed units to api, so we got back C or F, so don't need to convert
			set_property('Daily.%i.TempDay'		% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			set_property('Daily.%i.HighTemperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			#if 'F' in TEMPUNIT:
			#	set_property('Daily.%i.TempDay'		% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			#	set_property('Daily.%i.HighTemperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			#elif 'C' in TEMPUNIT:
			#	set_property('Daily.%i.TempDay'		% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
			#	set_property('Daily.%i.HighTemperature'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
			set_property('Daily.%i.TempNight'	% (count+1), '')
			set_property('Daily.%i.LowTemperature'	% (count+1), '')

		if item['isDaytime'] == False:
			set_property('Daily.%i.LongDay'		% (count+1), item['name'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (n)")

			set_property('Daily.%i.TempDay'		% (count+1), '')
			set_property('Daily.%i.HighTemperature'	% (count+1), '')
			## we passed units to api, so we got back C or F, so don't need to convert
			#if 'F' in TEMPUNIT:
			set_property('Daily.%i.TempNight'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			set_property('Daily.%i.LowTemperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			#elif 'C' in TEMPUNIT:
			#	set_property('Daily.%i.TempNight'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
			#	set_property('Daily.%i.LowTemperature'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))

		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))
		
		if rain:
			set_property('Daily.%i.Precipitation'	% (count+1), rain + '%')
		else:
			set_property('Daily.%i.Precipitation'	% (count+1), '')



########################################################################################
##  fetches daily weather data using alternative api endpoint
########################################################################################


def fetchAltDaily(num):

	latlong=ADDON.getSetting('Location'+str(num)+"LatLong")
	latitude =latlong.rsplit(',',1)[0]
	longitude=latlong.rsplit(',',1)[1]

	url="https://forecast.weather.gov/MapClick.php?lon="+longitude+"&lat="+latitude+"&FcstType=json"
	log('forecast url: %s' % url)

	daily_weather = get_url_JSON(url)

	if daily_weather and 'data' in daily_weather:

		dailydata=[
			{"startPeriodName": a,
			 "startValidTime": b,
			 "tempLabel": c,
			 "temperature": d,
			 "pop": e,
			 "weather": f,
			 "iconLink": g,
			 "hazard": h,
			 "hazardUrl": i,
			 "text": j
			} 
			for a,b,c,d,e,f,g,h,i,j in zip_x(None,
				daily_weather['time']['startPeriodName'], 
				daily_weather['time']['startValidTime'],
				daily_weather['time']['tempLabel'],
				daily_weather['data']['temperature'],
				daily_weather['data']['pop'],
				daily_weather['data']['weather'],
				daily_weather['data']['iconLink'],
				daily_weather['data']['hazard'],
				daily_weather['data']['hazardUrl'],
				daily_weather['data']['text']				
			)]

	else:
		xbmc.log('failed to retrieve weather data from : %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % daily_weather,level=xbmc.LOGERROR)
		return None

	for count, item in enumerate(dailydata):
		icon = item['iconLink']

		#https://api.weather.gov/icons/land/night/ovc?size=small
		code, rain=code_from_icon(icon)
		weathercode = WEATHER_CODES.get(code)

		starttime=item['startValidTime']
		startstamp=get_timestamp(starttime)
		set_property('Day%i.Title'		% (count), item['startPeriodName'])

		set_property('Day%i.Outlook'		% (count), item['weather'])
		set_property('Day%i.Details'		% (count), item['text'])
		set_property('Day%i.OutlookIcon'	% (count), weathercode)
		set_property('Day%i.RemoteIcon'		% (count), icon)

		# NOTE: Day props are 0 based, but Daily/Hourly are 1 based
		set_property('Daily.%i.Outlook'		% (count+1), item['text'])
		set_property('Daily.%i.ShortOutlook'	% (count+1), item['weather'])
		
		set_property('Daily.%i.RemoteIcon'	% (count+1), icon)
		set_property('Daily.%i.OutlookIcon'	% (count+1), WEATHER_ICON % weathercode)
		set_property('Daily.%i.FanartCode'	% (count+1), weathercode)

		if item['tempLabel'] == 'High':
			set_property('Daily.%i.LongDay'		% (count+1), item['startPeriodName'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (d)")

			if 'F' in TEMPUNIT:
				set_property('Daily.%i.TempDay'		% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
				set_property('Daily.%i.HighTemperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			elif 'C' in TEMPUNIT:
				set_property('Daily.%i.TempDay'		% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
				set_property('Daily.%i.HighTemperature'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
#			set_property('Daily.%i.TempDay'		% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
#			set_property('Daily.%i.HighTemperature'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
			set_property('Daily.%i.TempNight'	% (count+1), '')
			set_property('Daily.%i.LowTemperature'	% (count+1), '')

		if item['tempLabel'] == 'Low':
			set_property('Daily.%i.LongDay'		% (count+1), item['startPeriodName'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (n)")
			set_property('Daily.%i.TempDay'		% (count+1), '')
			set_property('Daily.%i.HighTemperature'	% (count+1), '')
			if 'F' in TEMPUNIT:
				set_property('Daily.%i.TempNight'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
				set_property('Daily.%i.LowTemperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
			elif 'C' in TEMPUNIT:
				set_property('Daily.%i.TempNight'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
				set_property('Daily.%i.LowTemperature'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
			#set_property('Daily.%i.TempNight'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
			#set_property('Daily.%i.LowTemperature'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))

		rain=str(item['pop'])
		if rain:
			set_property('Daily.%i.Precipitation'	% (count+1), rain + '%')
		else:
			set_property('Daily.%i.Precipitation'	% (count+1), '')
			



	if daily_weather and 'currentobservation' in daily_weather:
		data=daily_weather['currentobservation']
		icon = "http://forecast.weather.gov/newimages/large/%s" % data.get('Weatherimage')
		code, rain=code_from_icon(icon)
		weathercode = WEATHER_CODES.get(code)
		set_property('Current.Location', data.get('name'))
		set_property('Current.RemoteIcon',icon) 
		set_property('Current.OutlookIcon', '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
		set_property('Current.FanartCode', weathercode)
		set_property('Current.Condition', FORECAST.get(data.get('Weather'), data.get('Weather')))
		set_property('Current.Humidity'	, data.get('Relh'))
		set_property('Current.DewPoint', FtoC(data.get('Dewp')))
				
		try:
			temp=data.get('Temp')
			set_property('Current.Temperature',FtoC(temp)) # api values are in C
		except:
			set_property('Current.Temperature','') 

		try:
			set_property('Current.Wind', str(round(float(data.get('Winds'))*1.609298167)))
		except:
			set_property('Current.Wind','')

		try:
			set_property('Current.WindDirection', xbmc.getLocalizedString(WIND_DIR(int(data.get('Windd')))))
		except:
			set_property('Current.WindDirection', '')

		try:
			set_property('Current.WindGust'	, SPEED(float(data.get('Gust'))/2.237) + SPEEDUNIT)
		except:
			set_property('Current.WindGust'	, '')

		if rain:
			set_property('Current.ChancePrecipitaion', str(rain)+'%');
		else :
			set_property('Current.ChancePrecipitaion'		, '');

		try:
			set_property('Current.FeelsLike', FEELS_LIKE( FtoC(data.get('Temp')), float(data.get('Winds'))/2.237, int(data.get('Relh')), False))
		except:
			set_property('Current.FeelsLike', '')


		


########################################################################################
##  fetches current weather info for location
########################################################################################

def fetchCurrent(num):
	station=ADDON.getSetting('Location'+str(num)+'Station')
	url="https://api.weather.gov/stations/%s/observations/latest" %station	
	current=get_url_JSON(url)
	if current and 'properties' in current:
		data=current['properties']
	else:
		xbmc.log('failed to find weather data from : %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % current,level=xbmc.LOGERROR)
		return
	
	icon = data['icon']
	#https://api.weather.gov/icons/land/night/ovc?size=small
	code=''
	rain=''
	if icon:
		if '?' in icon:
			icon=icon.rsplit('?', 1)[0]
		code, rain=code_from_icon(icon)
		weathercode = WEATHER_CODES.get(code)
		set_property('Current.RemoteIcon',icon) 
		set_property('Current.OutlookIcon', '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
		set_property('Current.FanartCode', weathercode)
	set_property('Current.Condition', FORECAST.get(data.get('textDescription'), data.get('textDescription')))
	try:
		set_property('Current.Humidity'	, str(round(data.get('relativeHumidity').get('value'))))
	except:
		set_property('Current.Humidity'		, '')
				
	try:
		temp=int(round(data.get('temperature').get('value')))
		set_property('Current.Temperature',str(temp)) # api values are in C
	except:
		set_property('Current.Temperature','') 
	try:
		set_property('Current.Wind', str(int(round(data.get('windSpeed').get('value')))))
	except:
		set_property('Current.Wind','')

	try:
		set_property('Current.WindDirection', xbmc.getLocalizedString(WIND_DIR(int(round(data.get('windDirection').get('value'))))))
	except:
		set_property('Current.WindDirection', '')

	if rain:
		set_property('Current.ChancePrecipitaion', str(rain)+'%');
	else :
		set_property('Current.ChancePrecipitaion'		, '');

	try:
		set_property('Current.FeelsLike', FEELS_LIKE(data.get('temperature').get('value'), float(data.get('windSpeed').get('value'))/3.6, data.get('relativeHumidity').get('value'), False))
	except:
		set_property('Current.FeelsLike', '')

	try:
		temp=int(round(data.get('dewpoint').get('value',0)))
		set_property('Current.DewPoint', str(temp)) # api values are in C
	except:
		set_property('Current.DewPoint', '') 



## extended properties

	try:
		set_property('Current.WindGust'	, SPEED(float(data.get('windGust').get('value',0))/3.6) + SPEEDUNIT)
	except:
		set_property('Current.WindGust'	, '')


########################################################################################
##  fetches any weather alerts for location
########################################################################################


def fetchWeatherAlerts(num):

	### we could fetch alerts for either 'County', or 'Zone'
	#https://api.weather.gov/alerts/active/zone/CTZ006
	#https://api.weather.gov/alerts/active/zone/CTC009
	##https://api.weather.gov/alerts/active?status=actual&point=%7Blat%7D,%7Blong%7D

	#for now, lets use the point alert lookup, as suggested by the weather api team
	
	##a_zone=ADDON.getSetting('Location'+str(num)+'County')
	##url="https://api.weather.gov/alerts/active/zone/%s" %a_zone	
	
	# we are storing lat,long as comma separated already, so that is convienent for us and we can just drop it into the url
	latlong=ADDON.getSetting('Location'+str(num)+'LatLong')
	url="https://api.weather.gov/alerts/active?status=actual&point=%s" % (latlong)

	alerts=get_url_JSON(url)
	# if we have a valid response then clear our current alerts
	if alerts and 'features' in alerts:
		for count in range (1, 10):
			clear_property('Alerts.%i.event' % (count))	
	else:
		xbmc.log('failed to get proper alert response %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % alerts,level=xbmc.LOGDEBUG)
		return
		
	if 'features' in alerts and alerts['features']:
		data=alerts['features']
		set_property('Alerts.IsFetched'	, 'true')
	else:
		clear_property('Alerts.IsFetched')
		xbmc.log('No current weather alerts from  %s' % url,level=xbmc.LOGDEBUG)
		return
	
	for count, item in enumerate(data):
		
		thisdata=item['properties']
		set_property('Alerts.%i.status'		% (count+1), str(thisdata['status']))	
		set_property('Alerts.%i.messageType'	% (count+1), str(thisdata['messageType']))	
		set_property('Alerts.%i.category'	% (count+1), str(thisdata['category']))	
		set_property('Alerts.%i.severity'	% (count+1), str(thisdata['severity']))	
		set_property('Alerts.%i.certainty'	% (count+1), str(thisdata['certainty']))	
		set_property('Alerts.%i.urgency'	% (count+1), str(thisdata['urgency']))	
		set_property('Alerts.%i.event'		% (count+1), str(thisdata['event']))	
		set_property('Alerts.%i.headline'	% (count+1), str(thisdata['headline']))	
		set_property('Alerts.%i.description'	% (count+1), str(thisdata['description']))	
		set_property('Alerts.%i.instruction'	% (count+1), str(thisdata['instruction']))	
		set_property('Alerts.%i.response'	% (count+1), str(thisdata['response']))	



########################################################################################
##  fetches hourly weather data
########################################################################################

def fetchHourly(num):

	url=ADDON.getSetting('Location'+str(num)+'forecastHourly_url')		
	if 'F' in TEMPUNIT:
		url="%s?units=us" % url		
	elif 'C' in TEMPUNIT:
		url="%s?units=si" % url		

		
		
	hourly_weather = get_url_JSON(url)
	if hourly_weather and 'properties' in hourly_weather:
		data=hourly_weather['properties']
	else:
		xbmc.log('failed to find proper hourly weather from %s' % url,level=xbmc.LOGERROR)
		return

# extended properties
	for count, item in enumerate(data['periods']):
		
		icon=item['icon']
		#https://api.weather.gov/icons/land/night/ovc?size=small
		if icon:
			if '?' in icon:
				icon=icon.rsplit('?', 1)[0]
			code, rain=code_from_icon(icon)
		set_property('Hourly.%i.RemoteIcon'	% (count+1), icon)	
		
		weathercode = WEATHER_CODES.get(code)
		starttime=item['startTime']
		startstamp=get_timestamp(starttime)
		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Hourly.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Hourly.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Hourly.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Hourly.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))
	
		set_property('Hourly.%i.Time'			% (count+1), get_time(startstamp))
		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Hourly.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Hourly.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Hourly.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Hourly.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))
		outlook=FORECAST.get(item['detailedForecast'],item['detailedForecast'])
		if len(outlook) < 3 :
			outlook=FORECAST.get(item['shortForecast'],item['shortForecast'])
		set_property('Hourly.%i.Outlook'		% (count+1),	outlook)
		set_property('Hourly.%i.ShortOutlook'	% (count+1), FORECAST.get(item['shortForecast'], item['shortForecast']))
		set_property('Hourly.%i.OutlookIcon'	% (count+1), WEATHER_ICON % weathercode)
		set_property('Hourly.%i.FanartCode'	% (count+1), weathercode)
		#set_property('Hourly.%i.Humidity'		% (count+1), str(item['main'].get('humidity','')) + '%')
		set_property('Hourly.%i.WindDirection'	% (count+1), item['windDirection'])
		set_property('Hourly.%i.WindSpeed'	% (count+1), item['windSpeed'])

		#set_property('Hourly.%i.Temperature'		% (count+1),	str(item['temperature'])+u'\N{DEGREE SIGN}'+item['temperatureUnit'])

		## we passed units to api, so we got back C or F, so don't need to convert
		set_property('Hourly.%i.Temperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
		##if 'F' in TEMPUNIT:
		##	set_property('Hourly.%i.Temperature'	% (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
		##elif 'C' in TEMPUNIT:
		##	set_property('Hourly.%i.Temperature'	% (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
	

		if rain:
			set_property('Hourly.%i.Precipitation'	% (count+1), rain + '%')
			set_property('Hourly.%i.ChancePrecipitation'	% (count+1), rain + '%')
		else:
			set_property('Hourly.%i.Precipitation'	% (count+1), '')
			set_property('Hourly.%i.ChancePrecipitation'	% (count+1), '')
	count = 1


########################################################################################
##  Grabs map selection from user in settings
########################################################################################

def mapSettings(mapid):
	s_sel = ADDON.getSetting(mapid+"Sector")
	t_sel   = ADDON.getSetting(mapid+"Type")

	# convert our map data into matching arrays to pass into dialog
	s_keys = []
	s_values= []

	#1st option is blank for removing map
	s_keys.append("")
	s_values.append("")

	for key,value in MAPSECTORS.items():
		s_keys.append(key)
		s_values.append(value['name'])		

	t_keys = []
	t_values= []
	for key,value in MAPTYPES.items():
		t_keys.append(key)
		t_values.append(value)		

	dialog = xbmcgui.Dialog()

	# grab index of current region, and pass in as default to dialog
	si=0
	try:
		si=s_keys.index(s_sel.lower())
	except:
		#ignore if we did not find
		si=0
	si=dialog.select(LANGUAGE(32349),s_values,0,si)
	s_sel=s_keys[si]
	ADDON.setSetting(mapid+"Sector",s_sel)

	if si > 0:
		ti=0	
		try:
			ti=t_keys.index(t_sel)
		except:
			ti=0	
		ti=dialog.select(LANGUAGE(32350), t_values,0,ti)
		t_sel=t_keys[ti]
		ADDON.setSetting(mapid+"Type",t_keys[ti])
		ADDON.setSetting(mapid+"Label",MAPSECTORS[s_sel]['name']+":"+MAPTYPES[t_sel])
		ADDON.setSetting(mapid+"Select",MAPSECTORS[s_sel]['name']+":"+MAPTYPES[t_sel])
	else:
		ADDON.setSetting(mapid+"Label","")
		ADDON.setSetting(mapid+"Select","")
	
	# clean up referenced dialog object	
	del dialog
	


########################################################################################
##  Main Kodi entry point
########################################################################################

class MyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)

log('version %s started with argv: %s' % (ADDON.getAddonInfo('version'), sys.argv[1]))

MONITOR = MyMonitor()
set_property('Forecast.IsFetched'	, 'true')
set_property('Current.IsFetched'	, 'true')
set_property('Today.IsFetched'		, '')
set_property('Daily.IsFetched'		, 'true')
set_property('Detailed.IsFetched'	, 'true')
set_property('Weekend.IsFetched'	, '')
set_property('36Hour.IsFetched'		, '')
set_property('Hourly.IsFetched'		, 'true')
set_property('NOAA.IsFetched'		, 'true')
set_property('WeatherProvider'		, 'NOAA')
set_property('WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(ADDON.getAddonInfo('path'), 'resources', 'media', 'skin-banner.png')))


if sys.argv[1].startswith('EnterLocation'):
	num=sys.argv[2]
	enterLocation(num)

if sys.argv[1].startswith('FetchLocation'):
	num=sys.argv[2]
	LatLong = ADDON.getSetting("Location"+num+"LatLong")
	if not LatLong:
		enterLocation(num)
	elif LatLong:
		fetchLocation(num,LatLong)

elif sys.argv[1].startswith('Map'):

	mapSettings(sys.argv[1])

else:

	num=sys.argv[1]
	LatLong = ADDON.getSetting('Location%sLatLong' % num)
	
	station=ADDON.getSetting('Location'+str(num)+'Station')
	if station == '' :
		log("calling location with %s" % (LatLong))
		fetchLocation(str(num),LatLong)

	refresh_locations()

	LatLong = ADDON.getSetting('Location%s' % num)
	sourcePref=ADDON.getSetting("DataSourcePreference")

	if LatLong:
		fetchWeatherAlerts(num)
		if "forecast.weather.gov" == sourcePref:
			fetchAltDaily(num)
		else:
			fetchCurrent(num)
			fetchDaily(num)
		fetchHourly(num)
		Station=ADDON.getSetting('Location%sradarStation' % num)

		set_property('Map.IsFetched', 'true')
		#KODI will cache and not re-fetch the weather image, so inject a dummy time-stamp into the url to trick kodi because we want the new image
		nowtime=str(time.time())
		#Radar
		radarLoop=ADDON.getSetting('RadarLoop')
		if ("true" == radarLoop):
			#kodi will not loop gifs from a url, we have to actually 
			#download to a local file to get it to loop
			
			imagepath=xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
			#clean up previously fetched images
			for f in glob.glob(imagepath+"radar*.gif"):
				os.remove(f)
			xbmc.log('Option To Loop Radar Selected',level=xbmc.LOGDEBUG)
			url="https://radar.weather.gov/ridge/lite/%s_loop.gif" % (Station)
			radarfilename="radar_%s.gif" % (nowtime)
			dest=imagepath+radarfilename
			loop_image=get_url_image(url, dest)
			set_property('Map.%i.Area' % 1, loop_image)
		else:
			url="https://radar.weather.gov/ridge/lite/%s_0.gif?%s" % (Station,nowtime)
			set_property('Map.%i.Area' % 1, url)
			#clear_property('Map.%i.Area' % 1)
			#set_property('Map.%i.Layer' % 1, url)
		
		clear_property('Map.%i.Layer' % 1)
		set_property('Map.%i.Heading' % 1, LANGUAGE(32334))

		
		# add satellite maps if we configured any
		for count in range (1, 5):
			mcount=count+1
			mapsector = ADDON.getSetting('Map%iSector' % (mcount))
			maptype = ADDON.getSetting('Map%iType' % (mcount))
			maplabel = ADDON.getSetting('Map%iLabel' % (mcount))

			if (mapsector and maptype):
				path=MAPSECTORS.get(mapsector)['path']
				if mapsector != 'glm-e' and mapsector != 'glm-w':
					path=path.replace("%s",maptype)
				url="https://cdn.star.nesdis.noaa.gov/%s?%s" % (path,nowtime)
				
				set_property('Map.%i.Area' % (mcount), url)
				set_property('Map.%i.Heading' % (mcount), "%s" % (maplabel) )
				clear_property('Map.%i.Layer' % (mcount))
			else:
				clear_property('Map.%i.Area' % (mcount))
				clear_property('Map.%i.Heading' % (mcount))
				clear_property('Map.%i.Layer' % (mcount))
	else:
		log('no location provided')
		clear()

# clean up references to classes that we used
del MONITOR, xbmc, xbmcgui, xbmcvfs, xbmcaddon, WEATHER_WINDOW
# clean up everything we referenced from the utils to prevent any dangling classes hanging around
del FtoC, CtoF, log, ADDON, LANGUAGE, MAPSECTORS, MAPTYPES
del WEATHER_CODES, FORECAST, FEELS_LIKE, SPEED, WIND_DIR, SPEEDUNIT, zip_x 
del get_url_JSON, get_url_image
del get_month, get_timestamp, get_weekday, get_time



