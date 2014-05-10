# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *

import os, sys, urllib2, socket, re
import xbmcgui, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__      = xbmcaddon.Addon()
__addonname__  = __addon__.getAddonInfo('name')
__addonid__    = __addon__.getAddonInfo('id')
__version__    = __addon__.getAddonInfo('version')
__cwd__        = __addon__.getAddonInfo('path').decode("utf-8")
__language__   = __addon__.getLocalizedString
__resource__   = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))

sys.path.append (__resource__)

# Array for translate wind level and speed
WIND_SPEED = { "0" : "0",
               "1" : "3",
               "2" : "8.5",
               "3" : "15.5",
               "4" : "24",
               "5" : "33.5",
               "6" : "44",
               "7" : "55.5",
               "8" : "68",
               "9" : "81.5",
               "10" : "95.5",
               "11" : "110",
               "12" : "120"}

# Array for translate week to number
DAYS = { "星期一": 1,
         "星期二": 2,
         "星期三": 3,
         "星期四": 4,
         "星期五": 5,
         "星期六": 6,
         "星期日": 7}

# Array for translate OutlookIcon index
WEATHER_CODES = { '0' : '32',
                  '1' : '30',
                  '2' : '26',
                  '3' : '39',
                  '4' : '35',
                  '5' : '35',
                  '6' : '5',
                  '7' : '11',
                  '8' : '11',
                  '9' : '12',
                  '10' : '40',
                  '11' : '40',
                  '12' : '40',
                  '13' : '15',
                  '14' : '13',
                  '15' : '14',
                  '16' : '16',
                  '17' : '16',
                  '18' : '20',
                  '19' : '7',
                  '20' : '23',
                  '21' : '11',
                  '22' : '12',
                  '23' : '40',
                  '24' : '40',
                  '25' : '40',
                  '26' : '14',
                  '27' : '16',
                  '28' : '16',
                  '29' : '21',
                  '30' : '22',
                  '31' : '23',
                  '99' : 'na'}

GEOIP_URL       = 'http://61.4.185.48:81/g/'
LOCATION_URL    = 'http://m.weather.com.cn/data5/city%s.xml'
WEATHER_URL     = 'http://www.weather.com.cn/data/ks/%s.html'
WEATHER_DAY_URL = 'http://m.weather.com.cn/atad/%s.html'
WEATHER_HOURLY_URL = 'http://flash.weather.com.cn/sk2/%s.xml'
WEATHER_WINDOW  = xbmcgui.Window(12600)

socket.setdefaulttimeout(10)

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def set_property(name, value):
    WEATHER_WINDOW.setProperty(name, value)

def refresh_locations():
    locations = 0
    for count in range(1, 4):
        loc_name = __addon__.getSetting('Location%s' % count)
        if loc_name != '':
            locations += 1
        else:
            __addon__.setSetting('Location%sid' % count, '')
        set_property('Location%s' % count, loc_name)
    set_property('Locations', str(locations))
    log('available locations: %s' % str(locations))

def fetch(url):
    log('fetch weather from: %s' % url)
    try:
        req = urllib2.urlopen(url)
        json_string = req.read()
        req.close()
        log('forecast data: %s' % json_string)
    except:
        json_string = ''
        log('weather download failed')
    try:
        parsed_json = simplejson.loads(json_string)
    except:
        log('failed to parse weather data')
        parsed_json = ''
    return parsed_json

def location(string):
    log('searching for location: %s' % string)
    loc   = []
    locid = []
    url = LOCATION_URL % (urllib2.quote(string))
    try:
        req = urllib2.urlopen(url)
        ret_string = req.read()
        req.close()
        log('location data: %s' % ret_string)
    except:
        ret_string = ''
        log('location download failed')
    values = ret_string.split(',')
    for item in values:
        location   = item.split('|')[1]
        locationid = item.split('|')[0]
        loc.append(location)
        locid.append(locationid)
    return loc, locid

def geoip():
    try:
        req = urllib2.urlopen(GEOIP_URL)
        ret_string = req.read()
        req.close()
        log('geoip data: %s' % ret_string)
    except:
        ret_string = ''
        log('geoip download failed')
    match = re.compile('var id=([0-9]+);').search(ret_string)
    location = ''
    locationid = ''
    if match:
        locationid = match.group(1)
        data = fetch(WEATHER_URL % (locationid))
        if data != '':
            location = data['weatherinfo']['city'].encode('utf-8')
            __addon__.setSetting('Location1', location)
            __addon__.setSetting('Location1id', locationid)
            log('geoip location: %s' % location)
    return location, locationid

def forecast(loc,locid):
    log('weather location: %s' % locid)
    set_property('Current.Location'      , loc)
    query1 = fetch(WEATHER_URL % (locid))
    query2 = fetch(WEATHER_DAY_URL % (locid))
    if query1 == '' or query2 =='':
        clear()
    if query1 != '':
        properties1(query1)
    if query2 != '':
        properties2(query2)

def clear():
    set_property('Current.Condition'     , 'N/A')
    set_property('Current.Temperature'   , '0')
    set_property('Current.Wind'          , '0')
    set_property('Current.WindDirection' , 'N/A')
    set_property('Current.Humidity'      , '0')
    set_property('Current.FeelsLike'     , '0')
    set_property('Current.UVIndex'       , '0')
    set_property('Current.DewPoint'      , '0')
    set_property('Current.OutlookIcon'   , 'na.png')
    set_property('Current.FanartCode'    , 'na')
    for count in range (6):
        set_property('Day%i.Title'       % count, 'N/A')
        set_property('Day%i.HighTemp'    % count, '0')
        set_property('Day%i.LowTemp'     % count, '0')
        set_property('Day%i.Outlook'     % count, 'N/A')
        set_property('Day%i.OutlookIcon' % count, 'na.png')
        set_property('Day%i.FanartCode'  % count, 'na')

def properties1(query):
    set_property('Current.Temperature'   , query['weatherinfo']['temp'].encode('utf-8'))
    set_property('Current.Wind'          , WIND_SPEED[query['weatherinfo']['WSE'].encode('utf-8')])
    set_property('Current.WindDirection' , query['weatherinfo']['WD'].encode('utf-8'))
    set_property('Current.Humidity'      , query['weatherinfo']['SD'].rstrip('%'))
    set_property('Current.FeelsLike'     , query['weatherinfo']['temp'].encode('utf-8'))

def properties2(query):
    weathercode = WEATHER_CODES[query['weatherinfo']['img1'].encode('utf-8')]
    set_property('Current.Condition'     , query['weatherinfo']['weather1'].encode('utf-8'))
    set_property('Current.UVIndex'       , query['weatherinfo']['index_uv'].encode('utf-8'))
    # No DewPoint data from site www.weather.com.cn
    set_property('Current.DewPoint'      , '0')
    set_property('Current.OutlookIcon'   , '%s.png' % weathercode)
    set_property('Current.FanartCode'    , weathercode)
    week = DAYS[query['weatherinfo']['week'].encode('utf-8')]
    for count in range(6):
        img = query['weatherinfo']['img%i' % (count * 2 + 1)].encode('utf-8')
        weathercode = WEATHER_CODES[img]
        day = week + count
        if day > 7: day -= 7
        temp = query['weatherinfo']['temp%i' % (count + 1)].encode('utf-8').replace('℃', '').split('~')
        set_property('Day%i.Title'       % count, xbmc.getLocalizedString( 10 + day ))
        if int(temp[0]) > int(temp[1]):
            set_property('Day%i.HighTemp'    % count, temp[0])
            set_property('Day%i.LowTemp'     % count, temp[1])
        else:
            set_property('Day%i.HighTemp'    % count, temp[1])
            set_property('Day%i.LowTemp'     % count, temp[0])
        set_property('Day%i.Outlook'     % count, query['weatherinfo']['weather%i' % (count + 1)].encode('utf-8'))
        set_property('Day%i.OutlookIcon' % count, '%s.png' % weathercode)
        set_property('Day%i.FanartCode'  % count, weathercode)

log('version %s started: %s' % (__version__, sys.argv))

set_property('WeatherProvider', __addonname__)
set_property('WeatherProviderLogo', xbmc.translatePath(os.path.join(__cwd__, 'resources', 'banner.png')))

if sys.argv[1].startswith('Location'):
    dialog = xbmcgui.Dialog()
    # select Province
    locations, locationids = location('')
    if locations != []:
        selected = dialog.select(__language__(30201), locations)
        if selected != -1:
            name = locations[selected]
            code = locationids[selected]
            # select City
            locations, locationids = location(code)
            if locations != []:
                selected = dialog.select(__language__(30202).encode('utf-8') % (name), locations)
                if selected != -1:
                    name = locations[selected]
                    code = locationids[selected]
                    # select County
                    locations, locationids = location(code)
                    if locations != []:
                        selected = dialog.select(__language__(30203).encode('utf-8') % (name), locations)
                        if selected != -1:
                            name = locations[selected]
                            code = locationids[selected]
                            locations, locationids = location(code)
                            if locations != []:
                                __addon__.setSetting(sys.argv[1], name)
                                __addon__.setSetting(sys.argv[1] + 'id', locations[0])
                            else:
                                dialog.ok(__addonname__, xbmc.getLocalizedString(284))
                    else:
                        dialog.ok(__addonname__, xbmc.getLocalizedString(284))
            else:
                dialog.ok(__addonname__, xbmc.getLocalizedString(284))
    else:
        dialog.ok(__addonname__, xbmc.getLocalizedString(284))

else:
    location = __addon__.getSetting('Location%s' % sys.argv[1])
    locationid = __addon__.getSetting('Location%sid' % sys.argv[1])
    if (locationid == '') and (sys.argv[1] != '1'):
        location = __addon__.getSetting('Location1')
        locationid = __addon__.getSetting('Location1id')
        log('trying location 1 instead')
    if locationid == '':
        log('fallback to geoip')
        location, locationid = geoip()
    if not locationid == '':
        forecast(location, locationid)
    else:
        log('no location found')
        clear()
    refresh_locations()

log('finished')
