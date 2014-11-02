import math

#http://openweathermap.org/current#multi
        # xbmc lang name         # openweathermap code
LANG = { 'afrikaans'             : '',
         'albanian'              : '',
         'amharic'               : '',
         'arabic'                : '',
         'armenian'              : '',
         'azerbaijani'           : '',
         'basque'                : '',
         'belarusian'            : '',
         'bosnian'               : '',
         'bulgarian'             : 'bg',
         'burmese'               : '',
         'catalan'               : 'ca',
         'chinese (simple)'      : 'zh',
         'chinese (traditional)' : 'zh_tw',
         'croatian'              : 'hr',
         'czech'                 : '',
         'danish'                : '',
         'dutch'                 : 'nl',
         'english'               : 'en',
         'english (us)'          : 'en',
         'english (australia)'   : 'en',
         'english (new zealand)' : 'en',
         'esperanto'             : '',
         'estonian'              : '',
         'faroese'               : '',
         'finnish'               : 'fi',
         'french'                : 'fr',
         'galician'              : '',
         'german'                : 'de',
         'greek'                 : '',
         'georgian'              : '',
         'hebrew'                : '',
         'hindi (devanagiri)'    : '',
         'hungarian'             : '',
         'icelandic'             : '',
         'indonesian'            : '',
         'italian'               : 'it',
         'japanese'              : '',
         'korean'                : '',
         'latvian'               : '',
         'lithuanian'            : '',
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
         'portuguese'            : 'pt',
         'portuguese (brazil)'   : 'pt',
         'romanian'              : 'ro',
         'russian'               : 'ru',
         'serbian'               : '',
         'serbian (cyrillic)'    : '',
         'sinhala'               : '',
         'slovak'                : '',
         'slovenian'             : '',
         'spanish'               : 'es',
         'spanish (argentina)'   : 'es',
         'spanish (mexico)'      : 'es',
         'swedish'               : 'sv',
         'tajik'                 : '',
         'tamil (india)'         : '',
         'telugu'                : '',
         'thai'                  : '',
         'turkish'               : 'tr',
         'ukrainian'             : 'uk',
         'uzbek'                 : '',
         'vietnamese'            : '',
         'welsh'                 : '' }

WEATHER_CODES = { '200' : '4',
                  '201' : '4',
                  '202' : '3',
                  '210' : '4',
                  '211' : '4',
                  '212' : '3',
                  '221' : '38',
                  '230' : '4',
                  '231' : '4',
                  '232' : '4',
                  '300' : '9',
                  '301' : '9',
                  '302' : '9',
                  '310' : '9',
                  '311' : '9',
                  '312' : '9',
                  '313' : '9',
                  '314' : '9',
                  '321' : '9',
                  '500' : '11',
                  '501' : '11',
                  '502' : '11',
                  '503' : '11',
                  '504' : '11',
                  '511' : '11',
                  '520' : '11',
                  '521' : '11',
                  '522' : '11',
                  '531' : '40',
                  '600' : '14',
                  '601' : '16',
                  '602' : '41',
                  '611' : '18',
                  '612' : '6',
                  '615' : '5',
                  '616' : '5',
                  '620' : '14',
                  '621' : '46',
                  '622' : '43',
                  '701' : '20',
                  '711' : '22',
                  '721' : '21',
                  '731' : '19',
                  '741' : '20',
                  '751' : '19',
                  '761' : '19',
                  '762' : '19',
                  '771' : '2',
                  '781' : '0',
                  '800' : '32',
                  '801' : '34',
                  '802' : '30',
                  '803' : '30',
                  '804' : '28',
                  '900' : '0',
                  '901' : '1',
                  '902' : '2',
                  '903' : '25',
                  '904' : '36',
                  '905' : '24',
                  '906' : '17',
                  '951' : '33',
                  '952' : '24',
                  '953' : '24',
                  '954' : '24',
                  '955' : '24',
                  '956' : '24',
                  '957' : '23',
                  '958' : '23',
                  '959' : '23',
                  '960' : '4',
                  '961' : '3',
                  '962' : '2',
                  '200n' : '47',
                  '201n' : '47',
                  '202n' : '47',
                  '210n' : '47',
                  '211n' : '47',
                  '212n' : '47',
                  '221n' : '47',
                  '230n' : '47',
                  '231n' : '47',
                  '232n' : '47',
                  '300n' : '45',
                  '301n' : '45',
                  '302n' : '45',
                  '310n' : '45',
                  '311n' : '45',
                  '312n' : '45',
                  '313n' : '45',
                  '314n' : '45',
                  '321n' : '45',
                  '500n' : '45',
                  '501n' : '45',
                  '502n' : '45',
                  '503n' : '45',
                  '504n' : '45',
                  '511n' : '45',
                  '520n' : '45',
                  '521n' : '45',
                  '522n' : '45',
                  '531n' : '45',
                  '600n' : '46',
                  '601n' : '46',
                  '602n' : '46',
                  '611n' : '46',
                  '612n' : '46',
                  '615n' : '46',
                  '616n' : '46',
                  '620n' : '46',
                  '621n' : '46',
                  '622n' : '46',
                  '701n' : '29',
                  '711n' : '29',
                  '721n' : '29',
                  '731n' : '29',
                  '741n' : '29',
                  '751n' : '29',
                  '761n' : '29',
                  '762n' : '29',
                  '771n' : '29',
                  '781n' : '29',
                  '800n' : '31',
                  '801n' : '33',
                  '802n' : '29',
                  '803n' : '29',
                  '804n' : '27',
                  '900n' : '29',
                  '901n' : '29',
                  '902n' : '27',
                  '903n' : '33',
                  '904n' : '31',
                  '905n' : '27',
                  '906n' : '45',
                  '951n' : '31',
                  '952n' : '31',
                  '953n' : '33',
                  '954n' : '33',
                  '955n' : '29',
                  '956n' : '29',
                  '957n' : '29',
                  '958n' : '27',
                  '959n' : '27',
                  '960n' : '27',
                  '961n' : '45',
                  '962n' : '45',
                  ''    : 'na' }
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

#### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
def FEELS_LIKE( T=10, V=25, D='C' ):
    FeelsLike = T
    if round( ( V + .0 ) / 1.609344 ) > 4:
        FeelsLike = ( 13.12 + ( 0.6215 * T ) - ( 11.37 * V**0.16 ) + ( 0.3965 * T * V**0.16 ) )
    if D == 'C':
        return str( int( round( FeelsLike ) ) )
    else:
        return str( int( round( FeelsLike * 1.8 + 32 ) ) )

#### thanks to FrostBox @ http://forum.kodi.tv/showthread.php?tid=114637&pid=937168#pid937168
def DEW_POINT( Tc=0, RH=93, D='C', minRH=( 0, 0.075 )[ 0 ] ):
    Es = 6.11 * 10.0**( 7.5 * Tc / ( 237.7 + Tc ) )
    RH = RH or minRH
    E = ( RH * Es ) / 100
    try:
        DewPoint = ( -430.22 + 237.7 * math.log( E ) ) / ( -math.log( E ) + 19.08 )
    except ValueError:
        DewPoint = 0
    if D == 'C':
        return str( int( round( DewPoint ) ) )
    else:
        return str( int( round( DewPoint * 1.8 + 32 ) ) )

# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers
def GET_TILE(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
  return (xtile, ytile)

