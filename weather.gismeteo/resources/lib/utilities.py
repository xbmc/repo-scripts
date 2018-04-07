# -*- coding: utf-8 -*-
# Module: utilities
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import math
from .simpleweather import Weather

weather = Weather()

TEMPUNIT   = weather.tempunit
SPEEDUNIT  = weather.speedunit
PRESUNIT   = ['mmHg','hPa', 'mbar', 'inHg'][weather.get_setting("PresUnit")]
PRECIPUNIT = ['mm', 'inch'][weather.get_setting("PrecipUnit")]

         # kodi lang name          # gismeteo code
LANG = { 'afrikaans'             : '',
         'albanian'              : '',
         'amharic'               : '',
         'arabic'                : '',
         'armenian'              : '',
         'azerbaijani'           : '',
         'basque'                : '',
         'belarusian'            : 'ru',
         'bosnian'               : '',
         'bulgarian'             : '',
         'burmese'               : '',
         'catalan'               : '',
         'chinese (simple)'      : '',
         'chinese (traditional)' : '',
         'croatian'              : '',
         'czech'                 : '',
         'danish'                : '',
         'dutch'                 : '',
         'english'               : 'en',
         'english (us)'          : 'en',
         'english (australia)'   : 'en',
         'english (new zealand)' : 'en',
         'esperanto'             : '',
         'estonian'              : '',
         'faroese'               : '',
         'finnish'               : '',
         'french'                : '',
         'galician'              : '',
         'german'                : 'de',
         'greek'                 : '',
         'georgian'              : '',
         'hebrew'                : '',
         'hindi (devanagiri)'    : '',
         'hungarian'             : '',
         'icelandic'             : '',
         'indonesian'            : '',
         'italian'               : '',
         'japanese'              : '',
         'korean'                : '',
         'latvian'               : 'lt',
         'lithuanian'            : 'li',
         'macedonian'            : '',
         'malay'                 : '',
         'malayalam'             : '',
         'maltese'               : '',
         'maori'                 : '',
         'mongolian (mongolia)'  : '',
         'norwegian'             : '',
         'ossetic'               : '',
         'persian'               : '',
         'persian (iran)'        : '',
         'polish'                : 'pl',
         'portuguese'            : '',
         'portuguese (brazil)'   : '',
         'romanian'              : 'ro',
         'russian'               : 'ru',
         'serbian'               : '',
         'serbian (cyrillic)'    : '',
         'sinhala'               : '',
         'slovak'                : '',
         'slovenian'             : '',
         'spanish'               : '',
         'spanish (argentina)'   : '',
         'spanish (mexico)'      : '',
         'swedish'               : '',
         'tajik'                 : '',
         'tamil (india)'         : '',
         'telugu'                : '',
         'thai'                  : '',
         'turkish'               : '',
         'ukrainian'             : 'ua',
         'uzbek'                 : '',
         'vietnamese'            : '',
         'welsh'                 : '' }

WEATHER_CODES = {'c4':          '26',
                 'c4.st':       '26',
                 'c4.r1':       '11',
                 'c4.r1.st':    '4',
                 'c4.r2':       '11',
                 'c4.r2.st':    '4',
                 'c4.r3':       '12',
                 'c4.r3.st':    '4',
                 'c4.s1':       '16',
                 'c4.s1.st':    '16',
                 'c4.s2':       '16',
                 'c4.s2.st':    '16',
                 'c4.s3':       '16',
                 'c4.s3.st':    '16',
                 'c4.rs1':      '5',
                 'c4.rs1.st':   '5',
                 'c4.rs2':      '5',
                 'c4.rs2.st':   '5',
                 'c4.rs3':      '5',
                 'c4.rs3.st':   '5',
                 'd':           '32',
                 'd.st':        '32',
                 'd.c2':        '30',
                 'd.c2.r1':     '39',
                 'd.c2.r1.st':  '37',
                 'd.c2.r2':     '39',
                 'd.c2.r2.st':  '37',
                 'd.c2.r3':     '39',
                 'd.c2.r3.st':  '37',
                 'd.c2.rs1':    '42',
                 'd.c2.rs1.st': '42',
                 'd.c2.rs2':    '42',
                 'd.c2.rs2.st': '42',
                 'd.c2.rs3':    '42',
                 'd.c2.rs3.st': '42',
                 'd.c2.s1':     '41',
                 'd.c2.s1.st':  '41',
                 'd.c2.s2':     '41',
                 'd.c2.s2.st':  '41',
                 'd.c2.s3':     '41',
                 'd.c2.s3.st':  '41',
                 'd.c3':        '28',
                 'd.c3.r1':     '11',
                 'd.c3.r1.st':  '38',
                 'd.c3.r2':     '11',
                 'd.c3.r2.st':  '38',
                 'd.c3.r3':     '11',
                 'd.c3.r3.st':  '38',
                 'd.c3.s1':     '14',
                 'd.c3.s1.st':  '14',
                 'd.c3.s2':     '14',
                 'd.c3.s2.st':  '14',
                 'd.c3.s3':     '14',
                 'd.c3.s3.st':  '14',
                 'd.c3.rs1':    '42',
                 'd.c3.rs1.st': '42',
                 'd.c3.rs2':    '42',
                 'd.c3.rs2.st': '42',
                 'd.c3.rs3':    '42',
                 'd.c3.rs3.st': '42',
                 'n':           '31',
                 'n.st':        '31',
                 'n.c2':        '29',
                 'n.c2.r1':     '45',
                 'n.c2.r1.st':  '47',
                 'n.c2.r2':     '45',
                 'n.c2.r2.st':  '47',
                 'n.c2.r3':     '45',
                 'n.c2.r3.st':  '47',
                 'n.c2.rs1':    '42',
                 'n.c2.rs1.st': '42',
                 'n.c2.rs2':    '42',
                 'n.c2.rs2.st': '42',
                 'n.c2.rs3':    '42',
                 'n.c2.rs3.st': '42',
                 'n.c2.s1':     '46',
                 'n.c2.s1.st':  '46',
                 'n.c2.s2':     '46',
                 'n.c2.s2.st':  '46',
                 'n.c2.s3':     '46',
                 'n.c2.s3.st':  '46',
                 'n.c3':        '27',
                 'n.c3.r1':     '11',
                 'n.c3.r1.st':  '4',
                 'n.c3.r2':     '11',
                 'n.c3.r2.st':  '4',
                 'n.c3.r3':     '11',
                 'n.c3.r3.st':  '4',
                 'n.c3.rs1':    '42',
                 'n.c3.rs1.st': '42',
                 'n.c3.rs2':    '42',
                 'n.c3.rs2.st': '42',
                 'n.c3.rs3':    '42',
                 'n.c3.rs3.st': '42',
                 'n.c3.s1':     '14',
                 'n.c3.s1.st':  '14',
                 'n.c3.s2':     '14',
                 'n.c3.s2.st':  '14',
                 'n.c3.s3':     '14',
                 'n.c3.s3.st':  '14',
                 'mist':        '32',
                 'r1.mist':     '11',
                 'r1.st.mist':  '38',
                 'r2.mist':     '11',
                 'r2.st.mist':  '38',
                 'r3.mist':     '11',
                 'r3.st.mist':  '38',
                 's1.mist':     '14',
                 's1.st.mist':  '14',
                 's2.mist':     '14',
                 's2.st.mist':  '14',
                 's3.mist':     '14',
                 's3.st.mist':  '14',
                 'rs1.mist':    '42',
                 'rs1.st.mist': '42',
                 'rs2.mist':    '42',
                 'rs2.st.mist': '42',
                 'rs3.mist':    '42',
                 'rs3.st.mist': '42',
                 'nodata':      'na'}

WIND_DIRECTIONS = {'1': 71,
                   '2': 73,
                   '3': 75,
                   '4': 77,
                   '5': 79,
                   '6': 81,
                   '7': 83,
                   '8': 85}

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

def SPEED(mps):
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
    elif SPEEDUNIT in ['knots', 'kts']:
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

    if isinstance(speed, str):
        return speed
    else:
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
    elif TEMPUNIT in [u'°D', u'°De']:
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

#### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
def DEW_POINT(Tc=0, RH=93, ext=True, minRH=( 0, 0.075 )[ 0 ]):
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

def PRESSURE(mmHg):
    if PRESUNIT == 'mmHg':
        return '%.0f' % (float(mmHg))
    elif PRESUNIT in ['hPa', 'mbar']:
        return '%.0f' % (float(mmHg * 1.3332239))
    elif PRESUNIT == 'inHg':
        return '%.2f' % (float(mmHg * 0.0393701))

def PRECIPITATION(mm):
    if PRECIPUNIT == 'mm':
        return '%.1f' % (float(mm))
    elif PRECIPUNIT == 'inch':
        return '%.2f' % (float(mm) * 0.0393701)
