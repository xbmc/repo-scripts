from .conversions import *
from .providers import yahoo
from .providers import weatherbit
from .providers import openweathermap

LCURL = 'https://weather.yahoo.com/_atmos/api/search-assist/locations?query=%s'
FCURL = 'https://weather.yahoo.com/%s'
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
            location, locationurl, locationlat, locationlon = self.get_location(mode)
            log('location: %s' % (location))
            log('location id: %s' % (locationurl))
            if locationurl:
                self.get_forecast(location, locationurl, locationlat, locationlon)
            else:
                log('empty location url')
                self.clear_props()
            self.refresh_locations()
        log('finished')
    
    def search_location(self, mode):
        value = ADDON.getSettingString('%s_name' % mode)
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
                for item in locs['suggestions']:
                    if item['location']['region']['code']:
                        region = item['location']['region']['code']
                    else:
                        region = item['location']['region']['name']
                    listitem = xbmcgui.ListItem(item['location']['town']['name'], region + ' - ' + item['location']['country']['code'] + ' [' + str(item['location']['town']['latitude']) + '/' + str(item['location']['town']['longitude']) + ']')
                    items.append(listitem)
                selected = dialog.select(xbmc.getLocalizedString(396), items, useDetails=True)
                if selected != -1:
                    if locs['suggestions'][selected]['location']['region']['code']:
                        region = locs['suggestions'][selected]['location']['region']['code']
                    else:
                        region = locs['suggestions'][selected]['location']['region']['name']
                    name = '%s, %s, %s' % (locs['suggestions'][selected]['location']['town']['name'], region, locs['suggestions'][selected]['location']['country']['code'])
                    url = '%s/%s/%s' % (locs['suggestions'][selected]['location']['country']['code'].lower().replace(' ', '-'), region.lower().replace(' ', '-'), locs['suggestions'][selected]['location']['town']['name'].lower().replace(' ', '-'))
                    ADDON.setSettingString(mode + '_name', name)
                    ADDON.setSettingString(mode + '_url', url)
                    ADDON.setSettingNumber(mode + '_lat', locs['suggestions'][selected]['location']['town']['latitude'])
                    ADDON.setSettingNumber(mode + '_lon', locs['suggestions'][selected]['location']['town']['longitude'])
                    log('selected location: %s' % str(locs['suggestions'][selected]))
            else:
                log('no locations found')
                dialog.ok(ADDONNAME, xbmc.getLocalizedString(284))

    def get_location(self, mode):
        location = ADDON.getSettingString('loc%s_name' % mode)
        locationurl = ADDON.getSettingString('loc%s_url' % mode)
        locationlat = ADDON.getSettingNumber('loc%s_lat' % mode)
        locationlon = ADDON.getSettingNumber('loc%s_lon' % mode)
        if (locationurl == '') and (mode != '1'):
            log('trying location 1 instead')
            location = ADDON.getSettingString('loc1_name')
            locationurl = ADDON.getSettingString('loc1_url')
            locationlat = ADDON.getSettingNumber('loc1_lat')
            locationlon = ADDON.getSettingNumber('loc1_lon')
        return location, locationurl, locationlat, locationlon

    def get_data(self, url, json=True):
        try:
            wsession = requests.Session()
            response = wsession.get(url, headers=HEADERS, timeout=10)
            if 'consent' in response.url: # EU cookie wall: reject
                token = re.search('csrfToken" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                sessionid = re.search('sessionId" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                redirect = re.search('originalDoneUrl" value="(.*?)"', response.text, flags=re.DOTALL).group(1)
                log('EU token: %s' % token)
                log('EU sessionid: %s' % sessionid)
                log('EU redirect %s' % redirect)
                DATA = {'csrfToken': token, 'sessionId': sessionid, 'originalDoneUrl': redirect, 'namespace': 'yahoo', 'reject': 'reject'}
                response = wsession.post(response.url, headers=HEADERS, data=DATA)
            if json:
                return response.json()
            else:
                return response.text
        except:
            return
    
    def get_forecast(self, loc, locurl, lat, lon):
        set_property('WeatherProviderLogo', xbmcvfs.translatePath(os.path.join(CWD, 'resources', 'banner.png')))
        log('weather location: %s' % locurl)
        providers = 'provided by Yahoo'
        if MAPS and MAPID:
            providers = providers + ', Openweathermaps'
            openweathermap.Weather.get_weather(lat, lon, ZOOM, MAPID)
        retry = 0
        url = FCURL % locurl
        while (retry < 6) and (not self.MONITOR.abortRequested()):
            data = self.get_data(url, False)
            if data:
                break
            else:
                self.MONITOR.waitForAbort(10)
                retry += 1
                log('weather download failed')
        data = data.replace('\\','')
        soup = BeautifulSoup(data, 'html.parser')
        card = soup.find(id="summary-card")
        town = card.find('h1').get_text()
        weatherinfo = card.find_all('p')
        country = weatherinfo[0].get_text()
        temperature = weatherinfo[1].get_text().rstrip('°')
        realfeel = weatherinfo[2].get_text().lstrip('RealFeel® ').rstrip('°')
        hightemp = weatherinfo[4].get_text().rstrip('°')
        lowtemp = weatherinfo[5].get_text().rstrip('°')
        sunrise = weatherinfo[6].get_text()
        sunset = weatherinfo[7].get_text()
        outlook = card.find('svg').get('aria-label')
        weatherdata = {}
        weatherdata['location'] = {}
        weatherdata['location']['town'] = town
        weatherdata['location']['country'] = country
        weatherdata['location']['temperature'] = int(temperature)
        weatherdata['location']['realfeel'] = int(realfeel)
        weatherdata['location']['hightemp'] = int(hightemp)
        weatherdata['location']['lowtemp'] = int(lowtemp)
        weatherdata['location']['sunrise'] = sunrise
        weatherdata['location']['sunset'] = sunset
        weatherdata['location']['outlook'] = outlook
        matchcode = re.search('dailyForecasts":(.*?)}]]]}]', data, flags=re.DOTALL)
        if matchcode:
            matchdata = matchcode.group(1)
            weatherdata['forecasts'] = json.loads(matchdata)
        matchcode = re.search('","humidity",(.*?)],\\["', data, flags=re.DOTALL)
        if matchcode:
            matchdata = matchcode.group(1)
            weatherdata['conditions'] = json.loads(matchdata)
        log('yahoo forecast data: %s' % weatherdata)
        if not weatherdata:
            self.clear_props()
            return
        add_weather = ''
        if WADD and APPID:
            daily_string = 'forecast/daily?lat=%s&lon=%s&key=%s' % (lat, lon, APPID)
            url = AURL % daily_string
            add_weather = self.get_data(url)
            log('weatherbit data: %s' % add_weather)
            if not add_weather or (add_weather and 'error' in add_weather):
                add_weather = ''
        yahoo.Weather.get_weather(weatherdata, loc, locurl)
        if add_weather and add_weather != '':
            weatherbit.Weather.get_weather(add_weather)
            providers = providers + ', Weatherbit.io'
        else:
            yahoo.Weather.get_daily_weather(weatherdata)
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
            loc_name = ADDON.getSettingString('loc%s_name' % count)
            if loc_name:
                locations += 1
            set_property('Location%s' % count, loc_name)
        set_property('Locations', str(locations))
        log('available locations: %s' % str(locations))


class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self)
