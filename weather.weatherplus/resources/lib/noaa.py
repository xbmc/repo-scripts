# coding: utf-8

#*****************************************************
# 
#     Weather Client for Weather.gov (NOAA)
#
#                           created by brightsr
#
#*****************************************************

import sys, os, urllib2, re, time
import xbmcaddon, xbmcgui
from threading import Thread
from utilities import _fetch_data, _translate_text, printlog
from utilities import _translate_text, _normalize_outlook, _localize_unit, _english_localize_unit, _getFeelsLike
from utilities import MapParser, MaplistParser, BASE_URL, BASE_MAPS
from video_us import _create_video

try:
    import xbmc
    DEBUG = False
except:
    DEBUG = True

try:
    import hashlib
except:
    import md5

WEATHER_WINDOW = xbmcgui.Window( 12600 )
Addon = xbmcaddon.Addon( id="weather.weatherplus" )
TSource = {}
windir = {    
	    "N": "From the North",
	    "NNE": "From the North Northeast",
	    "NE": "From the Northeast",
	    "ENE": "From the East Northeast",
	    "E": "From the East",
	    "ESE": "From the East Southeast",
	    "SE": "From the Southeast",
	    "SSE": "From the South Southeast",
	    "S": "From the South",
	    "SSW": "From the South Southwest",
	    "SW": "From the Southwest",
	    "WSW": "From the West Southwest",
	    "W": "From the West",
	    "WNW": "From the West Northwest",
	    "NW": "From the Northwest",
	    "NNW": "From the North Northwest",
	    "N/A": "N/A"
	}   
icondir = { "na":"na",
	    "skc":"32", 
	    "nskc":"31", 
	    "few":"34", 
	    "nfew":"33", 
	    "sct":"30", 
	    "nsct":"29", 
	    "bkn":"28", 
	    "nbkn":"27", 
	    "ovc":"26", 
	    "novc":"26", 
	    "scttsra":"37", 
	    "nscttsra":"47", 
	    "tsra":"35", 
	    "ntsra":"35", 
	    "ra":"10", 
	    "nra":"10", 
	    "sn":"14", 
	    "nsn":"14", 
	    "shra":"39", 
	    "nshra":"45", 
	    "wind":"24", 
	    "nwind":"24", 
	    "fg":"20", 
	    "nfg":"20", 
	    "sctfg":"20", 
	    "nsctfg":"20", 
	    "hi_tsra":"37", 
	    "hi_ntsra":"47", 
	    "rasn":"5", 
	    "nrasn":"5", 
	    "hi_shwrs":"39" }


class WeatherClient:
	# base url
	BASE_NOAA_FORECAST_URL = "http://forecast.weather.gov/MapClick.php?%s"
	BASE_NOAA_QUICK_URL = "http://forecast.weather.gov/afm/PointClick.php?%s"
	BASE_NOAA_HOURLY_URL = "http://forecast.weather.gov/MapClick.php?%s&&FcstType=digital"
	BASE_WEATHER_COM_URL = "http://www.weather.com/weather/%s/%s?%s"

	def __init__( self, code=None, translate=None ):
		# set users locale
		self.code = code
		# set users translate preference
		self.translate = translate

	def _fetch_36_forecast( self, video="" ):
		# fetch source
		printlog( "Trying to fetch 36 hour and extended forecast.." )
		htmlSource = _fetch_data( self.BASE_NOAA_FORECAST_URL % ( self.code ), 15 )
		htmlSource_2 = _fetch_data( self.BASE_NOAA_QUICK_URL % ( self.code ), 15 )
		xmlSource = _fetch_data( self.BASE_NOAA_FORECAST_URL % ( self.code + "&FcstType=dwml" ), 15 )
		# parse source for forecast
		parser = NOAA_Forecast36HourParser( htmlSource, htmlSource_2, xmlSource, self.translate )
		# fetch any alerts
		alerts, alertsrss, alertsnotify, alertscolor = self._fetch_alerts( parser.alerts )
		# create video url
		video_title = [Addon.getSetting("video1"), Addon.getSetting("video2"), Addon.getSetting("video3")]
		video = _create_video ( video_title )
		# return forecast
		return alerts, alertsrss, alertsnotify, alertscolor, len(parser.alerts), parser.forecast, parser.extras, video, video_title

	def _fetch_hourly_forecast( self ):
		printlog( "Trying to fetch hourly forecast.." )
		# fetch source
		htmlSource = _fetch_data( self.BASE_NOAA_HOURLY_URL % ( self.code ), 15 )
		htmlSource_2 = _fetch_data( self.BASE_NOAA_QUICK_URL % ( self.code ), 15 )
		# parse source for forecast
		parser = NOAA_ForecastHourlyParser( htmlSource, htmlSource_2, self.translate )
		# return forecast
		return parser.forecast

	def _fetch_alerts( self, raw_alerts ):
		alerts = ""
		alertsrss = ""
		alertsnotify = ""
		alertscolor = ""
		if ( raw_alerts ):
			printlog( "Fetching Alerts... Trying" )
			htmlSource = _fetch_data( "http://forecast.weather.gov/showsigwx.php?%s" % raw_alerts[0][0], 15 )
			# pattern_title = "<h3>(.+?)</h3>"
			# pattern_state = "<pre>(.+?)</pre>"
			pattern_text = "<pre>([^<]+)</pre>"
			# titles = re.findall( pattern_title, htmlSource )
			# states = re.findall( pattern_state, htmlSource )
			texts = re.findall( pattern_text, htmlSource )
			alertscolor = "2"
			for count in range( len(raw_alerts) ):	
				if ( re.search( "Warning", raw_alerts[count][1] ) ): alertscolor = "1"
				text = texts[count]
				alerts += "[B]%s[/B]\n\n" % raw_alerts[count][1]
				# alerts += "\n[I]%s[/I]\n\n" % re.sub( "<[^>]+>", "", states[count].strip() )
				alerts += "%s\n\n%s\n\n" % ( text, "-"*100 )
				alertsrss += "%s  |  " % text[:100].replace("\n", "...")
				alertsnotify += "%s,  " % raw_alerts[count][1]
			alertsrss = alertsrss.strip().rstrip( "|" ).strip()
			alertsnotify = alertsnotify.strip().rstrip( "," ).strip()
			# print alerts, alertsrss, alertsnotify, alertscolor
			printlog( "Fetching Alerts... Done!" )

		return alerts, alertsrss, alertsnotify, alertscolor

	def fetch_map_list( self, maptype=0, userfile=None, locationindex=None ):
		# set url
		url = BASE_URL + BASE_MAPS[ maptype ][ 1 ]        
		# we handle None, local and custom map categories differently
		if ( maptype == 0 ):
			# return None if none category was selected
			return None, None
		elif ( maptype == 1 ):
			position = self.code.split("&")
			htmlSource = _fetch_data( "http://www.mapquest.com/?q=%s,%s" % ( position[3].split("=")[1], position[4].split("=")[1] ) )
			pattern_zip = "\"postalCode\":\"(.+?)\""
			zip = re.findall( pattern_zip, htmlSource )
			if (zip):
				url = url % ( "map", zip[0], "", )
			else:
				printlog( "ERROR : Mapquest.com might have been changed" )
				return None, None
		printlog( "maptype = " + str(maptype) )
		printlog( "map_list_url = " + url )
		# fetch source, only refresh once a week
		htmlSource = _fetch_data( url, 60 * 24 * 7, subfolder="maps" )
		# print htmlSource
		# parse source for map list
		parser = MaplistParser( htmlSource )
		# return map list
		# print parser.map_list
		return None, parser.map_list

	def fetch_map_urls( self, map, userfile=None, locationindex=None ):
		# set url
		if ( map.endswith( ".html" ) ):
		    url = BASE_URL + map
		    # print "made url = " + url
		else:
		    position = self.code.split("&")
		    htmlSource = _fetch_data( "http://www.mapquest.com/?q=%s,%s" % ( position[3].split("=")[1], position[4].split("=")[1] ) )
		    pattern_zip = "\"postalCode\":\"(.+?)\""
		    zip = re.findall( pattern_zip, htmlSource )
		    url = self.BASE_WEATHER_COM_URL % ( "map", zip[0], "&mapdest=%s" % ( map, ), )
		# fetch source
		htmlSource = _fetch_data( url, 60*60*24*7, subfolder="maps",  )
		# parse source for static map and create animated map list if available
		parser = MapParser( htmlSource )
		# return maps
		return parser.maps

# 36 hour and 10 day (actually 7 day) forecast parser
class NOAA_Forecast36HourParser:        
    def __init__( self, htmlSource, htmlSource_2, xmlSource, translate=None ):
        self.forecast = []
        self.extras = []
        self.alerts = []
        self.alertscolor = []
        self.video_location = []
        self.translate = translate
        self.sun = []
	self.xmlSource = xmlSource.replace("\n","").replace("\t","").replace("<value xsi:nil=\"true\">", "<value>0")

        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource, htmlSource_2, xmlSource )

    def _get_forecast( self, htmlSource, htmlSource_2, xmlSource ):
	printlog("Fetching Forecast from Noaa.gov...")
        # regex patterns
        pattern_days = "<b>(.+?): </b>"
	# pattern_date = "<b>Forecast Valid:</b></a> ([^-]+)-"
	pattern_date = "<div class=\"date\">[^,]+, ([^<]+)</div>"
	# pattern_temperature = "Temp</font></a><br /><font style=\"font-size:18px\">([0-9]+)\&deg;</font>"
	pattern_high_temp = "<temperature type=\"maximum\"[^>]+>(.+?)</temperature>"
	pattern_low_temp = "<temperature type=\"minimum\"[^>]+>(.+?)</temperature>"
	pattern_value = "<value>(.+?)</value>"
        pattern_forecast_brief = "<td class=\"weekly_weather\">(.+?)</td>"
	pattern_current_windchill = "<td><b>Wind Chill</b>:</td>[^<]+<td align=\"right\">(.+?)\&deg\;F"
	pattern_current_heatindex = "<td><b>Heat Index</b>:</td>[^<]+<td align=[^>]+>(.+?)\&deg\;F"

	pattern_current_block = "<data type=\"current observations\">"
	pattern_current_icon = "<icon-link>http://forecast.weather.gov/images/wtf/([^\d\s]+).jpg"
	pattern_current_temp = "<temperature type=\"apparent\"[^>]+>(.+?)</temperature>"
	pattern_current_dew = "<temperature type=\"dew point\"[^>]+>(.+?)</temperature>"
	pattern_current_humidity = "<humidity[^>]+>(.+?)</humidity>"
	pattern_current_visibility = "<visibility units=\"statute miles\">(.+?)</visibility>"
	pattern_current_time = "Last Update:</b></a> (.+?)</span>"
	# pattern_current_wind_block = "<direction type=\"wind\"[^>]+>(.+?)</direction>"
	pattern_current_pressure = "<pressure type=\"barometer\"[^>]+>(.+?)</pressure>"
	pattern_current_brief = "<weather-conditions weather-summary=\"([^\"]+)\"/>"

	pattern_current_wind = "<td><b>Wind Speed</b>:</td>[^<]+<td align=[^>]+>(.+?)</td>"
	pattern_current_wind_2 = "<td><b>Wind Speed</b>:</td><td align=[^>]+>(.+?)<br>"
        pattern_precip_amount = "no-repeat;\">([0-9]+)\%</td><td class=\"weekly_wind\">"
        pattern_outlook = ": </b>(.+?)<br><br>"
	pattern_sunrise = "sunrise will occur around (.+?)am"
	pattern_sunset = "sunset will occur around (.+?)pm"
	pattern_wind = "<td class=\"weekly_wind\"><img class=\"wind\" src=\"image/(.+?).png\" width=\"50\" height=\"22\" alt=\"[^\"]+\" /><br />(.+?)</td>"
	pattern_xml_high_temp = "<value>(.[0-9]+)</value>"
	pattern_xml_brief = "<weather-conditions weather-summary=\"(.+?)\"/>"	
	pattern_xml_days = "<start-valid-time period-name=\"(.+?)\">"
	pattern_icon = "<icon-link>(.+?).jpg</icon-link>"

	pattern_alerts = "showsigwx.php[?]([^\"]+)\"><[^>]+>([^<]+)<"

	# fetch alerts
	self.alerts = re.findall( pattern_alerts, htmlSource )
	# print self.alerts, "*"*100

        # fetch day title
	days_10day = re.findall( pattern_xml_days, xmlSource )
        # printlog("days_10day : " + ",".join(days_10day))

 	# am or pm now?
	# cor = 0
	# if (days_10day[0] == "Late Afternoon" ): cor = 1
	ampm = 0
	if (days_10day[0] == "Tonight" or days_10day[0] == "Overnight"): ampm = 1
        # printlog("ampm : " + str(ampm))

	# current info.
	current = self.xmlSource.split( pattern_current_block )[1]
	try:
		current_icon = re.findall( pattern_current_icon, current )[0]
	except:
		current_icon = "na"
	# printlog( "Current Icon : %s" % current_icon )

	# fetch icons
	icon = []
	icons = re.findall( pattern_icon, xmlSource )
	current_icon = "/".join( [ "special://temp", "weather", "128x128", icondir.get( current_icon, "na" ) + ".png" ] )
	for count in range(0, 13-ampm):
		icon += [ icondir.get ( re.findall( "([^\d\s]+)", icons[count].split("/")[-1] )[0], "na" ) ]
	# printlog("NOAA icons : " + ",".join(icon))

        # enumerate thru and combine the day with it's forecast
        if ( len( icon ) ):
	    # fetch today's date
	    today = re.findall( pattern_date, htmlSource_2 )[0]
	    today = today.split(" ")[0] + " " + today.split(" ")[1]       
            # fetch brief description
	    current_brief = re.findall( pattern_current_brief, current )[0]
	    brief = re.findall( pattern_xml_brief, xmlSource )   
	    # fetch wind
	    wind = re.findall( pattern_wind, htmlSource_2 )
            # fetch temperature
            current_temp = re.findall( pattern_current_temp, current )[0]
	    current_temp = re.findall( pattern_value, current_temp )[0]
	    try:
	        current_feel_like = re.findall( pattern_current_windchill, htmlSource )[0]
	    except:
	        try:	    
		    current_feel_like = re.findall( pattern_current_heatindex, htmlSource )[0]
		except:
		    current_feel_like = current_temp
	    high_temp_block = re.findall( pattern_high_temp, self.xmlSource )[0]
    	    low_temp_block = re.findall( pattern_low_temp, self.xmlSource )[0]
	    high_temp = re.findall( pattern_value, high_temp_block )
	    low_temp = re.findall( pattern_value, low_temp_block )
	    # temp = re.findall( pattern_temperature, htmlSource_2 )
	    # xmltemp = re.findall( pattern_xml_high_temp, xmlSource )
	    '''
	    if (ampm == 1):
		temp += [ xmltemp[ 12 ], xmltemp[ 6 ] ]
	    else:
		temp += [ xmltemp[ 6+cor ] ]
	    '''
	    # last_temp = re.findall( pattern_xml_high_temp, xmlSource )[ [6, 12+cor][ampm] ]
	    temperature_info = ["High", "Low", "High", "Low"]
	    temperature = [ ( high_temp[0], low_temp[0], high_temp[1]), ( low_temp[0], high_temp[0], low_temp[1] ) ]
	    temp = []
	    if (ampm == 1):
		for i in range( len(high_temp) ):
			temp += [ low_temp[i], high_temp[i] ]
	    else:
		for i in range( len(low_temp) ):
			temp += [ high_temp[i], low_temp[i] ]
		temp += [ high_temp[ len(high_temp) - 1 ] ]

	    # fecth current infos
	    current_humidity = re.findall( pattern_current_humidity, current )[0]
	    current_humidity = re.findall( pattern_value, current_humidity )[0]
	    current_winddirection = ""
	    current_dew = re.findall( pattern_current_dew, current )[0]
	    current_dew = re.findall( pattern_value, current_dew )[0]
            try:
		current_wind = re.findall( pattern_current_wind, htmlSource )[0]
	    except:
		current_wind = re.findall( pattern_current_wind_2, htmlSource )[0]
	    if ( current_wind.lower() != "calm"  ):
	        if ( current_wind.split(" ")[1] != "M" ):
		    try:
			current_wind = current_wind.split(" ")[0]+" "+_localize_unit( current_wind.split(" ")[1], "speed" ).replace(" mph","").replace(" km/h","") +" Gust "+_localize_unit( current_wind.split(" ")[3], "speed" )
		    except:	
			current_wind = current_wind.split(" ")[0]+" "+_localize_unit( current_wind.split(" ")[1], "speed" )
		    
            # fetch precip
	    precip_title = []
            precip_amount = re.findall( pattern_precip_amount, htmlSource_2 )

            # fetch forecasts
            outlook = re.findall( pattern_outlook, htmlSource )

            # fetch extra info
	    pressure = re.findall( pattern_current_pressure, current )[0]
	    pressure = re.findall( pattern_value, pressure )[0]
	    visibility = re.findall( pattern_current_visibility, current )[0]
            # printlog("pressure, visibility : %s, %s" % ( pressure, visibility ))
            sunrise = re.findall( pattern_sunrise, htmlSource_2 ) 
	    sunset = re.findall( pattern_sunset, htmlSource_2 )
	    daylight = []
	    if( len(sunrise) != 6 ):
		daylight = [ ("Sunrise", "N/A"), ("Sunset", sunset[0]+" PM"), ]
	    for count in range (0, 6):
		try:
          		if( len(sunrise) == 6 ):
				daylight += [ ("Sunrise", sunrise[count]+" AM"), ("Sunset", sunset[count]+" PM") ]
			else:
				daylight += [ ("Sunrise", sunrise[count]+" AM"), ("Sunset", sunset[count+1]+" PM") ]
		except:
			daylight += [ ("Sunrise", "N/A"), ("Sunset", "N/A"), ]
	    # Current temereatures should be always in C
	    current_temp = _localize_unit( current_temp, "temp" )
	    current_feel_like = _localize_unit( current_feel_like, "temp" )
	    current_dew = _localize_unit( current_dew, "temp" )
	    self.extras += [( pressure, visibility, daylight[0][1], daylight[1][1], current_temp, current_feel_like, current_brief, current_wind, current_humidity, current_dew, current_icon, current_winddirection )]
	    days = ["Today", "Tonight", "Tomorrow", "Tomorrow Night", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]
            for count in range(0, 13):
                # make icon path
                try :
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count ] + ".png" ] )
                except :
                  printlog("Icon is not available")
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", "na.png" ] ) 
		# printlog( iconpath )
                # date calculation for 6 day
		year = time.strftime( "%Y", time.localtime() )
		date = time.strptime( today, "%B %d" )
		yeardate = time.strftime( "%j", date )
		yeardate = str( int(yeardate) + int( (count+1)/2 ) )
		date = time.strptime( "%s %s" % ( yeardate, year ), "%j %Y" )
		date = time.strftime( "%b %d", date )
		print date
                if ( count < 3 ): # just for logging
		  printlog(days[count+ampm])       # days is for 36 hour forecast ( today, tonight, tomorrow, tomorrow night ) 
		                                   # ampm = 0 : starting with "today", ampm = 1 : starting with "tonight"
		else:
		  printlog(days_10day[count]) 
                try :
                  printlog(brief[ count ])
                except :
                  printlog("brief["+str(count)+"] is not available")
                  brief += [ ("N/A", ) ]
                try :
                  printlog(temperature_info[ count+ampm ])
                except :
                  printlog("temperature_info["+str(count+ampm)+"] is not available")
                  temperature_info += [ ("High", ) ]
                try :
                  printlog(_localize_unit( temperature[ ampm ][ count ] ))
		  t = _localize_unit( temperature[ ampm ][ count ] )
                except :
                  printlog("temperature["+str(count+ampm)+"] is not available")
		  t = temp[ count ]
                try :
                  printlog(precip_title[ count ])
                except :
                  printlog("precip_title["+str(count)+"] is not available")
                  precip_title += [ "Rain/Snow" ]
		try:
                  printlog(precip_amount[ count ].replace( "%", "" ))
                except :
                  printlog("precip_amount["+str(count)+"] is not available")
                  precip_amount += [ "N/A" ]
                try :
                  printlog(brief[ count ])
                except :
                  printlog("brief["+str(count)+"] is not available")
                  brief += [ ("N/A", "N/A", "N/A", "N/A", ) ]
                try :
                  printlog(daylight[ count+ampm ][ 0 ])
                except :
                  printlog("daylight["+str(count+ampm)+"][0] is not available")
                  daylight += [ ("N/A", "00:00") ]
                try :
                  printlog(_localize_unit( daylight[ count+ampm ][ 1 ], "time" ))
                except :
                  printlog("daylight["+str(count+ampm)+"][1] is not available")
                  daylight += [ ("N/A", "00:00") ]
		try :
		  printlog(days_10day[count].replace("This Afternoon", "Today"))
		except :
		  printlog("days_10day["+str(count)+"] is not available")
		  days_10day += [ ("N/A", ) ]
		try:
		  printlog(date)
		except :
		  printlog("date is not available")
		  date = "N/A"
		try:
		  printlog("wind : " + ",".join(wind[count]))
		except :
		  printlog("wind["+str(count)+"] is not available")
		  wind += [ ("N/A", "0") ]
		try: # localize wind speed
		  wind_temp = wind[count][1].split(" ") # NOAA usually gives wind info in the form "XX G XX", XX = speed, G = Gust
		  windspeed = " ".join( [ _localize_unit( wind_temp[0], "speed" ), wind_temp[1], _localize_unit( wind_temp[2], "speed" ) ] )
		except: # if no gust
		  windspeed = _localize_unit( wind[count][1].split(" ")[0], "speed" )

		self.forecast += [ ( days[count+ampm],						# [0] 36hour.%d.Heading
		                     iconpath,							# [1] 36hour.%d.OutlookIcon or Daily.%d.OutlookIcon
				     brief[ count ],						# [2] 36hour.%d.Outlook or Daily.%d.Outlook
				     temperature_info[ count+ampm ], 
				     t, 
				     precip_title[ count ], 
				     precip_amount[ count ].replace( "%", "" ), 
				     outlook[ count ], 
				     daylight[ count+ampm ][ 0 ], 
				     _localize_unit( daylight[ count+ampm ][ 1 ], "time"  ), 
				     days_10day[count].replace("This Afternoon", "Today"), 
				     date, 
				     windir.get(wind[count][0]),				# [12] Daily.%d.WindDirection
				     windspeed,							# [13] Daily.%d.WindSpeed
				     wind[count][0] ) ]						# [14] Daily.%d.ShortWindDirection
				 
class NOAA_ForecastHourlyParser:
    def __init__( self, htmlSource, htmlSource_2, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource, htmlSource_2 )

    def _get_forecast( self, htmlSource, htmlSource_2 ):
        # regex patterns
	pattern_date = "<td width=\"3%\" class=\"date\"><font size=\"1\"(.+?)</font></td>"
	pattern_hour = "<td class=\"date\"><font size=\"1\">(.+?)</font></td>"
	pattern_temp = "<td align=\"center\" width=\"3%\"><font color=\"#FF0000\" size=\"1\"><b>(.+?)</b></font>"
	pattern_humid = "<td align=\"center\" width=\"3%\"><font color=\"#006600\" size=\"1\"><b>(.+?)</b></font></td>"
	pattern_precip = "<font color=\"#996633\" size=\"1\"><b>(.+?)</b></font>"
	pattern_wind = "<font color=\"#990099\" size=\"1\"><b>(.+?)</b></font>"
	pattern_winddir = "<font color=\"#666666\" size=\"1\"><b>(.+?)</b></font>"
	pattern_cover = "<font color=\"#0000CC\" size=\"1\"><b>([^<]+)</b></font>"
	pattern_thunder = "<font color=\"#FF0000\" size=\"1\"><b>(.+?)</b></font>"
	pattern_rain = "<font color=\"#009900\" size=\"1\"><b>(.+?)</b></font>"
	pattern_snow = "<font color=\"#0099CC\" size=\"1\"><b>(.+?)</b></font>"
	pattern_freezing_rain = "<font color=\"#CC99CC\" size=\"1\"><b>(.+?)</b></font>"
	pattern_sleet = "<font color=\"#F06600\" size=\"1\"><b>(.+?)</b></font>"

	# fetch info
	date_raw = re.findall( pattern_date, htmlSource )
	dates = []
	for count, date in enumerate( date_raw ):
		if ( date == ">" ):
			date = dates[ count - 1 ]
		dates += [ date.replace("<b>","").replace("</b>","").replace(">", "") ]
	
	hours = re.findall( pattern_hour, htmlSource )
	temperature = re.findall( pattern_temp, htmlSource )
	humidity = re.findall( pattern_humid, htmlSource )
	precip = re.findall( pattern_precip, htmlSource )
	wind = re.findall( pattern_wind, htmlSource )
	wind_direction = re.findall( pattern_winddir, htmlSource )
	cover = re.findall( pattern_cover, htmlSource )

	htmlSource_3 = htmlSource.split("Thunder</font>")[1]

	thunder = re.findall( pattern_thunder, htmlSource_3 )
	rain = re.findall( pattern_rain, htmlSource_3 )
	snow = re.findall( pattern_snow, htmlSource_3 )
	freezing_rain = re.findall( pattern_freezing_rain, htmlSource_3 )
	sleet = re.findall( pattern_sleet, htmlSource_3 )

	icondir = { 
		"chanceflurries": "13",
		"chancerain": "11",
		"chancesleet": "5",
		"chancesnow": "13",
		"chancetstorms": "38",	
		"clear": "32",
		"cloudy": "26",
		"flurries": "13",
		"fog": "22",
		"hazy": "19",
		"mostlycloudy": "28",
		"mostlysunny": "30",	
		"partlycloudy": "30",
		"partlysunny": "30",	
		"sleet": "5",	
		"rain": "10",
		"snow": "16",
		"sunny": "32",
		"tstorms": "35",
		"freeze": "25",
		"windy": "23",
		"nt_chanceflurries": "13",
		"nt_chancerain": "11",
		"nt_chancesleet": "5",
		"nt_chancesnow": "13",
		"nt_chancetstorms": "38",	
		"nt_clear": "31",
		"nt_cloudy": "26",
		"nt_flurries": "13",
		"nt_fog": "22",
		"nt_hazy": "19",
		"nt_mostlycloudy": "27",
		"nt_mostlysunny": "29",	
		"nt_partlycloudy": "29",
		"nt_partlysunny": "29",	
		"nt_sleet": "5",	
		"nt_rain": "10",
		"nt_snow": "16",
		"nt_sunny": "32",
		"nt_tstorms": "35",
		"unknown": "na"	
	}
 
	daylight = [ ( WEATHER_WINDOW.getProperty("36Hour.%s.DaylightTitle" % i), _localize_unit( WEATHER_WINDOW.getProperty("36Hour.%s.DaylightTime" % i), "time24" ) ) for i in range(1, 4) ]
	cor = 0
	try:
		daylight_time = [ int(daylight[0][1].split(":")[0]), int(daylight[1][1].split(":")[0]) ]
	except:   # sunrise = "N/A" and first heading = "Late Afternoon"
		daylight_time = [ int(daylight[1][1].split(":")[0]), int(daylight[2][1].split(":")[0]) ]
		cor = 1
		
	# overnight = WEATHER_WINDOW.getProperty("Daily.1.ShortDay") == "Overn."
	hour_temp = int( hours[ 0 ].replace("<b>","").replace("</b>","") )
	if (hour_temp < 7 and daylight[0][0] == "Sunset") : hour_temp += 24

	for count in range( 0, 24 ):
		hour = int( hours[ count ].replace("<b>","").replace("</b>","") )
		icon = ""
		outlook = "N/A"
		if( hour >= 12 ):
			hour -= 12
			if ( hour == 0 ): hour = 12
			hour = str(hour) + ":00 PM"
		else:
			hour = str(hour) + ":00 AM"
		feelslike = _getFeelsLike( int(_localize_unit( temperature[count], "tempf2c" )), int(_localize_unit( wind[count], "speedmph2kmh" ).split(" ")[0]), int(humidity[count]) )
		print "hour = %s, daylight(1) = %s, daylight(2) = %s" % (hour_temp, daylight_time[0], daylight_time[1] + 24 * ( daylight[1+cor][0] == "Sunrise" ))
		if ( hour_temp <= daylight_time[0] ):
			if ( daylight[0+cor][0] == "Sunrise" ):
				icon = "nt_"	
		elif ( hour_temp <= daylight_time[1] + 24 * ( daylight[1+cor][0] == "Sunrise" ) ):
			if ( daylight[1+cor][0] == "Sunrise" ):
				icon = "nt_"
		else:
			if ( daylight[2+cor][0] == "Sunrise" ):
				icon = "nt_"
		if ( thunder[count] != "--" ):		
			if ( thunder[count] == "SChc" ):
				outlook = "Slight Chace of T-Storms"
				icon += "chance"
			elif ( thunder[count] == "Chc" ):
				outlook = "Chance of T-Storms"
				icon += "chance"
			else:
				outlook = "T-Storms Likely"
			icon += "tstorms"
		elif ( rain[count] != "--" ):
			if ( rain[count] == "SChc" ):
				outlook = "Slight Chace of Rain"
				icon += "chance"
			elif ( rain[count] == "Chc" ):
				outlook = "Chance of Rain"
				icon += "chance"
			else:
				outlook = "Rain Likely"
			icon += "rain"
		elif ( snow[count] != "--" ):
			if ( rain[count] == "SChc" ):
				outlook = "Slight Chace of Snow"
				icon += "chance"
			elif ( rain[count] == "Chc" ):
				outlook = "Chance of Snow"
				icon += "chance"
			else:
				outlook = "Snow Likely"
			icon += "snow"
		elif ( freezing_rain[count] != "--" ):
			if ( rain[count] == "SChc" ):
				outlook = "Slight Chace of Freezing Rain"
				icon += "chance"
			elif ( rain[count] == "Chc" ):
				outlook = "Chance of Freezing Rain"
				icon += "chance"
			else:
				outlook = "Freezing Rain Likely"
			icon += "freeze"
		elif ( sleet[count] != "--" ):
			if ( rain[count] == "SChc" ):
				outlook = "Slight Chace of Sleet"
				icon += "chance"
			elif ( rain[count] == "Chc" ):
				outlook = "Chance of Sleet"
				icon += "chance"
			else:
				outlook = "Sleet Likely"			
			icon += "sleet"		
		elif ( int(wind[count]) > 20 ):
			icon = "windy"
			outlook = "Windy"
		elif ( int(cover[count]) == 0 ): 
			icon += "clear"
			outlook = "Clear"
		elif ( int(cover[count]) < 10 ):
			icon += "clear"
			outlook = "Fair"
		elif ( int(cover[count]) < 40 ):
			icon += "mostlysunny"
			outlook = ( "Mostly Sunny", "Mostly Clear" )[ icon.startswith("nt") ]
		elif ( int(cover[count]) < 70 ):
			icon += "partlycloudy"
			outlook = "Partly Cloudy"
		elif ( int(cover[count]) < 90 ):
			icon += "mostlycloudy"
			outlook = "Mostly Cloudy"
		else:
			icon += "cloudy"
			outlook = "Cloudy"
		hour_temp += 1
		self.forecast += [ ( _localize_unit( hour, "time" ), dates[ count ], "special://temp/weather/128x128/%s.png" % icondir.get(icon, "na"), _localize_unit(temperature[ count ]), outlook, _english_localize_unit( feelslike ), precip[ count ], humidity[ count ], windir.get( wind_direction[ count ] ), _localize_unit( wind[ count ]+" mph", "speed" ), "" ) ]		
