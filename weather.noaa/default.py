# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

#from future import standard_library
#standard_library.install_aliases()

import os, glob, sys, time, re
import xbmc, xbmcgui, xbmcvfs, xbmcaddon
import datetime

from resources.lib.utils import FtoC, CtoF, log, ADDON, LANGUAGE, MAPSECTORS, LOOPSECTORS, MAPTYPES
from resources.lib.utils import WEATHER_CODES, FORECAST, FEELS_LIKE, SPEED, WIND_DIR, SPEEDUNIT, zip_x 
from resources.lib.utils import get_url_JSON, get_url_image 
from resources.lib.utils import get_month, get_timestamp, get_weekday, get_time
from dateutil.parser import parse

WEATHER_WINDOW  = xbmcgui.Window(12600)
WEATHER_ICON  = xbmcvfs.translatePath('%s.png')
DATEFORMAT  = xbmc.getRegion('dateshort')
TIMEFORMAT  = xbmc.getRegion('meridiem')
MAXDAYS    = 10
TEMPUNIT  = xbmc.getRegion('tempunit')
SOURCEPREF  = ADDON.getSetting("DataSourcePreference")

def set_property(name, value):
  WEATHER_WINDOW.setProperty(name, value)

def clear_property(name):
  WEATHER_WINDOW.clearProperty(name)

def clear():
  set_property('Current.Condition'  , 'N/A')
  set_property('Current.Temperature'  , '0')
  set_property('Current.Wind'    , '0')
  set_property('Current.WindDirection'  , 'N/A')
  set_property('Current.Humidity'    , '0')
  set_property('Current.FeelsLike'  , '0')
  set_property('Current.UVIndex'    , '0')
  set_property('Current.DewPoint'    , '0')
  set_property('Current.OutlookIcon'  , 'na.png')
  set_property('Current.FanartCode'  , 'na')
  for count in range (0, MAXDAYS+1):
    set_property('Day%i.Title'  % count, 'N/A')
    set_property('Day%i.HighTemp'  % count, '0')
    set_property('Day%i.LowTemp'  % count, '0')
    set_property('Day%i.Outlook'  % count, 'N/A')
    set_property('Day%i.OutlookIcon' % count, 'na.png')
    set_property('Day%i.FanartCode'  % count, 'na')

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

  
def code_from_icon(icon):
  if icon:
    #xbmc.log('icon: %s' % (icon) ,level=xbmc.LOGDEBUG)


    daynight="day"  

    #special handling of forecast.weather.gov "dualimage" icon generator urls
    #https://forecast.weather.gov/DualImage.php?i=bkn&j=shra&jp=30
    #https://forecast.weather.gov/DualImage.php?i=shra&j=bkn&ip=30
    if 'DualImage' in icon:
      params = icon.split("?")[1].split("&")
      code="day"
      rain=None
      for param in params:
        thing=param.split("=")     
        p=thing[0]
        v=thing[1]
        if p == "i":
          code="%s/%s" % ("day",v)
        if p == "ip" or p == "jp":
          if rain is None or v > rain:
            rain=v

      return code, rain
        

    if '?' in icon:
      icon=icon.rsplit('?', 1)[0]

    # strip off file extension if we have one
    icon=icon.replace(".png","")    
    icon=icon.replace(".jpg","")    

    if "/day/" in icon:
      daynight="day"
    elif "/night/" in icon:
      daynight="night"

    rain = None
    code = None
    # loop though our "split" icon paths, and get max rain percent
    # take last icon code in the process
    for checkcode in icon.rsplit('/'):
      thing=checkcode.split(",")
      code="%s/%s" % (daynight,thing[0])
      if len(thing) > 1:
        train=thing[1]
        if rain is None or train > rain:
          rain=train

    return code, rain
    

########################################################################################
##  Dialog for getting Latitude and Longitude
########################################################################################



def enterLocation(num):  
##  log("argument: %s" % (sys.argv[1]))

  text = ADDON.getSetting("Location"+num+"LatLong")
  Latitude=""
  Longitude=""
  if text and "," in text:
    thing=text.split(",")
    Latitude=thing[0]
    Longitude=thing[1]

  dialog = xbmcgui.Dialog()
  
  Latitude=dialog.input(LANGUAGE(32341),defaultt=Latitude,type=xbmcgui.INPUT_ALPHANUM)
  
  if not Latitude:
    ADDON.setSetting("Location"+num+"LatLong","")
    return False

  Longitude=dialog.input(heading=LANGUAGE(32342),defaultt=Longitude,type=xbmcgui.INPUT_ALPHANUM)

  if not Longitude:
    ADDON.setSetting("Location"+num+"LatLong","")
    return False
  LatLong=Latitude+","+Longitude
  ADDON.setSetting("Location"+num+"LatLong",LatLong)
  get_Stations(num,LatLong,True)
  return


########################################################################################
##  fetches location data (weather grid point, station, etc, for lattitude,logngitude
##  returns url for fetching local weather stations
########################################################################################



def get_Points(num,LatLong,resetName=False):

  prefix="Location"+num
  log('searching for location: %s' % LatLong)
  url = 'https://api.weather.gov/points/%s' % LatLong
  log("url:"+url)
  data=get_url_JSON(url)  
  log('location data: %s' % data)
  if not data:
    log('failed to retrieve location data')
    return None
  if data and 'properties' in data:

    if resetName:
      city  =  data['properties']['relativeLocation']['properties']['city']
      state =    data['properties']['relativeLocation']['properties']['state']
      locationName=  city+", "+state
      ADDON.setSetting(prefix, locationName)

    gridX=data['properties']['gridX']
    ADDON.setSetting(prefix+'gridX',str(gridX))
    
    gridY=data['properties']['gridY']
    ADDON.setSetting(prefix+'gridY',str(gridY))
    
    cwa=data['properties']['cwa']
    ADDON.setSetting(prefix+'cwa',  cwa)

    forecastZone=data['properties']['forecastZone']
    zone=forecastZone.rsplit('/',1)[1]
    ADDON.setSetting(prefix+'Zone',  zone)

    forecastCounty=data['properties']['county']
    county=forecastCounty.rsplit('/',1)[1]
    ADDON.setSetting(prefix+'County', county)
    
    forecastGridData_url =  data['properties']['forecastGridData']
    ADDON.setSetting(prefix+'forecastGrid_url', forecastGridData_url)

    forecastHourly_url =  data['properties']['forecastHourly']
    ADDON.setSetting(prefix+'forecastHourly_url', forecastHourly_url)

    forecast_url =    data['properties']['forecast']
    ADDON.setSetting(prefix+'forecast_url',  forecast_url)

    radarStation =    data['properties']['radarStation']
    ADDON.setSetting(prefix+'radarStation',  radarStation)
    

    #current_datetime = parse("now")
    current_datetime = datetime.datetime.now()
    ADDON.setSetting(prefix+'lastPointsCheck',  str(current_datetime))


    stations_url =  data['properties']['observationStations']
    return stations_url

########################################################################################
##  fetches location data (weather grid point, station, etc, for lattitude,logngitude
########################################################################################

def get_Stations(num,LatLong,resetName=False):
    
    prefix="Location"+num
    odata=None
    stations_url=get_Points(num,LatLong,resetName)
    if stations_url:
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

  log("SOURCEPREF: %s" % SOURCEPREF)
  url=ADDON.getSetting('Location'+str(num)+'forecast_url')
  if "preview-api.weather.gov" == SOURCEPREF:
    url=url.replace("https://api.weather.gov","https://preview-api.weather.gov")
      
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

  for count, item in enumerate(data['periods'], start=0):
    icon = item['icon']
    #https://api.weather.gov/icons/land/night/ovc?size=small
    if icon and '?' in icon:
      icon=icon.rsplit('?', 1)[0]
    code, rain=code_from_icon(icon)

    weathercode = WEATHER_CODES.get(code)
    starttime=item['startTime']
    startstamp=get_timestamp(starttime)
    set_property('Day%i.isDaytime'    % (count),str(item['isDaytime']))
    set_property('Day%i.Title'    % (count), item['name'])

    if item['isDaytime'] == True:
      ##Since we passed units into api, we may need to convert to C, or may not
      if 'F' in TEMPUNIT:
        set_property('Day%i.HighTemp'  % (count), str(FtoC(item['temperature'])))
        set_property('Day%i.LowTemp'  % (count), str(FtoC(item['temperature'])))
      elif 'C' in TEMPUNIT:
        set_property('Day%i.HighTemp'  % (count), str(item['temperature']))
        set_property('Day%i.LowTemp'  % (count), str(item['temperature']))
    if item['isDaytime'] == False:
      if 'F' in TEMPUNIT:
        set_property('Day%i.HighTemp'  % (count), str(FtoC(item['temperature'])))
        set_property('Day%i.LowTemp'  % (count), str(FtoC(item['temperature'])))
      elif 'C' in TEMPUNIT:
        set_property('Day%i.HighTemp'  % (count), str(item['temperature']))
        set_property('Day%i.LowTemp'  % (count), str(item['temperature']))
    set_property('Day%i.Outlook'    % (count), item['shortForecast'])
    set_property('Day%i.FanartCode'  % (count), weathercode)
    set_property('Day%i.OutlookIcon'% (count), WEATHER_ICON % weathercode)
    set_property('Day%i.RemoteIcon'  % (count), icon)

    # NOTE: Day props are 0 based, but Daily/Hourly are 1 based
    set_property('Daily.%i.isDaytime'  % (count+1),str(item['isDaytime']))
    set_property('Daily.%i.Outlook'    % (count+1), item['shortForecast'])
    set_property('Daily.%i.ShortOutlook'  % (count+1), item['shortForecast'])
    set_property('Daily.%i.DetailedOutlook'  % (count+1), item['detailedForecast'])
    
    set_property('Daily.%i.RemoteIcon'  % (count+1), icon)
    set_property('Daily.%i.OutlookIcon'  % (count+1), WEATHER_ICON % weathercode)
    set_property('Daily.%i.FanartCode'  % (count+1), weathercode)
    set_property('Daily.%i.WindDirection'  % (count+1), item['windDirection'])
    set_property('Daily.%i.WindSpeed'  % (count+1), item['windSpeed'])

    if item['isDaytime'] == True:
      set_property('Daily.%i.LongDay'    % (count+1), item['name'])
      set_property('Daily.%i.ShortDay'  % (count+1), get_weekday(startstamp,'s')+" (d)")
        #set_property('Daily.%i.TempDay'    % (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))
        #set_property('Daily.%i.HighTemperature'  % (count+1), u'%i\N{DEGREE SIGN}%s' % (item['temperature'], item['temperatureUnit']))

      ## we passed units to api, so we got back C or F, so don't need to convert
      set_property('Daily.%i.TempDay'    % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      set_property('Daily.%i.HighTemperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      #if 'F' in TEMPUNIT:
      #  set_property('Daily.%i.TempDay'    % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      #  set_property('Daily.%i.HighTemperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      #elif 'C' in TEMPUNIT:
      #  set_property('Daily.%i.TempDay'    % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
      #  set_property('Daily.%i.HighTemperature'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
      set_property('Daily.%i.TempNight'  % (count+1), '')
      set_property('Daily.%i.LowTemperature'  % (count+1), '')

    if item['isDaytime'] == False:
      set_property('Daily.%i.LongDay'    % (count+1), item['name'])
      set_property('Daily.%i.ShortDay'  % (count+1), get_weekday(startstamp,'s')+" (n)")

      set_property('Daily.%i.TempDay'    % (count+1), '')
      set_property('Daily.%i.HighTemperature'  % (count+1), '')
      ## we passed units to api, so we got back C or F, so don't need to convert
      #if 'F' in TEMPUNIT:
      set_property('Daily.%i.TempNight'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      set_property('Daily.%i.LowTemperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      #elif 'C' in TEMPUNIT:
      #  set_property('Daily.%i.TempNight'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
      #  set_property('Daily.%i.LowTemperature'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))

    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
      set_property('Daily.%i.LongDate'  % (count+1), get_month(startstamp, 'dl'))
      set_property('Daily.%i.ShortDate'  % (count+1), get_month(startstamp, 'ds'))
    else:
      set_property('Daily.%i.LongDate'  % (count+1), get_month(startstamp, 'ml'))
      set_property('Daily.%i.ShortDate'  % (count+1), get_month(startstamp, 'ms'))
    
    if rain and str(rain) and not "0" == str(rain):
      set_property('Daily.%i.ChancePrecipitation'  % (count+1), str(rain) + '%')
    else:
      ##set_property('Daily.%i.ChancePrecipitation'  % (count+1), '')
      clear_property('Daily.%i.ChancePrecipitation'  % (count+1))



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

  for count, item in enumerate(dailydata, start=0):
    icon = item['iconLink']

    #https://api.weather.gov/icons/land/night/ovc?size=small
    code, ignoreme = code_from_icon(icon)
    weathercode = WEATHER_CODES.get(code)

    starttime=item['startValidTime']
    startstamp=get_timestamp(starttime)
    set_property('Day%i.Title'    % (count), item['startPeriodName'])

    set_property('Day%i.Outlook'    % (count), item['weather'])
    set_property('Day%i.Details'    % (count), item['text'])

    set_property('Day%i.OutlookIcon'  % (count), WEATHER_ICON % weathercode)
    set_property('Day%i.RemoteIcon'    % (count), icon)
    set_property('Day%i.FanartCode'    % (count), weathercode)

    # NOTE: Day props are 0 based, but Daily/Hourly are 1 based
    set_property('Daily.%i.DetailedOutlook'  % (count+1), item['text'])
    set_property('Daily.%i.Outlook'    % (count+1), item['weather'])
    set_property('Daily.%i.ShortOutlook'  % (count+1), item['weather'])
    
    set_property('Daily.%i.OutlookIcon'  % (count+1), WEATHER_ICON % weathercode)
    set_property('Daily.%i.RemoteIcon'  % (count+1), icon)
    set_property('Daily.%i.FanartCode'  % (count+1), weathercode)

    if item['tempLabel'] == 'High':
      set_property('Daily.%i.LongDay'    % (count+1), item['startPeriodName'])
      set_property('Daily.%i.ShortDay'  % (count+1), get_weekday(startstamp,'s')+" (d)")

      if 'F' in TEMPUNIT:
        set_property('Daily.%i.TempDay'    % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
        set_property('Daily.%i.HighTemperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      elif 'C' in TEMPUNIT:
        set_property('Daily.%i.TempDay'    % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
        set_property('Daily.%i.HighTemperature'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
#      set_property('Daily.%i.TempDay'    % (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
#      set_property('Daily.%i.HighTemperature'  % (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
      set_property('Daily.%i.TempNight'  % (count+1), '')
      set_property('Daily.%i.LowTemperature'  % (count+1), '')

    if item['tempLabel'] == 'Low':
      set_property('Daily.%i.LongDay'    % (count+1), item['startPeriodName'])
      set_property('Daily.%i.ShortDay'  % (count+1), get_weekday(startstamp,'s')+" (n)")
      set_property('Daily.%i.TempDay'    % (count+1), '')
      set_property('Daily.%i.HighTemperature'  % (count+1), '')
      if 'F' in TEMPUNIT:
        set_property('Daily.%i.TempNight'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
        set_property('Daily.%i.LowTemperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
      elif 'C' in TEMPUNIT:
        set_property('Daily.%i.TempNight'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
        set_property('Daily.%i.LowTemperature'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
      #set_property('Daily.%i.TempNight'  % (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
      #set_property('Daily.%i.LowTemperature'  % (count+1), u'%s\N{DEGREE SIGN}%s' % (item['temperature'], "F"))
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
      set_property('Daily.%i.LongDate'  % (count+1), get_month(startstamp, 'dl'))
      set_property('Daily.%i.ShortDate'  % (count+1), get_month(startstamp, 'ds'))
    else:
      set_property('Daily.%i.LongDate'  % (count+1), get_month(startstamp, 'ml'))
      set_property('Daily.%i.ShortDate'  % (count+1), get_month(startstamp, 'ms'))

    rain = item['pop']
    if rain and str(rain) and not "0" == str(rain):
      set_property('Daily.%i.ChancePrecipitation'  % (count+1), str(rain) + '%')
    else:
      ##set_property('Daily.%i.ChancePrecipitation'  % (count+1), '')
      clear_property('Daily.%i.ChancePrecipitation'  % (count+1))
      



  if daily_weather and 'currentobservation' in daily_weather:
    data=daily_weather['currentobservation']
    icon = "http://forecast.weather.gov/newimages/large/%s" % data.get('Weatherimage')
    code, rain = code_from_icon(icon)
    weathercode = WEATHER_CODES.get(code)

    set_property('Current.Location', data.get('name'))
    set_property('Current.RemoteIcon',icon) 
    set_property('Current.OutlookIcon', '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
    set_property('Current.FanartCode', weathercode)
    set_property('Current.Condition', FORECAST.get(data.get('Weather'), data.get('Weather')))
    set_property('Current.Humidity'  , str(data.get('Relh')))
    set_property('Current.DewPoint', str(FtoC(data.get('Dewp'))))
        
    try:
      temp=data.get('Temp')
      set_property('Current.Temperature',str(FtoC(temp))) # api values are in C
    except:
      #set_property('Current.Temperature','') 
      clear_property('Current.Temperature') 

    try:
      set_property('Current.Wind', str(round(float(data.get('Winds'))*1.609298167)))
    except:
      #set_property('Current.Wind','')
      clear_property('Current.Wind')

    try:
      set_property('Current.WindDirection', xbmc.getLocalizedString(WIND_DIR(int(data.get('Windd')))))
    except:
      #set_property('Current.WindDirection', '')
      clear_property('Current.WindDirection')

    try:
      set_property('Current.WindGust'  , str(SPEED(float(data.get('Gust'))/2.237)) + SPEEDUNIT)
    except:
      clear_property('Current.WindGust')
      ##set_property('Current.WindGust'  , '')

    if rain and str(rain) and not "0" == str(rain):
      set_property('Current.ChancePrecipitation', str(rain)+'%')
    else :
      clear_property('Current.ChancePrecipitation')

    # calculate feels like
    clear_property('Current.FeelsLike')
    try:
      feels = FEELS_LIKE( FtoC(data.get('Temp')), float(data.get('Winds'))/2.237, int(data.get('Relh')), False)
      set_property('Current.FeelsLike', str(feels))
    except:
      clear_property('Current.FeelsLike')
      #set_property('Current.FeelsLike', '')

    # if we have windchill or heatindex directly, then use that instead
    if data.get('WindChill') and not "NA" == data.get('WindChill'):
      set_property('Current.FeelsLike', str(FtoC(data.get('WindChill'))) )
    if data.get('HeatIndex') and not "NA" == data.get('HeatIndex'):
      set_property('Current.FeelsLike', str(FtoC(data.get('HeatIndex'))) )

    


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
  code = None
  rain = None
  if icon:
    if '?' in icon:
      icon=icon.rsplit('?', 1)[0]
    code, rain = code_from_icon(icon)
    weathercode = WEATHER_CODES.get(code)
    set_property('Current.RemoteIcon',icon) 
    set_property('Current.OutlookIcon', '%s.png' % weathercode) # xbmc translates it to Current.ConditionIcon
    set_property('Current.FanartCode', weathercode)

  set_property('Current.Condition', FORECAST.get(data.get('textDescription'), data.get('textDescription')))
  try:
    set_property('Current.Humidity'  , str(round(data.get('relativeHumidity').get('value'))))
  except:
    ##set_property('Current.Humidity'    , '')
    clear_property('Current.Humidity')
        
  try:
    temp=int(round(data.get('temperature').get('value')))
    set_property('Current.Temperature',str(temp)) # api values are in C
  except:
    ##set_property('Current.Temperature','') 
    clear_property('Current.Temperature') 
  try:
    set_property('Current.Wind', str(int(round(data.get('windSpeed').get('value')))))
  except:
    ##set_property('Current.Wind','')
    clear_property('Current.Wind')

  try:
    set_property('Current.WindDirection', xbmc.getLocalizedString(WIND_DIR(int(round(data.get('windDirection').get('value'))))))
  except:
    #set_property('Current.WindDirection', '')
    clear_property('Current.WindDirection')

  if rain and str(rain) and not "0" == str(rain):
    set_property('Current.ChancePrecipitation', str(rain)+'%')
  else :
    #set_property('Current.ChancePrecipitation', '')
    clear_property('Current.ChancePrecipitation')

  clear_property('Current.FeelsLike')
  #calculate feels like
  windspeed=data.get('windSpeed').get('value')
  if not windspeed:
    windspeed=0
  
  try:
    set_property('Current.FeelsLike', FEELS_LIKE(data.get('temperature').get('value'), float(windspeed)/3.6, data.get('relativeHumidity').get('value'), False))
  except:
    clear_property('Current.FeelsLike')

  # if we have windchill or heat index directly, then use that instead
  if data.get('windChill').get('value'):
    set_property('Current.FeelsLike', str(data.get('windChill').get('value')) )
  if data.get('heatIndex').get('value'):
    set_property('Current.FeelsLike', str(data.get('heatIndex').get('value')) )

  try:
    temp=int(round(data.get('dewpoint').get('value',0)))
    set_property('Current.DewPoint', str(temp)) # api values are in C
  except:
    set_property('Current.DewPoint', '') 



## extended properties

  try:
    set_property('Current.WindGust'  , SPEED(float(data.get('windGust').get('value',0))/3.6) + SPEEDUNIT)
  except:
    set_property('Current.WindGust'  , '')

  try:
    set_property('Current.SeaLevel'  , str(data.get('seaLevelPressure').get('value',0)))
  except:
    set_property('Current.SeaLevel'  , '')

  try:
    set_property('Current.GroundLevel' ,str(data.get('barometricPressure').get('value',0)))
  except:
    set_property('Current.GroundLevel'  , '')





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
    set_property('Alerts.IsFetched'  , 'true')
  else:
    clear_property('Alerts.IsFetched')
    xbmc.log('No current weather alerts from  %s' % url,level=xbmc.LOGDEBUG)
    return
  
  for count, item in enumerate(data, start=1):
    
    thisdata=item['properties']
    set_property('Alerts.%i.status'    % (count), str(thisdata['status']))  
    set_property('Alerts.%i.messageType'  % (count), str(thisdata['messageType']))  
    set_property('Alerts.%i.category'  % (count), str(thisdata['category']))  
    set_property('Alerts.%i.severity'  % (count), str(thisdata['severity']))  
    set_property('Alerts.%i.certainty'  % (count), str(thisdata['certainty']))  
    set_property('Alerts.%i.urgency'  % (count), str(thisdata['urgency']))  
    set_property('Alerts.%i.event'    % (count), str(thisdata['event']))  
    set_property('Alerts.%i.headline'  % (count), str(thisdata['headline']))  
    set_property('Alerts.%i.description'  % (count), str(thisdata['description']))  
    set_property('Alerts.%i.instruction'  % (count), str(thisdata['instruction']))  
    set_property('Alerts.%i.response'  % (count), str(thisdata['response']))  



########################################################################################
##  fetches hourly weather data
########################################################################################

def fetchHourly(num):

  log("SOURCEPREF: %s" % SOURCEPREF)

  url=ADDON.getSetting('Location'+str(num)+'forecastHourly_url')  
  if "preview-api.weather.gov" == SOURCEPREF:
    url=url.replace("https://api.weather.gov","https://preview-api.weather.gov")
    log("url-x: %s" % url)
  
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
  #api is currently returning a 0 % rain icon url, which is not valid, so need to clean it
  iconreplacepattern1 = re.compile(r"[,]0$")

# extended properties
  for count, item in enumerate(data['periods'], start = 0):
    
    icon=item['icon']
    #https://api.weather.gov/icons/land/night/ovc?size=small
    if icon:
      if '?' in icon:
        icon=icon.rsplit('?', 1)[0]
      code, rain=code_from_icon(icon)
      icon=iconreplacepattern1.sub("",icon)
    set_property('Hourly.%i.RemoteIcon'  % (count+1), icon)  

    weathercode = WEATHER_CODES.get(code)
    starttime=item['startTime']
    startstamp=get_timestamp(starttime)
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
      set_property('Hourly.%i.LongDate'  % (count+1), get_month(startstamp, 'dl'))
      set_property('Hourly.%i.ShortDate'  % (count+1), get_month(startstamp, 'ds'))
    else:
      set_property('Hourly.%i.LongDate'  % (count+1), get_month(startstamp, 'ml'))
      set_property('Hourly.%i.ShortDate'  % (count+1), get_month(startstamp, 'ms'))
  
    set_property('Hourly.%i.Time'      % (count+1), get_time(startstamp))
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
      set_property('Hourly.%i.LongDate'  % (count+1), get_month(startstamp, 'dl'))
      set_property('Hourly.%i.ShortDate'  % (count+1), get_month(startstamp, 'ds'))
    else:
      set_property('Hourly.%i.LongDate'  % (count+1), get_month(startstamp, 'ml'))
      set_property('Hourly.%i.ShortDate'  % (count+1), get_month(startstamp, 'ms'))

    set_property('Hourly.%i.Outlook'  % (count+1), FORECAST.get(item['shortForecast'], item['shortForecast']))
    set_property('Hourly.%i.ShortOutlook'  % (count+1), FORECAST.get(item['shortForecast'], item['shortForecast']))
    set_property('Hourly.%i.OutlookIcon'  % (count+1), WEATHER_ICON % weathercode)
    set_property('Hourly.%i.FanartCode'  % (count+1), weathercode)
    #set_property('Hourly.%i.Humidity'    % (count+1), str(item['main'].get('humidity','')) + '%')
    set_property('Hourly.%i.WindDirection'  % (count+1), item['windDirection'])
    set_property('Hourly.%i.WindSpeed'  % (count+1), item['windSpeed'])

    #set_property('Hourly.%i.Temperature'    % (count+1),  str(item['temperature'])+u'\N{DEGREE SIGN}'+item['temperatureUnit'])

    ## we passed units to api, so we got back C or F, so don't need to convert
    set_property('Hourly.%i.Temperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
    ##if 'F' in TEMPUNIT:
    ##  set_property('Hourly.%i.Temperature'  % (count+1), u'%s%s' % (item['temperature'], TEMPUNIT))
    ##elif 'C' in TEMPUNIT:
    ##  set_property('Hourly.%i.Temperature'  % (count+1), u'%s%s' % (FtoC(item['temperature']), TEMPUNIT))
  

    if rain and str(rain) and not "0" == str(rain):
      set_property('Hourly.%i.ChancePrecipitation'  % (count+1), str(rain) + '%')
    else:
      ##set_property('Hourly.%i.ChancePrecipitation'  % (count+1), '')
      clear_property('Hourly.%i.ChancePrecipitation'  % (count+1))
  count = 1


########################################################################################
##  Grabs map selection from user in settings
########################################################################################

def mapSettings(mapid):
  s_sel = ADDON.getSetting(mapid+"Sector")
  t_sel   = ADDON.getSetting(mapid+"Type")

  t_keys = []
  t_values= []

  #1st option is blank for removing map
  t_keys.append("")
  t_values.append("")


  for key,value in MAPTYPES.items():
    t_keys.append(key)
    t_values.append(value)    


  dialog = xbmcgui.Dialog()

  ti=0  
  try:
    ti=t_keys.index(t_sel)
  except:
    ti=0  
  ti=dialog.select(LANGUAGE(32350), t_values,0,ti)
  t_sel=t_keys[ti]
  ADDON.setSetting(mapid+"Type",t_keys[ti])





  if ti > 0:

    if ("LOOP" == t_sel):
      Sectors=LOOPSECTORS
    else:
      Sectors=MAPSECTORS  

    # convert our map data into matching arrays to pass into dialog
    s_keys = []
    s_values= []

    for key,value in Sectors.items():
      s_keys.append(key)
      s_values.append(value['name'])    

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
    ADDON.setSetting(mapid+"Label",Sectors[s_sel]['name']+":"+MAPTYPES[t_sel])
    ADDON.setSetting(mapid+"Select",Sectors[s_sel]['name']+":"+MAPTYPES[t_sel])
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
set_property('Forecast.IsFetched'  , 'true')
set_property('Current.IsFetched'  , 'true')
set_property('Today.IsFetched'    , '')
set_property('Daily.IsFetched'    , 'true')
set_property('Detailed.IsFetched'  , 'true')
set_property('Weekend.IsFetched'  , '')
set_property('36Hour.IsFetched'    , '')
set_property('Hourly.IsFetched'    , 'true')
set_property('NOAA.IsFetched'    , 'true')
set_property('WeatherProvider'    , 'NOAA')
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
    get_Stations(num,LatLong)

elif sys.argv[1].startswith('Map'):

  mapSettings(sys.argv[1])

else:

  num=sys.argv[1]
  LatLong = ADDON.getSetting('Location%sLatLong' % num)
  
  station=ADDON.getSetting('Location'+str(num)+'Station')
  if station == '' :
    log("calling location with %s" % (LatLong))
    get_Stations(str(num),LatLong)

  try:   
    lastPointsCheck=ADDON.getSetting('Location'+str(num)+'lastPointsCheck')
    last_check=parse(lastPointsCheck)
    current_datetime = datetime.datetime.now()
    next_check=last_check+datetime.timedelta(days=2)
    if (next_check < current_datetime):
      get_Points(str(num),LatLong)
  except: 
    get_Points(str(num),LatLong)

  refresh_locations()

  LatLong = ADDON.getSetting('Location%s' % num)

  if LatLong:
    fetchWeatherAlerts(num)
    if "forecast.weather.gov" == SOURCEPREF:
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

    #clean up previously fetched radar loop images
    imagepath=xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
    for f in glob.glob(imagepath+"radar*.gif"):
      os.remove(f)
    
    if ("true" == radarLoop):
      #kodi will not loop gifs from a url, we have to actually 
      #download to a local file to get it to loop
      
      #xbmc.log('Option To Loop Radar Selected',level=xbmc.LOGDEBUG)
      xbmc.log('Option To Loop Radar Selected',level=xbmc.LOGDEBUG)
      url="https://radar.weather.gov/ridge/standard/%s_loop.gif" % (Station)
      radarfilename="radar_%s_%s.gif" % (Station,nowtime)
      dest=imagepath+radarfilename
      loop_image=get_url_image(url, dest)
      set_property('Map.%i.Area' % 1, loop_image)
    else:
      url="https://radar.weather.gov/ridge/standard/%s_0.gif?%s" % (Station,nowtime)
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

        if ("LOOP" == maptype):
        # want looping radar gifs
          path=LOOPSECTORS.get(mapsector)['path']
          imagepath=xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
          url="https://radar.weather.gov/%s" % (path)
          radarfilename="radar_%s_%s.gif" % (mapsector,nowtime)
          dest=imagepath+radarfilename
          loop_image=get_url_image(url, dest)

          set_property('Map.%i.Area' % (mcount), loop_image)
          set_property('Map.%i.Heading' % (mcount), "%s" % (maplabel) )
          clear_property('Map.%i.Layer' % (mcount))
        else:
        # want normal satellite images
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
del FtoC, CtoF, log, ADDON, LANGUAGE, MAPSECTORS, LOOPSECTORS, MAPTYPES
del WEATHER_CODES, FORECAST, FEELS_LIKE, SPEED, WIND_DIR, SPEEDUNIT, zip_x 
del get_url_JSON, get_url_image
del get_month, get_timestamp, get_weekday, get_time



