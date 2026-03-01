# -*- coding: utf-8 -*-
from .utils import *

# convert weatherbit.io weather codes to kodi weather codes
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

# convert short day name to long localized day name (sun = sunday)
LONGDAY = { 'Mon' : 11,
            'Tue' : 12,
            'Wed' : 13,
            'Thu' : 14,
            'Fri' : 15,
            'Sat' : 16,
            'Sun' : 17,
            'Today': 33006,
            'Tomorrow': 33007}

# convert short day name to shor localized day name (sun = sun)
SHORTDAY = { 'Mon' : 41,
             'Tue' : 42,
             'Wed' : 43,
             'Thu' : 44,
             'Fri' : 45,
             'Sat' : 46,
             'Sun' : 47,
             'Today': 33006,
             'Tomorrow': 33007}

# convert day numbers to names (0 = sunday)
WEEK_DAY_LONG = { '0' : 17,
                  '1' : 11,
                  '2' : 12,
                  '3' : 13,
                  '4' : 14,
                  '5' : 15,
                  '6' : 16 }

# convert day numbers to short names (0 = sun)
WEEK_DAY_SHORT = { '0' : 47,
                   '1' : 41,
                   '2' : 42,
                   '3' : 43,
                   '4' : 44,
                   '5' : 45,
                   '6' : 46 }

# convert month numbers to names (01 = januari)
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

# convert month numbers to short names (01 = jan)
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

# convert moonphase string to localized string
MOONPHASE = { "new moon": LANGUAGE(32300),
              "waxing crescent": LANGUAGE(32301),
              "first quarter": LANGUAGE(32302),
              "waxing gibbous": LANGUAGE(32303),
              "full moon": LANGUAGE(32304),
              "waning gibbous": LANGUAGE(32305),
              "third quarter": LANGUAGE(32306),
              "waning crescent": LANGUAGE(32307)}

# convert yahoo forecast strings to icon codes
CONDITION = {"Tornado": LANGUAGE(32251),
            "Tropical Storm": LANGUAGE(32252),
            "Hurricane": LANGUAGE(32253),
            "Severe Thunderstorms": LANGUAGE(32254),
            "Thunderstorms": LANGUAGE(32255),
            "Mixed Rain and Snow": LANGUAGE(32256),
            "Mixed Rain and Sleet": LANGUAGE(32257),
            "Mixed Snow and Sleet": LANGUAGE(32258),
            "Freezing Drizzle": LANGUAGE(32259),
            "Drizzle": LANGUAGE(32260),
            "Freezing Rain": LANGUAGE(32261),
            "Showers": LANGUAGE(32262),
            "Rain": LANGUAGE(32263),
            "Snow Flurries": LANGUAGE(32264),
            "Light Snow Showers": LANGUAGE(32265),
            "Blowing Snow": LANGUAGE(32266),
            "Snow": LANGUAGE(32267),
            "Hail": LANGUAGE(32268),
            "Sleet": LANGUAGE(32269),
            "Dust": LANGUAGE(32270),
            "Foggy": LANGUAGE(32271),
            "Haze": LANGUAGE(32272),
            "Smoky": LANGUAGE(32273),
            "Blustery": LANGUAGE(32274),
            "Windy": LANGUAGE(32275),
            "Cold": LANGUAGE(32276),
            "Cloudy": LANGUAGE(32277),
            "Mostly Cloudy": LANGUAGE(32278),
            "Partly Cloudy": LANGUAGE(32279),
            "Clear": LANGUAGE(32280),
            "Sunny": LANGUAGE(32281),
            "Fair": LANGUAGE(32282),
            "Mixed Rain and Hail": LANGUAGE(32283),
            "Hot": LANGUAGE(32284),
            "Isolated Thunderstorms": LANGUAGE(32285),
            "Scattered Thunderstorms": LANGUAGE(32286),
            "Scattered Showers": LANGUAGE(32287),
            "Heavy Rain": LANGUAGE(32288),
            "Scattered Snow Showers": LANGUAGE(32289),
            "Heavy Snow": LANGUAGE(32290),
            "Blizzard": LANGUAGE(32291),
            "Not Available": LANGUAGE(32292),
            "Scattered Showers": LANGUAGE(32293),
            "Scattered Snow Showers": LANGUAGE(32294),
            "Scattered Thundershowers": LANGUAGE(32295),
            "Flurries": LANGUAGE(32245), # snow flurries
            "Mostly Sunny": LANGUAGE(32246), # fair day
            "Mostly Clear": LANGUAGE(32247), # fair night
            "Rain And Snow": LANGUAGE(32248), # sleet
            "Fog": LANGUAGE(32249), # foggy
            "Frigid": LANGUAGE(32250)} # cold

OUTLOOK = {"Tornado": "0",
           "Tropical Storm": "1",
           "Hurricane": "2",
           "Severe Thunderstorms": "3",
           "Thunderstorms": "4",
           "Mixed Rain and Snow": "5",
           "Mixed Rain and Sleet": "6",
           "Mixed Snow and Sleet": "7",
           "Freezing Drizzle": "8",
           "Drizzle": "9",
           "Freezing Rain": "10",
           "Showers": "11",
           "Rain": "12",
           "Snow Flurries": "13",
           "Light Snow Showers": "14",
           "Blowing Snow": "15",
           "Snow": "16",
           "Hail": "17",
           "Sleet": "18",
           "Dust": "19",
           "Foggy": "20",
           "Haze": "21",
           "Smoky": "22",
           "Blustery": "23",
           "Windy": "24",
           "Cold": "25",
           "Cloudy": "26",
           "Mostly Cloudy Night": "27",
           "Mostly Cloudy Day": "28",
           "Partly Cloudy Night": "29",
           "Partly Cloudy Day": "30",
           "Clear": "31",
           "Sunny": "32",
           "Fair Night": "33",
           "Fair Day": "34",
           "Mixed Rain and Hail": "35",
           "Hot": "36",
           "Isolated Thunderstorms": "37",
           "Scattered Thunderstorms": "38",
           "Scattered Showers": "39",
           "Heavy Rain": "40",
           "Scattered Snow Showers": "41",
           "Heavy Snow": "42",
           "Blizzard": "43",
           "Not Available": "44",
           "Scattered Showers": "45",
           "Scattered Snow Showers": "46",
           "Scattered Thundershowers": "47",
           "Flurries": "13", # snow flurries
           "Mostly Sunny": "34", # fair day
           "Mostly Clear": "33", # fair night
           "Rain And Snow": "18", # sleet
           "Fog": "20", # foggy
           "Frigid": "25"} # cold

# convert weatherbit.io forecast codes to localized strings
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

# convert winddir string to localized string
WINDDIR = {"north": 71,
           "northeast": 73,
           "east": 75,
           "southeast": 77,
           "south": 79,
           "southwest": 81,
           "west": 83,
           "northwest": 85,
           "variable": 87}

# convert timestamp to localized time and date
# stamp (input value): either datetime (2020-02-28T22:00:00.000Z), timestamp (1582871381), daynumber (1) or AM/PM time
# inpt (input format) either 'datetime', 'timestamp', 'seconds' (after midnight), 'day' or 'ampm'
# outpt (return value) time+date, month+day, weekday, time
# form (output format) either long or short names 
def convert_datetime(stamp, inpt, outpt, form):
    if inpt == 'datetime':
        timestruct = time.strptime(stamp[:-5], "%Y-%m-%dT%H:%M:%S")
    elif inpt == 'timestamp':
        timestruct = time.localtime(stamp)
    elif inpt == 'seconds':
        m, s = divmod(stamp, 60)
        h, m = divmod(m, 60)
        hm = "%02d:%02d" % (h, m)
        timestruct = time.strptime(hm, "%H:%M")
    elif inpt == 'ampm':
        if stamp == 'Now':
            return stamp
        elif stamp == 'Midnight':
            stamp = '12:00 AM'
        elif stamp == 'Noon':
            stamp = '12:00 PM'
        if TIMEFORMAT != '/':
            return stamp
        else:
            try:
                timestruct = time.strptime(stamp, '%I:%M %p')
            except:
                timestruct = time.strptime(stamp, '%I %p')
            return time.strftime('%H:%M', timestruct)
    if outpt == 'timedate':
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
        label = localtime + '  ' + localdate
    elif outpt == 'monthday':
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
    elif outpt == 'weekday':
        if inpt == 'day':
            weekday = str(stamp)
        else:
            weekday = time.strftime('%w', timestruct)
        if form == 'short':
            label = xbmc.getLocalizedString(WEEK_DAY_SHORT[weekday])
        elif form == 'long':
            label =  xbmc.getLocalizedString(WEEK_DAY_LONG[weekday])
    elif outpt == 'time':
        if TIMEFORMAT != '/':
            label = time.strftime('%I:%M %p', timestruct)
        else:
            label = time.strftime('%H:%M', timestruct)
    return label

# convert temperature in Fahrenheit or Celcius to other formats
# val: temperature
# inf (input format): 'F' (fahrenheit) or 'C' (celcius)
# outf (force output format): 'C' (celcius)
def convert_temp(val, inf, outf=None):
    if inf == 'F':
        #fahrenheit to celcius
        val = (float(val)-32) * 5/9
    else:
        val = float(val)
    if outf == 'C':
        temp = val
    elif TEMPUNIT == u'°F':
        temp = val * 1.8 + 32
    elif TEMPUNIT == u'K':
        temp = val + 273.15
    elif TEMPUNIT == u'°Ré':
        temp = val * 0.8
    elif TEMPUNIT == u'°Ra':
        temp = val * 1.8 + 491.67
    elif TEMPUNIT == u'°Rø':
        temp = val * 0.525 + 7.5
    elif TEMPUNIT == u'°D':
        temp = val / -0.667 + 150
    elif TEMPUNIT == u'°N':
        temp = val * 0.33
    else:
        temp = val
    return str(int(round(temp)))

# convert speed in mph or mps to other formats
# val: speed
# inf (input format): 'mph' (miles per hour) or 'mps' (metre per seconds)
# outf (force output format): 'kmh' (kilometre per hour)
def convert_speed(val, inf, outf=None):
    if inf == 'mph':
        val = float(val) / 2.237
    if outf == 'kmh':
        speed = val * 3.6
    elif SPEEDUNIT == 'km/h':
        speed = val * 3.6
    elif SPEEDUNIT == 'm/min':
        speed = val * 60.0
    elif SPEEDUNIT == 'ft/h':
        speed = val * 11810.88
    elif SPEEDUNIT == 'ft/min':
        speed = val * 196.84
    elif SPEEDUNIT == 'ft/s':
        speed = val * 3.281
    elif SPEEDUNIT == 'mph':
        speed = val * 2.237
    elif SPEEDUNIT == 'knots':
        speed = val * 1.944
    elif SPEEDUNIT == 'Beaufort':
        speed = float(KPHTOBFT(val* 3.6))
    elif SPEEDUNIT == 'inch/s':
        speed = val * 39.37
    elif SPEEDUNIT == 'yard/s':
        speed = val * 1.094
    elif SPEEDUNIT == 'Furlong/Fortnight':
        speed = val * 6012.886
    else:
        speed = val
    return str(int(round(speed)))

# convert windspeed in km/h to beaufort
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

# convert weatherbit winddirection in degrees to a string (eg. NNW)
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

# calculate windchill in fahrenheit from temperature in fahrenheit and windspeed in mph
def windchill(temp, speed):
    if temp < 51 and speed > 2:
        windchill = str(int(round(35.74 + 0.6215 * temp - 35.75 * (speed**0.16) + 0.4275 * temp * (speed**0.16))))
    else:
        windchill = temp
    return windchill

# calculate dewpoint celcius from temperature in celcius and humidity
def dewpoint(Tc=0, RH=93, minRH=(0, 0.075)[0]):
    """ Dewpoint from relative humidity and temperature
        If you know the relative humidity and the air temperature,
        and want to calculate the dewpoint, the formulas are as follows.
        
        getDewPoint(tCelsius, humidity)
    """
    #First, if your air temperature is in degrees Fahrenheit, then you must convert it to degrees Celsius by using the Fahrenheit to Celsius formula.
    # Tc = 5.0 / 9.0 * (Tf - 32.0)
    #The next step is to obtain the saturation vapor pressure(Es) using this formula as before when air temperature is known.
    Es = 6.11 * 10.0**(7.5 * Tc / (237.7 + Tc))
    #The next step is to use the saturation vapor pressure and the relative humidity to compute the actual vapor pressure(E) of the air. This can be done with the following formula.
    #RH=relative humidity of air expressed as a percent. or except minimum(.075) humidity to abort error with math.log.
    RH = RH or minRH #0.075
    E = (RH * Es) / 100
    #Note: math.log() means to take the natural log of the variable in the parentheses
    #Now you are ready to use the following formula to obtain the dewpoint temperature.
    try:
        DewPoint = (-430.22 + 237.7 * math.log(E)) / (-math.log(E) + 19.08)
    except ValueError:
        #math domain error, because RH = 0%
        #return "N/A"
        DewPoint = 0 #minRH
    #Note: Due to the rounding of decimal places, your answer may be slightly different from the above answer, but it should be within two degrees.
    return str(int(round(DewPoint)))
