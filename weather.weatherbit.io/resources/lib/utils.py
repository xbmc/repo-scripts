# -*- coding: utf-8 -*-

import math
import xbmc, xbmcgui, xbmcaddon

ADDON      = xbmcaddon.Addon()
ADDONID    = ADDON.getAddonInfo('id')
LANGUAGE   = ADDON.getLocalizedString

WEATHER_WINDOW = xbmcgui.Window(12600)
DEBUG          = ADDON.getSetting('Debug')
TEMPUNIT       = unicode(xbmc.getRegion('tempunit'),encoding='utf-8')
SPEEDUNIT      = xbmc.getRegion('speedunit')

def log(txt):
    if DEBUG == 'true':
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDONID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

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
