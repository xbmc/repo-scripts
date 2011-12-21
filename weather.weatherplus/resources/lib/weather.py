# coding: utf-8

#*********************************************************
# 
#     Weather Client for Weather.com
#
#                           created by brightsr
#                           - based on Nuka1195's script
#
#*********************************************************

import sys, os, urllib2, re, time
import xbmcaddon, xbmcgui
from threading import Thread
from utilities import _fetch_data, _translate_text, printlog
from utilities import _translate_text, _normalize_outlook, _localize_unit, _english_localize_unit, _getFeelsLike
from utilities import MapParser, MaplistParser, BASE_URL, BASE_MAPS

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
windir = {}

class WeatherClient:
	# base url
	BASE_FORECAST_URL = "http://www.weather.com/weather/%s/%s?%s"

	def __init__( self, code=None, translate=None ):
		# set users locale
		self.code = code
		# set users translate preference
		self.translate = translate

    	def fetch_36_forecast( self, video ):
		printlog( "Trying to fetch 36 hour forecast.. " )
		# fetch source
		htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( "local", self.code, "", ), 15 )
		htmlSource_5 = _fetch_data( BASE_URL + "/weather/5-day/"+ self.code, 15 )
		_localtime_source_ = _fetch_data( BASE_URL + "/outlook/events/weddings/wxdetail/" + self.code, )
	
		# setting local time
		try:
		     _localtime_ = int(re.findall ("([0-9]+):([0-9]+) AM", _localtime_source_)[0][0])
		except:
		     _localtime_ = None

		# parse source for forecast
		parser = Forecast36HourParser( htmlSource, htmlSource_5, _localtime_, self.translate )
		while ( parser.error > 0 and parser.error < 5 ):
			printlog( "Error!" )
			printlog( "Retrying..." )
			# fetch source
			htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( "local", self.code, "", ), 15 )
			htmlSource_5 = _fetch_data( BASE_URL + "/weather/5-day/"+ self.code, 15 )
			parser._get_forecast( htmlSource, htmlSource_5, _localtime_ )

		# fetch any alerts
		alerts, alertsrss, alertsnotify = self._fetch_alerts( parser.alerts )
		# create video url
		if ( self.code.startswith( "US" ) or len(self.code) == 5 ):                     # U.S video
			from video_us import _create_video
			video_title = [Addon.getSetting("video1"), Addon.getSetting("video2"), Addon.getSetting("video3")]
			video = _create_video ( video_title )
		else:										# Non-U.S video
			from video_non_us import _create_video
			video, video_title = _create_video( self.code[:2], "" )
		if ( parser.alertscolor is not None ) :
		     try : 
			 return alerts, alertsrss, alertsnotify, parser.alertscolor[0], len(parser.alerts), parser.forecast, parser.extras, video, video_title
		     except : 
			 return alerts, alertsrss, alertsnotify, "", len(parser.alerts), parser.forecast, parser.extras, video, video_title

    	def fetch_10day_forecast( self ):
		printlog( "Trying to fetch 10 day forecast.." )
		# fetch source
		htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( "tenday", self.code, "", ), 15 )
		# parse source for forecast
		parser = Forecast10DayParser( htmlSource, self.translate )
		# return forecast
		return parser.forecast

    	def fetch_hourly_forecast( self ):
		printlog( "Trying to fetch hourly forecast.." )
		# fetch source
		htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( "hourbyhour", self.code, "", ), 15 )
		# parse source for forecast
		parser = ForecastHourlyParser( htmlSource, self.translate )
		# return forecast
		return parser.forecast

   	def fetch_weekend_forecast( self ):
		printlog( "Trying to fetch weekend forecast.." )
		# fetch source
		htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( "weekend", self.code, "", ), 15 )
		# parse source for forecast
		parser = ForecastWeekendParser( htmlSource, self.translate )
		# return forecast
		return parser.forecast

	def _fetch_alerts( self, urls ):
		# print urls
		alerts = ""
		# alertscolor = ""
		alertsrss = ""
		alertsnotify = ""
		
		if ( urls ):
		    # alertscolor = urls[ 0 ][ 0 ]
		    titles = []
		    # enumerate thru the alert urls and add the alerts to one big string
		    # count = 0
		    for url in urls:
			#if (count == 0):
			#	count = 1
			#	continue	
			print url
		        # fetch source refresh every 15 minutes
		        htmlSource = _fetch_data( self.BASE_URL + "/weather/alerts/"+ url, 15 )
		        # parse source for alerts
		        parser = WeatherAlert( htmlSource )
		        # needed in case a new alert format was used and we errored
		        if ( parser.alert is not None ):
		            # add result to our alert string
		            alerts += parser.alert
		            titles += [ parser.title ]
		            alertsrss += "%s  |  " % ( parser.alert_rss, )
		            alertsnotify += "%s  |  " % ( parser.title.replace( "[B]", "" ).replace( "[/B]", "" ), )
		    # TODO: maybe handle this above passing count to the parser
		    # make our title string if more than one alert
		    if ( len( titles ) > 1 ):
		        title_string = ""
		        for count, title in enumerate( titles ):
		            title_string += "%d. %s\n" % ( count + 1, title, )
		        # add titles to alerts
		        alerts = "%s\n%s\n%s\n\n%s" % (  "-" * 100, title_string.strip(), "-" * 100, alerts )
		# return alert string stripping the last newline chars
		# return alerts.strip(), alertsrss.strip().rstrip( "|" ).strip(), alertsnotify.rstrip( " |" ), alertscolor
		return alerts.strip(), alertsrss.strip().rstrip( "|" ).strip(), alertsnotify.rstrip( " |" )

	def fetch_map_list( self, maptype=0, userfile=None, locationindex=None ):
		# set url
		url = BASE_URL + BASE_MAPS[ maptype ][ 1 ]        
		# we handle None, local and custom map categories differently
		if ( maptype == 0 ):
		    # return None if none category was selected
		    return None, None
		elif ( maptype == 1 ):
		    # add locale to local map list if local category
		    url = url % ( "map", self.code, "", )
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
			url = self.BASE_FORECAST_URL % ( "map", self.code, "&mapdest=%s" % ( map, ), )
		# fetch source
		htmlSource = _fetch_data( url, 60*60*24*7, subfolder="maps",  )
		# parse source for static map and create animated map list if available
		parser = MapParser( htmlSource )
		# return maps
		return parser.maps


class Forecast36HourParser:
    def __init__( self, htmlSource, htmlSource_5, localtime, translate=None ):
        self.forecast = []
        self.extras = []
        self.alerts = []
        self.alertscolor = []
        self.video_location = []
	self.video_local_location = []
	self.video_local_number = 0
        self.translate = translate
	self.error = 0
        self.sun = []

        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource, htmlSource_5, localtime )

    def _get_forecast( self, htmlSource, htmlSource_5, localtime ):
        # regex patterns
        pattern_locstate = "wx.config.loc.state=\"([^\"]+)\""
        pattern_video_location = "US_Current_Weather:([^\"]+)\""
        pattern_video_local_location = "/outlook/videos/(.+?)-60-second-forecast-(.+?)\""
        pattern_alert_color = "<div id=\"wx-alert-bar\" class=\"wx-alert-([0-9]+)"
        pattern_alerts = "href=\"/weather/alerts/([^\"]+)\" from=\"local_alert_list_overview\">"
        pattern_days = "<td class=\"twc-col-[0-9]+ twc-forecast-when\">(.+?)</td>"
        pattern_icon = "<img src=\"http://s\.imwx\.com/v\.20100719\.135915/img/wxicon/[0-9]+/([0-9]+)\.png\" width=\"72\""
        pattern_forecast_brief = "<td class=\"twc-col-[0-9]+ \">(.+?)</td>"
        pattern_temp_info = "<td class=\"twc-col-[0-9]+ twc-forecast-temperature-info\">(.+?)</td>"
        pattern_temp = "<td class=\"twc-col-[0-9]+ twc-forecast-temperature\"><strong>(.+?)\&deg;</strong>"
        pattern_precip_title = "Chance of ([^\:]+):"
        pattern_precip_amount = "<br><strong>(.+?)</strong>"
        pattern_outlook = "<td class=\"twc-col-[0-9]+ twc-line-nar \">(.+?)</td>"
        pattern_daylight = "<td class=\"twc-col-[0-9]+ twc-line-daylight\">(.+?)<strong>\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n\s(.+?)\n"
        pattern_pressure = "Pressure:</span>(.+?)<img src=\"http://s.imwx.com/v.20100719.135915/img/common/icon-(.+?).gif\""	                     
        pattern_visibility = "Visibility:</span>(.+?)</td>"	        
        pattern_sunrise_now = "Sunrise:</span> <br><strong>\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n\s(.+?)\n"
        pattern_sunset_now = "Sunset:</span> <br><strong>\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n.*\n\s(.+?)\n"
	pattern_current_icon = "<img src=\"http://s\.imwx\.com/v\.20100719\.135915/img/wxicon/[0-9]+/([0-9]+)\.png\" alt=\"([^\"]+)\" width=\"130\""
	pattern_current_temp = "<td class=\"twc-col-[0-9]+ twc-forecast-temperature\"><strong>(.+?)\&deg;F</strong>"
	pattern_feels_like = "<td class=\"twc-col-1 twc-forecast-temperature-info\">Feels Like: <strong>([0-9]+)\&deg;</strong>"
	pattern_current_wind = "Wind:<br><strong>([^<]+)"
	pattern_current_humidity = "Humidity:</span> ([0-9]+)%"
	pattern_current_dewpoint = "Dew Point:</span>([0-9]+)"
	pattern_UVIndex = "UV Index:</span>([^<]+)"

	# fetch days
        days = re.findall( pattern_days, htmlSource )
       
        # enumerate thru and combine the day with it's forecast
        if ( len( days ) ):
	    # fetch current info
	    current_icon_brief = re.findall( pattern_current_icon, htmlSource )
	    try:
		current_icon = "/".join( [ "special://temp", "weather", "128x128", current_icon_brief[ 0 ][ 0 ] + ".png" ] )
		current_brief = current_icon_brief [ 0 ][ 1 ]
	    except:
	        current_icon = "/".join( [ "special://temp", "weather", "128x128", "na" + ".png" ] )
		current_brief = "N/A"
	    current_temp = re.findall( pattern_current_temp, htmlSource )
	    current_feels_like = re.findall( pattern_feels_like, htmlSource )
	    try:
	        current_temp =  _localize_unit( current_temp[ 0 ] )
		current_feels_like = _localize_unit( current_feels_like [ 0 ] )
	    except:
		current_temp = "N/A"
		current_feels_like = "N/A"
	    current_wind = re.findall( pattern_current_wind, htmlSource )
	    try:
		current_wind = current_wind[ 0 ].replace("\t","").replace("\n","").strip()
		current_wind_buffer = re.findall( "From (.+?) at ([0-9]+)", current_wind )
		try: 
		   if ( self.translate) :
			'''
			speed = _localize_unit( current_wind_buffer[ 0 ][ 1 ], "speed" )
			unit = speed.split(" ")[-1]
			current_wind = _translate_text( "%s %s" % ( current_wind_buffer[ 0 ][ 0 ], speed.split(" ")[0] ), self.translate )
			current_wind += " %s" % unit
			'''
			current_wind = "%s %s" % ( current_wind_buffer[ 0 ][ 0 ], _localize_unit( current_wind_buffer[ 0 ][ 1 ], "speed" ) )
		   else:		
			current_wind = "From %s at %s" % ( current_wind_buffer[ 0 ][ 0 ], _localize_unit( current_wind_buffer[ 0 ][ 1 ], "speed" ) )
		except:
		   pass
	    except:
		current_wind = "N/A"
	    current_humidity = re.findall( pattern_current_humidity, htmlSource )
	    current_dewpoint = re.findall( pattern_current_dewpoint, htmlSource )
	    try:
	        current_humidity = current_humidity[ 0 ] + "%"
		current_dewpoint = _localize_unit( current_dewpoint[ 0 ], "tempf2c" )
	    except:
	        current_humidity = "N/A"
		current_dewpoint = "N/A"
	    current_UVIndex = re.findall( pattern_UVIndex, htmlSource )
	    try:
		current_UVIndex = current_UVIndex[ 0 ].replace("\t","").replace("\n","").strip()
	    except:
	        current_UVIndex = "N/A"
	    
            # fetch alerts
            self.alertscolor = re.findall(pattern_alert_color, htmlSource)
            self.alerts = re.findall( pattern_alerts, htmlSource )

	    # fetch icon
            icon = re.findall( pattern_icon, htmlSource )
            # fetch brief description
            brief = re.findall( pattern_forecast_brief, htmlSource )
	    # fetch outlook
	    outlook = re.findall( pattern_outlook, htmlSource )
            # fetch temperature
            temperature = re.findall( pattern_temp, htmlSource )
            temperature_info = re.findall( pattern_temp_info, htmlSource)
	    # fetch precip title
            precip_title = re.findall( pattern_precip_title, htmlSource )
            # fetch precip title
            precip_amount = re.findall( pattern_precip_amount, htmlSource )
            # fetch daylight
            daylight = re.findall( pattern_daylight, htmlSource )
            sunrise_ = re.findall( pattern_sunrise_now, htmlSource_5)
            sunset_ =  re.findall( pattern_sunset_now, htmlSource_5)
            try : 
               time_diff = int(sunrise_[ 0 ].split( " " )[ 3 ][:2])-localtime
            except :
               time_diff = 0
            printlog( "Timezone : " + str(localtime) + " " + str(time_diff) )
            
            # fetch current extra info
            pressure_ = re.findall( pattern_pressure, htmlSource, re.DOTALL )
            visibility_ = re.findall( pattern_visibility, htmlSource, re.DOTALL )
            pressure = "N/A"
            visibility = "N/A"
            sunrise = "N/A"
            sunset = "N/A"
            
            if ( pressure_ ) :
                    pressure = "".join(pressure_[0][0].split("\n"))
                    pressure = "".join(pressure.split("\t"))
                    pressure = pressure.replace("in", "")
		    try:
			pressure = _localize_unit(pressure, "pressure")
		    except:
			pass
                    try:
			pressure = pressure + { "pressure-up": u"\u2191", "pressure-down": u"\u2193", "pressure-steady": u"\u2192" }[ pressure_[0][1] ]
		    except:
			pass
            if ( visibility_ ) :
                   visibility = "".join(visibility_[0].split("\n"))
                   visibility = "".join(visibility.split("\t"))
                   visibility = visibility.replace("mi", "")
            if ( sunrise_ ) :
                   sunrise = "".join(sunrise_[0].split("\n"))
                   sunrise = "".join(sunrise.split("\t"))
                   try : 
                      sunrise = _localize_unit( str(int(sunrise.split(" ")[3].split(":")[0])-time_diff) + ":" + sunrise.split(" ")[3].split(":")[1], "time" )
                   except :
                      sunrise = "N/A"
            if ( sunset_ ) :
                   sunset = "".join(sunset_[0].split("\n"))
                   sunset = "".join(sunset.split("\t"))
                   try : 
                      sunset = _localize_unit( str(int(sunset.split(" ")[3].split(":")[0])-time_diff) + ":" + sunset.split(" ")[3].split(":")[1], "time" )
                   except :
                      sunset = "N/A"    

            # convert outlook wind/temp values
            outlook = _normalize_outlook( outlook )
            # translate brief and outlook if user preference
            if ( self.translate is not None ):
		text = current_brief
		text += "|||||"
                text += "|".join( brief )
                text += "|||||"
                text += "|".join( outlook )
                # translate text
                text = _translate_text( text, self.translate )
                # split text into it's original list
		print text
 		current_brief = text.split("|||||")[0]
		brief = text.split("|||||")[1].split( "|" )
                outlook = text.split( "|||||" )[2].split( "|" )

	    self.extras += [(pressure, _localize_unit(visibility, "distance"), sunrise, sunset, current_temp, current_feels_like, current_icon, current_brief, current_humidity, current_dewpoint, current_wind, current_UVIndex )]

	    printlog( "Checking parsed data..." )
            for count, day in enumerate( days ):
                # make icon path
                try :
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count ] + ".png" ] )
                except :
                  printlog( "Icon is not available" )
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", "0.png" ] ) 
                printlog( iconpath )
                # add result to our class variable
                try :
                  printlog( days[count] )
                except :
                  printlog( "days["+str(count)+"] is not available" )
                  days += [ ("N/A", ) ]              
		printlog( "brief = %s" % ",".join(brief) )
                try :
                  printlog( brief[ count ] )
                except :
                  printlog( "brief[" +str(count)+ "] is not available" )
                  brief += [ ("N/A", ) ]
                try :
                  printlog( temperature_info[ count ] )
                except :
                  printlog( "temperature_info["+str(count)+"] is not available" )
                  temperature_info += [ ("N/A", ) ]
                try :
                  printlog( _localize_unit( temperature[ count ] ) )
                except :
                  printlog( "temperature["+str(count)+"] is not available" )
                  temperature += [ ("N/A", ) ]
                try :
                  printlog( precip_title[ count ] )
                except :
                  printlog( "precip_title["+str(count)+"] is not available" )
                  precip_title += [ ("N/A", ) ]
                try :
                  printlog( precip_amount[ count ].replace( "%", "" ) )
                except :
                  printlog( "precip_amount["+str(count)+"] is not available" )
                  precip_amount += [ ("N/A", ) ]
                try :
                  printlog( outlook[ count ] )
                except :
                  printlog( "outlook["+str(count)+"] is not available" )
                  outlook += [ ("N/A", ) ]
                try :
                  printlog( daylight[ count ][ 0 ] )
                except :
                  printlog( "daylight["+str(count)+"][0] is not available" )
                  daylight += [ ("N/A", ) ]
                try :
                  printlog( _localize_unit( str(int(daylight[count][1].split(" ")[3].split(":")[0])-time_diff) + ":" + daylight[count][1].split(" ")[3].split(":")[1], "time"  ) )
                  self.forecast += [ ( days[count], iconpath, brief[ count ], temperature_info[ count ], _localize_unit( temperature[ count ] ), precip_title[ count ], precip_amount[ count ].replace( "%", "" ), outlook[ count ], daylight[ count ][ 0 ], _localize_unit( str(int(daylight[count][1].split(" ")[3].split(":")[0])-time_diff) + ":" + daylight[count][1].split(" ")[3].split(":")[1], "time"  ), ) ]
                except :
                  printlog( "daylight["+str(count)+"][1] is not available" )
                  self.forecast += [ ( days[count], iconpath, brief[ count ], temperature_info[ count ], _localize_unit( temperature[ count ] ), precip_title[ count ], precip_amount[ count ].replace( "%", "" ), outlook[ count ], daylight[ count ][ 0 ], "N/A", ) ]
            
        else:
	    self.error += 1

class ForecastHourlyParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
        # regex patterns
        # pattern_headings = "<div class=\"hbhTD[^\"]+\"><div title=\"[^>]+>([^<]+)</div></div>"
        pattern_date = "<div class=\"hbhDateHeader\">([^<]+)</div>"
        pattern_sunrise = "<img src=\"http://i.imwx.com/web/local/hourbyhour/icon_sunrise.gif\"[^>]+>([^<]+)"
        pattern_sunset = "<img src=\"http://i.imwx.com/web/local/hourbyhour/icon_sunset.gif\"[^>]+>([^<]+)"
        # use this to grab the 15 minutes details
        # pattern_info = "<div class=\"hbhTDTime[^>]+><div>([^<]+)</div></div>\
        # use this to grab only 1 hour details
        pattern_info = "<div class=\"hbhTDTime\"><div>([^<]+)</div></div>\
[^<]+<div class=\"hbhTDConditionIcon\"><div><img src=\"http://i.imwx.com/web/common/wxicons/[0-9]+/(gray/)?([0-9]+).gif\"[^>]+></div></div>\
[^<]+<div class=\"hbhTDCondition\"><div><b>([^<]+)</b><br>([^<]+)</div></div>\
[^<]+<div class=\"hbhTDFeels\"><div>([^<]*)</div></div>\
[^<]+<div class=\"hbhTDPrecip\"><div>([^<]*)</div></div>\
[^<]+<div class=\"hbhTDHumidity\"><div>([^<]*)</div></div>\
[^<]+<div class=\"hbhTDWind\"><div>([^<]*)(<br>)?([^<]*)</div></div>"
        
        # fetch info
        info = re.findall( pattern_info, htmlSource )
        # fetch dates
        dates = re.findall( pattern_date, htmlSource )
        # hack for times when weather.com, does not display date
        dates += [ ", " ]
        # fetch sunrise
        sunrises = re.findall( pattern_sunrise, htmlSource )
        # fetch sunset
        sunsets = re.findall( pattern_sunset, htmlSource )
        # enumerate thru and create heading and forecast
        if ( len( info ) ):
            # we convert wind direction to full text
            windir = {    
                            "From N": "From the North",
                            "From NNE": "From the North Northeast",
                            "From NE": "From the Northeast",
                            "From ENE": "From the East Northeast",
                            "From E": "From the East",
                            "From ESE": "From the East Southeast",
                            "From SE": "From the Southeast",
                            "From SSE": "From the South Southeast",
                            "From S": "From the South",
                            "From SSW": "From the South Southwest",
                            "From SW": "From the Southwest",
                            "From WSW": "From the West Southwest",
                            "From W": "From the West",
                            "From WNW": "From the West Northwest",
                            "From NW": "From the Northwest",
                            "From NNW": "From the North Northwest"
                        }
            brief = []
            wind = []
            for item in info:
                wind += [ windir.get( item[ 8 ], item[ 8 ] ) ]
                brief += [ item[ 4 ] ]
            # translate brief and outlook if user preference
            if ( self.translate is not None ):
                # we only need outlook and brief. the rest the skins or xbmc language file can handle
                # we separate each item with single pipe
                text = "|".join( wind )
                # separator for different info
                text += "|||||"
                # we separate each item with single pipe
                text += "|".join( brief )
                # translate text
                text = _translate_text( text, self.translate )
                # split text into it's original list
                wind = text.split( "|||||" )[ 0 ].split( "|" )
                brief = text.split( "|||||" )[ 1 ].split( "|" )
            # counter for date
            date_counter = 0
            # create our forecast list
            for count, item in enumerate( info ):
                # make icon path
                iconpath = "/".join( [ "special://temp", "weather", "128x128", item[ 2 ] + ".png" ] )
                # do we need to increment date_counter
                if ( item[ 0 ] == "12 am" and count > 0 ):
                    date_counter += 1
                # does sunrise/sunset fit in this period
                sunrise = ""
                sunset = ""
                # we want 24 hour as the math is easier
                period = _localize_unit( item[ 0 ], "time24" )
                # set to a high number, we use this for checking next time period
                period2 = "99:00"
                if ( count < len( info ) - 2 ):
                    period2 = _localize_unit( info[ count + 1 ][ 0 ], "time24" )
                    period2 = ( period2, "24:%s" % ( period2.split( ":" )[ 1 ], ), )[ period2.split( ":" )[ 0 ] == "0" ]
                # sunrise
                if ( sunrises ):
                    # get the 24 hour sunrise time
                    sunrise_check = _localize_unit( sunrises[ 0 ].strip().split( "Sunrise" )[ 1 ].strip(), "time24" )
                    # if in the correct time range, set our variable
                    if ( int( sunrise_check.split( ":" )[ 0 ] ) == int( period.split( ":" )[ 0 ] ) and int( sunrise_check.split( ":" )[ 1 ] ) >= int( period.split( ":" )[ 1 ] ) and 
                        ( int( sunrise_check.split( ":" )[ 1 ] ) < int( period2.split( ":" )[ 1 ] ) or int( sunrise_check.split( ":" )[ 0 ] ) < int( period2.split( ":" )[ 0 ] ) ) ):
                        sunrise = _localize_unit( sunrises[ 0 ].strip().split( "Sunrise" )[ 1 ].strip(), "time" )
                # sunset
                if ( sunsets ):
                    # get the 24 hour sunset time
                    sunset_check = _localize_unit( sunsets[ 0 ].strip().split( "Sunset" )[ 1 ].strip(), "time24" )
                    # if in the correct time range, set our variable
                    if ( int( sunset_check.split( ":" )[ 0 ] ) == int( period.split( ":" )[ 0 ] ) and int( sunset_check.split( ":" )[ 1 ] ) >= int( period.split( ":" )[ 1 ] ) and 
                        ( int( sunset_check.split( ":" )[ 1 ] ) < int( period2.split( ":" )[ 1 ] ) or int( sunset_check.split( ":" )[ 0 ] ) < int( period2.split( ":" )[ 0 ] ) ) ):
                        sunset = _localize_unit( sunsets[ 0 ].strip().split( "Sunset" )[ 1 ].strip(), "time" )
                # add result to our class variable
                self.forecast += [ ( _localize_unit( item[ 0 ], "time" ), dates[ date_counter ].split( ", " )[ -1 ], iconpath, _localize_unit( item[ 3 ] ), brief[ count ], _localize_unit( item[ 5 ] ), item[ 6 ].replace( "%", "" ), item[ 7 ].replace( "%", "" ), wind[ count ], _localize_unit( item[ 10 ], "speed" ), item[ 8 ].split( " " )[ -1 ], sunrise, sunset, ) ]

class ForecastWeekendParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
        # regex patterns
        pattern_heading = "from=[\"]*weekend[\"]+>([^<]+)</A>.*\s.*\s\
[^<]+<TD width=\"[^\"]+\" class=\"wkndButton[A-Z]+\" align=\"[^\"]+\" valign=\"[^\"]+\"><FONT class=\"[^\"]+\">([^\&]+)&nbsp;.*\s.*\s.*\s.*\s.*\s.*\s.*\s.*\s.*\s.*\s\
[^>]+>[^>]+>([^<]+)<"
        pattern_observed = ">(Observed:)+"
        pattern_brief = "<IMG src=\"http://(?:i.imwx.com)?(?:image.weather.com)?/web/common/wxicons/(?:pastwx/)?[0-9]+/([0-9]+).gif.*alt=\"([^\"]+)\""
        pattern_past = "<TD align=\"left\" class=\"grayFont10\">([^<]+)</TD>"
        pattern_past2 = "<TD align=\"[left|right]+\" class=\"blueFont10\">[<B>]*<FONT color=\"[^\"]+\">([^\s|^<]+)[^\n]+"
        pattern_avg = "<tr><td align=\"right\" valign=\"top\" CLASS=\"blueFont10\">([^<]+)<.*\s.*\s[^[A-Z0-9]+(.*&deg;[F|C]+)"
        pattern_high = "<FONT class=\"[^\"]+\">([^<]+)<BR><FONT class=\"[^\"]+\"><NOBR>([^<]+)</FONT></NOBR>"
        pattern_low = "<FONT class=\"[^\"]+\">([^<]+)</FONT><BR><FONT class=\"[^\"]+\"><B>([^<]+)</B></FONT>"
        pattern_precip = "<TD valign=\"top\" width=\"50%\" class=\"blueFont10\" align=\"[left|right]+\">(.*)"
        pattern_wind = "<td align=\"[^\"]+\" valign=\"[^\"]+\" CLASS=\"[^\"]+\">([^<]+)</td><td align=\"[^\"]+\">&nbsp;</td><td valign=\"[^\"]+\" CLASS=\"[^\"]+\"><B>.*\n[^A-Z]+([A-Z]+)<br>([^<]+)</B>"
        pattern_uv = "<td align=\"[^\"]+\" valign=\"[^\"]+\" CLASS=\"[^\"]+\">([^<]+)</td>\s[^>]+>[^>]+>[^>]+><B>([^<]+)"
        pattern_humidity = "<td align=\"[^\"]+\" valign=\"[^\"]+\" CLASS=\"[^\"]+\">([^<]+)[^>]+>[^>]+>[^>]+>[^>]+><B>([0-9]+%)"
        pattern_daylight = "<td align=\"[^\"]+\" valign=\"[^\"]+\" CLASS=\"[^\"]+\">([^<]+)[^>]+>[^>]+>[^>]+>[^>]+><B>([0-9]+:[0-9]+[^<]+)</B></td>"
        pattern_outlook = "<TD colspan=\"3\" class=\"blueFont10\" valign=\"middle\" align=\"left\">([^<]+)</TD>"
        pattern_departures = "<FONT COLOR=\"#7d8c9f\"><B>\s.*\s\s+(.+?F)"
        # fetch headings
        headings = re.findall( pattern_heading, htmlSource )
        # fetch observed status
        observeds = re.findall( pattern_observed, htmlSource )
        # insert necessary dummy entries
        for i in range( 3 - len( observeds ) ):
            observeds.append( "" )
        # fetch briefs
        briefs = re.findall( pattern_brief, htmlSource )
        # insert necessary dummy entries
        for count, i in enumerate( range( 3 - len( briefs ) ) ):
            briefs.insert( count, ( "na", "", ) )
        # fetch departue from normal
        departures = re.findall( pattern_departures, htmlSource )
        for i in range( 6 - len( departures ) ):
            departures.append( "" )
        # fetch past info
        pasts = re.findall( pattern_past, htmlSource )
        if ( pasts == [] ):
            pasts2 = re.findall( pattern_past2, htmlSource )
            # create the pasts list
            for count, i in enumerate( range( 0, len( pasts2 ), 2 ) ):
                pasts += [ pasts2[ count * 2 ] + pasts2[ count * 2 + 1 ] ]
        # insert necessary dummy entries
        for i in range( 9 - len( pasts ) ):
            pasts.append( ":&nbsp;" )
        # fetch average info
        avgs = re.findall( pattern_avg, htmlSource )
        # insert necessary dummy entries
        for i in range( 0, 12 - len( avgs ) ):
            avgs.append( ( "", "", ) )
        # fetch highs
        highs = re.findall( pattern_high, htmlSource )
        # insert necessary dummy entries
        for count, i in enumerate( range( 3 - len( highs ) ) ):
            highs.insert( count, ( pasts[ count * 3 ].split( ":&nbsp;" )[ 0 ], pasts[ count * 3 ].split( ":&nbsp;" )[ 1 ], ) )
        # fetch lows
        lows = re.findall( pattern_low, htmlSource )
        # insert necessary dummy entries
        for count, i in enumerate( range( 3 - len( lows ) ) ):
            lows.insert( count, ( pasts[ count * 3 + 1 ].split( ":&nbsp;" )[ 0 ], pasts[ count * 3 + 1 ].split( ":&nbsp;" )[ 1 ], ) )
        # fetch precips
        precips = re.findall( pattern_precip, htmlSource )
        # insert necessary dummy entries
        for i in range( 6 - len( precips ) ):
            precips.insert( 0, "" )
        # fetch winds
        tmp_winds = re.findall( pattern_wind, htmlSource )
        # insert necessary dummy entries
        for i in range( 3 - len( tmp_winds ) ):
            tmp_winds.insert( 0, ( "", "", "", ) )
        winds = []
        for i in range( len( tmp_winds ) ):
            if ( tmp_winds[ i ][ 0 ] != "" ):
                winds += [ ( tmp_winds[ i ][ 0 ], "%s at %s" % ( tmp_winds[ i ][ 1 ], _localize_unit( tmp_winds[ i ][ 2 ].split()[ 1 ], "speed" ), ) ), ]
            else:
                winds += [ ( "", "", ) ]
        # fetch uvs
        uvs = re.findall( pattern_uv, htmlSource )
        # insert necessary dummy entries
        for i in range( 3 - len( uvs ) ):
            uvs.insert( 0, ( "", "", ) )
        # fetch humids
        humids = re.findall( pattern_humidity, htmlSource )
        # insert necessary dummy entries
        for i in range( 3 - len( humids ) ):
            humids.insert( 0, ( "", "", ) )
        # fetch daylights
        daylights = re.findall( pattern_daylight, htmlSource )
        # insert necessary dummy entries
        for i in range( 6 - len( daylights ) ):
            daylights.insert( 0, ( "", "" ) )
        # fetch outlooks
        outlooks = re.findall( pattern_outlook, htmlSource )
        # insert necessary dummy entries
        for i in range( 3 - len( outlooks ) ):
            outlooks.insert( 0, "" )
        # separate briefs
        brief = []
        icon = []
        for item in briefs:
            brief += [ item[ 1 ] ]
            icon += [ item[ 0 ] ]
        # convert outlook wind/temp values
        # normalize turned off due to variety of expressions : 'upper', 'single digits', etc.
        # TODO : getting most expressions covered
        outlooks = _normalize_outlook( outlooks )
        # translate brief and outlook if user preference
        if ( self.translate is not None ):
            # we only need outlook and brief. the rest the skins or xbmc language file can handle
            # we separate each item with single pipe
            text = "|".join( outlooks )
            # separator for different info
            text += "|||||"
            # we separate each item with single pipe
            text += "|".join( brief )
            # translate text
            text = _translate_text( text, self.translate )
            # split text into it's original list
            outlooks = text.split( "|||||" )[ 0 ].split( "|" )
            brief = text.split( "|||||" )[ 1 ].split( "|" )
        # no need to run if none found
        if ( len( headings ) ):
            # set our previous variables to the first items
            prevday = int( headings[ 0 ][ 1 ].split( " " )[ -1 ] )
            prevmonth = headings[ 0 ][ 1 ].split( " " )[ 0 ]
            # use a dictionary for next month
            nextmonth = { "Jan": "Feb", "Feb": "Mar", "Mar": "Apr", "Apr": "May", "May": "Jun", "Jun": "Jul", "Jul": "Aug", "Aug": "Sep", "Sep": "Oct", "Oct": "Nov", "Nov": "Dec", "Dec": "Jan" }
            # enumerate thru and create our forecast list
            for count, ( day, date, alert, ) in enumerate( headings ):
                # add a month to the date
                month = date.split( " " )[ 0 ]
                mday = int( date.split( " " )[ -1 ] )
                # month change
                if ( mday < prevday ):
                    prevmonth = nextmonth[ prevmonth ]
                # set the new date
                date = "%s %d" % ( prevmonth, mday, )
                prevday = mday
                # if no icon, set it to na
                if ( not briefs[ count ][ 0 ] ):
                    pass
                # make icon path
                iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count ] + ".png" ] )
                # add result to our class variable
                self.forecast += [ ( day, date, iconpath, brief[ count ], highs[count][ 0 ], _localize_unit( highs[ count ][ 1 ] ),
                lows[ count ][ 0 ], _localize_unit( lows[ count ][ 1 ] ), precips[ count * 2 ], precips[ count * 2 + 1 ].replace( "%", "" ).replace( "<B>", "" ).replace( "</B>", "" ),
                winds[ count ][ 0 ], winds[ count ][ 1 ], uvs[ count ][ 0 ], uvs[ count ][ 1 ],
                humids[ count ][ 0 ], humids[ count ][ 1 ].replace( "%", "" ), daylights[ count * 2 ][ 0 ], _localize_unit( daylights[ count * 2 ][ 1 ], "time" ), daylights[ count * 2 + 1 ][ 0 ],
                _localize_unit( daylights[ count * 2 + 1 ][ 1 ], "time" ), outlooks[ count ], observeds[ count ], pasts[ count * 3 + 2 ].split( "&nbsp;" )[ 0 ], _localize_unit( pasts[ count * 3 + 2 ].split( "&nbsp;" )[ 1 ], "depth" ),
                avgs[ count * 4 ][ 0 ], _localize_unit( avgs[ count * 4 ][ 1 ] ), avgs[ count * 4 + 1 ][ 0 ], _localize_unit( avgs[ count * 4 + 1 ][ 1 ] ),
                avgs[ count * 4 + 2 ][ 0 ], _localize_unit( avgs[ count * 4 + 2 ][ 1 ] ), avgs[ count * 4 + 3 ][ 0 ], _localize_unit( avgs[ count * 4 + 3 ][ 1 ] ),
                alert.strip(), _localize_unit( departures[ count * 2 ], "tempdiff" ), _localize_unit( departures[ count * 2 + 1 ], "tempdiff" ), ) ]

class Forecast10DayParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
        # regex patterns
	pattern_heading = "<th class=\"twc-col-[0-9]+ twc-forecast-when \" id=\"twc-date-col[0-9]+\">(.+?)<span>([^:]+):"
	pattern_icon = "http://s.imwx.com/v.20100719.135915/img/wxicon/45/([0-9]+).png"
	pattern_brief = "<span class=\"fc-wx-phrase\">([^<]+)</span>"
	pattern_high_temp = "id=\"twc-wx-hi[0-9]+\">([^<]+)<"
	pattern_low_temp = "id=\"twc-wx-low[0-9]+\">([^<]+)<"
	pattern_wind = "<div class=\"fc-wind-desc\"><strong>(.+?)<br>at<br>(.+?)</strong>"
	pattern_precip = "twc-line-precip\">(.+?):<br><strong>(.+?)</strong>"
        # fetch headings
        heading = re.findall( pattern_heading, htmlSource )
	# print heading
	headings = [( heading[0][0], heading[0][1].replace("\n","").replace("\t","").split(" ")[1] + " " + heading[0][1].replace("\n","").replace("\t","").split(" ")[2] )]
	for count in range(1, 10):
		try:
			headings += [( heading[count][0].split(" ")[0], heading[count][0].split(" ")[1] + " " + heading[count][0].split(" ")[2] )]
		except:
			headings += [( "N/A", "N/A" )]
	# fetch icons
	icon = re.findall( pattern_icon, htmlSource )
	# fetch brief
	brief = re.findall( pattern_brief, htmlSource )
	# fetch temperatures
	high_temp = re.findall( pattern_high_temp, htmlSource )
	low_temp = re.findall( pattern_low_temp, htmlSource )
	# fetch wind
	wind = re.findall( pattern_wind, htmlSource )
	# fetch precip
	precip = re.findall( pattern_precip, htmlSource )
        # enumerate thru and create heading and forecast
        if ( len( headings ) ):
            # we convert wind direction to abbreviated text for LongWindDirection property
            windir = {    
                            "N": "From the North",
                            "NNE": "From the North Northeast",
                            "NE": "From the Northeast",
                            "ENE": "From the East Northeast",
                            "E": "From the East",
                            "ESE": "From the East Southeast",
                            "SE": "From the Southeast",
                            "SSE": "From the South Southeast",
                            "S": "From the South" ,
                            "SSW": "From the South Southwest",
                            "SW": "From the Southwest",
                            "WSW": "From the West Southwest",
                            "W": "From the West",
                            "WNW": "From the West Northwest",
                            "NW": "From the Northwest",
                            "NNW": "From the North Northwest" 
                        }
            # translate brief and outlook if user preference
            if ( self.translate is not None ):
                # we only need outlook and brief. the rest the skins or xbmc language file can handle
                # we separate each item with single pipe
		text = ""
                # we separate each item with single pipe
                try:
		   text += "|".join( brief )
		except:
		   printlog( "No Info : 10day Brief" )
                # translate text
                text = _translate_text( text, self.translate )
                # split text into it's original list
                brief = text.split( "|" )
            # create our forecast list
            for count in range(0, 10):
                # make icon path
                try:
			iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count ] + ".png" ] )
		except:
			iconpath = "special://temp/weather/128x128/na.png"
		# print headings, iconpath, brief, high_temp, low_temp, precip, wind
		# add result to our class variable
		if ( self.translate is not None ):
			try:
				self.forecast += [ ( headings[ count ][ 0 ], headings[ count ][ 1 ], iconpath, brief[ count ].replace("\n","").replace("\t",""), _localize_unit( high_temp[ count ].strip("\nt&deg;") ), _localize_unit( low_temp[ count ].strip("\nt&deg;") ), precip[ count ][ 1 ].replace( "%", "" ), _translate_text( windir.get( wind[ count ][ 0 ], wind[ count ][ 0 ] ), self.translate ), _localize_unit( wind[ count ][ 1 ], "speed" ), wind[ count ][ 0 ], ) ]
			except:
				try: 
					self.forecast += [ ( headings[ count ][ 0 ], headings[ count ][ 1 ], iconpath, brief[ count ].replace("\n","").replace("\t",""), "N/A", _localize_unit( low_temp[ count ].strip("\nt&deg;") ), precip[ count ][ 1 ].replace( "%", "" ), _translate_text( windir.get( wind[ count ][ 0 ], wind[ count ][ 0 ] ), self.translate ) , _localize_unit( wind[ count ][ 1 ], "speed" ), wind[ count ][ 0 ], ) ]
				except:
					self.forecast += [ ( "N/A", "N/A ", iconpath, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ) ]
		else:
			try:
				self.forecast += [ ( headings[ count ][ 0 ], headings[ count ][ 1 ], iconpath, brief[ count ].replace("\n","").replace("\t",""), _localize_unit( high_temp[ count ].strip("\nt&deg;") ), _localize_unit( low_temp[ count ].strip("\nt&deg;") ), precip[ count ][ 1 ].replace( "%", "" ), windir.get( wind[ count ][ 0 ], wind[ count ][ 0 ] ), _localize_unit( wind[ count ][ 1 ], "speed" ), wind[ count ][ 0 ], ) ]
			except:
				try: 
					self.forecast += [ ( headings[ count ][ 0 ], headings[ count ][ 1 ], iconpath, brief[ count ].replace("\n","").replace("\t",""), "N/A", _localize_unit( low_temp[ count ].strip("\nt&deg;") ), precip[ count ][ 1 ].replace( "%", "" ), windir.get( wind[ count ][ 0 ], wind[ count ][ 0 ] ) , _localize_unit( wind[ count ][ 1 ], "speed" ), wind[ count ][ 0 ], ) ]
				except:
					self.forecast += [ ( "N/A", "N/A ", iconpath, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ) ]

class WeatherAlert:
    def __init__( self, htmlSource ):
        self.alert = ""
        self.title = ""
        self.alert_rss = ""
        try:            
            self._get_alert( htmlSource )
        except:
            pass

    def _get_alert( self, htmlSource ):
        # regex patterns

        # pattern_alert = "<h1>([^<]+)</h1>"      
        # pattern_issuedby = "<p class=\"alIssuedBy\">(.+?)</p>"
        pattern_narrative = "<p class=\"alNarrative\">(.+?)</p>"
        # pattern_expires = "<p>(<b>.+?</b>[^<]+)</p>" 
        pattern_moreinfo = "<h2>([^<]+)</h2>\n.+?<p class=\"alSynopsis\">"
        pattern_synopsis = "<p class=\"alSynopsis\">(.+?)</p>"
        
        pattern_alert_ = "</span>([^<]+)</h2>"
        pattern_issuedby_ = "Issued by (.+?)</h3>"
        # pattern_narrative_ = "\.\.\. (.*?)<br class=\"clear-content\">"
        pattern_narrative_ = "</div>[^<]+</div>[^<]+</div>[^<]+<p>(.+?)<br class=\"clear-content\">"
        pattern_expires_ = "<h3 class=\"twc-module-sub-header twc-timestamp twc-alert-timestamp\">([^<]+)</h3>"

	# print htmlSource

        # fetch alert
        alert = re.findall( pattern_alert_, htmlSource )[ 0 ].replace("\n", "").replace("\t","")

        # fetch expires
        try:
            expires = re.findall( pattern_expires_, htmlSource )[ 0 ].replace( "\n", "" ).replace( "\t", "" )
        except:
            expires = ""
        # TODO : localizing expire time?
        expires = ""
        # fetch issued by
        try:
            issuedby_list = re.findall( pattern_issuedby_, htmlSource, re.DOTALL )[ 0 ].split( "<br>" )
            issuedby = "[I]Issued by "
            for item in issuedby_list:
                issuedby += item.strip()
                issuedby += "\n"
            issuedby += "[/I]"
            # fetch narrative
	    narrative = ""
 	    description_list = re.findall( pattern_narrative, htmlSource, re.DOTALL )
	    # print description_list
	    if (not len(description_list)):
	        description_list = re.findall( pattern_narrative_, htmlSource, re.DOTALL )
		narrative = "... "
            
            for item in description_list:
                narrative += "%s\n\n" % ( item.strip().replace("\n", "").replace("\t","").replace("</p>","\n\n").replace("<p>","").replace("</div>","").replace("<h2>","").replace("</h2>",""), )
            try:
                # fetch more info
                moreinfo = re.findall( pattern_moreinfo, htmlSource )[ 0 ]
                moreinfo = "[B]%s[/B]" % ( moreinfo, )
                # fetch sysnopsis
                description_list = re.findall( pattern_synopsis, htmlSource, re.DOTALL )
                synopsis = ""
                for item in description_list:
                    synopsis += "%s\n\n" % ( item.strip(), )
            except:
                moreinfo = ""
                synopsis = ""
        except:
            try:
                narrative = ""
                synopsis = ""
                issuedby = re.findall( "<p>(.+)?</p>", htmlSource )[ 0 ]
                items =  re.findall( "<B>(.+)?</B>\s.*\s.*\s.*\s.+?<IMG SRC=\"[^>]+> <B>([^<]+)</B><BR>Type: (.+)", htmlSource )[ 0 ]
                moreinfo = "\nType: %s (%s)\nLevel: %s" % ( items[ 0 ], items[ 2 ], items[ 1 ], )
            except:
                pass
        try:
            # create our alert string
            self.alert = "[B]%s[/B]\n%s\n\n%s\n%s\n\n%s\n\n%s" % ( alert, expires, issuedby, narrative.strip(), moreinfo, synopsis.strip(), )
            self.alert = "%s\n%s\n\n" % ( self.alert.strip(), "-"*100, )
            # we use this for adding titles at the begining of the alerts text for multiple alerts
            self.title = "[B]%s[/B]" % ( alert, )
            # set the alert rss
            self.alert_rss = "[COLOR=rss_headline]%s:[/COLOR] %s %s - %s" % ( alert, alert, expires, issuedby.replace( "\n", " " ), )
        except:
            self.alert = None
            self.title = ""
            self.alert_rss = ""

