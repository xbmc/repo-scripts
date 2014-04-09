import xbmc #@UnresolvedImport
import xbmcgui #@UnresolvedImport
import xbmcaddon #@UnresolvedImport
import urllib
import pytz
WEATHER_WINDOW_ID = 12600
SETTINGS_WINDOW_ID = 10014

TZ = pytz.timezone('Europe/London') #TODO: Need to pull the actual timezone out of xbmc. Somehow.
TZUK = pytz.timezone('Europe/London')
WINDOW = xbmcgui.Window(WEATHER_WINDOW_ID)
FORECASTMAP_SLIDER = WINDOW.getProperty('ForecastMap.Slider') or '0'
OBSERVATIONMAP_SLIDER = WINDOW.getProperty('ObservationMap.Slider') or '0'
FORECASTMAP_LAYER_SELECTION = WINDOW.getProperty('ForecastMap.LayerSelection') or 'Rainfall'#@UndefinedVariable
OBSERVATIONMAP_LAYER_SELECTION = WINDOW.getProperty('ObservationMap.LayerSelection') or 'Rainfall'#@UndefinedVariable
CURRENT_VIEW = WINDOW.getProperty('Weather.CurrentView')

ADDON = xbmcaddon.Addon(id="weather.metoffice")
DIALOG = xbmcgui.Dialog()
KEYBOARD = xbmc.Keyboard()
ADDON_DATA_PATH = xbmc.translatePath('special://profile/addon_data/%s/' % ADDON.getAddonInfo('id'))
WEATHER_ICON_PATH = xbmc.translatePath('special://temp/weather/%s.png').decode("utf-8")
TEMPERATUREUNITS = xbmc.getInfoLabel('System.TemperatureUnits')

API_KEY = ADDON.getSetting('ApiKey')
GEOLOCATION = ADDON.getSetting('GeoLocation')
GEOIP = ADDON.getSetting('GeoIPProvider')
FORECAST_LOCATION = ADDON.getSetting('ForecastLocation')
FORECAST_LOCATION_ID = ADDON.getSetting('ForecastLocationID')
OBSERVATION_LOCATION = ADDON.getSetting('ObservationLocation')
OBSERVATION_LOCATION_ID = ADDON.getSetting('ObservationLocationID')
REGIONAL_LOCATION = ADDON.getSetting('RegionalLocation')
REGIONAL_LOCATION_ID = ADDON.getSetting('RegionalLocationID')
LATITUDE = ADDON.getSetting('ForecastLocationLatitude')
LONGITUDE = ADDON.getSetting('ForecastLocationLongitude')

DATAPOINT_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
DATAPOINT_DATE_FORMAT = '%Y-%m-%dZ'
SHORT_DAY_FORMAT = "%a"
MAPTIME_FORMAT = '%H%M %a'
ISSUEDAT_FORMAT = '%H:%M %a %d %b %Y'

GOOGLE_BASE = 'http://maps.googleapis.com/maps/api/staticmap'
GOOGLE_GLOBAL = GOOGLE_BASE + "?sensor=false&center=55,-3.5&zoom=5&size=323x472"
GOOGLE_SURFACE = GOOGLE_GLOBAL + "&maptype=satellite"
GOOGLE_MARKER = GOOGLE_GLOBAL + '&style=feature:all|element:all|visibility:off&markers={0},{1}'.format(LATITUDE, LONGITUDE)

RAW_DATAPOINT_IMG_WIDTH = 500
CROP_WIDTH = 40
CROP_HEIGHT = 20

WEATHER_CODES = {
    'na': ('na', 'Not Available'),
    '0': ('31', 'Clear'), #night
    '1': ('32', 'Sunny'),
    '2': ('29', 'Partly Cloudy'), #night
    '3': ('30', 'Partly Cloudy'),
#   '4': ('na', 'Not available'),
    '5': ('21', 'Mist'),
    '6': ('20', 'Fog'),
    '7': ('26', 'Cloudy'),
    '8': ('26', 'Overcast'),
    '9': ('45', 'Light Rain'), #night
    '10': ('11', 'Light Rain'),
    '11': ('9', 'Drizzle'),
    '12': ('11', 'Light Rain'),
    '13': ('45', 'Heavy Rain'), #night
    '14': ('40', 'Heavy Rain'),
    '15': ('40', 'Heavy Rain'),
    '16': ('46', 'Sleet'), #night
    '17': ('6', 'Sleet'),
    '18': ('6', 'Sleet'),
    '19': ('45', 'Hail'), #night
    '20': ('18', 'Hail'),
    '21': ('18', 'Hail'),
    '22': ('46', 'Light Snow'), #night
    '23': ('14', 'Light snow'),
    '24': ('14', 'Light Snow'),
    '25': ('46', 'Heavy Snow'), #night
    '26': ('16', 'Heavy Snow'),
    '27': ('16', 'Heavy Snow'),
    '28': ('47', 'Thunder'), #night
    '29': ('17', 'Thunder'),
    '30': ('17', 'Thunder')
}

#This list must appear in the same order as it appears in 
#the settings.xml in order for the indexes to align.
GEOIP_PROVIDERS = [{'url':'http://ip-api.com/json/', 'latitude':'lat', 'longitude':'lon'},
             {'url':'http://freegeoip.net/json/', 'latitude':'latitude', 'longitude':'longitude'},
             {'url':'http://www.telize.com/geoip/','latitude':'latitude', 'longitude':'longitude'},
             {'url':'http://api.hostip.info/get_json.php?position=true','latitude':'lat', 'longitude':'lng'},
             {'url':'http://geoiplookup.net/geoapi.php?output=json', 'latitude':'latitude', 'longitude':'longitude'}
                   ]
GEOIP_PROVIDER = GEOIP_PROVIDERS[int(GEOIP)]

URL_TEMPLATE = "http://datapoint.metoffice.gov.uk/public/data/{format}/{resource}/{group}/{datatype}/{object}?{get}"

FORECAST_SITELIST_URL = URL_TEMPLATE.format(format='val', resource='wxfcs', group='all', datatype='json', object='sitelist', 
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))
OBSERVATION_SITELIST_URL = URL_TEMPLATE.format(format='val', resource='wxobs', group='all', datatype='json', object='sitelist',
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))
REGIONAL_SITELIST_URL = URL_TEMPLATE.format(format='txt', resource='wxfcs', group='regionalforecast', datatype='json', object='sitelist',
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))

DAILY_LOCATION_FORECAST_URL = URL_TEMPLATE.format(format='val', resource='wxfcs', group='all', datatype='json', object=FORECAST_LOCATION_ID,
                                            get=urllib.unquote(urllib.urlencode((('res', 'daily'),('key',API_KEY)))))
THREEHOURLY_LOCATION_FORECAST_URL = URL_TEMPLATE.format(format='val', resource='wxfcs', group='all', datatype='json', object=FORECAST_LOCATION_ID,
                                            get=urllib.unquote(urllib.urlencode((('res', '3hourly'),('key',API_KEY)))))
HOURLY_LOCATION_OBSERVATION_URL = URL_TEMPLATE.format(format='val', resource='wxobs', group='all', datatype='json', object=OBSERVATION_LOCATION_ID,
                                            get=urllib.unquote(urllib.urlencode((('res', 'hourly'),('key',API_KEY)))))
TEXT_FORECAST_URL = URL_TEMPLATE.format(format='txt', resource='wxfcs', group='regionalforecast', datatype='json', object=REGIONAL_LOCATION_ID,
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))
FORECAST_LAYER_CAPABILITIES_URL = URL_TEMPLATE.format(format='layer', resource='wxfcs', group='all', datatype='json', object='capabilities',
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))
OBSERVATION_LAYER_CAPABILITIES_URL = URL_TEMPLATE.format(format='layer', resource='wxobs', group='all', datatype='json', object='capabilities',
                                            get=urllib.unquote(urllib.urlencode((('key',API_KEY),))))

LONG_REGIONAL_NAMES = {'os': 'Orkney and Shetland',
                       'he': 'Highland and Eilean Siar',
                       'gr': 'Grampian',
                       'ta': 'Tayside',
                       'st': 'Strathclyde',
                       'dg': 'Dumfries, Galloway, Lothian',
                       'ni': 'Northern Ireland',
                       'yh': 'Yorkshire and the Humber',
                       'ne': 'Northeast England',
                       'em': 'East Midlands',
                       'ee': 'East of England',
                       'se': 'London and Southeast England',
                       'nw': 'Northwest England',
                       'wm': 'West Midlands',
                       'sw': 'Southwest England',
                       'wl': 'Wales',
                       'uk': 'United Kingdom'}