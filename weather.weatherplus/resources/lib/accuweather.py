# coding: utf-8

#*****************************************************
# 
#     Weather Client for Accuweather.com
#
#                           created by brightsr
#
#*****************************************************

import sys, os, urllib2, re, time
import xbmcaddon, xbmcgui
from threading import Thread
from utilities import _fetch_data, _translate_text, printlog
from utilities import _translate_text, _normalize_outlook, _localize_unit, _english_localize_unit
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
icondir = {"1":"32", "2":"30", "3":"28", "4":"30", "5":"34", 
	   "6":"28", "7":"26", "8":"26", "11":"19", "12":"11", 
	   "13":"39", "14":"39", "15":"3", "16":"37", "17":"37",
	   "18":"12", "19":"14", "20":"14", "21":"14", "22":"16", 
	   "23":"16", "24":"25", "25":"25", "26":"25", "29":"5", 
   	   "30":"36", "31":"32", "32":"23", "33":"31", "34":"29", 
	   "35":"27", "36":"27", "38":"27", "37":"33", "39":"45", 
	   "40":"45", "41":"47", "42":"47", "43":"46", "44":"46" }  

uvindex_dir = {	"0": "Low", "1": "Low", "2": "Low", "3": "Minimal", "4": "Minimal", "5": "Moderate", "6": "Moderate",
		"7": "High", "8": "High", "9": "High", 
		"10": "Very high", "11": "Very high", "12": "Very high", "13": "Very high", "14": "Very high", "15": "Very high", "16": "Very high" }      

areadir = { "iseas" : "KSXX0037",  # East Asia 
	    "isasi" : "KSXX0037",  # Asia
       	    "iseur" : "FRXX0076",  # Europe
	    "iscan" : "CAXX0504",  # Canada
	    "ismex" : "MXDF0132",  # Mexico
	    "iscam" : "PMXX0004",  # Caribbean
	    "iscsa" : "CIXX0020",  # South America
	    "isssa" : "CIXX0020",
	    "isnsa" : "CIXX0020",
	    "isaus" : "ASXX0112",  # Austrailia
	    "isnz"  : "NZXX0003",  # New Zealand
	    "isind" : "INXX0096",  # India
	    "isafr" : "UGXX0001",  # Africa
	    "ismid" : "IRXX0036" } # Middle East
 	

class WeatherClient:
	# base url
	BASE_FORECAST_URL = "http://www.accuweather.com/%s/%s.aspx?cityid=%s"
	BASE_MOBILE_URL = "http://m.accuweather.com/%s/%s/%s/%s"
	BASE_WEATHER_COM_URL = "http://www.weather.com/weather/%s/%s?%s"

	def __init__( self, code=None, translate=None, accu_translate=None ):
		# set users locale
		self.code = code
		# set users translate preference
		self.translate = translate
		self.accu_translate = accu_translate
		if ( self.accu_translate != "en-us" ): self.code = self.code.replace( "en-us", self.accu_translate )
		# set wind directory and translate pharses if needed
		self._set_windir()
		# set urls to be fetched
		self.urls = []
		self._set_urls()
		# fetch urls
		self._fetch_urls(15)		

	def _set_urls ( self ):
		addr = self.code.split(" ")[0]
		addr_en = "en-us" + self.code.split(" ")[0].lstrip( str(self.code.split("/")[0]) )
		cityID = self.code.split(" ")[1]
		self.hourly_url = self.BASE_FORECAST_URL % ( addr, "hourly", cityID )
		TSource[ self.hourly_url ] = _fetch_data( self.hourly_url, 0 )
		pattern_date = "<option selected=\"selected\" value=\"([0-9]+)\">"
		date = re.findall( pattern_date, TSource[ self.hourly_url ] )
		self.urls = [ self.BASE_FORECAST_URL % ( addr, "quick-look", cityID ),
			self.BASE_FORECAST_URL % ( addr, "details", cityID ),
			self.BASE_FORECAST_URL % ( addr, "details2", cityID ),
			self.BASE_FORECAST_URL % ( addr_en, "quick-look", cityID ),
			self.BASE_FORECAST_URL % ( addr_en, "details2", cityID ),
			self.BASE_FORECAST_URL % ( addr_en, "satellite", cityID ),
			self.BASE_FORECAST_URL % ( addr, "forecast", cityID ),
			self.BASE_FORECAST_URL % ( addr, "forecast2", cityID ),
			self.BASE_FORECAST_URL % ( addr_en, "forecast", cityID ),
			self.BASE_FORECAST_URL % ( addr_en, "forecast2", cityID ),
			self.BASE_FORECAST_URL % ( addr, "hourly"+date[1], cityID ),
			self.BASE_FORECAST_URL % ( addr, "hourly"+ str( int(date[1])+7 ), cityID ), ]
		org_cityID = cityID
		if ( addr_en.split("/")[1] == "us" ) :
			cityID = "00000"
			addr_en = addr_en.split("/")
			addr_en = "/".join( addr_en[:2] ) + "/%s-%s" % ( addr_en[3], addr_en[2] )
		else:
			addr_en = addr_en.split("/")
			addr_en = "/".join( addr_en[:2] ) + "/%s" % addr_en[3]
		for count in range(1, 11):
			self.urls += [ self.BASE_MOBILE_URL % ( addr_en, cityID, "daily-weather-forecast", "%s?day=%d" % (org_cityID, count) ) ]
		self.urls += [ self.BASE_MOBILE_URL % ( addr_en, cityID, "hourly-weather-forecast", org_cityID ),
			self.BASE_MOBILE_URL % ( addr_en, cityID, "hourly-weather-forecast", "%s?day=2" % org_cityID ) ]

	def _fetch_urls ( self, refreshtime=0 ):
		printlog( "Multi-threaded URL Fetching started.." )
		start = time.clock()
		Threads = [ Thread( name = url, target = self.ThreadURL, args = (url, refreshtime, ) ) for url in self.urls ]
		for t in Threads:
			t.start()
		count = 0
		for t in Threads:
			count += 1
			t.join()
		printlog( "Multi-threaded URL Fetching finished.." )
		printlog( "Elapsed time : %f sec." % (time.clock() - start) )
	
	def _set_windir ( self ):
		global windir
		windir_en = "From the North|From the North Northeast|From the Northeast|From the East Northeast|From the East|From the East Southeast|From the Southeast|From the South Southeast|From the South|From the South Southwest|From the Southwest|From the West Southwest|From the West|From the West Northwest|From the Northwest|From the North Northwest"
		if (self.translate == "en-us"):
			windir_tr = windir_en.split("|")
		else:
			windir_tr = _translate_text( windir_en, self.accu_translate, "accu" ).split("|")
			windir = {    
		                    "N": windir_tr[0],
		                    "NNE": windir_tr[1],
		                    "NE": windir_tr[2],
		                    "ENE": windir_tr[3],
		                    "E": windir_tr[4],
		                    "ESE": windir_tr[5],
		                    "SE": windir_tr[6],
		                    "SSE": windir_tr[7],
		                    "S": windir_tr[8],
		                    "SSW": windir_tr[9],
		                    "SW": windir_tr[10],
		                    "WSW": windir_tr[11],
		                    "W": windir_tr[12],
		                    "WNW": windir_tr[13],
		                    "NW": windir_tr[14],
		                    "NNW": windir_tr[15]
			}

    	def _fetch_36_forecast( self, video="" ):
		printlog( "Trying to fetch 36 hour forecast.. " )
		# parse source for forecast
		parser = ACCU_Forecast36HourParser( TSource[self.urls[0]], TSource[self.urls[1]], TSource[self.urls[2]], TSource[self.urls[3]], TSource[self.urls[4]], TSource[self.urls[12]] + TSource[self.urls[13]], self.translate )
		# any errors?
		addr = self.code.split(" ")[0]
		addr_en = "en-us" + self.code.split(" ")[0].lstrip( str(self.code.split("/")[0]) )
		cityID = self.code.split(" ")[1]
		mobile = TSource[self.urls[12]] + TSource[self.urls[13]]
		while ( parser.error > 0 and parser.error < 5 ):
			printlog( "Error!" )
			printlog( "Retrying..." )		
			self.urls = [ self.BASE_FORECAST_URL % ( addr, "quick-look", cityID ),
					self.BASE_FORECAST_URL % ( addr, "details", cityID ),
					self.BASE_FORECAST_URL % ( addr, "details2", cityID ),
			 		self.BASE_FORECAST_URL % ( addr_en, "quick-look", cityID ),
			 		self.BASE_FORECAST_URL % ( addr_en, "details2", cityID ),
			 		self.BASE_FORECAST_URL % ( addr_en, "satellite", cityID ) ]
			start = time.clock()
			self._fetch_urls()
			printlog( "Multi-threaded URL Fetching finished.." )
			printlog( "Elapsed time : %f sec." % (time.clock() - start) )
			# parse source for forecast
			parser._get_forecast( TSource[self.urls[0]], TSource[self.urls[1]], TSource[self.urls[2]], TSource[self.urls[3]], TSource[self.urls[4]], mobile )
		# create video url
		if ( self.code.split("/")[1]=="us" ):
			from video_us import _create_video
			self.loc = re.findall("zip: '(.[0-9]+)'", TSource[self.urls[0]])[0]
			video_title = [Addon.getSetting("video1"), Addon.getSetting("video2"), Addon.getSetting("video3")]
			video = _create_video ( video_title )
		else:
			from video_non_us import _create_video
			try:
				self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", TSource[self.urls[5]])[0]
				video, video_title = _create_video( self.code.split("/")[1], self.loc )
			except:
				htmlSource_5 = _fetch_data( self.BASE_FORECAST_URL % ( addr_en, "satellite", cityID ), 0 )
				self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", htmlSource_5)[0]
				video, video_title = _create_video( self.code.split("/")[1], self.loc )
		return "", "", "", "", "", parser.forecast, parser.extras, video, video_title

    	def _fetch_hourly_forecast( self ):
		printlog( "Trying to fetch hourly forecast.." )
		# parse source for forecast
		parser = ACCU_ForecastHourlyParser( TSource[self.urls[10]] + TSource[self.urls[11]] + TSource[self.urls[22]] + TSource[self.urls[23]], TSource[self.hourly_url] )
		# any error?
		while (parser.error > 0 and parser.error < 5):
			try:
				htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
			except:
				htmlSource_3 = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ), 0 )
				date = re.findall( pattern_date, htmlSource_3 )
				htmlSource = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
			htmlSource_2 = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ), 0 )
			parser._get_forecast( htmlSource + htmlSource_2, htmlSource_3 )
	
		# return forecast
		printlog( "Parsing Hourly Forecast.. Done!" )
		return parser.forecast

    	def _fetch_10day_forecast( self ):
		printlog( "Trying to fetch 10 day forecast.." )       
		Details = ""
		for count in range(12, 22):
			Details += TSource [ self.urls[count] ]
		# parse source for forecast
		parser = ACCU_Forecast10DayParser( TSource [ self.urls[6] ] + TSource [ self.urls[7] ], TSource [ self.urls[8] ] + TSource [ self.urls[9] ], Details, self.code.split(" ")[0].split("/")[0] )

		# any error?
		while (parser.error > 0 and parser.error < 5):
			printlog( "Retrying to fetch..." )
			code = "en-us" + self.code.split(" ")[0].lstrip( str(self.code.split("/")[0]) )
			htmlSource_1 = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "forecast", self.code.split(" ")[1] ), 0 )
			htmlSource_2 = _fetch_data( self.BASE_FORECAST_URL % ( self.code.split(" ")[0], "forecast2", self.code.split(" ")[1] ), 0 )
			htmlSource_3 = _fetch_data( self.BASE_FORECAST_URL % ( code, "forecast", self.code.split(" ")[1] ), 0 )
			htmlSource_4 = _fetch_data( self.BASE_FORECAST_URL % ( code, "forecast2", self.code.split(" ")[1] ), 0 )
			parser.forecast = []
			parser._get_forecast( htmlSource_1 + htmlSource_2, htmlSource_3 + htmlSource_4, Details )

		# return forecast
		return parser.forecast

	def ThreadURL( self, url, refreshtime=0 ):
		global TSource
		data = _fetch_data( url, refreshtime )
		# store results
		TSource[ url ] = data

	def fetch_map_list( self, maptype=0, userfile=None, locationindex=None ):
		# set url
		url = BASE_URL + BASE_MAPS[ maptype ][ 1 ]        
		# we handle None, local and custom map categories differently
		if ( maptype == 0 ):
			# return None if none category was selected
			return None, None
		elif ( maptype == 1 ):
			# add locale to local map list if local category
			printlog( "Accuweather Map Location = " + self.loc )
			WEATHER_WINDOW.setProperty( "Map.Location", self.loc )     # leave footprint for 'map only' call
		    	try: 
				loc = self.loc[:5]
	   	        except:
				loc = self.loc
			areacode = areadir.get( loc, self.loc )    # if no match, it may be US zip. so appending itself.
			url = url % ( "map", areacode, "", )
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
			self.loc = WEATHER_WINDOW.getProperty( "Map.Location" )
			try: 
				loc = self.loc[:5]
			except:
				loc = self.loc
			areacode = areadir.get( loc, self.loc )    # if no match, it may be US zip. so appending itself.
			url = self.BASE_WEATHER_COM_URL % ( "map", areacode, "&mapdest=%s" % ( map, ), )
		# fetch source
		htmlSource = _fetch_data( url, 60*60*24*7, subfolder="maps",  )
		# parse source for static map and create animated map list if available
		parser = MapParser( htmlSource )
		# return maps
		return parser.maps

class ACCU_Forecast36HourParser:
	def __init__( self, htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4, precips, translate=None ):
		self.forecast = []
		self.extras = []
		self.alerts = []
		self.alertscolor = []
		self.video_location = []
		self.translate = translate
		self.sun = []
		self.error = 0

		# only need to parse source if there is source
		if ( htmlSource ):
		    self._get_forecast( htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4, precips )

	def _get_forecast( self, htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4, precips ):
		# regex patterns
		pattern_icon = "/wxicons/87x79_blue/([0-9]+)_int.jpg"
		pattern_current_brief = "<span id=\"ctl00_cphContent_lblCurrentText\" style=\"display: block; font-size: 11px;line-height: 17px;\">(.+?)</span>"
		pattern_forecast_brief = "<span id=\"ctl00_cphContent_lbl(.+?)Text\">(.+?)</span>"
		pattern_temp = "<span id=\"ctl00_cphContent_lbl(.+?)Value\">(.+?)\&deg"
		pattern_current_temp = "<span id=\"ctl00_cphContent_lblCurrentTemp\" style=\"display: block; font-weight: bold;font-size: 18px; line-height: 24px;\">(.+?)\&deg"
		pattern_current_feel_like = "<span id=\"ctl00_cphContent_lblRealFeelValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)\&deg"
		pattern_current_time = "<span id=\"ctl00_cphContent_lblCurrentTime\" style=\"display: block; font-size: 11px;line-height: 17px;\">(.+?)</span>"
		pattern_current_wind = "<span id=\"ctl00_cphContent_lblWindsValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)</span>"
		pattern_current_humidity = "<span id=\"ctl00_cphContent_lblHumidityValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)%</span>"
		pattern_current_dew = "<span id=\"ctl00_cphContent_lblDewPointValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)\&deg"
		pattern_pressure = "<span id=\"ctl00_cphContent_lblPressureValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)</span>"	                     
		pattern_visibility = "<span id=\"ctl00_cphContent_lblVisibilityValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)</span>"	        
		pattern_current_sunrise = "<span id=\"ctl00_cphContent_lblSunRiseValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)</span>"
		pattern_current_sunset = "<span id=\"ctl00_cphContent_lblSunSetValue\" class=\"fltRight\" style=\"width: 80px; display: block;\">(.+?)</span>"
		pattern_sunrise = "Sunrise: (.+?)</span>"
		pattern_sunset = "Sunset: (.+?)</span>"
		pattern_precip = "<p>Precipitation: <b>(.+?)%</b>"    
				
		try:
			# fetch icons
			icon = []
			current_icon = icondir.get( re.findall( pattern_icon, htmlSource )[0] ) 
			current_icon = current_icon + ".png"
			icon_day1 = re.findall( pattern_icon, htmlSource_1 )
			icon_day2 = re.findall( pattern_icon, htmlSource_2 )
			icon = [ icondir.get(icon_day1[0]), icondir.get(icon_day1[1]), icondir.get(icon_day2[0]), icondir.get(icon_day2[1]) ]
			printlog( "icons... Done!" )
			# enumerate thru and combine the day with it's forecast
			if ( len( icon ) ):           
				    # fetch brief description
				    current_brief = re.findall( pattern_current_brief, htmlSource )[0].title()
				    day1_brief = re.findall( pattern_forecast_brief, htmlSource_1 )
				    day2_brief = re.findall( pattern_forecast_brief, htmlSource_2 )
				    if ( day1_brief is not None and day2_brief is not None):
					brief_buffer = [ day1_brief[0][1], day1_brief[1][1], day2_brief[0][1], day2_brief[1][1] ]
					brief = [ s.title() for s in brief_buffer ]			
				    else:
					brief = [ "", "", "", "" ]
				    printlog( "briefs... Done!" )
				    # fetch temperature        
				    current_temp = re.findall( pattern_current_temp, htmlSource )[0]
				    current_feel_like = re.findall( pattern_current_feel_like, htmlSource )[0]
				    current_dew = re.findall( pattern_current_dew, htmlSource )[0]
				    day1_temp = re.findall( pattern_temp, htmlSource_1 )
				    day2_temp = re.findall( pattern_temp, htmlSource_2 )
				    temperature_info = ["High", "Low", "High", "Low"]
				    temperature = [ day1_temp[0][1], day1_temp[2][1], day2_temp[0][1], day2_temp[2][1] ]
				    printlog ( "temperatures... Done!" )
				    # fecth current infos
				    current_humidity = re.findall( pattern_current_humidity, htmlSource )[0]  
				    printlog ( "humidity... Done!" )
				    current_wind = re.findall( pattern_current_wind, htmlSource )[0]
				    printlog ( "wind... Done! (%s)" % current_wind )
				    current_winddirection = ""
				    try:
					current_winddirection = current_wind.split(" ")[0]
					current_wind = current_wind.split(" ")[1]
				    except:    # Calm or variable direction
					current_wind = "0"     # new pre-eden can't show "Calm", must fit the form "From XXX at XX km/h"
					current_winddirection = "VAR"
				    printlog ( "wind direction/speed split... Done!" )
				    # fetch precipitation
				    precip = re.findall( pattern_precip, precips )
				    # fetch sunrise and sunset
				    try:
					current_sunrise = _localize_unit( re.findall( pattern_current_sunrise, htmlSource_3 )[0], "time" )
				    except:
					current_sunrise = "N/A"
				    try:
					current_sunset = _localize_unit( re.findall( pattern_current_sunset, htmlSource_3 )[0], "time" )                      
				    except:
					current_sunset = "N/A"
				    try:
					sunrise = re.findall( pattern_sunrise, htmlSource_4 )[0]
				    except:
					sunrise = "N/A"
				    try:
					sunset = re.findall( pattern_sunset, htmlSource_4 )[0]
				    except:
					sunset = "N/A"
				    daylight = [ ("Sunrise", current_sunrise), ("Sunset", current_sunset), ("Sunrise", sunrise), ("Sunset", sunset) ]
				    # fetch extra info
				    try:
					pressure = _english_localize_unit( re.findall( pattern_pressure, htmlSource, re.DOTALL )[0], "pressure" )
				    except:
					pressure = "N/A"
				    try:
					visibility = _english_localize_unit( re.findall( pattern_visibility, htmlSource, re.DOTALL )[0], "distance" )
				    except:
					visibility = "N/A"
				    # print "[Weather Plus] pressure : " + pressure
				    self.extras += [( pressure, visibility, current_sunrise, current_sunset, current_temp, current_feel_like, current_brief, current_wind, current_humidity, current_dew, current_icon, current_winddirection )]
				    # am or pm now?
				    try: 
					current_time = re.findall( pattern_current_time, htmlSource_3 )[0]
				    except:
					current_time = xbmc.getInfoLabel("System.Time")
				    ampm = 0
				    try:
					if ( current_time.split(" ")[1] == "PM" ):
						ampm = 1	    
				    except:
					if ( int(current_time.split(":")[0]) > 11 ):
						ampm = 1
				    # print "[Weather Plus] Current Time : " + current_time
				    days = ["Today", "Tonight", "Tomorrow", "Tomorrow Night"]
				    printlog( "Checking fetched information... See below..." )
				    for count in range(0, 3):
					# make icon path
					try :
					  iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count+ampm ] + ".png" ] )
					except :
					  printlog( "Icon%s is not available" % icon[ count+ampm ] )
					  iconpath = "/".join( [ "special://temp", "weather", "128x128", "na.png" ] ) 
					printlog( days[count+ampm] )
					printlog( iconpath )
					try :
					  printlog( brief[ count+1 ] )
					except :
					  printlog( "iconpath is not available" )
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
					  printlog( precip[ count+ampm ] )
					except :
					  printlog( "precip["+str(count+ampm)+"] is not available" )
					  precip_amount += [ "N/A" ]
					try :
					  printlog( brief[ count+ampm ] )
					except :
					  printlog( "brief["+str(count+ampm)+"] is not available" )
					  brief += [ ("N/A", "N/A", "N/A", "N/A", ) ]
					try :
					  printlog( daylight[ count+ampm ][ 0 ] )
					except :
					  printlog( "daylight["+str(count+ampm)+"] is not available" )
					  daylight += [ ("N/A", ) ]
					try :
					  printlog( _localize_unit( daylight[ count+ampm ][ 1 ], "time"  ) )
					except :
					  printlog( "daylight["+str(count+ampm)+"] is not available" )
					  daylight += [ ("00:00", ) ]

					self.forecast += [ ( days[count+ampm], iconpath, "", temperature_info[ count+ampm ], _english_localize_unit( temperature[ count+ampm ] ), "", precip[ count+ampm ], brief[ count+ampm ], daylight[ count+ampm ][ 0 ], _localize_unit( daylight[ count+ampm ][ 1 ], "time"  ), ) ]
				    self.error = 0
			else:
				    self.error = self.error + 1
				    return
		except:
		    self.error = self.error + 1
		    return

class ACCU_ForecastHourlyParser:
    def __init__( self, htmlSource, enSource ):
        self.forecast = []
	self.error = 0
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource, enSource )

    def _get_forecast( self, htmlSource, enSource ):
        # regex patterns
	pattern_date = [ "([0-9]+)/([0-9]+)/20", "([0-9]+)-([0-9]+)-20" ]
        pattern_info = "<div class=\".+?textBold\">([^<]+)</div>"
	pattern_brief = "<div class=\".+?hbhWxText\">([^<]+)</div>"
	pattern_icon = "wxicons/31x24/(.+?).gif"
	pattern_wind = "winds/24x24/(.+?).gif"
	pattern_precip = "<p class=\"precip\">[^<]+<b>(.+?)%</b></p>"
        # fetch info
	date = re.findall( pattern_date[0], enSource )
        raw_info = re.findall( pattern_info, htmlSource )
	raw_brief = re.findall( pattern_brief, htmlSource )
	icon = re.findall( pattern_icon, htmlSource )
	wind = re.findall( pattern_wind, htmlSource )
	precip = re.findall( pattern_precip, htmlSource )
	info_ = []
	info = []
	brief = []
	try: dates = [ ( date[0][0], date[0][1] ), ( date[3][0], date[3][1] ) ]
	except:
 	    date = re.findall( pattern_date[1], htmlSource )
	    dates = [ ( date[0][0], date[0][1] ), ( date[3][0], date[3][1] ) ]
	for item in raw_info:
	    info_ += [ item.replace("\n","").replace("\r","").replace("\t","").replace("&deg", "°") ]
	for item in raw_brief:
	    brief += [ item.replace("\n","").replace("\r","").replace("\t","").replace("&deg", "°") ]	
	for count in range(0, 7):
	    info += [ ( info_[count], icondir.get( icon[count] ), brief[count], info_[count+7], info_[count+14], info_[count+21], info_[count+28], windir.get( wind[count] ), info_[count+35],  ) ]
	for count in range(49, 56):
	    try:
	        info += [ ( info_[count], icondir.get( icon[count-43] ), brief[count-43], info_[count+7], info_[count+14], info_[count+21], info_[count+28], windir.get( wind[count-43] ), info_[count+35], ) ]
	    except:
	        self.error = self.error + 1
	        return
        if ( len( info ) ):
            # counter for date
            date_counter = 0
            # create our forecast list
            for count, item in enumerate( info ):
                # make icon path
                iconpath = "/".join( [ "special://temp", "weather", "128x128", item[ 1 ] + ".png" ] )
                # do we need to increment date_counter
                if ( item[ 0 ] == "12:00 AM" and count > 0 ):
                    date_counter += 1               
                try:
		   self.forecast += [ ( _localize_unit( item[ 0 ], "time" ), " ".join( dates[ date_counter ] ), iconpath, _english_localize_unit( item[ 3 ].split("°")[0] ), item[ 2 ], _english_localize_unit( item[ 4 ].split("°")[0] ), precip[ int(count/3) ], item[ 6 ].replace( "%", "" ), item[ 7 ], _english_localize_unit( item[ 8 ], "speed" ), item[ 7 ].split( " " )[ -1 ], "", "", ) ]
		except:
		   try:
		        self.forecast += [ ( item[ 0 ], " ".join( dates[ date_counter ] ), iconpath, _english_localize_unit( item[ 3 ].split("°")[0] ), item[ 2 ], _english_localize_unit( item[ 4 ].split("°")[0] ), precip[ int(count/3) ], item[ 6 ].replace( "%", "" ), item[ 7 ], _english_localize_unit( item[ 8 ], "speed" ), item[ 7 ].split( " " )[ -1 ], "", "", ) ]
		   except:
		        self.error = self.error + 1
			return

class ACCU_Forecast10DayParser:
    def __init__( self, htmlSource_1, htmlSource_2, details, translate ):
        self.forecast = []
        self.translate = translate
	self.error = 0
        # only need to parse source if there is source
        if ( htmlSource_1 and htmlSource_2 ):
            self._get_forecast( htmlSource_1, htmlSource_2, details )

    def _get_forecast( self, htmlSource_1, htmlSource_2, details ):
        # regex patterns
        pattern_day = "Day_ctl0[0-9]+_lblDate\">(.+?)</span>"
	pattern_outlook = "Day_ctl0[0-9]+_lblDesc\">(.+?)</span>"
        pattern_hightemp = "Day_ctl0[0-9]+_lblHigh\">(.+?)\&deg;"
	pattern_lowtemp = "Night_ctl0[0-9]+_lblHigh\">(.+?)\&deg;"
        pattern_icon = "/wxicons/87x79_blue/([0-9]+)_int.jpg"
	pattern_wind = "([A-Z]+) at ([0-9]+) ([a-z/]+)"
	pattern_sunrise = "Sunrise <b>(.+?)</b>"
	pattern_sunset = "Sunset <b>(.+?)</b>"
	pattern_UVindex = "<div class=\"d-wrap uv\">[^<]+<p[^>]+>([0-9]+) <em>(.+?)</em></p>"        
	pattern_precip = "<p>Precipitation: <b>(.+?)%</b>"    

        # fetch info
	htmlSource = htmlSource_1
	htmlSource_en = htmlSource_2
        days = re.findall( pattern_day, htmlSource_en )
	outlook = re.findall( pattern_outlook, htmlSource )
	hightemp = re.findall( pattern_hightemp, htmlSource )
	lowtemp = re.findall( pattern_lowtemp, htmlSource )
	icon = re.findall( pattern_icon, htmlSource )
	sunrise = re.findall( pattern_sunrise, details )
	sunset = re.findall( pattern_sunset, details )
	UVindex = re.findall( pattern_UVindex, details )
	wind = re.findall( pattern_wind, details )	
	precip = re.findall( pattern_precip, details )
	# print days, outlook, hightemp,lowtemp, icon, sunrise, sunset, UVindex, wind
	# print details

	# enumerate thru and create heading and forecast
	try:	
	    for count, day in enumerate(days):
		if (count>9): break	
	    	if (count<7):
		    iconpath = "/".join( [ "special://temp", "weather", "128x128", icondir.get( icon[count] ) + ".png" ] )
		else:
		    iconpath = "/".join( [ "special://temp", "weather", "128x128", icondir.get( icon[count+7] ) + ".png" ] )
		try:
		    winddirection = wind[2*count][0].lstrip()
		    windspeed = wind[2*count][1]
		except:
		    winddirection = "Calm"
		    windspeed = "0 k/h"
		windspeed = ( _localize_unit( windspeed, "speed" ), _english_localize_unit( windspeed, "speed" ) )[ windspeed.endswith("k/h") ]
		# if ( wind[count].split(" ")[0] != wind[count] ): windspeed = wind[count].split(" ")[1]
	        self.forecast += [ ( day.split(" ")[0], day.split(" ")[1], iconpath, outlook[count].title(), _english_localize_unit( hightemp[count] ), _english_localize_unit( lowtemp[count] ), precip[2*count], windir.get( winddirection, winddirection ), windspeed, winddirection, sunrise[count], sunset[count], "%s - %s" % ( UVindex[count][0], UVindex[count][1] ) ) ]
	except:
	    self.error = self.error + 1


