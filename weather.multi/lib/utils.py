# -*- coding: utf-8 -*-
import time
import _strptime
import math
import xbmc
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
LANGUAGE = ADDON.getLocalizedString

DEBUG = ADDON.getSettingBool('Debug')

WEATHER_WINDOW = xbmcgui.Window(12600)

TEMPUNIT   = xbmc.getRegion('tempunit')
DATEFORMAT = xbmc.getRegion('dateshort')
TIMEFORMAT = xbmc.getRegion('meridiem')
SPEEDUNIT = xbmc.getRegion('speedunit')
MAXDAYS = 6

WEATHER_CODES = { '200d': '4',
                  '201d': '4',
                  '202d': '3',
                  '230d': '4',
                  '231d': '4',
                  '232d': '3',
                  '233d': '4',
                  '300d': '9',
                  '301d': '9',
                  '302d': '9',
                  '500d': '11',
                  '501d': '11',
                  '502d': '11',
                  '511d': '10',
                  '520d': '11',
                  '521d': '11',
                  '522d': '11',
                  '600d': '13',
                  '601d': '14',
                  '602d': '16',
                  '610d': '5',
                  '611d': '18',
                  '612d': '18',
                  '621d': '14',
                  '622d': '16',
                  '623d': '13',
                  '700d': '20',
                  '711d': '22',
                  '721d': '21',
                  '731d': '19',
                  '741d': '20',
                  '751d': '8',
                  '800d': '32',
                  '801d': '34',
                  '802d': '30',
                  '803d': '28',
                  '804d': '26',
                  '900d': 'na',
                  '200n': '4',
                  '201n': '4',
                  '202n': '3',
                  '230n': '4',
                  '231n': '4',
                  '232n': '3',
                  '233n': '4',
                  '300n': '9',
                  '301n': '9',
                  '302n': '9',
                  '500n': '11',
                  '501n': '11',
                  '502n': '11',
                  '511n': '10',
                  '520n': '11',
                  '521n': '11',
                  '522n': '11',
                  '600n': '13',
                  '601n': '14',
                  '602n': '16',
                  '610n': '5',
                  '611n': '18',
                  '612n': '18',
                  '621n': '14',
                  '622n': '16',
                  '623n': '13',
                  '700n': '20',
                  '711n': '22',
                  '721n': '21',
                  '731n': '19',
                  '741n': '20',
                  '751n': '8',
                  '800n': '31',
                  '801n': '33',
                  '802n': '29',
                  '803n': '27',
                  '804n': '27',
                  '900n': 'na' }

WEEK_DAY_LONG = { '0' : 17,
                  '1' : 11,
                  '2' : 12,
                  '3' : 13,
                  '4' : 14,
                  '5' : 15,
                  '6' : 16 }

WEEK_DAY_SHORT = { '0' : 47,
                   '1' : 41,
                   '2' : 42,
                   '3' : 43,
                   '4' : 44,
                   '5' : 45,
                   '6' : 46 }

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
                    '12' : 32 }

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
                     '12' : 62 }

MOONPHASE = { 0: LANGUAGE(32300),
              1: LANGUAGE(32301),
              2: LANGUAGE(32302),
              3: LANGUAGE(32303),
              4: LANGUAGE(32304),
              5: LANGUAGE(32305),
              6: LANGUAGE(32306),
              7: LANGUAGE(32307)}

FORECAST = { '200': LANGUAGE(32201),
             '201': LANGUAGE(32202),
             '202': LANGUAGE(32203),
             '230': LANGUAGE(32204),
             '231': LANGUAGE(32205),
             '232': LANGUAGE(32206),
             '233': LANGUAGE(32207),
             '300': LANGUAGE(32208),
             '301': LANGUAGE(32209),
             '302': LANGUAGE(32210),
             '500': LANGUAGE(32211),
             '501': LANGUAGE(32212),
             '502': LANGUAGE(32213),
             '511': LANGUAGE(32214),
             '520': LANGUAGE(32215),
             '521': LANGUAGE(32216),
             '522': LANGUAGE(32217),
             '600': LANGUAGE(32218),
             '601': LANGUAGE(32219),
             '602': LANGUAGE(32220),
             '610': LANGUAGE(32221),
             '611': LANGUAGE(32222),
             '612': LANGUAGE(32223),
             '621': LANGUAGE(32224),
             '622': LANGUAGE(32225),
             '623': LANGUAGE(32226),
             '700': LANGUAGE(32227),
             '711': LANGUAGE(32228),
             '721': LANGUAGE(32229),
             '731': LANGUAGE(32230),
             '741': LANGUAGE(32231),
             '751': LANGUAGE(32232),
             '800': LANGUAGE(32233),
             '801': LANGUAGE(32234),
             '802': LANGUAGE(32235),
             '803': LANGUAGE(32236),
             '804': LANGUAGE(32237),
             '900': LANGUAGE(32238) }

def convert_datetime(stamp):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
        localdate = time.strftime('%d-%m-%Y', timestruct)
    elif DATEFORMAT[1] == 'm' or DATEFORMAT[0] == 'M':
        localdate = time.strftime('%m-%d-%Y', timestruct)
    else:
        localdate = time.strftime('%Y-%m-%d', timestruct)
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M %p', timestruct)
    else:
        localtime = time.strftime('%H:%M', timestruct)
    return localtime + '  ' + localdate

def convert_date(stamp):
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
    return localtime + '  ' + localdate

def get_date(stamp, form):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    month = time.strftime('%m', timestruct)
    day = time.strftime('%d', timestruct)
    if form == 'short':
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_SHORT[month])
        else:
            label = xbmc.getLocalizedString(MONTH_NAME_SHORT[month]) + ' ' + day
    elif form == 'long':
        if DATEFORMAT[1] == 'd' or DATEFORMAT[0] == 'D':
            label = day + ' ' + xbmc.getLocalizedString(MONTH_NAME_LONG[month])
        else:
            label = xbmc.getLocalizedString(MONTH_NAME_LONG[month]) + ' ' + day
    return label

def get_time(stamp):
    timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    if TIMEFORMAT != '/':
        localtime = time.strftime('%I:%M %p', timestruct)
    else:
        localtime = time.strftime('%H:%M', timestruct)
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

def convert_temp(temp):
    celc = (float(temp)-32) * 5/9
    return str(int(round(celc)))

def convert_speed(speed):
    kmh = float(speed) * 1.609
    return str(int(round(kmh)))

def convert_seconds(sec):
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    hm = "%02d:%02d" % (h, m)
    if TIMEFORMAT != '/':
        timestruct = time.strptime(hm, "%H:%M")
        hm = time.strftime('%I:%M %p', timestruct)
    return hm

def log(txt):
    if DEBUG:
        message = '%s: %s' % (ADDONID, txt)
        xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def YTEMP(deg, unit='F'):
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

def YSPEED(mph):
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

def SPEED(mps):
    if SPEEDUNIT == 'km/h':
        speed = mps * 3.6
    elif SPEEDUNIT == 'm/min':
        speed = mps * 60.0
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

def TEMP(deg):
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
