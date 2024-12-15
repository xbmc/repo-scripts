import os
import xbmc
import xbmcvfs
import xbmcaddon

from . import utils

# API
map_api = {
	'search': 'https://geocoding-api.open-meteo.com/v1/search?name={}&count=10&language=en&format=json',
	'geoip': 'https://api.openht.org/geoipweather',
	'weather': 'https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,dew_point_2m,precipitation_probability,visibility,uv_index,direct_radiation&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,pressure_msl,surface_pressure,cloud_cover,visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index,is_day,direct_radiation&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,daylight_duration,sunshine_duration,uv_index_max,precipitation_hours&timeformat=unixtime&forecast_days=9&past_days=2',
	'airquality': 'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={}&longitude={}&current=european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,ozone,dust,nitrogen_dioxide,sulphur_dioxide,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&hourly=pm10,pm2_5,carbon_monoxide,ozone,dust,european_aqi,us_aqi,nitrogen_dioxide,sulphur_dioxide,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&timeformat=unixtime&forecast_days=7&past_days=2',
	'sun': 'https://api.met.no/weatherapi/sunrise/3.0/sun?lat={}&lon={}&date={}',
	'moon': 'https://api.met.no/weatherapi/sunrise/3.0/moon?lat={}&lon={}&date={}',
	'osm': 'https://tile.openstreetmap.org/{}/{}/{}.png',
	'rvindex': 'https://api.rainviewer.com/public/weather-maps.json',
	'rvradar': 'https://tilecache.rainviewer.com{}/256/{}/{}/{}/4/1_1.png',
	'rvsatellite': 'https://tilecache.rainviewer.com{}/256/{}/{}/{}/0/0_0.png',
	'gctemp': 'https://geo.weather.gc.ca/geomet?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={},{},{},{}&CRS=EPSG:4326&WIDTH=256&HEIGHT=256&LAYERS=GDPS.ETA_TT&FORMAT=image/png',
	'gcwind': 'https://geo.weather.gc.ca/geomet?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&BBOX={},{},{},{}&CRS=EPSG:4326&WIDTH=256&HEIGHT=256&LAYERS=GDPS.ETA_UU&FORMAT=image/png',
}

# Limits
maxdays  = 8
mindays  = 2
maxhours = 73
minhours = 25
mindata  = 0
maxdata  = 300

# ADDON
addon_ua    = {'user-agent': f'{xbmc.getUserAgent()} (weather.openmeteo v{utils.xbmcaddon.Addon().getAddonInfo("version")}, support@openht.org)'}
addon_info  = f'{xbmc.getUserAgent()} (weather.openmeteo v{utils.xbmcaddon.Addon().getAddonInfo("version")})'
addon_data  = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
addon_cache = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile')) + "cache"
addon_icons = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path')) + "resources/icons"
addon_path  = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('path'))
neterr      = 0

# Cache
dnscache = {}
mapcache = {}

# Modules (disabled)
# sys.path.append(f'{addon_path}/lib/modules')

# Mapping (Weather)
map_weather = [
	[ "current",	[ 'latitude' ],				[ 'current', 'latitude' ],		'round2' ],
	[ "current",	[ 'longitude' ],			[ 'current', 'longitude' ],		'round2' ],
	[ "current",	[ 'elevation' ],			[ 'current', 'elevation' ],		'round' ],

	[ "current",	[ 'current_units', 'wind_speed_10m' ],		[ 'unit', 'speed' ], 		'unitspeed' ],
	[ "current",	[ 'current_units', 'temperature_2m' ],		[ 'unit', 'temperature' ], 	'unittemperature' ],
	[ "current",	[ 'current_units', 'precipitation' ],		[ 'unit', 'precipitation' ],	'unitprecipitation' ],
	[ "current",	[ 'current_units', 'pressure_msl' ],		[ 'unit', 'pressure' ],		'unitpressure' ],
	[ "current",	[ 'current_units', 'relative_humidity_2m' ],	[ 'unit', 'percent' ], 		'unitpercent' ],
	[ "current",	[ 'hourly_units', 'visibility' ],		[ 'unit', 'distance' ],		'unitdistance' ],
	[ "current",	[ 'hourly_units', 'direct_radiation' ],		[ 'unit', 'radiation' ],	'unitradiation' ],
	[ "current",	[ 'hourly_units', 'direct_radiation' ],		[ 'unit', 'solarradiation' ],	'unitradiation' ],

	[ "current",	[ 'current', "time" ],			[ 'current', "date" ],			"date" ],
	[ "hourly",	[ 'hourly', "time" ],			[ 'hourly', "date" ],			"date" ],
	[ "hourly",	[ 'hourly', "time" ],			[ 'hourly', "shortdate" ],		"date" ],

	[ "current",	[ 'current', "time" ],			[ 'current', "time" ],			"time" ],
	[ "hourly",	[ 'hourly', "time" ],			[ 'hourly', "time" ],			"time" ],

	[ "current",	[ 'current', "time" ],			[ 'current', "hour" ],			"hour" ],
	[ "hourly",	[ 'hourly', "time" ],			[ 'hourly', "hour" ],			"hour" ],

	[ "current",	[ 'current', "temperature_2m" ],	[ 'current', "temperatureaddon" ],	"temperature" ],
	[ "current",	[ 'current', "apparent_temperature" ],	[ 'current', "feelslikeaddon" ],	"temperature" ],
	[ "current",	[ 'current', "dew_point_2m" ],		[ 'current', "dewpointaddon" ],		"temperature" ],

	[ "current",	[ 'current', "temperature_2m" ],	[ 'current', "temperature" ],		"temperaturekodi" ],
	[ "currentkodi",[ 'current', "temperature_2m" ],	[ 'current', "temperature" ],		"round" ],
	[ "current",	[ 'current', "apparent_temperature" ],	[ 'current', "feelslike" ],		"temperaturekodi" ],
	[ "currentkodi",[ 'current', "apparent_temperature" ],	[ 'current', "feelslike" ],		"round" ],
	[ "current",	[ 'current', "dew_point_2m" ],		[ 'current', "dewpoint" ],		"temperaturekodi" ],
	[ "currentkodi",[ 'current', "dew_point_2m" ],		[ 'current', "dewpoint" ],		"round" ],

	[ "hourly",	[ 'hourly', "temperature_2m" ],		[ 'hourly', "temperature" ],			"temperatureunit" ],
	[ "hourlyskin",	[ 'hourly', "temperature_2m" ],		[ 'hourly', "temperature" ],			"temperature" ],
	[ "hourly",	[ 'hourly', "temperature_2m" ],		[ 'hourly', "temperaturegraph" ],		"graph", "50", "temperature" ],

	[ "hourly",	[ 'hourly', "apparent_temperature" ],	[ 'hourly', "feelslike" ],			"temperatureunit" ],
	[ "hourlyskin",	[ 'hourly', "apparent_temperature" ],	[ 'hourly', "feelslike" ],			"temperature" ],
	[ "hourly",	[ 'hourly', "apparent_temperature" ],	[ 'hourly', "feelslikegraph" ],			"graph", "50", "temperature" ],

	[ "hourly",	[ 'hourly', "dew_point_2m" ],		[ 'hourly', "dewpoint" ],			"temperatureunit" ],
	[ "hourlyskin",	[ 'hourly', "dew_point_2m" ],		[ 'hourly', "dewpoint" ],			"temperature" ],
	[ "hourly",	[ 'hourly', "dew_point_2m" ],		[ 'hourly', "dewpointgraph" ],			"graph", "50", "temperature" ],

	[ "current",	[ 'current', "relative_humidity_2m" ],	[ 'current', "humidity" ],			"%" ],
	[ "currentkodi",[ 'current', "relative_humidity_2m" ],	[ 'current', "humidity" ],			"round" ],
	[ "hourly",	[ 'hourly', "relative_humidity_2m" ],	[ 'hourly', "humidity" ],			"roundpercent" ],
	[ "hourlyskin",	[ 'hourly', "relative_humidity_2m" ],	[ 'hourly', "humidity" ],			"round" ],
	[ "hourly",	[ 'hourly', "relative_humidity_2m" ],	[ 'hourly', "humiditygraph" ],			"graph", "100" ],

	[ "current",	[ 'current', "precipitation" ],			[ 'current', "precip" ],			"precipitation" ],
	[ "hourly",	[ 'hourly', "precipitation" ],			[ 'hourly', "precip" ],				"precipitation" ],
	[ "hourly",	[ 'hourly', "precipitation" ],			[ 'hourly', "precipitationgraph" ],		"graph", "100" ],
	[ "current",	[ 'current', "precipitation_probability" ],	[ 'current', "precipitation" ],			"roundpercent" ],
	[ "hourly",	[ 'hourly', "precipitation_probability" ],	[ 'hourly', "precipitation" ],			"roundpercent" ],
	[ "hourly",	[ 'hourly', "precipitation_probability" ],	[ 'hourly', "precipitationprobabilitygraph" ],	"graph", "100" ],

	[ "currentskin",[ 'current', "precipitation" ],			[ 'current', "precipitation" ],			"precipitation" ],
	[ "hourlyskin",	[ 'hourly', "precipitation" ],			[ 'hourly', "precipitation" ],			"precipitation" ],
	[ "currentskin",[ 'current', "precipitation_probability" ],	[ 'current', "precipitationprobability" ],	"round" ],
	[ "hourlyskin",	[ 'hourly', "precipitation_probability" ],	[ 'hourly', "precipitationprobability" ],	"round" ],

	[ "current",	[ 'current', "pressure_msl" ],		[ 'current', "pressure" ],		"pressure" ],
	[ "hourly",	[ 'hourly', "pressure_msl" ],		[ 'hourly', "pressure" ],		"pressure" ],
	[ "hourly",	[ 'hourly', "pressure_msl" ],		[ 'hourly', "pressuregraph" ],		"graph", "100", "pressure" ],

	[ "current",	[ 'current', "surface_pressure" ],	[ 'current', "pressuresurface" ],	"pressure" ],
	[ "hourly",	[ 'hourly', "surface_pressure" ],	[ 'hourly', "pressuresurface" ],	"pressure" ],
	[ "hourly",	[ 'hourly', "surface_pressure" ],	[ 'hourly', "pressuresurfacegraph" ],	"graph", "100", "pressure" ],

	[ "current",	[ 'current', "wind_speed_10m" ],	[ 'current', "wind" ],			"windkodi" ],
	[ "currentkodi",[ 'current', "wind_speed_10m" ],	[ 'current', "wind" ],			"round" ],

	[ "current",	[ 'current', "wind_speed_10m" ],	[ 'current', "windaddon" ],		"windaddon" ],
	[ "current",	[ 'current', "wind_speed_10m" ],	[ 'current', "windspeed" ],		"speed" ],
	[ "hourly",	[ 'hourly', "wind_speed_10m" ],		[ 'hourly', "windspeed" ],		"speed" ],
	[ "hourly",	[ 'hourly', "wind_speed_10m" ],		[ 'hourly', "windspeedgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "wind_direction_10m" ],	[ 'current', "winddirection" ],		"direction" ],
	[ "current",	[ 'current', "wind_direction_10m" ],	[ 'current', "winddirectiondegree" ],	"round" ],
	[ "hourly",	[ 'hourly', "wind_direction_10m" ],	[ 'hourly', "winddirection" ],		"direction" ],
	[ "hourly",	[ 'hourly', "wind_direction_10m" ],	[ 'hourly', "winddirectiondegree" ],	"round" ],

	[ "current",	[ 'current', "wind_gusts_10m" ],	[ 'current', "windgust" ],		"speed" ],
	[ "hourly",	[ 'hourly', "wind_gusts_10m" ],		[ 'hourly', "windgust" ],		"speed" ],
	[ "hourly",	[ 'hourly', "wind_gusts_10m" ],		[ 'hourly', "windgustgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "weather_code" ],		[ 'current', "condition" ],		"wmocond" ],
	[ "current",	[ 'current', "weather_code" ],		[ 'current', "outlookicon" ],		"image" ],
	[ "current",	[ 'current', "weather_code" ],		[ 'current', "outlookiconwmo" ],	"wmoimage" ],
	[ "current",	[ 'current', "weather_code" ],		[ 'current', "fanartcode" ],		"code" ],
	[ "current",	[ 'current', "weather_code" ],		[ 'current', "fanartcodewmo" ],		"wmocode" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "outlook" ],		"wmocond" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "outlookicon" ],		"image" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "outlookiconwmo" ],		"wmoimage" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "fanartcode" ],		"code" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "fanartcodewmo" ],		"wmocode" ],

	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "condition" ],		"wmocond" ],
	[ "hourly",	[ 'hourly', "weather_code" ],		[ 'hourly', "conditiongraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "cloud_cover" ],		[ 'current', "cloudiness" ],		"roundpercent" ],
	[ "currentskin",[ 'current', "cloud_cover" ],		[ 'current', "cloudiness" ],		"round" ],
	[ "hourly",	[ 'hourly', "cloud_cover" ],		[ 'hourly', "cloudiness" ],		"roundpercent" ],
	[ "hourlyskin",	[ 'hourly', "cloud_cover" ],		[ 'hourly', "cloudiness" ],		"round" ],
	[ "hourly",	[ 'hourly', "cloud_cover" ],		[ 'hourly', "cloudinessgraph" ],	"graph", "100" ],

	[ "current",	[ 'current', "is_day" ],		[ 'current', "isday" ],			"bool" ],
	[ "hourly",	[ 'hourly', "is_day" ],			[ 'hourly', "isday" ],			"bool" ],

	[ "current",	[ 'current', "visibility" ],		[ 'current', "visibility" ],		"distance" ],
	[ "hourly",	[ 'hourly', "visibility" ],		[ 'hourly', "visibility" ],		"distance" ],
	[ "hourly",	[ 'hourly', "visibility" ],		[ 'hourly', "visibilitygraph" ],	"graph", "100", "divide1000" ],

	[ "current",	[ 'current', "uv_index" ],		[ 'current', "uvindex" ],		"uvindex" ],
	[ "hourly",	[ 'hourly', "uv_index" ],		[ 'hourly', "uvindex" ],		"uvindex" ],
	[ "hourly",	[ 'hourly', "uv_index" ],		[ 'hourly', "uvindexgraph" ],		"graph", "10" ],

	[ "current",	[ 'current', "direct_radiation" ],	[ 'current', "solarradiation" ],	"radiation" ],
	[ "hourly",	[ 'hourly', "direct_radiation" ],	[ 'hourly', "solarradiation" ],		"radiation" ],
	[ "hourly",	[ 'hourly', "direct_radiation" ],	[ 'hourly', "solarradiationgraph" ],	"graph", "100", "divide10" ],

	[ "daily",	[ 'daily', "time" ],			[ 'day', "title" ],			"weekday" ],
	[ "daily",	[ 'daily', "time" ],			[ 'day', "date" ],			"date" ],
	[ "daily",	[ 'daily', "time" ],			[ 'day', "shortdate" ],			"date" ],
	[ "daily",	[ 'daily', "time" ],			[ 'day', "shortday" ],			"weekdayshort" ],
	[ "daily",	[ 'daily', "time" ],			[ 'day', "longday" ],			"weekday" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "condition" ],			"wmocond" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "outlook" ],			"wmocond" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "outlookicon" ],		"image" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "outlookiconwmo" ],		"wmoimage" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "fanartcode" ],		"code" ],
	[ "daily",	[ 'daily', "weather_code" ],		[ 'day', "fanartcodewmo" ],		"wmocode" ],

	[ "daily",	[ 'daily', "temperature_2m_max" ],	[ 'day', "hightemp" ],			"temperaturekodi" ],
	[ "daily",	[ 'daily', "temperature_2m_min" ],	[ 'day', "lowtemp" ],			"temperaturekodi" ],
	[ "dailykodi",	[ 'daily', "temperature_2m_max" ],	[ 'day', "hightemp" ],			"round" ],
	[ "dailykodi",	[ 'daily', "temperature_2m_min" ],	[ 'day', "lowtemp" ],			"round" ],

	[ "daily",	[ 'daily', "temperature_2m_max" ],	[ 'day', "hightemperature" ],		"temperatureunit" ],
	[ "daily",	[ 'daily', "temperature_2m_min" ],	[ 'day', "lowtemperature" ],		"temperatureunit" ],
	[ "dailyskin",	[ 'daily', "temperature_2m_max" ],	[ 'day', "hightemperature" ],		"temperature" ],
	[ "dailyskin",	[ 'daily', "temperature_2m_min" ],	[ 'day', "lowtemperature" ],		"temperature" ],

	[ "daily",	[ 'daily', "sunrise" ],			[ 'day', "sunrise" ],			"time" ],
	[ "daily",	[ 'daily', "sunset" ],			[ 'day', "sunset" ],			"time" ],
	[ "current",	[ 'daily', "sunrise", 1 ],		[ 'today', "sunrise" ],			"time" ],
	[ "current",	[ 'daily', "sunset", 1 ],		[ 'today', "sunset" ],			"time" ],

	[ "daily",	[ 'daily', "daylight_duration" ],	[ 'day', "daylight" ],			"time" ],
	[ "daily",	[ 'daily', "sunshine_duration" ],	[ 'day', "sunshine" ],			"time" ],
	[ "daily",	[ 'daily', "precipitation_hours" ],	[ 'day', "precipitationhours" ],	"time" ],
	[ "daily",	[ 'daily', "uv_index_max" ],		[ 'day', "uvindex" ],			"uvindex" ],
]

map_airquality = [
	[ "current",	[ 'current_units', "pm10" ],		[ 'unit', "particles" ],		"unitparticles" ],
	[ "current",	[ 'current_units', "alder_pollen" ],	[ 'unit', "pollen" ],			"unitpollen" ],

	[ "current",	[ 'current', "time" ],			[ 'current', "aqdate" ],		"date" ],
	[ "current",	[ 'current', "time" ],			[ 'current', "aqtime" ],		"time" ],
	[ "current",	[ 'current', "time" ],			[ 'current', "aqhour" ],		"hour" ],

	[ "current",	[ 'current', "pm2_5" ],			[ 'current', "pm25" ],			"particles" ],
	[ "hourly",	[ 'hourly', "pm2_5" ],			[ 'hourly', "pm25" ],			"particles" ],
	[ "hourly",	[ 'hourly', "pm2_5" ],			[ 'hourly', "pm25graph" ],		"graph", "100" ],

	[ "current",	[ 'current', "pm10" ],			[ 'current', "pm10" ],			"particles" ],
	[ "hourly",	[ 'hourly', "pm10" ],			[ 'hourly', "pm10" ],			"particles" ],
	[ "hourly",	[ 'hourly', "pm10" ],			[ 'hourly', "pm10graph" ],		"graph", "100" ],

	[ "current",	[ 'current', "carbon_monoxide" ],	[ 'current', "co" ],			"particles" ],
	[ "hourly",	[ 'hourly', "carbon_monoxide" ],	[ 'hourly', "co" ],			"particles" ],
	[ "hourly",	[ 'hourly', "carbon_monoxide" ],	[ 'hourly', "cograph" ],		"graph", "100", "divide10" ],

	[ "current",	[ 'current', "ozone" ],			[ 'current', "ozone" ],			"particles" ],
	[ "hourly",	[ 'hourly', "ozone" ],			[ 'hourly', "ozone" ],			"particles" ],
	[ "hourly",	[ 'hourly', "ozone" ],			[ 'hourly', "ozonegraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "dust" ],			[ 'current', "dust" ],			"particles" ],
	[ "hourly",	[ 'hourly', "dust" ],			[ 'hourly', "dust" ],			"particles" ],
	[ "hourly",	[ 'hourly', "dust" ],			[ 'hourly', "dustgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "nitrogen_dioxide" ],	[ 'current', "no2" ],			"particles" ],
	[ "hourly",	[ 'hourly', "nitrogen_dioxide" ],	[ 'hourly', "no2" ],			"particles" ],
	[ "hourly",	[ 'hourly', "nitrogen_dioxide" ],	[ 'hourly', "no2graph" ],		"graph", "100" ],

	[ "current",	[ 'current', "sulphur_dioxide" ],	[ 'current', "so2" ],			"particles" ],
	[ "hourly",	[ 'hourly', "sulphur_dioxide" ],	[ 'hourly', "so2" ],			"particles" ],
	[ "hourly",	[ 'hourly', "sulphur_dioxide" ],	[ 'hourly', "so2graph" ],		"graph", "100" ],

	[ "current",	[ 'current', "european_aqi" ],		[ 'current', "aqieu" ],			"round" ],
	[ "hourly",	[ 'hourly', "european_aqi" ],		[ 'hourly', "aqieu" ],			"round" ],
	[ "hourly",	[ 'hourly', "european_aqi" ],		[ 'hourly', "aqieugraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "us_aqi" ],		[ 'current', "aqius" ],			"round" ],
	[ "hourly",	[ 'hourly', "us_aqi" ],			[ 'hourly', "aqius" ],			"round" ],
	[ "hourly",	[ 'hourly', "us_aqi" ],			[ 'hourly', "aqiusgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "alder_pollen" ],		[ 'current', "alder" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "alder_pollen" ],		[ 'hourly', "alder" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "alder_pollen" ],		[ 'hourly', "aldergraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "birch_pollen" ],		[ 'current', "birch" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "birch_pollen" ],		[ 'hourly', "birch" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "birch_pollen" ],		[ 'hourly', "birchgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "grass_pollen" ],		[ 'current', "grass" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "grass_pollen" ],		[ 'hourly', "grass" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "grass_pollen" ],		[ 'hourly', "grassgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "mugwort_pollen" ],	[ 'current', "mugwort" ],		"pollen" ],
	[ "hourly",	[ 'hourly', "mugwort_pollen" ],		[ 'hourly', "mugwort" ],		"pollen" ],
	[ "hourly",	[ 'hourly', "mugwort_pollen" ],		[ 'hourly', "mugwortgraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "olive_pollen" ],		[ 'current', "olive" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "olive_pollen" ],		[ 'hourly', "olive" ],			"pollen" ],
	[ "hourly",	[ 'hourly', "olive_pollen" ],		[ 'hourly', "olivegraph" ],		"graph", "100" ],

	[ "current",	[ 'current', "ragweed_pollen" ],	[ 'current', "ragweed" ],		"pollen" ],
	[ "hourly",	[ 'hourly', "ragweed_pollen" ],		[ 'hourly', "ragweed" ],		"pollen" ],
	[ "hourly",	[ 'hourly', "ragweed_pollen" ],		[ 'hourly', "ragweedgraph" ],		"graph", "100" ],
]

map_moon = [
	[ "current",	[ 'properties', 'moonrise', 'time' ],		[ 'today', "moonrise" ],	"timeiso" ],
	[ "current",	[ 'properties', 'moonrise', 'azimuth' ],	[ 'today', "moonriseazimuth" ],	"round" ],
	[ "current",	[ 'properties', 'moonset', 'time' ],		[ 'today', "moonset" ],		"timeiso" ],
	[ "current",	[ 'properties', 'moonset', 'azimuth' ],		[ 'today', "moonsetazimuth" ],	"round" ],
	[ "current",	[ 'properties', 'moonphase' ],			[ 'today', "moonphase" ],	"moonphase" ],
	[ "current",	[ 'properties', 'moonphase' ],			[ 'today', "moonphaseimage" ],	"moonphaseimage" ],
	[ "current",	[ 'properties', 'moonphase' ],			[ 'today', "moonphasedegree" ],	"round" ],
]

map = {
	'weather': map_weather,
	'airquality': map_airquality,
	'moon': map_moon,
}

# Alert (Condition)
map_alert_condition = {
		45: 'fog',
		48: 'fog',

		51: 'rain',
		53: 'rain',
		55: 'rain',
		61: 'rain',
		63: 'rain',
		65: 'rain',
		80: 'rain',
		81: 'rain',
		82: 'rain',
		56: 'rain',
		57: 'rain',
		66: 'rain',
		67: 'rain',

		71: 'snow',
		73: 'snow',
		75: 'snow',
		77: 'snow',
		85: 'snow',
		86: 'snow',

		95: 'storm',
		96: 'storm',
		99: 'storm',
}

# Mapping (Rainviewer)
map_rvradar     = [ 'radar', 'past' ]
map_rvsatellite = [ 'satellite', 'infrared' ]
map_layers      = { 'rvradar': map_rvradar, 'rvsatellite': map_rvsatellite, 'gctemp': '', 'gcwind': '' }
map_maps        = { 'osm': '', **map_layers }

# Mapping WMO to KODI
map_wmo = {
	'0d': 32,
	'0n': 31,
	'1d': 34,
	'1n': 33,
	'2d': 30,
	'2n': 29,
	'3d': 26,
	'3n': 26,
	'45d': 20,
	'45n': 20,
	'48d': 20,
	'48n': 20,
	'51d': 9,
	'51n': 9,
	'53d': 12,
	'53n': 12,
	'55d': 18,
	'55n': 18,
	'56d': 8,
	'56n': 8,
	'57d': 8,
	'57n': 8,
	'61d': 9,
	'61n': 9,
	'63d': 12,
	'63n': 12,
	'65d': 18,
	'65n': 18,
	'66d': 8,
	'66n': 8,
	'67d': 8,
	'67n': 8,
	'71d': 14,
	'71n': 14,
	'73d': 16,
	'73n': 16,
	'75d': 16,
	'75n': 16,
	'77d': 13,
	'77n': 13,
	'80d': 9,
	'80n': 9,
	'81d': 12,
	'81n': 12,
	'82d': 18,
	'82n': 18,
	'85d': 5,
	'85n': 5,
	'86d': 5,
	'86n': 5,
	'95d': 4,
	'95n': 4,
	'96d': 3,
	'96n': 3,
	'99d': 3,
	'99n': 3,
}

# Graph (Resolution)
map_height = {
	720: 720,
	1080: 1080,
	1440: 1440,
	2160: 2160,
	800: 720,
	1200: 1080,
	1600: 1440,
	2400: 2160
}

# Pressure
map_pressure = { 950: 0, 951: 1, 952: 2, 953: 3, 954: 4, 955: 5, 956: 6, 957: 7, 958: 8, 959: 9, 960: 10, 961: 11, 962: 12, 963: 13, 964: 14, 965: 15, 966: 16, 967: 17, 968: 18, 969: 19, 970: 20, 971: 21, 972: 22, 973: 23, 974: 24, 975: 25, 976: 26, 977: 27, 978: 28, 979: 29, 980: 30, 981: 31, 982: 32, 983: 33, 984: 34, 985: 35, 986: 36, 987: 37, 988: 38, 989: 39, 990: 40, 991: 41, 992: 42, 993: 43, 994: 44, 995: 45, 996: 46, 997: 47, 998: 48, 999: 49, 1000: 50, 1001: 51, 1002: 52, 1003: 53, 1004: 54, 1005: 55, 1006: 56, 1007: 57, 1008: 58, 1009: 59, 1010: 60, 1011: 61, 1012: 62, 1013: 63, 1014: 64, 1015: 65, 1016: 66, 1017: 67, 1018: 68, 1019: 69, 1020: 70, 1021: 71, 1022: 72, 1023: 73, 1024: 74, 1025: 75, 1026: 76, 1027: 77, 1028: 78, 1029: 79, 1030: 80, 1031: 81, 1032: 82, 1033: 83, 1034: 84, 1035: 85, 1036: 86, 1037: 87, 1038: 88, 1039: 89, 1040: 90, 1041: 91, 1042: 92, 1043: 93, 1044: 94, 1045: 95, 1046: 96, 1047: 97, 1048: 98, 1049: 99, 1050: 100 }

# Dynamic localization mapping
def localization():

	localization.wmo = {
		'0d': utils.locaddon(32200),
		'0n': utils.locaddon(32250),
		'1d': utils.locaddon(32201),
		'1n': utils.locaddon(32251),
		'2d': utils.locaddon(32202),
		'2n': utils.locaddon(32202),
		'3d': utils.locaddon(32203),
		'3n': utils.locaddon(32203),
		'45d': utils.locaddon(32204),
		'45n': utils.locaddon(32204),
		'48d': utils.locaddon(32205),
		'48n': utils.locaddon(32205),
		'51d': utils.locaddon(32206),
		'51n': utils.locaddon(32206),
		'53d': utils.locaddon(32207),
		'53n': utils.locaddon(32207),
		'55d': utils.locaddon(32208),
		'55n': utils.locaddon(32208),
		'56d': utils.locaddon(32209),
		'56n': utils.locaddon(32209),
		'57d': utils.locaddon(32210),
		'57n': utils.locaddon(32210),
		'61d': utils.locaddon(32211),
		'61n': utils.locaddon(32211),
		'63d': utils.locaddon(32212),
		'63n': utils.locaddon(32212),
		'65d': utils.locaddon(32213),
		'65n': utils.locaddon(32213),
		'66d': utils.locaddon(32214),
		'66n': utils.locaddon(32214),
		'67d': utils.locaddon(32215),
		'67n': utils.locaddon(32215),
		'71d': utils.locaddon(32216),
		'71n': utils.locaddon(32216),
		'73d': utils.locaddon(32217),
		'73n': utils.locaddon(32217),
		'75d': utils.locaddon(32218),
		'75n': utils.locaddon(32218),
		'77d': utils.locaddon(32219),
		'77n': utils.locaddon(32219),
		'80d': utils.locaddon(32220),
		'80n': utils.locaddon(32220),
		'81d': utils.locaddon(32221),
		'81n': utils.locaddon(32221),
		'82d': utils.locaddon(32222),
		'82n': utils.locaddon(32222),
		'85d': utils.locaddon(32223),
		'85n': utils.locaddon(32223),
		'86d': utils.locaddon(32224),
		'86n': utils.locaddon(32224),
		'95d': utils.locaddon(32225),
		'95n': utils.locaddon(32225),
		'96d': utils.locaddon(32226),
		'96n': utils.locaddon(32226),
		'99d': utils.locaddon(32227),
		'99n': utils.locaddon(32227)
	}

	localization.weekday = {
		'1': utils.loc(11),
		'2': utils.loc(12),
		'3': utils.loc(13),
		'4': utils.loc(14),
		'5': utils.loc(15),
		'6': utils.loc(16),
		'7': utils.loc(17)
	}

	localization.weekdayshort = {
		'1': utils.loc(41),
		'2': utils.loc(42),
		'3': utils.loc(43),
		'4': utils.loc(44),
		'5': utils.loc(45),
		'6': utils.loc(46),
		'7': utils.loc(47)
	}

	localization.layers = {
		'rvradar': utils.locaddon(32400),
		'rvsatellite': utils.locaddon(32401),
		'gctemp': utils.locaddon(32320),
		'gcwind': utils.locaddon(32323),
	}

# Dynamic settings
def alert(cache=False):

	alert.map = {
	        'temperaturegraph': {
			'type': 'temperature',
			'loc': 32320,
			'alert_temperature_high_1': utils.setting('alert_temperature_high_1', 'str', cache),
			'alert_temperature_high_2': utils.setting('alert_temperature_high_2', 'str', cache),
			'alert_temperature_high_3': utils.setting('alert_temperature_high_3', 'str', cache),
			'alert_temperature_low_1': utils.setting('alert_temperature_low_1', 'str', cache),
			'alert_temperature_low_2': utils.setting('alert_temperature_low_2', 'str', cache),
			'alert_temperature_low_3': utils.setting('alert_temperature_low_3', 'str', cache),
		},
	        'precipitationgraph': {
			'type': 'precipitation',
			'loc': 32321,
			'alert_precipitation_high_1': utils.setting('alert_precipitation_high_1', 'str', cache),
			'alert_precipitation_high_2': utils.setting('alert_precipitation_high_2', 'str', cache),
			'alert_precipitation_high_3': utils.setting('alert_precipitation_high_3', 'str', cache),
		},
	        'conditiongraph': {
			'type': 'condition',
			'loc': 32322,
			'alert_condition_wmo_1': utils.setting('alert_condition_wmo_1', 'str', cache),
			'alert_condition_wmo_2': utils.setting('alert_condition_wmo_2', 'str', cache),
			'alert_condition_wmo_3': utils.setting('alert_condition_wmo_3', 'str', cache),
		},
	        'windspeedgraph': {
			'type': 'windspeed',
			'loc': 32323,
			'alert_windspeed_high_1': utils.setting('alert_windspeed_high_1', 'str', cache),
			'alert_windspeed_high_2': utils.setting('alert_windspeed_high_2', 'str', cache),
			'alert_windspeed_high_3': utils.setting('alert_windspeed_high_3', 'str', cache),
		},
	        'windgustgraph': {
			'type': 'windgust',
			'loc': 32324,
			'alert_windgust_high_1': utils.setting('alert_windgust_high_1', 'str', cache),
			'alert_windgust_high_2': utils.setting('alert_windgust_high_2', 'str', cache),
			'alert_windgust_high_3': utils.setting('alert_windgust_high_3', 'str', cache),
		},
	        'feelslikegraph': {
			'type': 'feelslike',
			'loc': 32332,
			'alert_feelslike_high_1': utils.setting('alert_feelslike_high_1', 'str', cache),
			'alert_feelslike_high_2': utils.setting('alert_feelslike_high_2', 'str', cache),
			'alert_feelslike_high_3': utils.setting('alert_feelslike_high_3', 'str', cache),
		},
	        'dewpointgraph': {
			'type': 'dewpoint',
			'loc': 32333,
			'alert_dewpoint_high_1': utils.setting('alert_dewpoint_high_1', 'str', cache),
			'alert_dewpoint_high_2': utils.setting('alert_dewpoint_high_2', 'str', cache),
			'alert_dewpoint_high_3': utils.setting('alert_dewpoint_high_3', 'str', cache),
		},
	        'cloudinessgraph': {
			'type': 'cloudiness',
			'loc': 32334,
			'alert_cloudiness_high_1': utils.setting('alert_cloudiness_high_1', 'str', cache),
			'alert_cloudiness_high_2': utils.setting('alert_cloudiness_high_2', 'str', cache),
			'alert_cloudiness_high_3': utils.setting('alert_cloudiness_high_3', 'str', cache),
		},
	        'humiditygraph': {
			'type': 'humidity',
			'loc': 32346,
			'alert_humidity_high_1': utils.setting('alert_humidity_high_1', 'str', cache),
			'alert_humidity_high_2': utils.setting('alert_humidity_high_2', 'str', cache),
			'alert_humidity_high_3': utils.setting('alert_humidity_high_3', 'str', cache),
		},
	        'precipitationprobabilitygraph': {
			'type': 'precipitationprobability',
			'loc': 32321,
			'alert_precipitationprobability_high_1': utils.setting('alert_precipitationprobability_high_1', 'str', cache),
			'alert_precipitationprobability_high_2': utils.setting('alert_precipitationprobability_high_2', 'str', cache),
			'alert_precipitationprobability_high_3': utils.setting('alert_precipitationprobability_high_3', 'str', cache),
		},
	        'pressuregraph': {
			'type': 'pressure',
			'loc': 32347,
			'alert_pressure_high_1': utils.setting('alert_pressure_high_1', 'str', cache),
			'alert_pressure_high_2': utils.setting('alert_pressure_high_2', 'str', cache),
			'alert_pressure_high_3': utils.setting('alert_pressure_high_3', 'str', cache),
		},
	        'pressuresurfacegraph': {
			'type': 'pressuresurface',
			'loc': 32347,
			'alert_pressuresurface_high_1': utils.setting('alert_pressuresurface_high_1', 'str', cache),
			'alert_pressuresurface_high_2': utils.setting('alert_pressuresurface_high_2', 'str', cache),
			'alert_pressuresurface_high_3': utils.setting('alert_pressuresurface_high_3', 'str', cache),
		},
	        'solarradiationgraph': {
			'type': 'solarradiation',
			'loc': 32348,
			'alert_solarradiation_high_1': utils.setting('alert_solarradiation_high_1', 'str', cache),
			'alert_solarradiation_high_2': utils.setting('alert_solarradiation_high_2', 'str', cache),
			'alert_solarradiation_high_3': utils.setting('alert_solarradiation_high_3', 'str', cache),
		},
	        'visibilitygraph': {
			'type': 'visibility',
			'loc': 32349,
			'alert_visibility_low_1': utils.setting('alert_visibility_low_1', 'str', cache),
			'alert_visibility_low_2': utils.setting('alert_visibility_low_2', 'str', cache),
			'alert_visibility_low_3': utils.setting('alert_visibility_low_3', 'str', cache),
		},
	        'aqieugraph': {
			'type': 'aqieu',
			'loc': 32325,
			'alert_aqieu_high_1': utils.setting('alert_aqieu_high_1', 'str', cache),
			'alert_aqieu_high_2': utils.setting('alert_aqieu_high_2', 'str', cache),
			'alert_aqieu_high_3': utils.setting('alert_aqieu_high_3', 'str', cache),
		},
	        'aqiusgraph': {
			'type': 'aqius',
			'loc': 32326,
			'alert_aqius_high_1': utils.setting('alert_aqius_high_1', 'str', cache),
			'alert_aqius_high_2': utils.setting('alert_aqius_high_2', 'str', cache),
			'alert_aqius_high_3': utils.setting('alert_aqius_high_3', 'str', cache),
		},
	        'pm25graph': {
			'type': 'pm25',
			'loc': 32327,
			'alert_pm25_high_1': utils.setting('alert_pm25_high_1', 'str', cache),
			'alert_pm25_high_2': utils.setting('alert_pm25_high_2', 'str', cache),
			'alert_pm25_high_3': utils.setting('alert_pm25_high_3', 'str', cache),
		},
	        'pm10graph': {
			'type': 'pm10',
			'loc': 32328,
			'alert_pm10_high_1': utils.setting('alert_pm10_high_1', 'str', cache),
			'alert_pm10_high_2': utils.setting('alert_pm10_high_2', 'str', cache),
			'alert_pm10_high_3': utils.setting('alert_pm10_high_3', 'str', cache),
		},
	        'cograph': {
			'type': 'co',
			'loc': 32337,
			'alert_co_high_1': utils.setting('alert_co_high_1', 'str', cache),
			'alert_co_high_2': utils.setting('alert_co_high_2', 'str', cache),
			'alert_co_high_3': utils.setting('alert_co_high_3', 'str', cache),
		},
        	'ozonegraph': {
			'type': 'ozone',
			'loc': 32338,
			'alert_ozone_high_1': utils.setting('alert_ozone_high_1', 'str', cache),
			'alert_ozone_high_2': utils.setting('alert_ozone_high_2', 'str', cache),
			'alert_ozone_high_3': utils.setting('alert_ozone_high_3', 'str', cache),
		},
	        'dustgraph': {
			'type': 'dust',
			'loc': 32339,
			'alert_dust_high_1': utils.setting('alert_dust_high_1', 'str', cache),
			'alert_dust_high_2': utils.setting('alert_dust_high_2', 'str', cache),
			'alert_dust_high_3': utils.setting('alert_dust_high_3', 'str', cache),
		},
	        'no2graph': {
			'type': 'no2',
			'loc': 32330,
			'alert_no2_high_1': utils.setting('alert_no2_high_1', 'str', cache),
			'alert_no2_high_2': utils.setting('alert_no2_high_2', 'str', cache),
			'alert_no2_high_3': utils.setting('alert_no2_high_3', 'str', cache),
		},
	        'so2graph': {
			'type': 'so2',
			'loc': 32331,
			'alert_so2_high_1': utils.setting('alert_so2_high_1', 'str', cache),
			'alert_so2_high_2': utils.setting('alert_so2_high_2', 'str', cache),
			'alert_so2_high_3': utils.setting('alert_so2_high_3', 'str', cache),
		},
	        'uvindexgraph': {
			'type': 'uvindex',
			'loc': 32329,
			'alert_uvindex_high_1': utils.setting('alert_uvindex_high_1', 'str', cache),
			'alert_uvindex_high_2': utils.setting('alert_uvindex_high_2', 'str', cache),
			'alert_uvindex_high_3': utils.setting('alert_uvindex_high_3', 'str', cache),
		},
	        'aldergraph': {
			'type': 'alder',
			'loc': 32450,
			'alert_alder_high_1': utils.setting('alert_alder_high_1', 'str', cache),
			'alert_alder_high_2': utils.setting('alert_alder_high_2', 'str', cache),
			'alert_alder_high_3': utils.setting('alert_alder_high_3', 'str', cache),
		},
	        'birchgraph': {
			'type': 'birch',
			'loc': 32451,
			'alert_birch_high_1': utils.setting('alert_birch_high_1', 'str', cache),
			'alert_birch_high_2': utils.setting('alert_birch_high_2', 'str', cache),
			'alert_birch_high_3': utils.setting('alert_birch_high_3', 'str', cache),
		},
	        'grassgraph': {
			'type': 'grass',
			'loc': 32452,
			'alert_grass_high_1': utils.setting('alert_grass_high_1', 'str', cache),
			'alert_grass_high_2': utils.setting('alert_grass_high_2', 'str', cache),
			'alert_grass_high_3': utils.setting('alert_grass_high_3', 'str', cache),
		},
	        'mugwortgraph': {
			'type': 'mugwort',
			'loc': 32453,
			'alert_mugwort_high_1': utils.setting('alert_mugwort_high_1', 'str', cache),
			'alert_mugwort_high_2': utils.setting('alert_mugwort_high_2', 'str', cache),
			'alert_mugwort_high_3': utils.setting('alert_mugwort_high_3', 'str', cache),
		},
	        'olivegraph': {
			'type': 'olive',
			'loc': 32454,
			'alert_olive_high_1': utils.setting('alert_olive_high_1', 'str', cache),
			'alert_olive_high_2': utils.setting('alert_olive_high_2', 'str', cache),
			'alert_olive_high_3': utils.setting('alert_olive_high_3', 'str', cache),
		},
	        'ragweedgraph': {
			'type': 'ragweed',
			'loc': 32455,
			'alert_ragweed_high_1': utils.setting('alert_ragweed_high_1', 'str', cache),
			'alert_ragweed_high_2': utils.setting('alert_ragweed_high_2', 'str', cache),
			'alert_ragweed_high_3': utils.setting('alert_ragweed_high_3', 'str', cache),
		},
	}

def addon(cache=False):

	# Vars
	addon.settings   = utils.settings()
	addon.alerts     = 0
	addon.msgqueue   = []
	addon.scalecache = {}

	# Bool
	addon.debug       = utils.setting('debug', 'bool', cache)
	addon.verbose     = utils.setting('verbose', 'bool', cache)
	addon.enablehour  = utils.setting('enablehour', 'bool', cache)

	# Str
	addon.icons       = utils.setting('icons', 'str', cache)
	addon.unitsep     = utils.setting('unitsep', 'str', cache)
	addon.temp        = utils.setting('unittemp', 'str', cache)
	addon.tempdp      = utils.setting('unittempdp', 'str', cache)
	addon.speed       = utils.setting('unitspeed', 'str', cache)
	addon.speeddp     = utils.setting('unitspeeddp', 'str', cache)
	addon.precip      = utils.setting('unitprecip', 'str', cache)
	addon.precipdp    = utils.setting('unitprecipdp', 'str', cache)
	addon.distance    = utils.setting('unitdistance', 'str', cache)
	addon.distancedp  = utils.setting('unitdistancedp', 'str', cache)
	addon.particlesdp = utils.setting('unitparticlesdp', 'str', cache)
	addon.pollendp    = utils.setting('unitpollendp', 'str', cache)
	addon.uvindexdp   = utils.setting('unituvindexdp', 'str', cache)
	addon.pressuredp  = utils.setting('unitpressuredp', 'str', cache)
	addon.radiationdp = utils.setting('unitradiationdp', 'str', cache)
	addon.cdefault    = utils.setting('colordefault', 'str', cache)
	addon.cnegative   = utils.setting('colornegative', 'str', cache)
	addon.cnormal     = utils.setting('colornormal', 'str', cache)
	addon.cnotice     = utils.setting('colornotice', 'str', cache)
	addon.ccaution    = utils.setting('colorcaution', 'str', cache)
	addon.cdanger     = utils.setting('colordanger', 'str', cache)

	# Int
	addon.mapzoom     = utils.setting('mapzoom', 'int', cache)
	addon.maphistory  = utils.setting('maphistory', 'int', cache)
	addon.alerthours  = utils.setting('alert_hours', 'int', cache)

	# Maxlocs
	if utils.setting('explocations', 'bool', cache):
		addon.maxlocs = 6
	else:
		addon.maxlocs = 4

	# Addon mode
	# Note (v0.9.4): Remove "skin.estuary.openht" in a future update
	skin = utils.settingrpc('lookandfeel.skin')

	if skin == utils.winprop('openmeteo') or skin == 'skin.estuary.openht':
		addon.skin = True
	else:
		addon.skin = False


def kodi():
	kodi.long     = utils.region('datelong')
	kodi.date     = utils.region('dateshort')
	kodi.time     = utils.region('time')
	kodi.meri     = utils.region('meridiem')
	kodi.speed    = utils.region('speedunit')
	kodi.temp     = utils.region('tempunit')
	kodi.height   = map_height.get(utils.xbmcgui.getScreenHeight(), 1080)

def loc(locid, cache=False):
	loc.id   = locid
	loc.cid  = str(utils.settingrpc("weather.currentlocation"))
	loc.name = utils.setting(f'loc{locid}', 'str')
	loc.lat  = utils.setting(f'loc{locid}lat', 'float')
	loc.lon  = utils.setting(f'loc{locid}lon', 'float')
	loc.utz  = utils.setting(f'loc{locid}utz', 'bool')

	try:
		loc.tz = utils.timezone(utils.setting(f'loc{locid}tz'))
	except:
		loc.tz = utils.timezone('UTC')

def init(cache=False):
	kodi()
	localization()
	addon(cache)
	alert(cache)

	# Directory
	utils.createdir()

