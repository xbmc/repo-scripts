import urllib.parse

import pytz
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

# Magic numbers. See https://kodi.wiki/view/Window_IDs
WEATHER_WINDOW_ID = 12600
ADDON_BROWSER_WINDOW_ID = 10040

TZ = pytz.timezone(
    "Europe/London"
)  # TODO: Need to pull the actual timezone out of xbmc. Somehow.


def window():
    return xbmcgui.Window(WEATHER_WINDOW_ID)


def dialog():
    return xbmcgui.Dialog()


def keyboard():
    return xbmc.Keyboard()


def addon():
    return xbmcaddon.Addon(id="weather.metoffice")


ADDON_BANNER_PATH = xbmcvfs.translatePath(
    "special://home/addons/%s/resources/banner.png" % addon().getAddonInfo("id")
)
ADDON_DATA_PATH = xbmcvfs.translatePath(
    "special://profile/addon_data/%s/" % addon().getAddonInfo("id")
)

TEMPERATUREUNITS = xbmc.getRegion("tempunit")

API_KEY = addon().getSetting("ApiKey")
GEOLOCATION = addon().getSetting("GeoLocation")
GEOIP = addon().getSetting("GeoIPProvider")
FORECAST_LOCATION = addon().getSetting("ForecastLocation")
FORECAST_LOCATION_ID = addon().getSetting("ForecastLocationID")
OBSERVATION_LOCATION = addon().getSetting("ObservationLocation")
OBSERVATION_LOCATION_ID = addon().getSetting("ObservationLocationID")
REGIONAL_LOCATION = addon().getSetting("RegionalLocation")
REGIONAL_LOCATION_ID = addon().getSetting("RegionalLocationID")
LATITUDE = addon().getSetting("ForecastLocationLatitude")
LONGITUDE = addon().getSetting("ForecastLocationLongitude")

DATAPOINT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
DATAPOINT_DATE_FORMAT = "%Y-%m-%dZ"
SHORT_DAY_FORMAT = "%a"
SHORT_DATE_FORMAT = "%d %b"
MAPTIME_FORMAT = "%H%M %a"
ISSUEDAT_FORMAT = "%H:%M %a %d %b %Y"
TIME_FORMAT = "%H:%M"

RAW_DATAPOINT_IMG_WIDTH = 500
CROP_WIDTH = 40
CROP_HEIGHT = 20

WEATHER_CODES = {
    "na": ("na", "Not Available"),
    "0": ("31", "Clear"),  # night
    "1": ("32", "Sunny"),
    "2": ("29", "Partly Cloudy"),  # night
    "3": ("30", "Partly Cloudy"),
    #   '4': ('na', 'Not available'),
    "5": ("21", "Mist"),
    "6": ("20", "Fog"),
    "7": ("26", "Cloudy"),
    "8": ("26", "Overcast"),
    "9": ("45", "Light Rain"),  # night
    "10": ("11", "Light Rain"),
    "11": ("9", "Drizzle"),
    "12": ("11", "Light Rain"),
    "13": ("45", "Heavy Rain"),  # night
    "14": ("40", "Heavy Rain"),
    "15": ("40", "Heavy Rain"),
    "16": ("46", "Sleet"),  # night
    "17": ("6", "Sleet"),
    "18": ("6", "Sleet"),
    "19": ("45", "Hail"),  # night
    "20": ("18", "Hail"),
    "21": ("18", "Hail"),
    "22": ("46", "Light Snow"),  # night
    "23": ("14", "Light snow"),
    "24": ("14", "Light Snow"),
    "25": ("46", "Heavy Snow"),  # night
    "26": ("16", "Heavy Snow"),
    "27": ("16", "Heavy Snow"),
    "28": ("47", "Thunder"),  # night
    "29": ("17", "Thunder"),
    "30": ("17", "Thunder"),
}

# This list must appear in the same order as it appears in
# the settings.xml in order for the indexes to align.
GEOIP_PROVIDERS = [
    {"url": "http://ip-api.com/json/", "latitude": "lat", "longitude": "lon"},
    {
        "url": "https://api.geoiplookup.net/?json=true",
        "latitude": "latitude",
        "longitude": "longitude",
    },
    {
        "url": "https://ipapi.co/json/",
        "latitude": "latitude",
        "longitude": "longitude",
    },
]
GEOIP_PROVIDER = GEOIP_PROVIDERS[int(GEOIP) if GEOIP else 0]

URL_TEMPLATE = "http://datapoint.metoffice.gov.uk/public/data/{format}/{resource}/{group}/{datatype}/{object}?{get}"

FORECAST_SITELIST_URL = URL_TEMPLATE.format(
    format="val",
    resource="wxfcs",
    group="all",
    datatype="json",
    object="sitelist",
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

OBSERVATION_SITELIST_URL = URL_TEMPLATE.format(
    format="val",
    resource="wxobs",
    group="all",
    datatype="json",
    object="sitelist",
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

REGIONAL_SITELIST_URL = URL_TEMPLATE.format(
    format="txt",
    resource="wxfcs",
    group="regionalforecast",
    datatype="json",
    object="sitelist",
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

DAILY_LOCATION_FORECAST_URL = URL_TEMPLATE.format(
    format="val",
    resource="wxfcs",
    group="all",
    datatype="json",
    object=FORECAST_LOCATION_ID,
    get=urllib.parse.unquote(
        urllib.parse.urlencode((("res", "daily"), ("key", API_KEY)))
    ),
)

THREEHOURLY_LOCATION_FORECAST_URL = URL_TEMPLATE.format(
    format="val",
    resource="wxfcs",
    group="all",
    datatype="json",
    object=FORECAST_LOCATION_ID,
    get=urllib.parse.unquote(
        urllib.parse.urlencode((("res", "3hourly"), ("key", API_KEY)))
    ),
)

HOURLY_LOCATION_OBSERVATION_URL = URL_TEMPLATE.format(
    format="val",
    resource="wxobs",
    group="all",
    datatype="json",
    object=OBSERVATION_LOCATION_ID,
    get=urllib.parse.unquote(
        urllib.parse.urlencode((("res", "hourly"), ("key", API_KEY)))
    ),
)

TEXT_FORECAST_URL = URL_TEMPLATE.format(
    format="txt",
    resource="wxfcs",
    group="regionalforecast",
    datatype="json",
    object=REGIONAL_LOCATION_ID,
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

FORECAST_LAYER_CAPABILITIES_URL = URL_TEMPLATE.format(
    format="layer",
    resource="wxfcs",
    group="all",
    datatype="json",
    object="capabilities",
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

OBSERVATION_LAYER_CAPABILITIES_URL = URL_TEMPLATE.format(
    format="layer",
    resource="wxobs",
    group="all",
    datatype="json",
    object="capabilities",
    get=urllib.parse.unquote(urllib.parse.urlencode((("key", API_KEY),))),
)

LONG_REGIONAL_NAMES = {
    "os": "Orkney and Shetland",
    "he": "Highland and Eilean Siar",
    "gr": "Grampian",
    "ta": "Tayside",
    "st": "Strathclyde",
    "dg": "Dumfries, Galloway, Lothian",
    "ni": "Northern Ireland",
    "yh": "Yorkshire and the Humber",
    "ne": "Northeast England",
    "em": "East Midlands",
    "ee": "East of England",
    "se": "London and Southeast England",
    "nw": "Northwest England",
    "wm": "West Midlands",
    "sw": "Southwest England",
    "wl": "Wales",
    "uk": "United Kingdom",
}
