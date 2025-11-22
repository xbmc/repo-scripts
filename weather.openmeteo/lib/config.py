import os
import xbmc
import xbmcvfs
import xbmcaddon

from . import utils

# API
map_api = {
	'search': 'https://geocoding-api.open-meteo.com/v1/search?name={}&count=10&language=en&format=json',
	'geoip': 'https://api.openht.org/geoipweather',
	'weather': 'https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,snowfall,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,dew_point_2m,precipitation_probability,visibility,uv_index,direct_radiation&hourly=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,precipitation_probability,precipitation,snowfall,weather_code,pressure_msl,surface_pressure,cloud_cover,visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index,is_day,direct_radiation&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,daylight_duration,sunshine_duration,uv_index_max,precipitation_hours&timeformat=unixtime&forecast_days={}&past_days=1',
	'airquality': 'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={}&longitude={}&current=european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,ozone,dust,nitrogen_dioxide,sulphur_dioxide,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&hourly=pm10,pm2_5,carbon_monoxide,ozone,dust,european_aqi,us_aqi,nitrogen_dioxide,sulphur_dioxide,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen&timeformat=unixtime&forecast_days=4&past_days=1',
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
maxdays  = utils.setting('fcdays', 'int')
mindays  = 1
maxhours = 72
minhours = 24
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

	# Location
	[ "current",     [ 'latitude' ],                              [ 'current', 'latitude' ],                             'round2' ],
	[ "current",     [ 'latitude' ],                              [ 'current', 'season' ],                               'season' ],
	[ "current",     [ 'longitude' ],                             [ 'current', 'longitude' ],                            'round2' ],
	[ "current",     [ 'elevation' ],                             [ 'current', 'elevation' ],                            'round' ],

	# Units
	[ "current",     [ 'current_units', 'wind_speed_10m' ],       [ 'unit', 'speed' ],                                   'unitspeed' ],
	[ "current",     [ 'current_units', 'temperature_2m' ],       [ 'unit', 'temperature' ],                             'unittemperature' ],
	[ "current",     [ 'current_units', 'precipitation' ],        [ 'unit', 'precipitation' ],                           'unitprecipitation' ],
	[ "current",     [ 'current_units', 'snowfall' ],             [ 'unit', 'snow' ],                                    'unitsnow' ],
	[ "current",     [ 'current_units', 'pressure_msl' ],         [ 'unit', 'pressure' ],                                'unitpressure' ],
	[ "current",     [ 'current_units', 'relative_humidity_2m' ], [ 'unit', 'percent' ],                                 'unitpercent' ],
	[ "current",     [ 'hourly_units', 'visibility' ],            [ 'unit', 'distance' ],                                'unitdistance' ],
	[ "current",     [ 'hourly_units', 'direct_radiation' ],      [ 'unit', 'radiation' ],                               'unitradiation' ],
	[ "current",     [ 'hourly_units', 'direct_radiation' ],      [ 'unit', 'solarradiation' ],                          'unitradiation' ],

	# Current
	[ "current",     [ 'current', "time" ],                       [ 'current', "date" ],                                 "date" ],
	[ "current",     [ 'current', "time" ],                       [ 'current', "time" ],                                 "time" ],
	[ "current",     [ 'current', "time" ],                       [ 'current', "hour" ],                                 "hour" ],
	[ "current",     [ 'current', "temperature_2m" ],             [ 'current', "temperature" ],                          "temperaturekodi" ],
	[ "current",     [ 'current', "temperature_2m" ],             [ 'current', "temperatureaddon" ],                     "temperature" ],
	[ "currentkodi", [ 'current', "temperature_2m" ],             [ 'current', "temperature" ],                          "round" ],
	[ "currentskin", [ 'current', "temperature_2m" ],             [ 'current', "temperature" ],                          "temperature" ],
	[ "current",     [ 'current', "apparent_temperature" ],       [ 'current', "feelslike" ],                            "temperaturekodi" ],
	[ "current",     [ 'current', "apparent_temperature" ],       [ 'current', "feelslikeaddon" ],                       "temperature" ],
	[ "currentkodi", [ 'current', "apparent_temperature" ],       [ 'current', "feelslike" ],                            "round" ],
	[ "currentskin", [ 'current', "apparent_temperature" ],       [ 'current', "feelslike" ],                            "temperature" ],
	[ "current",     [ 'current', "dew_point_2m" ],               [ 'current', "dewpoint" ],                             "temperaturekodi" ],
	[ "current",     [ 'current', "dew_point_2m" ],               [ 'current', "dewpointaddon" ],                        "temperature" ],
	[ "currentkodi", [ 'current', "dew_point_2m" ],               [ 'current', "dewpoint" ],                             "round" ],
	[ "currentskin", [ 'current', "dew_point_2m" ],               [ 'current', "dewpoint" ],                             "temperature" ],
	[ "current",     [ 'current', "relative_humidity_2m" ],       [ 'current', "humidity" ],                             "%" ],
	[ "current",     [ 'current', "relative_humidity_2m" ],       [ 'current', "humidityaddon" ],                        "round" ],
	[ "currentkodi", [ 'current', "relative_humidity_2m" ],       [ 'current', "humidity" ],                             "round" ],
	[ "current",     [ 'current', "precipitation_probability" ],  [ 'current', "precipitation" ],                        "roundpercent" ],
	[ "currentskin", [ 'current', "precipitation" ],              [ 'current', "precipitation" ],                        "precipitation" ],
	[ "current",     [ 'current', "precipitation" ],              [ 'current', "precipitationaddon" ],                   "precipitation" ],
	[ "current",     [ 'current', "precipitation_probability" ],  [ 'current', "precipitationprobability" ],             "round" ],
	[ "current",     [ 'current', "snowfall" ],                   [ 'current', "snow" ],                                 "snow" ],
	[ "current",     [ 'current', "pressure_msl" ],               [ 'current', "pressure" ],                             "pressure" ],
	[ "current",     [ 'current', "surface_pressure" ],           [ 'current', "pressuresurface" ],                      "pressure" ],
	[ "current",     [ 'current', "wind_speed_10m" ],             [ 'current', "wind" ],                                 "windkodi" ],
	[ "currentkodi", [ 'current', "wind_speed_10m" ],             [ 'current', "wind" ],                                 "round" ],
	[ "currentskin", [ 'current', "wind_speed_10m" ],             [ 'current', "wind" ],                                 "windkodi" ],
	[ "current",     [ 'current', "wind_speed_10m" ],             [ 'current', "windspeed" ],                            "speed" ],
	[ "current",     [ 'current', "wind_direction_10m" ],         [ 'current', "winddirection" ],                        "direction" ],
	[ "current",     [ 'current', "wind_direction_10m" ],         [ 'current', "winddirectiondegree" ],                  "round" ],
	[ "current",     [ 'current', "wind_gusts_10m" ],             [ 'current', "windgust" ],                             "speed" ],
	[ "current",     [ 'current', "weather_code" ],               [ 'current', "condition" ],                            "wmocond" ],
	[ "current",     [ 'current', "weather_code" ],               [ 'current', "outlookicon" ],                          "image" ],
	[ "currentskin", [ 'current', "weather_code" ],               [ 'current', "outlookicon" ],                          "wmoimage" ],
	[ "current",     [ 'current', "weather_code" ],               [ 'current', "outlookiconwmo" ],                       "wmoimage" ],
	[ "current",     [ 'current', "weather_code" ],               [ 'current', "fanartcode" ],                           "code" ],
	[ "currentskin", [ 'current', "weather_code" ],               [ 'current', "fanartcode" ],                           "wmocode" ],
	[ "current",     [ 'current', "weather_code" ],               [ 'current', "fanartcodewmo" ],                        "wmocode" ],
	[ "current",     [ 'current', "cloud_cover" ],                [ 'current', "cloudiness" ],                           "roundpercent" ],
	[ "current",     [ 'current', "cloud_cover" ],                [ 'current', "cloudinessaddon" ],                      "round" ],
	[ "currentskin", [ 'current', "cloud_cover" ],                [ 'current', "cloudiness" ],                           "round" ],
	[ "current",     [ 'current', "is_day" ],                     [ 'current', "isday" ],                                "bool" ],
	[ "current",     [ 'current', "visibility" ],                 [ 'current', "visibility" ],                           "distance" ],
	[ "current",     [ 'current', "uv_index" ],                   [ 'current', "uvindex" ],                              "uvindex" ],
	[ "current",     [ 'current', "direct_radiation" ],           [ 'current', "solarradiation" ],                       "radiation" ],

	# Hourly
	[ "hourly",      [ 'hourly', "time" ],                        [ 'hourly', "date" ],                                  "date" ],
	[ "hourly",      [ 'hourly', "time" ],                        [ 'hourly', "shortdate" ],                             "date" ],
	[ "hourly",      [ 'hourly', "time" ],                        [ 'hourly', "time" ],                                  "time" ],
	[ "hourly",      [ 'hourly', "time" ],                        [ 'hourly', "hour" ],                                  "hour" ],
	[ "hourly",      [ 'hourly', "temperature_2m" ],              [ 'hourly', "temperature" ],                           "temperatureunit" ],
	[ "hourlyskin",  [ 'hourly', "temperature_2m" ],              [ 'hourly', "temperature" ],                           "temperature" ],
	[ "hourly",      [ 'hourly', "apparent_temperature" ],        [ 'hourly', "feelslike" ],                             "temperatureunit" ],
	[ "hourlyskin",  [ 'hourly', "apparent_temperature" ],        [ 'hourly', "feelslike" ],                             "temperature" ],
	[ "hourly",      [ 'hourly', "dew_point_2m" ],                [ 'hourly', "dewpoint" ],                              "temperatureunit" ],
	[ "hourlyskin",  [ 'hourly', "dew_point_2m" ],                [ 'hourly', "dewpoint" ],                              "temperature" ],
	[ "hourly",      [ 'hourly', "relative_humidity_2m" ],        [ 'hourly', "humidity" ],                              "roundpercent" ],
	[ "hourlyskin",  [ 'hourly', "relative_humidity_2m" ],        [ 'hourly', "humidity" ],                              "round" ],
	[ "hourly",      [ 'hourly', "precipitation_probability" ],   [ 'hourly', "precipitation" ],                         "roundpercent" ],
	[ "hourlyskin",  [ 'hourly', "precipitation" ],               [ 'hourly', "precipitation" ],                         "precipitation" ],
	[ "hourly",      [ 'hourly', "precipitation" ],               [ 'hourly', "precipitationaddon" ],                    "precipitation" ],
	[ "hourly",      [ 'hourly', "precipitation_probability" ],   [ 'hourly', "precipitationprobability" ],              "round" ],
	[ "hourly",      [ 'hourly', "snowfall" ],                    [ 'hourly', "snow" ],                                  "snow" ],
	[ "hourly",      [ 'hourly', "pressure_msl" ],                [ 'hourly', "pressure" ],                              "pressure" ],
	[ "hourly",      [ 'hourly', "surface_pressure" ],            [ 'hourly', "pressuresurface" ],                       "pressure" ],
	[ "hourly",      [ 'hourly', "wind_speed_10m" ],              [ 'hourly', "windspeed" ],                             "speed" ],
	[ "hourly",      [ 'hourly', "wind_direction_10m" ],          [ 'hourly', "winddirection" ],                         "direction" ],
	[ "hourly",      [ 'hourly', "wind_direction_10m" ],          [ 'hourly', "winddirectiondegree" ],                   "round" ],
	[ "hourly",      [ 'hourly', "wind_gusts_10m" ],              [ 'hourly', "windgust" ],                              "speed" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "outlook" ],                               "wmocond" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "outlookicon" ],                           "image" ],
	[ "hourlyskin",  [ 'hourly', "weather_code" ],                [ 'hourly', "outlookicon" ],                           "wmoimage" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "outlookiconwmo" ],                        "wmoimage" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "fanartcode" ],                            "code" ],
	[ "hourlyskin",  [ 'hourly', "weather_code" ],                [ 'hourly', "fanartcode" ],                            "wmocode" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "fanartcodewmo" ],                         "wmocode" ],
	[ "hourly",      [ 'hourly', "weather_code" ],                [ 'hourly', "condition" ],                             "wmocond" ],
	[ "hourly",      [ 'hourly', "cloud_cover" ],                 [ 'hourly', "cloudiness" ],                            "roundpercent" ],
	[ "hourlyskin",  [ 'hourly', "cloud_cover" ],                 [ 'hourly', "cloudiness" ],                            "round" ],
	[ "hourly",      [ 'hourly', "is_day" ],                      [ 'hourly', "isday" ],                                 "bool" ],
	[ "hourly",      [ 'hourly', "visibility" ],                  [ 'hourly', "visibility" ],                            "distance" ],
	[ "hourly",      [ 'hourly', "uv_index" ],                    [ 'hourly', "uvindex" ],                               "uvindex" ],
	[ "hourly",      [ 'hourly', "direct_radiation" ],            [ 'hourly', "solarradiation" ],                        "radiation" ],

	# Graphs
	[ "graph",      [ 'hourly', "temperature_2m" ],              [ 'hourly', "temperature.graph" ],                     "graph", "temperature" ],
	[ "graph",      [ 'hourly', "apparent_temperature" ],        [ 'hourly', "feelslike.graph" ],                       "graph", "temperature" ],
	[ "graph",      [ 'hourly', "dew_point_2m" ],                [ 'hourly', "dewpoint.graph" ],                        "graph", "temperature" ],
	[ "graph",      [ 'hourly', "relative_humidity_2m" ],        [ 'hourly', "humidity.graph" ],                        "graph", "round" ],
	[ "graph",      [ 'hourly', "precipitation" ],               [ 'hourly', "precipitation.graph" ],                   "graph", "precipitation" ],
	[ "graph",      [ 'hourly', "precipitation_probability" ],   [ 'hourly', "precipitationprobability.graph" ],        "graph", "round" ],
	[ "graph",      [ 'hourly', "snowfall" ],                    [ 'hourly', "snow.graph" ],                            "graph", "snow" ],
	[ "graph",      [ 'hourly', "pressure_msl" ],                [ 'hourly', "pressure.graph" ],                        "graph", "pressure" ],
	[ "graph",      [ 'hourly', "surface_pressure" ],            [ 'hourly', "pressuresurface.graph" ],                 "graph", "pressure" ],
	[ "graph",      [ 'hourly', "wind_speed_10m" ],              [ 'hourly', "windspeed.graph" ],                       "graph", "speed" ],
	[ "graph",      [ 'hourly', "wind_gusts_10m" ],              [ 'hourly', "windgust.graph" ],                        "graph", "speed" ],
	[ "graph",      [ 'hourly', "weather_code" ],                [ 'hourly', "condition.graph" ],                       "graph", "round" ],
	[ "graph",      [ 'hourly', "cloud_cover" ],                 [ 'hourly', "cloudiness.graph" ],                      "graph", "round" ],
	[ "graph",      [ 'hourly', "visibility" ],                  [ 'hourly', "visibility.graph" ],                      "graph", "distance" ],
	[ "graph",      [ 'hourly', "uv_index" ],                    [ 'hourly', "uvindex.graph" ],                         "graph", "uvindex" ],
	[ "graph",      [ 'hourly', "direct_radiation" ],            [ 'hourly', "solarradiation.graph" ],                  "graph", "radiation" ],

	# Daily
	[ "daily",       [ 'daily', "time" ],                         [ 'day', "title" ],                                    "weekday" ],
	[ "daily",       [ 'daily', "time" ],                         [ 'day', "date" ],                                     "date" ],
	[ "daily",       [ 'daily', "time" ],                         [ 'day', "shortdate" ],                                "date" ],
	[ "daily",       [ 'daily', "time" ],                         [ 'day', "shortday" ],                                 "weekdayshort" ],
	[ "daily",       [ 'daily', "time" ],                         [ 'day', "longday" ],                                  "weekday" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "condition" ],                                "wmocond" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "outlook" ],                                  "wmocond" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "outlookicon" ],                              "image" ],
	[ "dailyskin",   [ 'daily', "weather_code" ],                 [ 'day', "outlookicon" ],                              "wmoimage" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "outlookiconwmo" ],                           "wmoimage" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "fanartcode" ],                               "code" ],
	[ "dailyskin",   [ 'daily', "weather_code" ],                 [ 'day', "fanartcode" ],                               "wmocode" ],
	[ "daily",       [ 'daily', "weather_code" ],                 [ 'day', "fanartcodewmo" ],                            "wmocode" ],
	[ "daily",       [ 'daily', "temperature_2m_max" ],           [ 'day', "hightemp" ],                                 "temperaturekodi" ],
	[ "dailykodi",   [ 'daily', "temperature_2m_max" ],           [ 'day', "hightemp" ],                                 "round" ],
	[ "dailyskin",   [ 'daily', "temperature_2m_max" ],           [ 'day', "hightemp" ],                                 "temperature" ],
	[ "daily",       [ 'daily', "temperature_2m_min" ],           [ 'day', "lowtemp" ],                                  "temperaturekodi" ],
	[ "dailykodi",   [ 'daily', "temperature_2m_min" ],           [ 'day', "lowtemp" ],                                  "round" ],
	[ "dailyskin",   [ 'daily', "temperature_2m_min" ],           [ 'day', "lowtemp" ],                                  "temperature" ],
	[ "daily",       [ 'daily', "temperature_2m_max" ],           [ 'day', "hightemperature" ],                          "temperatureunit" ],
	[ "dailyskin",   [ 'daily', "temperature_2m_max" ],           [ 'day', "hightemperature" ],                          "temperature" ],
	[ "daily",       [ 'daily', "temperature_2m_min" ],           [ 'day', "lowtemperature" ],                           "temperatureunit" ],
	[ "dailyskin",   [ 'daily', "temperature_2m_min" ],           [ 'day', "lowtemperature" ],                           "temperature" ],
	[ "daily",       [ 'daily', "sunrise" ],                      [ 'day', "sunrise" ],                                  "time" ],
	[ "daily",       [ 'daily', "sunset" ],                       [ 'day', "sunset" ],                                   "time" ],
	[ "daily",       [ 'daily', "daylight_duration" ],            [ 'day', "daylight" ],                                 "seconds" ],
	[ "daily",       [ 'daily', "sunshine_duration" ],            [ 'day', "sunshine" ],                                 "seconds" ],
	[ "daily",       [ 'daily', "precipitation_hours" ],          [ 'day', "precipitationhours" ],                       "round" ],
	[ "daily",       [ 'daily', "uv_index_max" ],                 [ 'day', "uvindex" ],                                  "uvindex" ],

	# Today
	[ "current",     [ 'daily', "sunrise", 3 ],                   [ 'today', "sunrise" ],                                "time" ],
	[ "current",     [ 'daily', "sunset", 3 ],                    [ 'today', "sunset" ],                                 "time" ],
	[ "current",     [ 'daily', "daylight_duration", 3 ],         [ 'today', "daylight" ],                               "seconds" ],
	[ "current",     [ 'daily', "sunshine_duration", 3 ],         [ 'today', "sunshine" ],                               "seconds" ],

	# TimeOfDay
	[ "timeofday",   [ 'hourly', "weather_code" ],                [ 'timeofday', "isfetched" ],                          "timeofday" ],
]

map_airquality = [

	# Units
	[ "current",    [ 'current_units', "pm10" ],          [ 'unit', "particles" ],                 "unitparticles" ],
	[ "current",    [ 'current_units', "alder_pollen" ],  [ 'unit', "pollen" ],                    "unitpollen" ],

	# Current
	[ "current",    [ 'current', "time" ],                [ 'current', "aqdate" ],                 "date" ],
	[ "current",    [ 'current', "time" ],                [ 'current', "aqtime" ],                 "time" ],
	[ "current",    [ 'current', "time" ],                [ 'current', "aqhour" ],                 "hour" ],
	[ "current",    [ 'current', "pm2_5" ],               [ 'current', "pm25" ],                   "particles" ],
	[ "current",    [ 'current', "pm10" ],                [ 'current', "pm10" ],                   "particles" ],
	[ "current",    [ 'current', "carbon_monoxide" ],     [ 'current', "co" ],                     "particles" ],
	[ "current",    [ 'current', "ozone" ],               [ 'current', "ozone" ],                  "particles" ],
	[ "current",    [ 'current', "dust" ],                [ 'current', "dust" ],                   "particles" ],
	[ "current",    [ 'current', "nitrogen_dioxide" ],    [ 'current', "no2" ],                    "particles" ],
	[ "current",    [ 'current', "sulphur_dioxide" ],     [ 'current', "so2" ],                    "particles" ],
	[ "current",    [ 'current', "european_aqi" ],        [ 'current', "aqieu" ],                  "round" ],
	[ "current",    [ 'current', "us_aqi" ],              [ 'current', "aqius" ],                  "round" ],
	[ "current",    [ 'current', "alder_pollen" ],        [ 'current', "alder" ],                  "pollen" ],
	[ "current",    [ 'current', "birch_pollen" ],        [ 'current', "birch" ],                  "pollen" ],
	[ "current",    [ 'current', "grass_pollen" ],        [ 'current', "grass" ],                  "pollen" ],
	[ "current",    [ 'current', "mugwort_pollen" ],      [ 'current', "mugwort" ],                "pollen" ],
	[ "current",    [ 'current', "olive_pollen" ],        [ 'current', "olive" ],                  "pollen" ],
	[ "current",    [ 'current', "ragweed_pollen" ],      [ 'current', "ragweed" ],                "pollen" ],

	# Hourly
	[ "hourly",     [ 'hourly', "pm2_5" ],                [ 'hourly', "pm25" ],                    "particles" ],
	[ "hourly",     [ 'hourly', "pm10" ],                 [ 'hourly', "pm10" ],                    "particles" ],
	[ "hourly",     [ 'hourly', "carbon_monoxide" ],      [ 'hourly', "co" ],                      "particles" ],
	[ "hourly",     [ 'hourly', "ozone" ],                [ 'hourly', "ozone" ],                   "particles" ],
	[ "hourly",     [ 'hourly', "dust" ],                 [ 'hourly', "dust" ],                    "particles" ],
	[ "hourly",     [ 'hourly', "nitrogen_dioxide" ],     [ 'hourly', "no2" ],                     "particles" ],
	[ "hourly",     [ 'hourly', "sulphur_dioxide" ],      [ 'hourly', "so2" ],                     "particles" ],
	[ "hourly",     [ 'hourly', "european_aqi" ],         [ 'hourly', "aqieu" ],                   "round" ],
	[ "hourly",     [ 'hourly', "us_aqi" ],               [ 'hourly', "aqius" ],                   "round" ],
	[ "hourly",     [ 'hourly', "alder_pollen" ],         [ 'hourly', "alder" ],                   "pollen" ],
	[ "hourly",     [ 'hourly', "birch_pollen" ],         [ 'hourly', "birch" ],                   "pollen" ],
	[ "hourly",     [ 'hourly', "grass_pollen" ],         [ 'hourly', "grass" ],                   "pollen" ],
	[ "hourly",     [ 'hourly', "mugwort_pollen" ],       [ 'hourly', "mugwort" ],                 "pollen" ],
	[ "hourly",     [ 'hourly', "olive_pollen" ],         [ 'hourly', "olive" ],                   "pollen" ],
	[ "hourly",     [ 'hourly', "ragweed_pollen" ],       [ 'hourly', "ragweed" ],                 "pollen" ],

	# Graphs
	[ "graph",     [ 'hourly', "pm2_5" ],                [ 'hourly', "pm25.graph" ],              "graph", "particles" ],
	[ "graph",     [ 'hourly', "pm10" ],                 [ 'hourly', "pm10.graph" ],              "graph", "particles" ],
	[ "graph",     [ 'hourly', "carbon_monoxide" ],      [ 'hourly', "co.graph" ],                "graph", "particles" ],
	[ "graph",     [ 'hourly', "ozone" ],                [ 'hourly', "ozone.graph" ],             "graph", "particles" ],
	[ "graph",     [ 'hourly', "dust" ],                 [ 'hourly', "dust.graph" ],              "graph", "particles" ],
	[ "graph",     [ 'hourly', "nitrogen_dioxide" ],     [ 'hourly', "no2.graph" ],               "graph", "particles" ],
	[ "graph",     [ 'hourly', "sulphur_dioxide" ],      [ 'hourly', "so2.graph" ],               "graph", "round" ],
	[ "graph",     [ 'hourly', "european_aqi" ],         [ 'hourly', "aqieu.graph" ],             "graph", "round" ],
	[ "graph",     [ 'hourly', "us_aqi" ],               [ 'hourly', "aqius.graph" ],             "graph", "pollen" ],
	[ "graph",     [ 'hourly', "alder_pollen" ],         [ 'hourly', "alder.graph" ],             "graph", "pollen" ],
	[ "graph",     [ 'hourly', "birch_pollen" ],         [ 'hourly', "birch.graph" ],             "graph", "pollen" ],
	[ "graph",     [ 'hourly', "grass_pollen" ],         [ 'hourly', "grass.graph" ],             "graph", "pollen" ],
	[ "graph",     [ 'hourly', "mugwort_pollen" ],       [ 'hourly', "mugwort.graph" ],           "graph", "pollen" ],
	[ "graph",     [ 'hourly', "olive_pollen" ],         [ 'hourly', "olive.graph" ],             "graph", "pollen" ],
	[ "graph",     [ 'hourly', "ragweed_pollen" ],       [ 'hourly', "ragweed.graph" ],           "graph", "pollen" ],
]

map_moon = [
	[ "current",    [ 'properties', 'moonrise', 'time' ],        [ 'today', "moonrise" ],              "timeiso" ],
	[ "current",    [ 'properties', 'moonrise', 'azimuth' ],     [ 'today', "moonriseazimuth" ],       "round" ],
	[ "current",    [ 'properties', 'moonset', 'time' ],         [ 'today', "moonset" ],               "timeiso" ],
	[ "current",    [ 'properties', 'moonset', 'azimuth' ],      [ 'today', "moonsetazimuth" ],        "round" ],
	[ "current",    [ 'properties', 'moonphase' ],               [ 'today', "moonphase" ],             "moonphase" ],
	[ "current",    [ 'properties', 'moonphase' ],               [ 'today', "moonphaseimage" ],        "moonphaseimage" ],
	[ "current",    [ 'properties', 'moonphase' ],               [ 'today', "moonphasedegree" ],       "round" ],
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
map_rv          = { 'rvradar': map_rvradar, 'rvsatellite': map_rvsatellite }
map_gc          = { 'gctemp': '', 'gcwind': '' }
map_layers      = { **map_rv, **map_gc }

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

# Personalized forecast
map_fcstart = {
	0: None,
	1: 1,
	2: 2,
	3: 3,
	4: 4,
	5: 5,
	6: 6,
	7: 7,
	8: 8,
	9: 9,
	10: 10,
	11: 11,
	12: 12,
}
map_fcend = {
	24: None,
	23: -1,
	22: -2,
	21: -3,
	20: -4,
	19: -5,
	18: -6,
	17: -7,
	16: -8,
	15: -9,
	14: -10,
	13: -11,
	14: -12,
}

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

	localization.timeofday = {
		0: utils.locaddon(32480),
		1: utils.locaddon(32481),
		2: utils.locaddon(32482),
		3: utils.locaddon(32483),
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
	        'temperature.graph': {
			'type': 'temperature',
			'unit': 'temperature',
			'icon': 'temperature',
			'loc': 32320,
			'alert_temperature_high_1': utils.setting('alert_temperature_high_1', 'str', cache),
			'alert_temperature_high_2': utils.setting('alert_temperature_high_2', 'str', cache),
			'alert_temperature_high_3': utils.setting('alert_temperature_high_3', 'str', cache),
			'alert_temperature_low_1': utils.setting('alert_temperature_low_1', 'str', cache),
			'alert_temperature_low_2': utils.setting('alert_temperature_low_2', 'str', cache),
			'alert_temperature_low_3': utils.setting('alert_temperature_low_3', 'str', cache),
		},
	        'precipitation.graph': {
			'type': 'precipitation',
			'unit': 'precipitation',
			'icon': 'precipitation',
			'loc': 32321,
			'alert_precipitation_high_1': utils.setting('alert_precipitation_high_1', 'str', cache),
			'alert_precipitation_high_2': utils.setting('alert_precipitation_high_2', 'str', cache),
			'alert_precipitation_high_3': utils.setting('alert_precipitation_high_3', 'str', cache),
		},
	        'snow.graph': {
			'type': 'snow',
			'unit': 'snow',
			'icon': 'snow',
			'loc': 32217,
			'alert_snow_high_1': utils.setting('alert_snow_high_1', 'str', cache),
			'alert_snow_high_2': utils.setting('alert_snow_high_2', 'str', cache),
			'alert_snow_high_3': utils.setting('alert_snow_high_3', 'str', cache),
		},
	        'condition.graph': {
			'type': 'condition',
			'unit': '',
			'icon': 'condition',
			'loc': 32322,
			'alert_condition_wmo_1': utils.setting('alert_condition_wmo_1', 'str', cache),
			'alert_condition_wmo_2': utils.setting('alert_condition_wmo_2', 'str', cache),
			'alert_condition_wmo_3': utils.setting('alert_condition_wmo_3', 'str', cache),
		},
	        'windspeed.graph': {
			'type': 'windspeed',
			'unit': 'speed',
			'icon': 'wind',
			'loc': 32323,
			'alert_windspeed_high_1': utils.setting('alert_windspeed_high_1', 'str', cache),
			'alert_windspeed_high_2': utils.setting('alert_windspeed_high_2', 'str', cache),
			'alert_windspeed_high_3': utils.setting('alert_windspeed_high_3', 'str', cache),
		},
	        'windgust.graph': {
			'type': 'windgust',
			'unit': 'speed',
			'icon': 'wind',
			'loc': 32324,
			'alert_windgust_high_1': utils.setting('alert_windgust_high_1', 'str', cache),
			'alert_windgust_high_2': utils.setting('alert_windgust_high_2', 'str', cache),
			'alert_windgust_high_3': utils.setting('alert_windgust_high_3', 'str', cache),
		},
	        'feelslike.graph': {
			'type': 'feelslike',
			'unit': 'temperature',
			'icon': 'temperature',
			'loc': 32332,
			'alert_feelslike_high_1': utils.setting('alert_feelslike_high_1', 'str', cache),
			'alert_feelslike_high_2': utils.setting('alert_feelslike_high_2', 'str', cache),
			'alert_feelslike_high_3': utils.setting('alert_feelslike_high_3', 'str', cache),
			'alert_feelslike_low_1': utils.setting('alert_feelslike_low_1', 'str', cache),
			'alert_feelslike_low_2': utils.setting('alert_feelslike_low_2', 'str', cache),
			'alert_feelslike_low_3': utils.setting('alert_feelslike_low_3', 'str', cache),
		},
	        'dewpoint.graph': {
			'type': 'dewpoint',
			'unit': 'temperature',
			'icon': 'temperature',
			'loc': 32333,
			'alert_dewpoint_high_1': utils.setting('alert_dewpoint_high_1', 'str', cache),
			'alert_dewpoint_high_2': utils.setting('alert_dewpoint_high_2', 'str', cache),
			'alert_dewpoint_high_3': utils.setting('alert_dewpoint_high_3', 'str', cache),
			'alert_dewpoint_low_1': utils.setting('alert_dewpoint_low_1', 'str', cache),
			'alert_dewpoint_low_2': utils.setting('alert_dewpoint_low_2', 'str', cache),
			'alert_dewpoint_low_3': utils.setting('alert_dewpoint_low_3', 'str', cache),
		},
	        'cloudiness.graph': {
			'type': 'cloudiness',
			'unit': '%',
			'icon': 'cloud',
			'loc': 32334,
			'alert_cloudiness_high_1': utils.setting('alert_cloudiness_high_1', 'str', cache),
			'alert_cloudiness_high_2': utils.setting('alert_cloudiness_high_2', 'str', cache),
			'alert_cloudiness_high_3': utils.setting('alert_cloudiness_high_3', 'str', cache),
		},
	        'humidity.graph': {
			'type': 'humidity',
			'unit': '%',
			'icon': 'humidity',
			'loc': 32346,
			'alert_humidity_high_1': utils.setting('alert_humidity_high_1', 'str', cache),
			'alert_humidity_high_2': utils.setting('alert_humidity_high_2', 'str', cache),
			'alert_humidity_high_3': utils.setting('alert_humidity_high_3', 'str', cache),
		},
	        'precipitationprobability.graph': {
			'type': 'precipitationprobability',
			'unit': '%',
			'icon': 'precipitation',
			'loc': 32321,
			'alert_precipitationprobability_high_1': utils.setting('alert_precipitationprobability_high_1', 'str', cache),
			'alert_precipitationprobability_high_2': utils.setting('alert_precipitationprobability_high_2', 'str', cache),
			'alert_precipitationprobability_high_3': utils.setting('alert_precipitationprobability_high_3', 'str', cache),
		},
	        'pressure.graph': {
			'type': 'pressure',
			'unit': 'pressure',
			'icon': 'pressure',
			'loc': 32347,
			'alert_pressure_high_1': utils.setting('alert_pressure_high_1', 'str', cache),
			'alert_pressure_high_2': utils.setting('alert_pressure_high_2', 'str', cache),
			'alert_pressure_high_3': utils.setting('alert_pressure_high_3', 'str', cache),
			'alert_pressure_low_1': utils.setting('alert_pressure_low_1', 'str', cache),
			'alert_pressure_low_2': utils.setting('alert_pressure_low_2', 'str', cache),
			'alert_pressure_low_3': utils.setting('alert_pressure_low_3', 'str', cache),
		},
	        'pressuresurface.graph': {
			'type': 'pressuresurface',
			'unit': 'pressure',
			'icon': 'pressure',
			'loc': 32347,
			'alert_pressuresurface_high_1': utils.setting('alert_pressuresurface_high_1', 'str', cache),
			'alert_pressuresurface_high_2': utils.setting('alert_pressuresurface_high_2', 'str', cache),
			'alert_pressuresurface_high_3': utils.setting('alert_pressuresurface_high_3', 'str', cache),
			'alert_pressuresurface_low_1': utils.setting('alert_pressuresurface_low_1', 'str', cache),
			'alert_pressuresurface_low_2': utils.setting('alert_pressuresurface_low_2', 'str', cache),
			'alert_pressuresurface_low_3': utils.setting('alert_pressuresurface_low_3', 'str', cache),
		},
	        'solarradiation.graph': {
			'type': 'solarradiation',
			'unit': 'solarradiation',
			'icon': 'solarradiation',
			'loc': 32348,
			'alert_solarradiation_high_1': utils.setting('alert_solarradiation_high_1', 'str', cache),
			'alert_solarradiation_high_2': utils.setting('alert_solarradiation_high_2', 'str', cache),
			'alert_solarradiation_high_3': utils.setting('alert_solarradiation_high_3', 'str', cache),
		},
	        'visibility.graph': {
			'type': 'visibility',
			'unit': 'distance',
			'icon': 'visibility',
			'loc': 32349,
			'alert_visibility_low_1': utils.setting('alert_visibility_low_1', 'str', cache),
			'alert_visibility_low_2': utils.setting('alert_visibility_low_2', 'str', cache),
			'alert_visibility_low_3': utils.setting('alert_visibility_low_3', 'str', cache),
		},
	        'uvindex.graph': {
			'type': 'uvindex',
			'unit': 'uvindex',
			'icon': 'uvindex',
			'loc': 32329,
			'alert_uvindex_high_1': utils.setting('alert_uvindex_high_1', 'str', cache),
			'alert_uvindex_high_2': utils.setting('alert_uvindex_high_2', 'str', cache),
			'alert_uvindex_high_3': utils.setting('alert_uvindex_high_3', 'str', cache),
		},
	        'aqieu.graph': {
			'type': 'aqieu',
			'unit': 'index',
			'icon': 'health',
			'loc': 32325,
			'alert_aqieu_high_1': utils.setting('alert_aqieu_high_1', 'str', cache),
			'alert_aqieu_high_2': utils.setting('alert_aqieu_high_2', 'str', cache),
			'alert_aqieu_high_3': utils.setting('alert_aqieu_high_3', 'str', cache),
		},
	        'aqius.graph': {
			'type': 'aqius',
			'unit': 'index',
			'icon': 'health',
			'loc': 32326,
			'alert_aqius_high_1': utils.setting('alert_aqius_high_1', 'str', cache),
			'alert_aqius_high_2': utils.setting('alert_aqius_high_2', 'str', cache),
			'alert_aqius_high_3': utils.setting('alert_aqius_high_3', 'str', cache),
		},
	        'pm25.graph': {
			'type': 'pm25',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32327,
			'alert_pm25_high_1': utils.setting('alert_pm25_high_1', 'str', cache),
			'alert_pm25_high_2': utils.setting('alert_pm25_high_2', 'str', cache),
			'alert_pm25_high_3': utils.setting('alert_pm25_high_3', 'str', cache),
		},
	        'pm10.graph': {
			'type': 'pm10',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32328,
			'alert_pm10_high_1': utils.setting('alert_pm10_high_1', 'str', cache),
			'alert_pm10_high_2': utils.setting('alert_pm10_high_2', 'str', cache),
			'alert_pm10_high_3': utils.setting('alert_pm10_high_3', 'str', cache),
		},
	        'co.graph': {
			'type': 'co',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32337,
			'alert_co_high_1': utils.setting('alert_co_high_1', 'str', cache),
			'alert_co_high_2': utils.setting('alert_co_high_2', 'str', cache),
			'alert_co_high_3': utils.setting('alert_co_high_3', 'str', cache),
		},
		'ozone.graph': {
			'type': 'ozone',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32338,
			'alert_ozone_high_1': utils.setting('alert_ozone_high_1', 'str', cache),
			'alert_ozone_high_2': utils.setting('alert_ozone_high_2', 'str', cache),
			'alert_ozone_high_3': utils.setting('alert_ozone_high_3', 'str', cache),
		},
	        'dust.graph': {
			'type': 'dust',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32339,
			'alert_dust_high_1': utils.setting('alert_dust_high_1', 'str', cache),
			'alert_dust_high_2': utils.setting('alert_dust_high_2', 'str', cache),
			'alert_dust_high_3': utils.setting('alert_dust_high_3', 'str', cache),
		},
	        'no2.graph': {
			'type': 'no2',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32330,
			'alert_no2_high_1': utils.setting('alert_no2_high_1', 'str', cache),
			'alert_no2_high_2': utils.setting('alert_no2_high_2', 'str', cache),
			'alert_no2_high_3': utils.setting('alert_no2_high_3', 'str', cache),
		},
	        'so2.graph': {
			'type': 'so2',
			'unit': 'particles',
			'icon': 'particles',
			'loc': 32331,
			'alert_so2_high_1': utils.setting('alert_so2_high_1', 'str', cache),
			'alert_so2_high_2': utils.setting('alert_so2_high_2', 'str', cache),
			'alert_so2_high_3': utils.setting('alert_so2_high_3', 'str', cache),
		},
	        'alder.graph': {
			'type': 'alder',
			'unit': 'pollen',
			'icon': 'pollen',
			'loc': 32450,
			'alert_alder_high_1': utils.setting('alert_alder_high_1', 'str', cache),
			'alert_alder_high_2': utils.setting('alert_alder_high_2', 'str', cache),
			'alert_alder_high_3': utils.setting('alert_alder_high_3', 'str', cache),
		},
	        'birch.graph': {
			'type': 'birch',
			'unit': 'pollen',
			'icon': 'pollen',
			'loc': 32451,
			'alert_birch_high_1': utils.setting('alert_birch_high_1', 'str', cache),
			'alert_birch_high_2': utils.setting('alert_birch_high_2', 'str', cache),
			'alert_birch_high_3': utils.setting('alert_birch_high_3', 'str', cache),
		},
	        'grass.graph': {
			'type': 'grass',
			'unit': 'pollen',
			'icon': 'pollen',
			'loc': 32452,
			'alert_grass_high_1': utils.setting('alert_grass_high_1', 'str', cache),
			'alert_grass_high_2': utils.setting('alert_grass_high_2', 'str', cache),
			'alert_grass_high_3': utils.setting('alert_grass_high_3', 'str', cache),
		},
	        'mugwort.graph': {
			'type': 'mugwort',
			'unit': 'pollen',
			'icon': 'pollen',
			'loc': 32453,
			'alert_mugwort_high_1': utils.setting('alert_mugwort_high_1', 'str', cache),
			'alert_mugwort_high_2': utils.setting('alert_mugwort_high_2', 'str', cache),
			'alert_mugwort_high_3': utils.setting('alert_mugwort_high_3', 'str', cache),
		},
	        'olive.graph': {
			'type': 'olive',
			'unit': 'pollen',
			'icon': 'pollen',
			'loc': 32454,
			'alert_olive_high_1': utils.setting('alert_olive_high_1', 'str', cache),
			'alert_olive_high_2': utils.setting('alert_olive_high_2', 'str', cache),
			'alert_olive_high_3': utils.setting('alert_olive_high_3', 'str', cache),
		},
	        'ragweed.graph': {
			'type': 'ragweed',
			'unit': 'pollen',
			'icon': 'pollen',
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
	addon.snow        = utils.setting('unitsnow', 'str', cache)
	addon.snowdp      = utils.setting('unitsnowdp', 'str', cache)
	addon.distance    = utils.setting('unitdistance', 'str', cache)
	addon.distancedp  = utils.setting('unitdistancedp', 'str', cache)
	addon.particlesdp = utils.setting('unitparticlesdp', 'str', cache)
	addon.pollendp    = utils.setting('unitpollendp', 'str', cache)
	addon.uvindexdp   = utils.setting('unituvindexdp', 'str', cache)
	addon.pressure    = utils.setting('unitpressure', 'str', cache)
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
	addon.fcstart     = utils.setting('fcstart', 'int', cache)
	addon.fcend       = utils.setting('fcend', 'int', cache)

	# Maxlocs
	if utils.setting('explocations', 'bool', cache):
		addon.maxlocs = 6
	else:
		addon.maxlocs = 4

	# Addon mode
	addon.api  = False
	addon.mode = { 'locations', 'location1', 'location2', 'location3', 'location4', 'location5' }
	mode = utils.winprop('openmeteo')

	if mode == 'full':
		addon.skin = True
		addon.full = True
	elif mode:
		addon.skin = True
		addon.full = False
	else:
		addon.skin = False
		addon.full = False

def kodi():
	kodi.long     = utils.region('datelong')
	kodi.date     = utils.region('dateshort')
	kodi.time     = utils.region('time')
	kodi.meri     = utils.region('meridiem')
	kodi.speed    = utils.region('speedunit')
	kodi.temp     = utils.region('tempunit')
	kodi.height   = 1080

def loc(locid, cache=False):
	loc.prop = {}
	loc.id   = locid
	loc.cid  = str(utils.settingrpc("weather.currentlocation"))
	loc.lat  = utils.setting(f'loc{locid}lat', 'float')
	loc.lon  = utils.setting(f'loc{locid}lon', 'float')
	loc.utz  = utils.setting(f'loc{locid}utz', 'bool')

	# Name
	name = utils.setting(f'loc{locid}', 'str')
	user = utils.setting(f'loc{locid}user', 'str')

	if user:
		loc.name  = user
		loc.short = user
	else:
		loc.name  = name
		loc.short = name.split(',')[0]

	# Timezone
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

