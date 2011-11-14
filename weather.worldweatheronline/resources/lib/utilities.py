# -*- coding: utf-8 -*- 

import sys
import xbmc

__scriptname__ = sys.modules[ "__main__" ].__scriptname__

DAYS = { "Mon": xbmc.getLocalizedString( 11 ), 
         "Tue": xbmc.getLocalizedString( 12 ), 
         "Wed": xbmc.getLocalizedString( 13 ), 
         "Thu": xbmc.getLocalizedString( 14 ), 
         "Fri": xbmc.getLocalizedString( 15 ), 
         "Sat": xbmc.getLocalizedString( 16 ), 
         "Sun": xbmc.getLocalizedString( 17 )}
         
WEATHER_CODES = { '395' : '42',   # Moderate or heavy snow in area with thunder
                  '392' : '14',   # Patchy light snow in area with thunder
                  '389' : '40',   # Moderate or heavy rain in area with thunder
                  '386' : '3',    # Patchy light rain in area with thunder
                  '377' : '18',   # Moderate or heavy showers of ice pellets
                  '374' : '18',   # Light showers of ice pellets
                  '371' : '16',   # Moderate or heavy snow showers
                  '368' : '14',   # Light snow showers
                  '365' : '6',    # Moderate or heavy sleet showers
                  '362' : '6',    # Light sleet showers
                  '359' : '12',   # Torrential rain shower
                  '356' : '40',   # Moderate or heavy rain shower
                  '353' : '39',   # Light rain shower
                  '350' : '18',   # Ice pellets
                  '338' : '42',   # Heavy snow
                  '335' : '16',   # Patchy heavy snow
                  '332' : '41',   # Moderate snow
                  '329' : '14',   # Patchy moderate snow
                  '326' : '14',   # Light snow
                  '323' : '14',   # Patchy light snow
                  '320' : '6',    # Moderate or heavy sleet
                  '317' : '6',    # Light sleet
                  '314' : '10',   # Moderate or Heavy freezing rain
                  '311' : '10',   # Light freezing rain
                  '308' : '40',   # Heavy rain
                  '305' : '39',   # Heavy rain at times
                  '302' : '40',   # Moderate rain
                  '299' : '39',   # Moderate rain at times
                  '296' : '11',   # Light rain
                  '293' : '11',   # Patchy light rain
                  '284' : '8',    # Heavy freezing drizzle
                  '281' : '8',    # Freezing drizzle
                  '266' : '9',    # Light drizzle
                  '263' : '9',    # Patchy light drizzle
                  '260' : '20',   # Freezing fog
                  '248' : '20',   # Fog
                  '230' : '42',   # Blizzard
                  '227' : '43',   # Blowing snow
                  '200' : '35',   # Thundery outbreaks in nearby
                  '185' : '8',    # Patchy freezing drizzle nearby
                  '182' : '6',    # Patchy sleet nearby
                  '179' : '41',   # Patchy snow nearby
                  '176' : '39',   # Patchy rain nearby
                  '143' : '20',   # Mist
                  '122' : '26',   # Overcast
                  '119' : '26',   # Cloudy
                  '116' : '30',   # Partly Cloudy
                  '113' : '32'    # Clear/Sunny
                  }

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG ) 