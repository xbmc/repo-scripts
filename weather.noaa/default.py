# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()

import os, sys, time
import xbmc, xbmcgui, xbmcaddon


#from datetime import datetime
from resources.lib.utils import FtoC, set_property, clear_property, log
from resources.lib.utils import WEATHER_CODES, FORECAST, FEELS_LIKE, SPEED, WIND_DIR, SPEEDUNIT, zip_x
from resources.lib.utils import get_url_JSON, decode_utf8  #, encode_utf8
from resources.lib.utils import get_month, get_timestamp, get_weekday, get_time



ADDON           = xbmcaddon.Addon()
ADDONNAME       = ADDON.getAddonInfo('name')
ADDONID         = ADDON.getAddonInfo('id')
CWD             = decode_utf8(ADDON.getAddonInfo('path'))
ADDONVERSION    = ADDON.getAddonInfo('version')
LANGUAGE        = ADDON.getLocalizedString
RESOURCE        = decode_utf8(xbmc.translatePath(os.path.join( CWD, 'resources', 'lib' ).encode("utf-8") ))
PROFILE         = decode_utf8(xbmc.translatePath(ADDON.getAddonInfo('profile')))

sys.path.append(RESOURCE)


WEATHER_ICON	= decode_utf8(xbmc.translatePath('%s.png'))
DATEFORMAT	= xbmc.getRegion('dateshort')
TIMEFORMAT	= xbmc.getRegion('meridiem')
KODILANGUAGE	= xbmc.getLanguage().lower()
MAXDAYS		= 10


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
		loc = ADDON.getSetting('Location%sLatLong' % count)
		loc_name = ADDON.getSetting('Location%s' % count)
		if loc != '':
			locations += 1
			if loc_name == '':
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
		icon=icon.rsplit('?', 1)[0]
		code=icon.rsplit('/',1)[1]
		thing=code.split(",")
		if len(thing) > 1:
			rain=thing[1]
			code=thing[0]
			return code, rain
		else:
			code=thing[0]
			return code, ''
		


########################################################################################
##  fetches location data (weather grid point, station, etc, for lattitude,logngitude
########################################################################################

def fetchLocation(locstr,prefix):
	log('searching for location: %s' % locstr)
	data = get_initial(locstr)
	log('location data: %s' % data)
	if not data:
		log('failed to retrieve location data')
		return None
	if data != '' and 'properties' in data:
		#radarStation = data['properties']['radarStation']

		city	=	data['properties']['relativeLocation']['properties']['city']
		state =		data['properties']['relativeLocation']['properties']['state']
		locationName=	city+", "+state
		ADDON.setSetting(prefix, locationName)
#		lat =		str(data['geometry']['coordinates'][1])
#		lon =		str(data['geometry']['coordinates'][0])
#		locationLatLong=lat+','+lon
		#ADDON.setSetting(prefix, locationLatLong)

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

#		log('location data: %s' % query)
		if odata != '' and 'features' in odata:
			stations={}
			stationlist=[]
			
			for count,item in enumerate(odata['features']):
				stationId=item['properties']['stationIdentifier']
				stationName=item['properties']['name']
				stationlist.append(stationName)
				stations[stationName]=stationId

			#xbmc.log('stationlist: %s' % stationlist,level=xbmc.LOGINFO)
			#xbmc.log('stations: %s' % stations,level=xbmc.LOGINFO)

			dialog = xbmcgui.Dialog()
			i=dialog.select(LANGUAGE(32331),stationlist)
			#xbmc.log('selected station name: %s' % stationlist[i],level=xbmc.LOGINFO)
			#xbmc.log('selected station: %s' % stations[stationlist[i]],level=xbmc.LOGINFO)

			ADDON.setSetting(prefix+'Station',stations[stationlist[i]])
			ADDON.setSetting(prefix+'StationName',stationlist[i])



########################################################################################
##  fetches daily weather data
########################################################################################

def fetchDaily(num):

	url=ADDON.getSetting('Location'+str(num)+'forecast_url')		
	log('forecast url: %s' % url)
		
	##current_props(current_weather,loc)

	daily_weather = get_url_JSON(url)

	if daily_weather and daily_weather != '' and 'properties' in daily_weather:
		data=daily_weather['properties']
	else:
		xbmc.log('failed to find weather data from : %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % daily_weather,level=xbmc.LOGERROR)
		###return None
		return fetchAltDaily(num)

	for count, item in enumerate(data['periods']):
		#code = str(item['weather'][0].get('id',''))
		icon = item['icon']
		#https://api.weather.gov/icons/land/night/ovc?size=small
		icon=icon.rsplit('?', 1)[0]
		code, rain=code_from_icon(icon)
		#xbmc.log('icon %s' % icon,level=xbmc.LOGINFO)
		#xbmc.log('code %s' % code,level=xbmc.LOGINFO)

		weathercode = WEATHER_CODES.get(code)
		starttime=item['startTime']
		startstamp=get_timestamp(starttime)
		set_property('Day%i.isDaytime'		% (count),str(item['isDaytime']))
		set_property('Day%i.Title'		% (count), item['name'])
		#xbmc.log('temperature %s' % item['temperature'],level=xbmc.LOGINFO)

		if item['isDaytime'] == True:
			set_property('Day%i.HighTemp'	% (count), str(FtoC(item['temperature'])))
			set_property('Day%i.LowTemp'	% (count), str(FtoC(item['temperature'])))
		if item['isDaytime'] == False:
			set_property('Day%i.HighTemp'	% (count), str(FtoC(item['temperature'])))
			set_property('Day%i.LowTemp'	% (count), str(FtoC(item['temperature'])))
		set_property('Day%i.Outlook'		% (count), item['shortForecast'])
		#set_property('Day%i.Details'		% (count+1), item['detailedForecast'])
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
			set_property('Daily.%i.TempDay'		% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
			set_property('Daily.%i.HighTemperature'	% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
			set_property('Daily.%i.TempNight'	% (count+1), '')
			set_property('Daily.%i.LowTemperature'	% (count+1), '')
		if item['isDaytime'] == False:
			set_property('Daily.%i.LongDay'		% (count+1), item['name'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (n)")
			set_property('Daily.%i.TempDay'		% (count+1), '')
			set_property('Daily.%i.HighTemperature'	% (count+1), '')
			set_property('Daily.%i.TempNight'	% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
			set_property('Daily.%i.LowTemperature'	% (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
		#set_property('Daily.%i.LongDay'		% (count+1), get_weekday(startstamp, 'l'))
		#set_property('Daily.%i.ShortDay'		% (count+1), get_weekday(startstamp,'s'))
		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))
		
		if (rain !=''):
			set_property('Daily.%i.Precipitation'	% (count+1), rain + '%')
		else:
			set_property('Daily.%i.Precipitation'	% (count+1), '')
			
#		set_property('Daily.%i.WindDegree'	% (count+1), str(item.get('deg','')) + u'\N{DEGREE SIGN}')
#		set_property('Daily.%i.Humidity'	% (count+1), str(item.get('humidity','')) + '%')
#		set_property('Daily.%i.TempMorn'	% (count+1), TEMP(item['temp']['morn']) + TEMPUNIT)
#		set_property('Daily.%i.TempDay'		% (count+1), TEMP(item['temp']['day']) + TEMPUNIT)
#		set_property('Daily.%i.TempEve'		% (count+1), TEMP(item['temp']['eve']) + TEMPUNIT)
#		set_property('Daily.%i.TempNight'	% (count+1), TEMP(item['temp']['night']) + TEMPUNIT)
#		set_property('Daily.%i.HighTemperature' % (count+1), TEMP(item['temp']['max']) + TEMPUNIT)
#		set_property('Daily.%i.LowTemperature'	% (count+1), TEMP(item['temp']['min']) + TEMPUNIT)
#		set_property('Daily.%i.FeelsLike'	% (count+1), FEELS_LIKE(item['temp']['day'], item['speed'] * 3.6, item['humidity']) + TEMPUNIT)
#		set_property('Daily.%i.DewPoint'	% (count+1), DEW_POINT(item['temp']['day'], item['humidity']) + TEMPUNIT)





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

	####	[{"Title": t, "Score": s} for t, s in zip(titles, scores)]if daily_weather and daily_weather != '' and 'data' in daily_weather:
	if daily_weather and daily_weather != '' and 'data' in daily_weather:

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
		#code = str(item['weather'][0].get('id',''))

		icon = item['iconLink']

		#https://api.weather.gov/icons/land/night/ovc?size=small
		#icon=icon.rsplit('?', 1)[0]
		code, rain=code_from_icon(icon)
		#xbmc.log('icon %s' % icon,level=xbmc.LOGINFO)
		#xbmc.log('code %s' % code,level=xbmc.LOGINFO)
		weathercode = WEATHER_CODES.get(code)

		starttime=item['startValidTime']
		startstamp=get_timestamp(starttime)
		set_property('Day%i.Title'		% (count), item['startPeriodName'])

#		if item['tempLabel'] == 'High':
#			set_property('Day%i.HighTemp'	% (count), str(FtoC(item['temperature'])))
#		if item['tempLabel'] == 'Low':
#			set_property('Day%i.LowTemp'	% (count), str(FtoC(item['temperature'])))
		set_property('Day%i.Outlook'		% (count), item['weather'])
		set_property('Day%i.Details'		% (count), item['text'])
		set_property('Day%i.OutlookIcon'	% (count), weathercode)
		set_property('Day%i.RemoteIcon'		% (count), icon)

		# NOTE: Day props are 0 based, but Daily/Hourly are 1 based
		####set_property('Daily.%i.isDaytime'	% (count+1),str(item['isDaytime']))
		set_property('Daily.%i.Outlook'		% (count+1), item['text'])
		set_property('Daily.%i.ShortOutlook'	% (count+1), item['weather'])
		
		set_property('Daily.%i.RemoteIcon'	% (count+1), icon)
		set_property('Daily.%i.OutlookIcon'	% (count+1), WEATHER_ICON % weathercode)
		set_property('Daily.%i.FanartCode'	% (count+1), weathercode)
		##set_property('Daily.%i.WindDirection'	% (count+1), item['windDirection'])
		##set_property('Daily.%i.WindSpeed'	% (count+1), item['windSpeed'])

		if item['tempLabel'] == 'High':
			set_property('Daily.%i.LongDay'		% (count+1), item['startPeriodName'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (d)")
			set_property('Daily.%i.TempDay'		% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
			set_property('Daily.%i.HighTemperature'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
			set_property('Daily.%i.TempNight'	% (count+1), '')
			set_property('Daily.%i.LowTemperature'	% (count+1), '')
		if item['tempLabel'] == 'Low':
			set_property('Daily.%i.LongDay'		% (count+1), item['startPeriodName'])
			set_property('Daily.%i.ShortDay'	% (count+1), get_weekday(startstamp,'s')+" (n)")
			set_property('Daily.%i.TempDay'		% (count+1), '')
			set_property('Daily.%i.HighTemperature'	% (count+1), '')
			set_property('Daily.%i.TempNight'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
			set_property('Daily.%i.LowTemperature'	% (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
		#set_property('Daily.%i.LongDay'		% (count+1), get_weekday(startstamp, 'l'))
		#set_property('Daily.%i.ShortDay'		% (count+1), get_weekday(startstamp,'s'))
		if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'dl'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ds'))
		else:
			set_property('Daily.%i.LongDate'	% (count+1), get_month(startstamp, 'ml'))
			set_property('Daily.%i.ShortDate'	% (count+1), get_month(startstamp, 'ms'))

		rain=str(item['pop'])
		if (rain !=''):
			set_property('Daily.%i.Precipitation'	% (count+1), rain + '%')
		else:
			set_property('Daily.%i.Precipitation'	% (count+1), '')
			
#		set_property('Daily.%i.WindDegree'	% (count+1), str(item.get('deg','')) + u'\N{DEGREE SIGN}')
#		set_property('Daily.%i.Humidity'	% (count+1), str(item.get('humidity','')) + '%')
#		set_property('Daily.%i.TempMorn'	% (count+1), TEMP(item['temp']['morn']) + TEMPUNIT)
#		set_property('Daily.%i.TempDay'		% (count+1), TEMP(item['temp']['day']) + TEMPUNIT)
#		set_property('Daily.%i.TempEve'		% (count+1), TEMP(item['temp']['eve']) + TEMPUNIT)
#		set_property('Daily.%i.TempNight'	% (count+1), TEMP(item['temp']['night']) + TEMPUNIT)
#		set_property('Daily.%i.HighTemperature' % (count+1), TEMP(item['temp']['max']) + TEMPUNIT)
#		set_property('Daily.%i.LowTemperature'	% (count+1), TEMP(item['temp']['min']) + TEMPUNIT)
#		set_property('Daily.%i.FeelsLike'	% (count+1), FEELS_LIKE(item['temp']['day'], item['speed'] * 3.6, item['humidity']) + TEMPUNIT)
#		set_property('Daily.%i.DewPoint'	% (count+1), DEW_POINT(item['temp']['day'], item['humidity']) + TEMPUNIT)



	if daily_weather and daily_weather != '' and 'currentobservation' in daily_weather:
		data=daily_weather['currentobservation']
		#xbmc.log('data %s' % data,level=xbmc.LOGINFO)
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

		#set_property('Current.Precipitation',	str(round(data.get('precipitationLast3Hours').get('value') *	0.04 ,2)) + ' in')
		if (rain != ''):
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
	if current and current != '' and 'properties' in current:
		data=current['properties']
		#xbmc.log('data: %s' % data,level=xbmc.LOGINFO)
	else:
		xbmc.log('failed to find weather data from : %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % current,level=xbmc.LOGERROR)
		return
	
	#xbmc.log('data %s' % data,level=xbmc.LOGINFO)
	icon = data['icon']
	#https://api.weather.gov/icons/land/night/ovc?size=small
	icon=icon.rsplit('?', 1)[0]
	code, rain=code_from_icon(icon)
	weathercode = WEATHER_CODES.get(code)
	#set_property('Current.Location', loc)
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
		#xbmc.log('raw temp %s' % data.get('temperature').get('value'),level=xbmc.LOGINFO)
		#xbmc.log('temp %s' % temp,level=xbmc.LOGINFO)
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

	#set_property('Current.Precipitation',	str(round(data.get('precipitationLast3Hours').get('value') *	0.04 ,2)) + ' in')
	if (rain != ''):
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


#	#set_property('Current.UVIndex'			, '') # no idea how the api returns it, use data from current_props()

# # extended properties

#		set_property('Current.Cloudiness'	, data['last']['clouds'][0].get('condition',''))
	try:
		set_property('Current.WindGust'	, SPEED(float(data.get('windGust').get('value',0))/3.6) + SPEEDUNIT)
	except:
		set_property('Current.WindGust'	, '')
		
#		if 'F' in TEMPUNIT:
#			set_property('Current.Precipitation', str(round(data['last']['rain']['1h'] *	0.04 ,2)) + ' in')
#		else:
#			set_property('Current.Precipitation', str(int(round(data['last']['rain']['1h']))) + ' mm')
#		if 'F' in TEMPUNIT:
#			set_property('Current.Pressure'	, str(round(data['last']['main']['pressure'] / 33.86 ,2)) + ' in')
#		else:
#			set_property('Current.Pressure'	, str(data['last']['main']['pressure']) + ' mb')




########################################################################################
##  fetches any weather alerts for location
########################################################################################


#https://api.weather.gov/alerts/active/zone/CTZ006
#https://api.weather.gov/alerts/active/zone/CTC009
def fetchWeatherAlerts(num):

	#a_zone=ADDON.getSetting('Location'+str(num)+'Zone')
	a_zone=ADDON.getSetting('Location'+str(num)+'County')
	url="https://api.weather.gov/alerts/active/zone/%s" %a_zone	
	alerts=get_url_JSON(url)
	#xbmc.log('current data: %s' % current_data,level=xbmc.LOGINFO)
	# if we have a valid response then clear our current alerts
	if alerts and alerts != '' and 'features' in alerts:
		for count in range (1, 10):
			clear_property('Alerts.%i.event' % (count))	
	else:
		xbmc.log('failed to get proper alert response %s' % url,level=xbmc.LOGERROR)
		xbmc.log('%s' % alerts,level=xbmc.LOGINFO)
		return
		
	if 'features' in alerts and alerts['features']:
		data=alerts['features']
		#xbmc.log('data: %s' % data,level=xbmc.LOGINFO)
		set_property('Alerts.IsFetched'	, 'true')
	else:
		clear_property('Alerts.IsFetched')
		xbmc.log('No current weather alerts from  %s' % url,level=xbmc.LOGINFO)
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
		
	hourly_weather = get_url_JSON(url)
	if hourly_weather and hourly_weather != '' and 'properties' in hourly_weather:
		data=hourly_weather['properties']
	else:
		xbmc.log('failed to find proper hourly weather from %s' % url,level=xbmc.LOGERROR)
		return

# extended properties
	for count, item in enumerate(data['periods']):
		
		icon=item['icon']
		#https://api.weather.gov/icons/land/night/ovc?size=small
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

		set_property('Hourly.%i.Temperature'		% (count+1),	str(item['temperature'])+u'\N{DEGREE SIGN}'+item['temperatureUnit'])
		

		if rain !='':
			set_property('Hourly.%i.Precipitation'	% (count+1), rain + '%')
			set_property('Hourly.%i.ChancePrecipitation'	% (count+1), rain + '%')
		else:
			set_property('Hourly.%i.Precipitation'	% (count+1), '')
			set_property('Hourly.%i.ChancePrecipitation'	% (count+1), '')
			
	
	count = 1



########################################################################################
##  Main Kodi entry point
########################################################################################

class MyMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):
		xbmc.Monitor.__init__(self)

log('version %s started with argv: %s' % (ADDONVERSION, sys.argv[1]))

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
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(CWD, 'resources', 'media', 'banner.png')))

if sys.argv[1].startswith('Location'):
	log("argument: %s" % (sys.argv[1]))
	text = ADDON.getSetting(sys.argv[1]+"LatLong")
	if text == '' :
		# request lattitude,longitude
		keyboard = xbmc.Keyboard('', LANGUAGE(32332), False)
		keyboard.doModal()
		if (keyboard.isConfirmed() and keyboard.getText() != ''):
			text = keyboard.getText()
	if text != '':
		log("calling location with %s and %s" % (text, sys.argv[1]))
		fetchLocation(text,sys.argv[1])
else:

	num=sys.argv[1]
	locationLatLong = ADDON.getSetting('Location%sLatLong' % num)
	
	station=ADDON.getSetting('Location'+str(num)+'Station')
	if station == '' :
		log("calling location with %s" % (locationLatLong))
		fetchLocation(locationLatLong,'Location%s' % str(num))

	refresh_locations()

	locationLatLong = ADDON.getSetting('Location%s' % num)
	sourcePref=ADDON.getSetting("DataSourcePreference")

	if not locationLatLong == '':
		fetchWeatherAlerts(num)
		if "forecast.weather.gov" == sourcePref:
			fetchAltDaily(num)
		else:
			fetchCurrent(num)
			#currentforecast(num)
			fetchDaily(num)
		fetchHourly(num)
		##Station=ADDON.getSetting('Location%scwa' % num)
		Station=ADDON.getSetting('Location%sradarStation' % num)
		
		set_property('Map.IsFetched', 'true')
#		url="https://radar.weather.gov/ridge/lite/NCR/%s_0.png?d=%s" % (Station,str(time.time()))
##https://radar.weather.gov/ridge/lite/KOKX_loop.gif
##https://radar.weather.gov/ridge/lite/KOKX_0.gif

#		xbmc.log('radar url:  %s' % url,level=xbmc.LOGINFO)
		nowtime=str(time.time())
		#Radar
		#KODI will cache and not re-fetch the weather image, so inject a dummy time-stamp into the url to trick kodi because we want the new image
###		set_property('Map.%i.Area' % 1, "https://radar.weather.gov/ridge/lite/NCR/%s_0.png?t=%s" % (Station,str(time.time())))
		url="https://radar.weather.gov/ridge/lite/%s_0.gif?%s" % (Station,nowtime)
		set_property('Map.%i.Area' % 1, url)
		#xbmc.log('radar url: %s' % url,level=xbmc.LOGINFO)


		#set_property('Map.%i.Layer' % 1, url)
		set_property('Map.%i.Heading' % 1, LANGUAGE(32334))
#		set_property('Map.%i.Legend' % 1, '')

		#Long Range Radar
##		set_property('Map.%i.Area' % 2, "https://radar.weather.gov/ridge/lite/N0Z/%s_0.png?t=%s" % (Station,str(time.time())))
#		url="https://radar.weather.gov/ridge/lite/%s_loop.gif?t=%s.gif" % (Station,str(time.time()))
#		#xbmc.log('radarloop url: %s' % url,level=xbmc.LOGINFO)
#		set_property('Map.%i.Area' % 2, url)
#		set_property('Map.%i.Heading' % 2, LANGUAGE(32333))
		
		# add satellite maps if we configured any
		for count in range (1, 5):
			mcount=count+1
			mapsector = ADDON.getSetting('Map%iSector' % (mcount))
			maptype = ADDON.getSetting('Map%iType' % (mcount))
			#xbmc.log('Map%iSector: %s' % (mcount,mapsector),level=xbmc.LOGINFO)
			#xbmc.log('Map%iType: %s' % (mcount,maptype),level=xbmc.LOGINFO)

			if (mapsector != '' and maptype != ''):
				if mapsector == 'CONUS':
					url="https://cdn.star.nesdis.noaa.gov/GOES16/ABI/CONUS/%s/1250x750.jpg?%s" % (maptype,nowtime)
				else:
					url="https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR/%s/%s/1200x1200.jpg?%s" % (mapsector,maptype,nowtime)
				
				#xbmc.log('map %i url: %s' % (mcount,url),level=xbmc.LOGINFO)
				set_property('Map.%i.Area' % (mcount), url)
				set_property('Map.%i.Heading' % (mcount), "%s:%s" % (mapsector,maptype) )
				clear_property('Map.%i.Layer' % (mcount))
			else:
				clear_property('Map.%i.Area' % (mcount))
				clear_property('Map.%i.Heading' % (mcount))
				clear_property('Map.%i.Layer' % (mcount))
	else:
		log('no location provided')
		clear()

log('finished')


