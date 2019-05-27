# -*- coding: utf-8 -*-

import math
import xbmc
import xbmcaddon

TEMPUNIT   = unicode(xbmc.getRegion('tempunit'),encoding='utf-8')
DATEFORMAT = xbmc.getRegion('dateshort')
TIMEFORMAT = xbmc.getRegion('meridiem')
SPEEDUNIT = xbmc.getRegion('speedunit')
MAXDAYS = 6

LDAYS = { 1: xbmc.getLocalizedString( 11 ),
          2: xbmc.getLocalizedString( 12 ),
          3: xbmc.getLocalizedString( 13 ),
          4: xbmc.getLocalizedString( 14 ),
          5: xbmc.getLocalizedString( 15 ),
          6: xbmc.getLocalizedString( 16 ),
          0: xbmc.getLocalizedString( 17 )}

DAYS = { 1: xbmc.getLocalizedString( 41 ),
         2: xbmc.getLocalizedString( 42 ),
         3: xbmc.getLocalizedString( 43 ),
         4: xbmc.getLocalizedString( 44 ),
         5: xbmc.getLocalizedString( 45 ),
         6: xbmc.getLocalizedString( 46 ),
         0: xbmc.getLocalizedString( 47 )}

LMONTHS = { '01' : 21,
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
            '12' : 32 }

MONTHS = { '01' : 51,
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
           '12' : 62 }

MOONPHASE = { 0: xbmcaddon.Addon().getLocalizedString(32200),
              1: xbmcaddon.Addon().getLocalizedString(32201),
              2: xbmcaddon.Addon().getLocalizedString(32202),
              3: xbmcaddon.Addon().getLocalizedString(32203),
              4: xbmcaddon.Addon().getLocalizedString(32204),
              5: xbmcaddon.Addon().getLocalizedString(32205),
              6: xbmcaddon.Addon().getLocalizedString(32206),
              7: xbmcaddon.Addon().getLocalizedString(32207)}

def TEMP(deg, unit='F'):
    if unit == 'F':
        #fahrenheit to celcius
        deg = (float(deg)-32) * 5/9
    else:
        deg = float(deg)
    if TEMPUNIT == u'°F':
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

def SPEED(mph):
    mps = float(mph) / 2.237
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
        speed = float(KPHTOBFT(mps* 3.6))
    elif SPEEDUNIT == 'inch/s':
        speed = mps * 39.37
    elif SPEEDUNIT == 'yard/s':
        speed = mps * 1.094
    elif SPEEDUNIT == 'Furlong/Fortnight':
        speed = mps * 6012.886
    else:
        speed = mps
    return str(int(round(speed)))

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

def WIND_DIR(deg):
    if deg >= 349 or deg <=  11:
        return 71
    elif deg >= 12 and deg <= 33:
        return 72
    elif deg >= 34 and deg <=  56:
        return 73
    elif deg >= 57 and deg <=  78:
        return 74
    elif deg >= 79 and deg <=  101:
        return 75
    elif deg >= 102 and deg <=  123:
        return 76
    elif deg >= 124 and deg <=  146:
        return 77
    elif deg >= 147 and deg <=  168:
        return 78
    elif deg >= 169 and deg <=  191:
        return 79
    elif deg >= 192 and deg <=  213:
        return 80
    elif deg >= 214 and deg <=  236:
        return 81
    elif deg >= 237 and deg <=  258:
        return 82
    elif deg >= 259 and deg <=  281:
        return 83
    elif deg >= 282 and deg <=  303:
        return 84
    elif deg >= 304 and deg <=  326:
        return 85
    elif deg >= 327 and deg <=  348:
        return 86

def windchill(temp,speed):
    if temp < 51 and speed > 2:
        windchill = str(int(round(35.74 + 0.6215 * temp - 35.75 * (speed**0.16) + 0.4275 * temp * (speed**0.16))))
    else:
        windchill = temp
    return windchill

def dewpoint( Tc=0, RH=93, minRH=( 0, 0.075 )[ 0 ] ):
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
    return str(int(round(DewPoint)))
