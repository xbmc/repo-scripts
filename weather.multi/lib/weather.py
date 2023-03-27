from .conversions import *
from .providers import yahoo
from .providers import weatherbit
from .providers import openweathermap

CURL = 'https://www.yahoo.com/'
YURL = 'https://www.yahoo.com/news/weather/'
LCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherSearch;text=%s'
FCURL = 'https://www.yahoo.com/news/_tdnews/api/resource/WeatherService;crumb={crumb};woeids=%5B{woeid}%5D'
AURL = 'https://api.weatherbit.io/v2.0/%s'

HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml'}

WADD = ADDON.getSettingBool('WAdd')
APPID = ADDON.getSettingString('API')

MAPS = ADDON.getSettingBool('WMaps')
MAPID = ADDON.getSettingString('MAPAPI')
ZOOM = str(ADDON.getSettingInt('Zoom') + 2)


class MAIN():
    def __init__(self, *args, **kwargs):
        log('version %s started: %s' % (ADDONVERSION, sys.argv))
        self.MONITOR = MyMonitor()
        mode = kwargs['mode']
        if mode.startswith('loc'):
            self.search_location(mode)
        else:
            location, locationid, locationlat, locationlon = self.get_location(mode)
            log('location: %s' % (location))
            log('location id: %s' % (locationid))
            if locationid > 0:
                ycookie, ycrumb = self.get_ycreds()
                if not ycookie:
                    log('no cookie')
                else:
                    self.get_forecast(location, locationid, locationlat, locationlon, ycookie, ycrumb)
            else:
                log('empty location id')
                self.clear_props()
            self.refresh_locations()
        log('finished')
    
    def search_location(self, mode):
        value = ADDON.getSettingString(mode)
        keyboard = xbmc.Keyboard(value, xbmc.getLocalizedString(14024), False)
        keyboard.doModal()
        if (keyboard.isConfirmed() and keyboard.getText()):
            text = keyboard.getText()
            locs = []
            log('searching for location: %s' % text)
            url = LCURL % text
            data = self.get_data(url)
            log('location data: %s' % data)
            if data:
                locs = data
            dialog = xbmcgui.Dialog()
            if locs:
                items = []
                for item in locs:
                    listitem = xbmcgui.ListItem(item['qualifiedName'], item['city'] + ' - ' + item['country'] + ' [' + str(item['lat']) + '/' + str(item['lon']) + ']')
                    items.append(listitem)
                selected = dialog.select(xbmc.getLocalizedString(396), items, useDetails=True)
                if selected != -1:
                    ADDON.setSettingString(mode, locs[selected]['qualifiedName'])
                    ADDON.setSettingInt(mode + 'id', locs[selected]['woeid'])
                    ADDON.setSettingNumber(mode + 'lat', locs[selected]['lat'])
                    ADDON.setSettingNumber(mode + 'lon', locs[selected]['lon'])
                    log('selected location: %s' % str(locs[selected]))
            else:
                log('no locations found')
                dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))

    def get_location(self, mode):
        location = ADDON.getSettingString('loc%s' % mode)
        locationid = ADDON.getSettingInt('loc%sid' % mode)
        locationlat = ADDON.getSettingNumber('loc%slat' % mode)
        locationlon = ADDON.getSettingNumber('loc%slon' % mode)
        if (locationid == -1) and (mode != '1'):
            log('trying location 1 instead')
            location = ADDON.getSettingString('loc1')
            locationid = ADDON.getSettingInt('loc1id')
            locationlat = ADDON.getSettingNumber('loc1lat')
            locationlon = ADDON.getSettingNumber('loc1lon')
        return location, locationid, locationlat, locationlon

    def get_ycreds(self):
        ycookie = ADDON.getSettingString('ycookie')
        ycrumb = ADDON.getSettingString('ycrumb')
        ystamp = ADDON.getSettingString('ystamp')
        log('cookie from settings: %s' % ycookie)
        log('crumb from settings: %s' % ycrumb)
        log('stamp from settings: %s' % ystamp)
        if ystamp == '' or (int(time.time()) - int(ystamp) > 31536000): # cookie expires after 1 year
            try:
                retry = 0
                while (retry < 6) and (not self.MONITOR.abortRequested()):
                    response = requests.get(CURL, headers=HEADERS, timeout=10)
                    if response.status_code == 200:
                        break
                    else:
                        self.MONITOR.waitForAbort(10)
                        retry += 1
                        log('getting yahoo website failed')
                if 'consent' in response.url: # EU users need to accept cookies
                    token = re.search('csrfToken" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                    sessionid = re.search('sessionId" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                    redirect = re.search('originalDoneUrl" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                    DATA = {'csrfToken': token, 'sessionId': sessionid, 'originalDoneUrl': redirect, 'namespace': 'yahoo', 'agree': 'agree'}
                    posturl = 'https://consent.yahoo.com/v2/collectConsent?sessionId=%s' % sessionid
                    response = requests.post(posturl, headers=HEADERS, data=DATA)
                try:
                    ycookie = response.cookies['A1']
                except:
                    ycookie = response.cookies['A1S'].replace('&j=GDPR', '')
                response = requests.get(YURL, headers=HEADERS, cookies=dict(A1=ycookie), timeout=10)
                match = re.search('WeatherStore":{"crumb":"(.*?)","weathers', response.text, re.IGNORECASE)
                if not match:
                    match = re.search("win.YAHOO.context.crumb = '(.*?)'", response.text, re.IGNORECASE)
                if not match:
                    match = re.search('window.YAHOO.context.*?"crumb": "(.*?)"', response.text, flags=re.DOTALL)
                ycrumb = codecs.decode(match.group(1), 'unicode-escape')
                ystamp = time.time()
                ADDON.setSettingString('ycookie', ycookie)
                ADDON.setSettingString('ycrumb', ycrumb)
                ADDON.setSettingString('ystamp', str(int(ystamp)))
                log('save cookie to settings: %s' % ycookie)
                log('save crumb to settings: %s' % ycrumb)
                log('save stamp to settings: %s' % str(int(ystamp)))
            except:
                log('exception while getting cookie')
                return '', ''
        return ycookie, ycrumb

    def get_data(self, url, cookie=''):
        try:
            if cookie:
                response = requests.get(url, headers=HEADERS, cookies=dict(A1=cookie), timeout=10)
            else:
                response = requests.get(url, headers=HEADERS, timeout=10)
            return response.json()
        except:
            return
    
    def get_forecast(self, loc, locid, lat, lon, ycookie='', ycrumb=''):
        set_property('WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
        log('weather location: %s' % locid)
        providers = 'provided by Yahoo'
        if MAPS and MAPID:
            providers = providers + ', Openweathermaps'
            openweathermap.Weather.get_weather(lat, lon, ZOOM, MAPID)
        retry = 0
        url = FCURL.format(crumb=ycrumb, woeid=locid)
        while (retry < 6) and (not self.MONITOR.abortRequested()):
            data = self.get_data(url, ycookie)
            if data:
                break
            else:
                self.MONITOR.waitForAbort(10)
                retry += 1
                log('weather download failed')
        log('yahoo forecast data: %s' % data)
        if not data:
            self.clear_props()
            return
        add_weather = ''
        if WADD and APPID:
            daily_string = 'forecast/daily?key=%s&lat=%s&lon=%s' % (APPID, lat, lon)
            url = AURL % daily_string
            add_weather = self.get_data(url)
            log('weatherbit data: %s' % add_weather)
            if not add_weather or (add_weather and 'error' in add_weather):
                add_weather = ''
        yahoo.Weather.get_weather(data, loc, locid)
        if add_weather and add_weather != '':
            weatherbit.Weather.get_weather(add_weather)
            providers = providers + ', Weatherbit.io'
        else:
            yahoo.Weather.get_daily_weather(data)
        set_property('WeatherProvider', providers)
        
    def clear_props(self):
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
        for count in range (0, MAXDAYS+1):
            set_property('Day%i.Title'       % count, 'N/A')
            set_property('Day%i.HighTemp'    % count, '0')
            set_property('Day%i.LowTemp'     % count, '0')
            set_property('Day%i.Outlook'     % count, 'N/A')
            set_property('Day%i.OutlookIcon' % count, 'na.png')
            set_property('Day%i.FanartCode'  % count, 'na')

    def refresh_locations(self):
        locations = 0
        for count in range(1, 6):
            loc_name = ADDON.getSettingString('loc%s' % count)
            if loc_name:
                locations += 1
            set_property('Location%s' % count, loc_name)
        set_property('Locations', str(locations))
        log('available locations: %s' % str(locations))


class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
