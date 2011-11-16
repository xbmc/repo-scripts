# -*- coding: utf-8 -*- 

import sys
import xbmc
import math

__scriptname__ = sys.modules[ "__main__" ].__scriptname__

DAYS = { 1: xbmc.getLocalizedString( 11 ), 
         2: xbmc.getLocalizedString( 12 ), 
         3: xbmc.getLocalizedString( 13 ), 
         4: xbmc.getLocalizedString( 14 ), 
         5: xbmc.getLocalizedString( 15 ), 
         6: xbmc.getLocalizedString( 16 ), 
         0: xbmc.getLocalizedString( 17 )}
         
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
  
  
#### below thanks to FrostBox @ http://forum.xbmc.org/showthread.php?p=937168#post937168  

def getFeelsLike( T=10, V=25 ): 
    """ The formula to calculate the equivalent temperature related to the wind chill is: 
        T(REF) = 13.12 + 0.6215 * T - 11.37 * V**0.16 + 0.3965 * T * V**0.16 
        Or: 
        T(REF): is the equivalent temperature in degrees Celsius 
        V: is the wind speed in km/h measured at 10m height 
        T: is the temperature of the air in degrees Celsius 
        source: http://zpag.tripod.com/Meteo/eolien.htm
        
        getFeelsLike( tCelsius, windspeed )
    """ 
    FeelsLike = T 
    #Wind speeds of 4 mph or less, the wind chill temperature is the same as the actual air temperature. 
    if round( ( V + .0 ) / 1.609344 ) > 4: 
        FeelsLike = ( 13.12 + ( 0.6215 * T ) - ( 11.37 * V**0.16 ) + ( 0.3965 * T * V**0.16 ) ) 
    # 
    return str( round( FeelsLike ) ) 
    
    
def getDewPoint( Tc=0, RH=93, minRH=( 0, 0.075 )[ 0 ] ): 
    """ Dewpoint from relative humidity and temperature 
        If you know the relative humidity and the air temperature, 
        and want to calculate the dewpoint, the formulas are as follows. 
        
        getDewPoint( tCelsius, humidity )
    """ 
    #First, if your air temperature is in degrees Fahrenheit, then you must convert it to degrees Celsius by using the Fahrenheit to Celsius formula. 
    # Tc = 5.0 / 9.0 * ( Tf - 32.0 ) 
    #The next step is to obtain the saturation vapor pressure(Es) using this formula as before when air temperature is known. 
    Es = 6.11 * 10.0**( 7.5 * Tc / ( 237.7 + Tc ) ) 
    #The next step is to use the saturation vapor pressure and the relative humidity to compute the actual vapor pressure(E) of the air. This can be done with the following formula. 
    #RH=relative humidity of air expressed as a percent. or except minimum(.075) humidity to abort error with math.log. 
    RH = RH or minRH #0.075 
    E = ( RH * Es ) / 100 
    #Note: math.log( ) means to take the natural log of the variable in the parentheses 
    #Now you are ready to use the following formula to obtain the dewpoint temperature. 
    try: 
        DewPoint = ( -430.22 + 237.7 * math.log( E ) ) / ( -math.log( E ) + 19.08 ) 
    except ValueError: 
        #math domain error, because RH = 0% 
        #return "N/A" 
        DewPoint = 0 #minRH 
    #Note: Due to the rounding of decimal places, your answer may be slightly different from the above answer, but it should be within two degrees. 
    return str( int( DewPoint ) )  
  