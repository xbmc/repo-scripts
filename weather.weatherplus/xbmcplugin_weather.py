"""
    GUI for displaying maps and forecasts from weather.com
    
    Nuka1195, Brightsr
"""

# main imports
import sys
import os

import xbmc
import xbmcgui

import WeatherClient as WeatherClient

from xbmcaddon import Addon
import re

def printlog( msg ):
    print "[Weather Plus] %s" % msg

class Main:
    __settings__ = Addon( id="weather.weatherplus" )
    __icon__ = __settings__.getAddonInfo("icon")
    __language__ = __settings__.getLocalizedString

    _ = __language__ 
    Settings = __settings__

    def __init__( self, *args, **kwargs ):
	# set location index
	self.maponly = sys.argv[ 1 ].startswith( "map=" )
        self.locationindex = xbmc.getInfoLabel( "Window(Weather).Property(LocationIndex)" )
	printlog("Location : %s" % self.locationindex)
        # get current window
        self._get_weather_window()
	# get provider info. ( 0 : Accuweather.com Global, 1 : NOAA, 2 : Weather.com)
	self.provider = self.Settings.getSetting("provider" + str(self.locationindex))
	if ( self.provider == "" ): 
	    if ( self.Settings.getSetting("alt_location" + str(self.locationindex)) == "True" ):
		self.provider = self.Settings.getSetting("alt_provider" + str(self.locationindex))
	    else:
		self.provider = "2"   # default provider : Weather.com
        # get our new WeatherClient
	self._get_client()
        # if user selected a new map, only need to fetch it
        if ( self.maponly ):
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
            # fetch map (map=%s&title=%s&location=
            self._fetch_map( params[ "map" ], params[ "title" ], params[ "location" ] )
        else:
	    # set name of weather provider
    	    self.WEATHER_WINDOW.setProperty( "WeatherProvider", ("Accuweather.com Global", "NOAA", "Weather.com")[ int(self.provider) ] )
	    # if not from weather.com  set name of location from addon's settings
	    if ( self.provider != "2" ):
		    # self.WEATHER_WINDOW.setProperty( "Location", Location)
	    	    Location = self.Settings.getSetting("location%s_%d" % ( self.locationindex, int(self.provider)+1 ))
		    self.WEATHER_WINDOW.setProperty( "Location" , Location )
		    self.WEATHER_WINDOW.setProperty( "Location%s" % self.locationindex, Location )
	    # verify areacode
	    if ( not self._verify_areacode() ): return
	    printlog("Verifying areacode... OK")
            # set plugin name property
            self._set_plugin_name()
            # clear key properties
            self._clear_properties()
            # initialize our thread list
	    if ( self.provider == "0" ):        # Accuweather.com Global
		printlog("Provider Selected : Accuweather.com Global (%s)" % self.areacode)
		self._accu_hourly_forecast()
		self._accu_10day_forecast()     # also making weekend properties from daily forecast
		self._accu_36_forecast()    
		# self._accu_weekend_forecast()
		self._fetch_map_list()
	    elif ( self.provider == "1" ):      # NOAA
		printlog("Provider Selected : NOAA (%s)" % self.areacode)
		self._noaa_hourly_forecast()
		# self._noaa_10day_forecast()
		self._noaa_weekend_forecast()   # just clearing propose
		self._noaa_36_forecast()
		self._fetch_map_list()
	    elif ( self.provider == "3" ):      # Wunderground.com (under construction)
		printlog("Provider Selected : Wunderground (%s)" % self.areacode)
		self._wunder_10day_forecast()
		self._wunder_hourly_forecast()
		self._wunder_36_forecast()
		# self._wunder_weekend_forecast()
		for count in range( 1, 4 ):
		      self._clear_map_list( count )
		# self._fetch_map_list()
            else :                              # Weather.com
		printlog("Provider Selected : Weather.com (%s)" % self.areacode)
		self._fetch_map_list()		
		self._fetch_hourly_forecast()
		self._fetch_10day_forecast()
		self._fetch_weekend_forecast()
		self._fetch_36_forecast()
	# leave areacode for checking later if location is new or not
	self.WEATHER_WINDOW.setProperty( "PreviousAreacode", self.areacode )
	# we're finished, exit
	printlog("*** Finish! ***")
        self._exit_script()

    def _get_weather_window( self ):
        # grab the weather window
        self.WEATHER_WINDOW = xbmcgui.Window( 12600 )

    def _set_plugin_name( self ):
        # set plugin name
        self.WEATHER_WINDOW.setProperty( "Plugin", sys.modules[ "__main__" ].__plugin__ )

    def _verify_areacode ( self ):
	printlog(self.areacode)
	if ( self.areacode == "" ):
	    printlog("ERROR : No Location Selected")
	    xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"No Location Selected!\",240, self.__icon__) ")
  	    return False
	if ( self.provider == "0" ): # Accuweather.com Global
            if ( re.search( "/", self.areacode ) is None ):
	    	xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Invalid Area Code!\",240, self.__icon__) ")
	    	printlog("ERROR : Invalid Code ( When you change a provider, you should re-select a location )")
		return False
	elif ( self.provider == "1" ): # NOAA
	    if ( re.search( "CityName", self.areacode ) is None ):
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Invalid Area Code!\",240, self.__icon__) ")
		printlog("ERROR : Invalid Code ( When you change a provider, you should re-select a location )")
		return False
	elif ( self.provider == "3" ): # Wunderground.com
	    if ( re.search( "zmw", self.areacode ) is None ):
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Invalid Area Code!\",240, self.__icon__) ")
		printlog("ERROR : Invalid Code ( When you change a provider, you should re-select a location )")
		return False
	return True

    def _get_client( self ):	
        self.settings = { "translate": None, "accu_translate": "en-us" }
        if ( self.Settings.getSetting( "translate" ) == "true" ):
            self.settings[ "translate" ] = {
                                        "Chinese (Simple)": "en_zh",
                                        "Chinese (Traditional)": "en_zt",
                                        "Dutch": "en_nl",
                                        "French": "en_fr",
                                        "German": "en_de",
                                        "German (Austria)": "en_de",
                                        "Greek": "en_el",
                                        "Italian": "en_it",
                                        "Japanese": "en_ja",
                                        "Korean": "en_ko",
                                        "Portuguese": "en_pt",
                                        "Portuguese (Brazil)": "en_pt",
                                        "Russian": "en_ru",
                                        "Spanish": "en_es",
                                        "Spanish (Mexico)": "en_es",
                                    }.get( xbmc.getLanguage(), None )

	self.settings[ "accu_translate" ] = {
                                        "2": "ca",
                                        "6": "cs",
                                        "7": "da",
                                        "13": "de",
                                        "28": "es-ar",
                                        "29": "es-mx",
                                        "1": "es",
                                        "11": "fr-ca",
                                        "12": "fr",
                                        "18": "it",
                                        "17": "hu",
                                        "8": "nl",
					"9": "en-us",
                                        "21": "no",
                                        "22": "pl",
                                        "23": "pt-br",
					"24": "pt",
					"25": "ro",
					"26": "ru",
					"30": "sv",
					"10": "fi",
					"27": "sk",
					"0": "ar",
					"3": "zh-cn",
					"4": "zh-tw",
					"5": "zh-hk",
					"31": "tr",
					"14": "el",
					"19": "ja",
					"20": "ko",
					"16": "hi",
					"15": "he"
                                    }.get( self.Settings.getSetting( "accu_translate%s" % self.locationindex ), "en-us" )
        if ( self.provider == "2" ): 
	    self.areacode = sys.argv[1]
	else:
	    self.areacode = self.Settings.getSetting("code%s_%d" % ( self.locationindex, int(self.provider)+1 ))  
	# set if new location
	self.new_location = self.WEATHER_WINDOW.getProperty( "PreviousAreacode" ) != self.areacode
        # setup our radar client
        self.WeatherClient = WeatherClient.WeatherClient( self.areacode, self.settings[ "translate" ], self.settings[ "accu_translate" ] )

    def _set_maps_path( self, path=0, maps_path="", legend_path="" ):
        # we have three possibilities. loading, default (error) or the actual map path
        if ( path == 0 ):
            self.WEATHER_WINDOW.setProperty( "MapStatus", "loading" )
            self.WEATHER_WINDOW.setProperty( "MapPath", "weather.com plus/loading" )
            self.WEATHER_WINDOW.setProperty( "LegendPath", "" )
        elif ( path == 1 ):
            self.WEATHER_WINDOW.setProperty( "MapStatus", "loaded" )
            self.WEATHER_WINDOW.setProperty( "MapPath", maps_path )
            self.WEATHER_WINDOW.setProperty( "LegendPath", legend_path )
        elif ( path == 2 ):
            self.WEATHER_WINDOW.setProperty( "MapStatus", "error" )
            self.WEATHER_WINDOW.setProperty( "MapPath", "weather.com plus/error" )
            self.WEATHER_WINDOW.setProperty( "LegendPath", "" )

    def _clear_properties( self ):
        # clear properties used for visibilty
        self.WEATHER_WINDOW.clearProperty( "Alerts" )
        self.WEATHER_WINDOW.setProperty( "Alerts.Color", "default" )
        self.WEATHER_WINDOW.clearProperty( "Video" )
        self.WEATHER_WINDOW.clearProperty( "36Hour.IsFetched" )
        self.WEATHER_WINDOW.clearProperty( "Weekend.IsFetched" )
        self.WEATHER_WINDOW.clearProperty( "Daily.IsFetched" )
        self.WEATHER_WINDOW.clearProperty( "Hourly.IsFetched" )
	self.WEATHER_WINDOW.clearProperty( "Current.Pressure" )
        self.WEATHER_WINDOW.clearProperty( "Current.Visibility" )
        self.WEATHER_WINDOW.clearProperty( "Current.Sunrise" )
        self.WEATHER_WINDOW.clearProperty( "Current.Temperature" )
        self.WEATHER_WINDOW.clearProperty( "Current.ConditionIcon" )
        self.WEATHER_WINDOW.clearProperty( "Current.Dewpoint" )
        self.WEATHER_WINDOW.clearProperty( "Current.Humidity" )
        self.WEATHER_WINDOW.clearProperty( "Current.Wind" )
	self.WEATHER_WINDOW.clearProperty( "Current.Condition" )
	self.WEATHER_WINDOW.clearProperty( "Current.Feelslike" )
	self.WEATHER_WINDOW.clearProperty( "Current.UVIndex" )

    def _clear_map_list( self, list_id ):
        # enumerate thru and clear all map list labels, icons and onclicks
        for count in range( 1, 31 ):
            # these are what the user sees and the action the button performs
            self.WEATHER_WINDOW.clearProperty( "MapList.%d.MapLabel.%d" % ( list_id, count, ) )
            self.WEATHER_WINDOW.clearProperty( "MapList.%d.MapLabel2.%d" % ( list_id, count, ) )
            self.WEATHER_WINDOW.clearProperty( "MapList.%d.MapIcon.%d" % ( list_id, count, ) )
            self.WEATHER_WINDOW.clearProperty( "MapList.%d.MapOnclick.%d" % ( list_id, count, ) )
        # set the default titles
        self._set_map_list_titles( list_id )

    def _set_map_list_titles( self, list_id, title=None, long_title=None ):
        # set map list titles for skinners buttons
        if ( title is None ):
            # non user defined list
            title = ( "", self._( 32800 + int( self.Settings.getSetting( "maplist%d" % ( list_id, ) ) ) ), )[ int( self.Settings.getSetting( "maplist%d" % ( list_id, ) ) ) > 0 ]
            long_title = self._( 32600 + int( self.Settings.getSetting( "maplist%d" % ( list_id, ) ) ) )
        # now set the titles
        self.WEATHER_WINDOW.setProperty( "MapList.%d.ShortTitle" % ( list_id, ), title )
        self.WEATHER_WINDOW.setProperty( "MapList.%d.LongTitle" % ( list_id, ), long_title )

    def _fetch_map_list( self ):
        # exit script if user changed locations
        if ( self.areacode != self.Settings.getSetting("code%s_%s" % ( self.locationindex, int(self.provider)+1 ))):
            return
        # intialize our download variable, we use this so we don't re-download same info
        map_download = []
        # enumerate thru and clear our properties if map is different (if user changed setiings), local and user defined list should be downloaded if location changed
        for count in range( 1, 4 ):
            # do we need to download this list?
            map_download += [ ( self.new_location and int( self.Settings.getSetting( "maplist%d" % ( count, ) ) ) == 1 ) or 
                                            ( self.new_location and int( self.Settings.getSetting( "maplist%d" % ( count, ) ) ) == len( self.WeatherClient.BASE_MAPS ) - 1 ) or 
                                            ( self.WEATHER_WINDOW.getProperty( "MapList.%d.LongTitle" % ( count, ) ) != self._( 32600 + int( self.Settings.getSetting( "maplist%d" % ( count, ) ) ) ) ) ]
            # do we need to clear the info?
            if ( map_download[ count - 1 ] ):
                self._clear_map_list( count )
        # we set this here in case we do not need to download new lists
        current_map = self.WEATHER_WINDOW.getProperty( "Weather.CurrentMapUrl" )
        current_map_title = self.WEATHER_WINDOW.getProperty( "Weather.CurrentMap" )
        printlog("Current Map : " + current_map)
        # only run if any new map lists
        if ( True ):
            # we set our maps path property to loading images while downloading
            self._set_maps_path()
            # set default map, we allow skinners to have users set this with a skin string
            # TODO: look at this, seems wrong, when changing locations maps can fail to load.
            default = ( self.WEATHER_WINDOW.getProperty( "Weather.CurrentMap" ), xbmc.getInfoLabel( "Skin.String(TWC.DefaultMap)" ), )[ xbmc.getInfoLabel( "Skin.String(TWC.DefaultMap)" ) != "" and self.WEATHER_WINDOW.getProperty( "Weather.CurrentMap" ) == "" ]
            # enumurate thru map lists and fetch map list
            for maplist_count in range( 1, 4 ):
                # only fetch new list if required
                # if ( not map_download[ maplist_count - 1 ] ):
                #     continue
                # get the correct category
		# print self.provider, maplist_count
		map_category = int( self.Settings.getSetting( "maplist%d" % ( maplist_count, ) ) )
                # fetch map list
                category_title, maps = self.WeatherClient.fetch_map_list( self.provider, map_category, self.Settings.getSetting( "maplist_user_file" ), xbmc.getInfoLabel( "Window(Weather).Property(LocationIndex)" ) )
                # print maps
                # only run if maps were found
                if ( maps is None ):
                    continue
                # set a current_map in case one isn't set
                if ( current_map == "" ):
                    try:
                       current_map = maps[ 0 ][ 0 ]
                       current_map_title = maps[ 0 ][ 1 ]
                    except:
                       print "ERROR : Failed Fatching Maps of Category No." + str( map_category )
                # if user defined map list set the new titles
                if ( category_title is not None ):
                    self._set_map_list_titles( maplist_count, category_title, category_title )
                # enumerate thru our map list and add map and title and check for default
                for count, map in enumerate( maps ):
                    # create our label, icon and onclick event
                    self.WEATHER_WINDOW.setProperty( "MapList.%d.MapLabel.%d" % ( maplist_count, count + 1, ), map[ 1 ] )
                    self.WEATHER_WINDOW.setProperty( "MapList.%d.MapLabel2.%d" % ( maplist_count, count + 1, ), map[ 0 ] )
                    self.WEATHER_WINDOW.setProperty( "MapList.%d.MapIcon.%d" % ( maplist_count, count + 1, ), map[ 1 ].replace( ":", " -" ).replace( "/", " - " ) + ".jpg" )
                    self.WEATHER_WINDOW.setProperty( "MapList.%d.MapOnclick.%d" % ( maplist_count, count + 1, ), "XBMC.RunScript(%s,map=%s&title=%s&location=%s)" % ( sys.argv[ 0 ], map[ 0 ], map[ 1 ], str( map[ 2 ] ) ) )
                    # if we have a match, set our class variable
                    if ( map[ 1 ] == default ):
                        current_map = map[ 0 ]
                        current_map_title = map[ 1 ]
        # fetch the current map
        self._fetch_map( current_map, current_map_title, self.locationindex )

    def _fetch_map( self, map, title, locationindex=None ):
        printlog("map = " + map)
        printlog("title = " + title)
        printlog("Locationindex = " + locationindex)
        printlog("maplist_user_file = " + self.Settings.getSetting("maplist_user_file"))
        # exit script if user changed locations
        #if ( self.areacode != xbmc.getInfoLabel( "Window(Weather).Property(Weather.AreaCode)" ) and self.areacode != self.Settings.getSetting("code%s_%s" % ( self.locationindex, int(self.provider)+1 ))):
        #    return
        # we set our maps path property to loading images while downloading
        self._set_maps_path()
        # we set Weather.CurrentMap and Weather.CurrentMapUrl, the skin can handle it when the user selects a new map for immediate update
        self.WEATHER_WINDOW.setProperty( "Weather.CurrentMap", title )
        self.WEATHER_WINDOW.setProperty( "Weather.CurrentMapUrl", map )
        # fetch the available map urls
        maps = self.WeatherClient.fetch_map_urls( map, self.Settings.getSetting( "maplist_user_file" ), locationindex, self.provider )
        # fetch the images
        maps_path, legend_path = self.WeatherClient.fetch_images( maps )
        # print "maps", maps
        # hack incase the weather in motion link was bogus
        if ( maps_path == "" and len( maps[ 1 ] ) ):
            maps_path, legend_path = self.WeatherClient.fetch_images( ( maps[ 0 ], [], maps[ 2 ], ) )
        # now set our window properties so multi image will display images 1==success, 2==failure
        self._set_maps_path( ( maps_path == "" ) + 1, maps_path, legend_path )

    def _set_alerts( self, alerts, alertsrss, alertsnotify, alertscolor, alertscount ):
	try:
		alertscolor = {"1":"red", "2":"orange"}.get(alertscolor)
	except:
		alertscolor = ""
        # send notification if user preference and there are alerts
        if ( alerts != "" and ( int( self.Settings.getSetting( "alert_notify_type" ) ) == 1 or 
            ( alertscolor == "red" and int( self.Settings.getSetting( "alert_notify_type" ) ) > 1 ) or 
            ( alertscolor == "orange" and int( self.Settings.getSetting( "alert_notify_type" ) ) == 3 ) ) and
            ( self.Settings.getSetting( "alert_notify_once" ) == "false" or self.WEATHER_WINDOW.getProperty( "Alerts.RSS" ) != alertsrss )
            ):
            xbmc.executebuiltin( "XBMC.Notification(%s,\"%s\",%d,weather.com plus/alert-%s.png)" % ( self._( 32100 ), alertsnotify, ( 10, 20, 30, 45, 60, 120, 300, 600, )[ int( self.Settings.getSetting( "alert_notify_time" ) ) ] * 1000, alertscolor, ) )
        # set any alerts
        self.WEATHER_WINDOW.setProperty( "Alerts", alerts )
        self.WEATHER_WINDOW.setProperty( "Alerts.RSS", alertsrss )
        self.WEATHER_WINDOW.setProperty( "Alerts.Color", ( "default", alertscolor, )[ alerts != "" ] )
        self.WEATHER_WINDOW.setProperty( "Alerts.Count", ( "", str( alertscount ), )[ alertscount > 1 ] )
        self.WEATHER_WINDOW.setProperty( "Alerts.Label", xbmc.getLocalizedString( 33049 + ( alertscount > 1 ) ) )

    def _set_video( self, video_url, video_title ):
	# print video_url
	if ( video_url[0] == "" ):
	        if ( video_url[1] == ""):
			self.WEATHER_WINDOW.setProperty( "Video", video_url[2] )
		else:
			self.WEATHER_WINDOW.setProperty( "Video", video_url[1] )
	else:
		self.WEATHER_WINDOW.setProperty( "Video", video_url[0] )

	self.WEATHER_WINDOW.setProperty( "Video.1", video_url[0] )	
	self.WEATHER_WINDOW.setProperty( "Video.1.Title", video_title[0] )
	self.WEATHER_WINDOW.setProperty( "Video.2", video_url[1] )	
	self.WEATHER_WINDOW.setProperty( "Video.2.Title", video_title[1] )
	self.WEATHER_WINDOW.setProperty( "Video.3", video_url[2] )	
	self.WEATHER_WINDOW.setProperty( "Video.3.Title", video_title[2] )
        # self.WEATHER_WINDOW.setProperty( "Video.regional", video_url )
	# self.WEATHER_WINDOW.setProperty( "Video.local", video_local_url )
	# print "[Weather Plus] Video_type = " + self.Settings.getSetting("video_type")
	# print "[Weather Plus] Video_url = " + video_url
	# print "[Weather Plus] Video_local_url = " + video_local_url
        printlog( "Video 1 = "+self.WEATHER_WINDOW.getProperty ("Video") )
        printlog( "Video 2 = "+self.WEATHER_WINDOW.getProperty ("Video.2") )
        printlog( "Video 3 = "+self.WEATHER_WINDOW.getProperty ("Video.3") )

    def _set_extra_current_info( self, extras ):
        if ( extras ):
            self.WEATHER_WINDOW.setProperty( "Current.Pressure", extras[ 0 ][0] )
            if ( extras[0][1] != "N/A" ) :
                try:
		     self.WEATHER_WINDOW.setProperty( "Current.Visibility", "%s %s" % ( extras[ 0 ][1].split( " " )[ 0 ], { "mile": self._( 32300 ), "miles": self._( 32301 ), "kilometer": self._( 32302 ), "kilometers": self._( 32303 ) }[ extras[ 0 ][1].split( " " )[ 1 ] ], ) )
		except:
		     self.WEATHER_WINDOW.setProperty( "Current.Visibility", extras[ 0 ][ 1 ])
	    else:
                self.WEATHER_WINDOW.setProperty( "Current.Visibility", extras[ 0 ][ 1 ])
            self.WEATHER_WINDOW.setProperty( "Current.Sunrise", extras[ 0 ][ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Current.Sunset", extras[ 0 ][ 3 ])
            # print self.WEATHER_WINDOW.getProperty( "Current.Pressure" )
        else:
            self.WEATHER_WINDOW.clearProperty( "Current.Pressure" )
            self.WEATHER_WINDOW.clearProperty( "Current.Visibility" )
            self.WEATHER_WINDOW.clearProperty( "Current.Sunrise" )
            self.WEATHER_WINDOW.clearProperty( "Current.Sunset" )

    def _fetch_36_forecast( self, showView=True ):
 	# fetch 36 hour forecast
        alerts, alertsrss, alertsnotify, alertscolor, alertscount, forecasts, extras, video, video_title = self.WeatherClient.fetch_36_forecast( self.WEATHER_WINDOW.getProperty( "Video" ) )
        # set any alerts
        self._set_alerts( alerts, alertsrss, alertsnotify, alertscolor, alertscount )
        # set video
        self._set_video( video, video_title )
	# set current info
	self.WEATHER_WINDOW.setProperty( "Current.Temperature", extras[0][4] )
	self.WEATHER_WINDOW.setProperty( "Current.FeelsLike", extras[0][5] )
	self.WEATHER_WINDOW.setProperty( "Current.ConditionIcon", extras[0][6] )
	self.WEATHER_WINDOW.setProperty( "Current.OutlookIcon", extras[0][6] )   # for new pre-eden compatability (XBMC copies outlookicon to conditionicon)
	self.WEATHER_WINDOW.setProperty( "Current.Condition", extras[0][7] )
	self.WEATHER_WINDOW.setProperty( "Current.Humidity", extras[0][8] )
	self.WEATHER_WINDOW.setProperty( "Current.DewPoint", extras[0][9] )
	self.WEATHER_WINDOW.setProperty( "Current.Wind", extras[0][10] )
	self.WEATHER_WINDOW.setProperty( "Current.UVIndex", extras[0][11] )
	# set extra info
        self._set_extra_current_info( extras )
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.OutlookIcon" % ( day + 1, ), forecast[ 1 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Outlook" % ( day + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureColor" % ( day + 1, ), forecast[ 3 ].lower() )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureHeading" % ( day + 1, ), ( xbmc.getLocalizedString( 393 ), xbmc.getLocalizedString( 391 ), )[ forecast[ 3 ] == "Low" ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Temperature" % ( day + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Precipitation" % ( day + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Forecast" % ( day + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTitle" % ( day + 1, ), forecast[ 8 ].replace( "Sunrise", xbmc.getLocalizedString( 33027 ) ).replace( "Sunset", xbmc.getLocalizedString( 33028 ) ) )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTime" % ( day + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightType" % ( day + 1, ), ( "sunrise", "sunset", )[ forecast[ 8 ] == "Sunset" ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Heading" % ( day + 1, ), { "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "Tomorrow": xbmc.getLocalizedString( 33007 ), "Tomorrow Night": xbmc.getLocalizedString( 33019 ) }[ forecast[ 0 ] ] )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "36Hour.IsFetched", "true" )

    def _fetch_hourly_forecast( self ):
        # fetch hourly forecast
        forecasts = self.WeatherClient.fetch_hourly_forecast()
        # localized long and short date dictionary
        longdate_dict = { "January": xbmc.getLocalizedString( 21 ), "February": xbmc.getLocalizedString( 22 ), "March": xbmc.getLocalizedString( 23 ), "April": xbmc.getLocalizedString( 24 ), "May": xbmc.getLocalizedString( 25 ), "June": xbmc.getLocalizedString( 26 ), "July": xbmc.getLocalizedString( 27 ), "August": xbmc.getLocalizedString( 28 ), "September": xbmc.getLocalizedString( 29 ), "October": xbmc.getLocalizedString( 30 ), "November": xbmc.getLocalizedString( 31 ), "December": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "January": xbmc.getLocalizedString( 51 ), "February": xbmc.getLocalizedString( 52 ), "March": xbmc.getLocalizedString( 53 ), "April": xbmc.getLocalizedString( 54 ), "May": xbmc.getLocalizedString( 55 ), "June": xbmc.getLocalizedString( 56 ), "July": xbmc.getLocalizedString( 57 ), "August": xbmc.getLocalizedString( 58 ), "September": xbmc.getLocalizedString( 59 ), "October": xbmc.getLocalizedString( 60 ), "November": xbmc.getLocalizedString( 61 ), "December": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            # set properties
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Time" % ( count + 1, ), forecast[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict.get( forecast[ 1 ].split( " " )[ 0 ], "" ), forecast[ 1 ].split( " " )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict.get( forecast[ 1 ].split( " " )[ 0 ], "" ), forecast[ 1 ].split( " " )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Temperature" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Outlook" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FeelsLike" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Humidity" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindDirection" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindSpeed" % ( count + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortWindDirection" % ( count + 1, ), forecast[ 10 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunrise" % ( count + 1, ), forecast[ 11 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunset" % ( count + 1, ), forecast[ 12 ] )
        # enumerate thru and clear all hourly times
        for count in range( len( forecasts ), 12 ):
            # clear any remaining hourly times as some locals do not have all of them
            self.WEATHER_WINDOW.clearProperty( "Hourly.%d.Time" % ( count + 1, ) )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Hourly.IsFetched", "true" )

    def _fetch_weekend_forecast( self ):
        # fetch weekend forecast
        forecasts = self.WeatherClient.fetch_weekend_forecast()
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.OutlookIcon" % ( day + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Outlook" % ( day + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.HighTemperature" % ( day + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.LowTemperature" % ( day + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Precipitation" % ( day + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Wind" % ( day + 1, ), forecast[ 11 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.UV" % ( day + 1, ), forecast[ 13 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Humidity" % ( day + 1, ), forecast[ 15 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunrise" % ( day + 1, ), forecast[ 17 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunset" % ( day + 1, ), forecast[ 19 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Forecast" % ( day + 1, ), forecast[ 20 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Observed" % ( day + 1, ), forecast[ 21 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedPrecipitation" % ( day + 1, ), forecast[ 23 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( day + 1, ), forecast[ 25 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( day + 1, ), forecast[ 27 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( day + 1, ), forecast[ 29 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( day + 1, ), forecast[ 31 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHigh" % ( day + 1, ), forecast[ 33 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHighColor" % ( day + 1, ), ( "low", "high", "default", )[ ( len( forecast[ 33 ] ) and forecast[ 33 ][ 0 ] == "+" ) + ( forecast[ 33 ] == "+0" ) ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLow" % ( day + 1, ), forecast[ 34 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLowColor" % ( day + 1, ), ( "low", "high", "default", )[ ( len( forecast[ 34 ] ) and forecast[ 34 ][ 0 ] == "+" ) + ( forecast[ 34 ] == "+0" ) ] )
            # do this last so skin's visibilty works better
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Date" % ( day + 1, ), forecast[ 1 ] )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Weekend.IsFetched", "true" )

    def _fetch_10day_forecast( self ):
        # fetch daily forecast
        forecasts = self.WeatherClient.fetch_10day_forecast()
        # localized long and short day dictionary
        longday_dict = { "Mon": xbmc.getLocalizedString( 11 ), "Tue": xbmc.getLocalizedString( 12 ), "Wed": xbmc.getLocalizedString( 13 ), "Thu": xbmc.getLocalizedString( 14 ), "Fri": xbmc.getLocalizedString( 15 ), "Sat": xbmc.getLocalizedString( 16 ), "Sun": xbmc.getLocalizedString( 17 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "N/A": "N/A" }
        shortday_dict = { "Mon": xbmc.getLocalizedString( 41 ), "Tue": xbmc.getLocalizedString( 42 ), "Wed": xbmc.getLocalizedString( 43 ), "Thu": xbmc.getLocalizedString( 44 ), "Fri": xbmc.getLocalizedString( 45 ), "Sat": xbmc.getLocalizedString( 46 ), "Sun": xbmc.getLocalizedString( 47 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "N/A": "N/A" }
        # localized long and short date dictionary
        longdate_dict = { "Jan": xbmc.getLocalizedString( 21 ), "Feb": xbmc.getLocalizedString( 22 ), "Mar": xbmc.getLocalizedString( 23 ), "Apr": xbmc.getLocalizedString( 24 ), "May": xbmc.getLocalizedString( 25 ), "Jun": xbmc.getLocalizedString( 26 ), "Jul": xbmc.getLocalizedString( 27 ), "Aug": xbmc.getLocalizedString( 28 ), "Sep": xbmc.getLocalizedString( 29 ), "Oct": xbmc.getLocalizedString( 30 ), "Nov": xbmc.getLocalizedString( 31 ), "Dec": xbmc.getLocalizedString( 32 ), "N/A": "" }
        shortdate_dict = { "Jan": xbmc.getLocalizedString( 51 ), "Feb": xbmc.getLocalizedString( 52 ), "Mar": xbmc.getLocalizedString( 53 ), "Apr": xbmc.getLocalizedString( 54 ), "May": xbmc.getLocalizedString( 55 ), "Jun": xbmc.getLocalizedString( 56 ), "Jul": xbmc.getLocalizedString( 57 ), "Aug": xbmc.getLocalizedString( 58 ), "Sep": xbmc.getLocalizedString( 59 ), "Oct": xbmc.getLocalizedString( 60 ), "Nov": xbmc.getLocalizedString( 61 ), "Dec": xbmc.getLocalizedString( 62 ), "N/A": "" }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( count + 1, ), longday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( count + 1, ), shortday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( count + 1, ), forecast[ 9 ] )
        # just in case day 10 is missing
        for count in range( len( forecasts ), 10 ):
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDay" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDay" % ( count + 1, ) )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Daily.IsFetched", "true" )
	
    def _accu_36_forecast( self ):
        # fetch 36 hour forecast
        try:
            alerts, alertsrss, alertsnotify, alertscolor, alertscount, forecasts, extras, video, video_local = self.WeatherClient.accu_36_forecast("")
	except:
	    return
	# set current info
	self.WEATHER_WINDOW.setProperty( "Current.Temperature", extras[0][4] )
	self.WEATHER_WINDOW.setProperty( "Current.FeelsLike", extras[0][5] )
	self.WEATHER_WINDOW.setProperty( "Current.Condition", extras[0][6] )
	self.WEATHER_WINDOW.setProperty( "Current.Wind", extras[0][7] )
	self.WEATHER_WINDOW.setProperty( "Current.WindDirection", extras[0][11] )
	self.WEATHER_WINDOW.setProperty( "Current.Humidity", extras[0][8] + "%" )
	self.WEATHER_WINDOW.setProperty( "Current.DewPoint", extras[0][9] )
	self.WEATHER_WINDOW.setProperty( "Current.UVIndex", "" )
	self.WEATHER_WINDOW.setProperty( "Current.ConditionIcon", extras[0][10] )
	self.WEATHER_WINDOW.setProperty( "Current.OutlookIcon", extras[0][10] )   # for new pre-eden compatability (XBMC copies outlookicon to conditionicon)
	self.WEATHER_WINDOW.setProperty( "Current.FanartCode", os.path.splitext( os.path.basename( extras[0][10] ) )[ 0 ] )

        # set any alerts
        self._set_alerts( alerts, alertsrss, alertsnotify, alertscolor, alertscount )
        # set video
        self._set_video( video, video_local )
        # set extra info
        self._set_extra_current_info( extras )
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.OutlookIcon" % ( day + 1, ), forecast[ 1 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Outlook" % ( day + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureColor" % ( day + 1, ), forecast[ 3 ].lower() )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureHeading" % ( day + 1, ), ( xbmc.getLocalizedString( 393 ), xbmc.getLocalizedString( 391 ), )[ forecast[ 3 ] == "Low" ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Temperature" % ( day + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Precipitation" % ( day + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Forecast" % ( day + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTitle" % ( day + 1, ), forecast[ 8 ].replace( "Sunrise", xbmc.getLocalizedString( 33027 ) ).replace( "Sunset", xbmc.getLocalizedString( 33028 ) ) )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTime" % ( day + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightType" % ( day + 1, ), ( "sunrise", "sunset", )[ forecast[ 8 ] == "Sunset" ] )
            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Heading" % ( day + 1, ), { "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "Tomorrow": xbmc.getLocalizedString( 33007 ), "Tomorrow Night": xbmc.getLocalizedString( 33019 ) }[ forecast[ 0 ] ] )
        # use this to hide info until fully fetched
	printlog( "Setting 36 Hour Properties... Done!" )
        self.WEATHER_WINDOW.setProperty( "36Hour.IsFetched", "true" )

    def _accu_hourly_forecast( self ):
        # fetch hourly forecast
        forecasts = self.WeatherClient.accu_fetch_hourly_forecast()
        # localized long and short date dictionary
        longdate_dict = { "1": xbmc.getLocalizedString( 21 ), "2": xbmc.getLocalizedString( 22 ), "3": xbmc.getLocalizedString( 23 ), "4": xbmc.getLocalizedString( 24 ), "5": xbmc.getLocalizedString( 25 ), "6": xbmc.getLocalizedString( 26 ), "7": xbmc.getLocalizedString( 27 ), "8": xbmc.getLocalizedString( 28 ), "9": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "1": xbmc.getLocalizedString( 51 ), "2": xbmc.getLocalizedString( 52 ), "3": xbmc.getLocalizedString( 53 ), "4": xbmc.getLocalizedString( 54 ), "5": xbmc.getLocalizedString( 55 ), "6": xbmc.getLocalizedString( 56 ), "7": xbmc.getLocalizedString( 57 ), "8": xbmc.getLocalizedString( 58 ), "9": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            # set properties
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Time" % ( count + 1, ), forecast[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict.get( forecast[ 1 ].split( " " )[ 0 ], "" ), forecast[ 1 ].split( " " )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict.get( forecast[ 1 ].split( " " )[ 0 ], "" ), forecast[ 1 ].split( " " )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Temperature" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Outlook" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FeelsLike" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Humidity" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindDirection" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindSpeed" % ( count + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortWindDirection" % ( count + 1, ), forecast[ 10 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunrise" % ( count + 1, ), forecast[ 11 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunset" % ( count + 1, ), forecast[ 12 ] )
        # enumerate thru and clear all hourly times
        for count in range( len( forecasts ), 12 ):
            # clear any remaining hourly times as some locals do not have all of them
            self.WEATHER_WINDOW.clearProperty( "Hourly.%d.Time" % ( count + 1, ) )
        # use this to hide info until fully fetched
	printlog( "Setting Hourly Properties... Done!" )
        self.WEATHER_WINDOW.setProperty( "Hourly.IsFetched", "true" )

    def _accu_weekend_forecast( self ):
        # fetch weekend forecast
        forecasts = self.WeatherClient.accu_weekend_forecast()
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.OutlookIcon" % ( day + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Outlook" % ( day + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.HighTemperature" % ( day + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.LowTemperature" % ( day + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Precipitation" % ( day + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Wind" % ( day + 1, ), forecast[ 11 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.UV" % ( day + 1, ), forecast[ 13 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Humidity" % ( day + 1, ), forecast[ 15 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunrise" % ( day + 1, ), forecast[ 17 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunset" % ( day + 1, ), forecast[ 19 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Forecast" % ( day + 1, ), forecast[ 20 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Observed" % ( day + 1, ), forecast[ 21 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedPrecipitation" % ( day + 1, ), forecast[ 23 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( day + 1, ), forecast[ 25 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( day + 1, ), forecast[ 27 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( day + 1, ), forecast[ 29 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( day + 1, ), forecast[ 31 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHigh" % ( day + 1, ), forecast[ 33 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHighColor" % ( day + 1, ), ( "low", "high", "default", )[ ( len( forecast[ 33 ] ) and forecast[ 33 ][ 0 ] == "+" ) + ( forecast[ 33 ] == "+0" ) ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLow" % ( day + 1, ), forecast[ 34 ] )
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLowColor" % ( day + 1, ), ( "low", "high", "default", )[ ( len( forecast[ 34 ] ) and forecast[ 34 ][ 0 ] == "+" ) + ( forecast[ 34 ] == "+0" ) ] )
            # do this last so skin's visibilty works better
            self.WEATHER_WINDOW.setProperty( "Weekend.%d.Date" % ( day + 1, ), forecast[ 1 ] )
        # use this to hide info until fully fetched
	printlog( "Setting Weekend Properties... Done!" )
        self.WEATHER_WINDOW.setProperty( "Weekend.IsFetched", "true" )

    def _accu_10day_forecast( self ):
        # fetch daily forecast
        forecasts = self.WeatherClient.accu_fetch_10day_forecast()
        # localized long and short day dictionary
        longday_dict = { "Monday": xbmc.getLocalizedString( 11 ), "Tuesday": xbmc.getLocalizedString( 12 ), "Wednesday": xbmc.getLocalizedString( 13 ), "Thursday": xbmc.getLocalizedString( 14 ), "Friday": xbmc.getLocalizedString( 15 ), "Saturday": xbmc.getLocalizedString( 16 ), "Sunday": xbmc.getLocalizedString( 17 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        shortday_dict = { "Monday": xbmc.getLocalizedString( 41 ), "Tuesday": xbmc.getLocalizedString( 42 ), "Wednesday": xbmc.getLocalizedString( 43 ), "Thursday": xbmc.getLocalizedString( 44 ), "Friday": xbmc.getLocalizedString( 45 ), "Saturday": xbmc.getLocalizedString( 46 ), "Sunday": xbmc.getLocalizedString( 47 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        # localized long and short date dictionary
        longdate_dict = { "1": xbmc.getLocalizedString( 21 ), "2": xbmc.getLocalizedString( 22 ), "3": xbmc.getLocalizedString( 23 ), "4": xbmc.getLocalizedString( 24 ), "5": xbmc.getLocalizedString( 25 ), "6": xbmc.getLocalizedString( 26 ), "7": xbmc.getLocalizedString( 27 ), "8": xbmc.getLocalizedString( 28 ), "9": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "1": xbmc.getLocalizedString( 51 ), "2": xbmc.getLocalizedString( 52 ), "3": xbmc.getLocalizedString( 53 ), "4": xbmc.getLocalizedString( 54 ), "5": xbmc.getLocalizedString( 55 ), "6": xbmc.getLocalizedString( 56 ), "7": xbmc.getLocalizedString( 57 ), "8": xbmc.getLocalizedString( 58 ), "9": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
	weekend_count = 0
	weekend = 0
	for count in range(1,4):
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.OutlookIcon" % ( count, ) )
	        self.WEATHER_WINDOW.clearProperty( "Weekend.%d.FanartCode" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Outlook" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.HighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.LowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Precipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Wind" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.UV" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Humidity" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunrise" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunset" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Forecast" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Observed" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedPrecipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHigh" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHighColor" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLow" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLowColor" % ( count, ) )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Date" % ( count, ) )
        for count, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( count + 1, ), longday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( count + 1, ), shortday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( count + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( count + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( count + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( count + 1, ), "" )
	    # weekend info
	    if ( forecast[ 0 ] == "Friday" and weekend_count == 0 ):
		weekend = 1
            elif ( forecast[ 0 ] == "Saturday" and weekend_count < 2 ):
		weekend = 2
	    elif ( forecast[ 0 ] == "Sunday" ):
		weekend = 3
	    if ( weekend != 0 and weekend_count != 100 ):
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.OutlookIcon" % ( weekend, ), forecast[ 2 ] )
	        self.WEATHER_WINDOW.setProperty( "Weekend.%d.FanartCode" % ( weekend, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Outlook" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.HighTemperature" % ( weekend, ), forecast[ 4 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.LowTemperature" % ( weekend, ), forecast[ 5 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Precipitation" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Wind" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.UV" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Humidity" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunrise" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunset" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Forecast" % ( weekend, ), forecast[ 3 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Observed" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedPrecipitation" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHigh" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHighColor" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLow" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLowColor" % ( weekend, ), "" )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Date" % ( weekend, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
		if ( weekend != 3 ):
			weekend_count += 1
		else:
			weekend_count = 100
	    weekend = 0
        # just in case day 10 is missing
        for count in range( len( forecasts ), 10 ):
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDate" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDate" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.OutlookIcon" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.Outlook" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.HighTemperature" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.LowTemperature" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.Precipitation" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.WindSpeed" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.WindDirection" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDay" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDay" % ( count + 1, ) )
        # use this to hide info until fully fetched
	printlog( "Setting 10 day & Weekend Properties... Done!" )
        self.WEATHER_WINDOW.setProperty( "Daily.IsFetched", "true" )
	self.WEATHER_WINDOW.setProperty( "Weekend.IsFetched", "true" )

    def _noaa_36_forecast( self ):
        # fetch 36 hour forecast
        try:
		alerts, alertsrss, alertsnotify, alertscolor, alertscount, forecasts, extras, video, video_local = self.WeatherClient.noaa_36_forecast()
	except:
		return
	# set current info
	print extras
	self.WEATHER_WINDOW.setProperty( "Current.Temperature", extras[0][4] )
	self.WEATHER_WINDOW.setProperty( "Current.FeelsLike", extras[0][5] )
	self.WEATHER_WINDOW.setProperty( "Current.Condition", extras[0][6] )
	self.WEATHER_WINDOW.setProperty( "Current.FanartCode", os.path.splitext( os.path.basename( extras[0][10] ) )[ 0 ] )
	self.WEATHER_WINDOW.setProperty( "Current.Wind", extras[0][7] )
	self.WEATHER_WINDOW.setProperty( "Current.WindDirection", extras[0][11])
	self.WEATHER_WINDOW.setProperty( "Current.Humidity", extras[0][8] + "%" )
	self.WEATHER_WINDOW.setProperty( "Current.DewPoint", extras[0][9] )
	self.WEATHER_WINDOW.setProperty( "Current.UVIndex", "N/A" )
	self.WEATHER_WINDOW.setProperty( "Current.ConditionIcon", extras[0][10] )
	self.WEATHER_WINDOW.setProperty( "Current.OutlookIcon", extras[0][10] )   # for new pre-eden compatability (XBMC copies outlookicon to conditionicon)
        # set any alerts
        self._set_alerts( alerts, alertsrss, alertsnotify, alertscolor, alertscount )
        # set video
        self._set_video( video, video_local )
        # set extra info
        self._set_extra_current_info( extras )
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
	    if ( day < 3 ):
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.OutlookIcon" % ( day + 1, ), forecast[ 1 ] )
		    self.WEATHER_WINDOW.setProperty( "36Hour.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Outlook" % ( day + 1, ), forecast[ 2 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureColor" % ( day + 1, ), forecast[ 3 ].lower() )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureHeading" % ( day + 1, ), ( xbmc.getLocalizedString( 393 ), xbmc.getLocalizedString( 391 ), )[ forecast[ 3 ] == "Low" ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Temperature" % ( day + 1, ), forecast[ 4 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Precipitation" % ( day + 1, ), forecast[ 6 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Forecast" % ( day + 1, ), forecast[ 7 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTitle" % ( day + 1, ), forecast[ 8 ].replace( "Sunrise", xbmc.getLocalizedString( 33027 ) ).replace( "Sunset", xbmc.getLocalizedString( 33028 ) ) )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTime" % ( day + 1, ), forecast[ 9 ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightType" % ( day + 1, ), ( "sunrise", "sunset", )[ forecast[ 8 ] == "Sunset" ] )
	            self.WEATHER_WINDOW.setProperty( "36Hour.%d.Heading" % ( day + 1, ), { "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "Tomorrow": xbmc.getLocalizedString( 33007 ), "Tomorrow Night": xbmc.getLocalizedString( 33019 ) }[ forecast[ 0 ] ] )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "36Hour.IsFetched", "true" )
	
	# localized long and short day dictionary
        longday_dict = { "Monday": xbmc.getLocalizedString( 11 ), "Tuesday": xbmc.getLocalizedString( 12 ), "Wednesday": xbmc.getLocalizedString( 13 ), "Thursday": xbmc.getLocalizedString( 14 ), "Friday": xbmc.getLocalizedString( 15 ), "Saturday": xbmc.getLocalizedString( 16 ), "Sunday": xbmc.getLocalizedString( 17 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        shortday_dict = { "Monday": xbmc.getLocalizedString( 41 ), "Tuesday": xbmc.getLocalizedString( 42 ), "Wednesday": xbmc.getLocalizedString( 43 ), "Thursday": xbmc.getLocalizedString( 44 ), "Friday": xbmc.getLocalizedString( 45 ), "Saturday": xbmc.getLocalizedString( 46 ), "Sunday": xbmc.getLocalizedString( 47 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        # localized long and short date dictionary
        longdate_dict = { "1": xbmc.getLocalizedString( 21 ), "2": xbmc.getLocalizedString( 22 ), "3": xbmc.getLocalizedString( 23 ), "4": xbmc.getLocalizedString( 24 ), "5": xbmc.getLocalizedString( 25 ), "6": xbmc.getLocalizedString( 26 ), "7": xbmc.getLocalizedString( 27 ), "8": xbmc.getLocalizedString( 28 ), "9": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "1": xbmc.getLocalizedString( 51 ), "2": xbmc.getLocalizedString( 52 ), "3": xbmc.getLocalizedString( 53 ), "4": xbmc.getLocalizedString( 54 ), "5": xbmc.getLocalizedString( 55 ), "6": xbmc.getLocalizedString( 56 ), "7": xbmc.getLocalizedString( 57 ), "8": xbmc.getLocalizedString( 58 ), "9": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
	for count in range(0, 11):
	        self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDay" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDay" % ( count ) )
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDate" % ( count ) )
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDate" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.OutlookIcon" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.FanartCode" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.Outlook" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.Precipitation" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.WindDirection" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.WindSpeed" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortWindDirection" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.HighTemperature" % ( count ))
		self.WEATHER_WINDOW.clearProperty( "Daily.%d.LowTemperature" % ( count ))

	ampm = 0
        for count, forecast in enumerate( forecasts ):
	    # print re.findall( "Night", forecast[ 10 ] )
	    if ( forecast[ 0 ] == "Tonight" and count == 0 ):
	 	self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( int( ( count + 1 + ampm )/2 ) + 1, ), longday_dict.get( forecast[ 10 ], forecast[ 10 ] ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( int( ( count + 1 + ampm )/2 ) + 1, ), shortday_dict.get( forecast[ 10 ], forecast[ 10 ][:5]+"." ) )		
		self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( int( ( count + 1 + ampm )/2 ) + 1, ), "%s %s" % ( longdate_dict[ forecast[ 11 ].split( " " )[ 1 ] ], forecast[ 11 ].split( " " )[ 0 ], ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( int( ( count + 1 + ampm )/2 ) + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 11 ].split( " " )[ 1 ] ], forecast[ 11 ].split( " " )[ 0 ], ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 1 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( int( ( count + 1 + ampm )/2 ) + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 2 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 6 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 12 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 13 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast [ 14 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( 1 ), "N/A" )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( 1 ), forecast[ 4 ] )
		ampm = 1
	    elif ( re.findall( "Night", forecast[ 10 ] ) == [] and forecast[ 10 ] != "Tonight" ):
		# print int( ( count + 1 + ampm )/2 ) + 1
		# print forecast
	 	self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( int( ( count + 1 + ampm )/2 ) + 1, ), longday_dict.get( forecast[ 10 ], forecast[ 10 ] ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( int( ( count + 1 + ampm )/2 ) + 1, ), shortday_dict.get( forecast[ 10 ], forecast[ 10 ][:5]+"." ) )		
		self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( int( ( count + 1 + ampm )/2 ) + 1, ), "%s %s" % ( longdate_dict[ forecast[ 11 ].split( " " )[ 1 ] ], forecast[ 11 ].split( " " )[ 0 ], ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( int( ( count + 1 + ampm )/2 ) + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 11 ].split( " " )[ 1 ] ], forecast[ 11 ].split( " " )[ 0 ], ) )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 1 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( int( ( count + 1 + ampm )/2 ) + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 2 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 4 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 6 ] )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 12 ] )
		if ( forecast[ 12 ] != "N/A" ):		
			self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast[ 13 ] )
		else:
			self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( int( ( count + 1 + ampm )/2 ) + 1, ), "N/A" )
		self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( int( ( count + 1 + ampm )/2 ) + 1, ), forecast [ 14 ] )
	    else:
		self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( int( ( count + 1 + ampm )/2 ) ), forecast[ 4 ] )	
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Daily.IsFetched", "true" )
	self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( int( ( count + 1 + ampm )/2 ) + 1 ), "N/A" )

    def _noaa_hourly_forecast( self ):
        # fetch hourly forecast
        forecasts = self.WeatherClient.noaa_fetch_hourly_forecast()
        # localized long and short date dictionary
        longdate_dict = { "01": xbmc.getLocalizedString( 21 ), "02": xbmc.getLocalizedString( 22 ), "03": xbmc.getLocalizedString( 23 ), "04": xbmc.getLocalizedString( 24 ), "05": xbmc.getLocalizedString( 25 ), "06": xbmc.getLocalizedString( 26 ), "07": xbmc.getLocalizedString( 27 ), "08": xbmc.getLocalizedString( 28 ), "09": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "01": xbmc.getLocalizedString( 51 ), "02": xbmc.getLocalizedString( 52 ), "03": xbmc.getLocalizedString( 53 ), "04": xbmc.getLocalizedString( 54 ), "05": xbmc.getLocalizedString( 55 ), "06": xbmc.getLocalizedString( 56 ), "07": xbmc.getLocalizedString( 57 ), "08": xbmc.getLocalizedString( 58 ), "09": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            # set properties
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Time" % ( count + 1, ), forecast[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict.get( forecast[ 1 ].split( "/" )[ 0 ], "" ), forecast[ 1 ].split( "/" )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict.get( forecast[ 1 ].split( "/" )[ 0 ], "" ), forecast[ 1 ].split( "/" )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Temperature" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Outlook" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FeelsLike" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Humidity" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindDirection" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindSpeed" % ( count + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortWindDirection" % ( count + 1, ), forecast[ 10 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunrise" % ( count + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunset" % ( count + 1, ), "" )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Hourly.IsFetched", "true" )

    def _noaa_weekend_forecast( self ):
        # exit script if user changed locations
	if ( self.areacode != self.Settings.getSetting("code%s_%s" % ( self.locationindex, int(self.provider)+1 ) ) ): return    
        # fetch weekend forecast
        # forecasts = self.WeatherClient.accu_weekend_forecast()
        # clear the info
	for count in range(1,4):
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.OutlookIcon" % ( count, ) )
	        self.WEATHER_WINDOW.clearProperty( "Weekend.%d.FanartCode" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Outlook" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.HighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.LowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Precipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Wind" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.UV" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Humidity" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunrise" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunset" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Forecast" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Observed" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedPrecipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHigh" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHighColor" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLow" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLowColor" % ( count, ) )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Date" % ( count, ) )
		# print self.WEATHER_WINDOW.getProperty( "Weekend.1.OutlookIcon" )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Weekend.IsFetched", "true" )

    def _noaa_10day_forecast( self ):
        # fetch daily forecast
        forecasts = self.WeatherClient.accu_fetch_10day_forecast()
	print forecasts
        # localized long and short day dictionary
        longday_dict = { "Monday": xbmc.getLocalizedString( 11 ), "Tuesday": xbmc.getLocalizedString( 12 ), "Wednesday": xbmc.getLocalizedString( 13 ), "Thursday": xbmc.getLocalizedString( 14 ), "Friday": xbmc.getLocalizedString( 15 ), "Saturday": xbmc.getLocalizedString( 16 ), "Sunday": xbmc.getLocalizedString( 17 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        shortday_dict = { "Monday": xbmc.getLocalizedString( 41 ), "Tuesday": xbmc.getLocalizedString( 42 ), "Wednesday": xbmc.getLocalizedString( 43 ), "Thursday": xbmc.getLocalizedString( 44 ), "Friday": xbmc.getLocalizedString( 45 ), "Saturday": xbmc.getLocalizedString( 46 ), "Sunday": xbmc.getLocalizedString( 47 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ) }
        # localized long and short date dictionary
        longdate_dict = { "1": xbmc.getLocalizedString( 21 ), "2": xbmc.getLocalizedString( 22 ), "3": xbmc.getLocalizedString( 23 ), "4": xbmc.getLocalizedString( 24 ), "5": xbmc.getLocalizedString( 25 ), "6": xbmc.getLocalizedString( 26 ), "7": xbmc.getLocalizedString( 27 ), "8": xbmc.getLocalizedString( 28 ), "9": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "1": xbmc.getLocalizedString( 51 ), "2": xbmc.getLocalizedString( 52 ), "3": xbmc.getLocalizedString( 53 ), "4": xbmc.getLocalizedString( 54 ), "5": xbmc.getLocalizedString( 55 ), "6": xbmc.getLocalizedString( 56 ), "7": xbmc.getLocalizedString( 57 ), "8": xbmc.getLocalizedString( 58 ), "9": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
	weekend_count = 0
	weekend = 0
	for count in range(1,3):
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.OutlookIcon" % ( count, ) )
	        self.WEATHER_WINDOW.clearProperty( "Weekend.%d.FanartCode" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Outlook" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.HighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.LowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Precipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Wind" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.UV" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Humidity" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunrise" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunset" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Forecast" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Observed" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedPrecipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHigh" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHighColor" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLow" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLowColor" % ( count, ) )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Date" % ( count, ) )
        for count, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( count + 1, ), longday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( count + 1, ), shortday_dict[ forecast[ 0 ] ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( count + 1, ), forecast[ 9 ] )
	    # weekend info
	    if ( forecast[ 0 ] == "Friday" and weekend_count == 0 ):
		weekend = 1
            elif ( forecast[ 0 ] == "Saturday" and weekend_count < 2 ):
		weekend = 2
	    elif ( forecast[ 0 ] == "Sunday" ):
		weekend = 3
	    if ( weekend != 0 and weekend_count != 100 ):
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.OutlookIcon" % ( weekend, ), forecast[ 2 ] )
	        self.WEATHER_WINDOW.setProperty( "Weekend.%d.FanartCode" % ( weekend, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Outlook" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.HighTemperature" % ( weekend, ), forecast[ 4 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.LowTemperature" % ( weekend, ), forecast[ 5 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Precipitation" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Wind" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.UV" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Humidity" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunrise" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Sunset" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Forecast" % ( weekend, ), forecast[ 3 ] )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Observed" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedPrecipitation" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHigh" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureHighColor" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLow" % ( weekend, ), "" )
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.DepartureLowColor" % ( weekend, ), "" )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.setProperty( "Weekend.%d.Date" % ( weekend, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( "/" )[ 0 ] ], forecast[ 1 ].split( "/" )[ 1 ], ) )
		if ( weekend != 3 ):
			weekend_count += 1
		else:
			weekend_count = 100
	    weekend = 0
        # just in case day 10 is missing
        for count in range( len( forecasts ), 10 ):
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.ShortDay" % ( count + 1, ) )
            self.WEATHER_WINDOW.clearProperty( "Daily.%d.LongDay" % ( count + 1, ) )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Daily.IsFetched", "true" )

    def _wunder_36_forecast( self ):
        # fetch 36 hour forecast
	try:
		alerts, alertsrss, alertsnotify, alertscolor, alertscount, forecasts, extras, video, video_local = self.WeatherClient.wunder_36_forecast("")
	except:
		return
	# set current info
	self.WEATHER_WINDOW.setProperty( "Current.Temperature", extras[0][4] )
	self.WEATHER_WINDOW.setProperty( "Current.FeelsLike", extras[0][5] )
	self.WEATHER_WINDOW.setProperty( "Current.Condition", extras[0][6] )
	self.WEATHER_WINDOW.setProperty( "Current.FanartCode", os.path.splitext( os.path.basename( extras[0][10] ) )[ 0 ] )
	self.WEATHER_WINDOW.setProperty( "Current.Wind", extras[0][7] )
	self.WEATHER_WINDOW.setProperty( "Current.Humidity", extras[0][8] + "%" )
	self.WEATHER_WINDOW.setProperty( "Current.DewPoint", extras[0][9] )
	self.WEATHER_WINDOW.setProperty( "Current.UVIndex", extras[0][11] )
	self.WEATHER_WINDOW.setProperty( "Current.ConditionIcon", extras[0][10] )	
	self.WEATHER_WINDOW.setProperty( "Current.OutlookIcon", extras[0][10] )   # for new pre-eden compatability (XBMC copies outlookicon to conditionicon)
        # set any alerts
        self._set_alerts( alerts, alertsrss, alertsnotify, alertscolor, alertscount )
        # set video
        self._set_video( video, video_local )
        # set extra info
        self._set_extra_current_info( extras )
        # enumerate thru and set the info
        for day, forecast in enumerate( forecasts ):
		# print forecast
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.OutlookIcon" % ( day + 1, ), forecast[ 1 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.FanartCode" % ( day + 1, ), os.path.splitext( os.path.basename( forecast[ 1 ] ) )[ 0 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.Outlook" % ( day + 1, ), forecast[ 2 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureColor" % ( day + 1, ), forecast[ 3 ].lower() )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.TemperatureHeading" % ( day + 1, ), ( xbmc.getLocalizedString( 393 ), xbmc.getLocalizedString( 391 ), )[ forecast[ 3 ] == "Low" ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.Temperature" % ( day + 1, ), forecast[ 4 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.Precipitation" % ( day + 1, ), forecast[ 6 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.Forecast" % ( day + 1, ), forecast[ 7 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTitle" % ( day + 1, ), forecast[ 8 ].replace( "Sunrise", xbmc.getLocalizedString( 33027 ) ).replace( "Sunset", xbmc.getLocalizedString( 33028 ) ) )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightTime" % ( day + 1, ), forecast[ 9 ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.DaylightType" % ( day + 1, ), ( "sunrise", "sunset", )[ forecast[ 8 ] == "Sunset" ] )
		self.WEATHER_WINDOW.setProperty( "36Hour.%d.Heading" % ( day + 1, ), { "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "Tomorrow": xbmc.getLocalizedString( 33007 ), "Tomorrow Night": xbmc.getLocalizedString( 33019 ) }[ forecast[ 0 ] ] )
	for count in range(1,4):
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.OutlookIcon" % ( count, ) )
	        self.WEATHER_WINDOW.clearProperty( "Weekend.%d.FanartCode" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Outlook" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.HighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.LowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Precipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Wind" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.UV" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Humidity" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunrise" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Sunset" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Forecast" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Observed" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedPrecipitation" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedAvgLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordHighTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.ObservedRecordLowTemperature" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHigh" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureHighColor" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLow" % ( count, ) )
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.DepartureLowColor" % ( count, ) )
		# do this last so skin's visibilty works better
		self.WEATHER_WINDOW.clearProperty( "Weekend.%d.Date" % ( count, ) )

        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "36Hour.IsFetched", "true" )

    def _wunder_10day_forecast( self ):
        # fetch daily forecast
	forecasts = self.WeatherClient.wunder_10day_forecast()
	try:
		if( forecasts[0] == "ERROR" ):
			return
	except:
		pass
        # localized long and short day dictionary
        longday_dict = { "Monday": xbmc.getLocalizedString( 11 ), "Tuesday": xbmc.getLocalizedString( 12 ), "Wednesday": xbmc.getLocalizedString( 13 ), "Thursday": xbmc.getLocalizedString( 14 ), "Friday": xbmc.getLocalizedString( 15 ), "Saturday": xbmc.getLocalizedString( 16 ), "Sunday": xbmc.getLocalizedString( 17 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "N/A": "N/A" }
        shortday_dict = { "Monday": xbmc.getLocalizedString( 41 ), "Tuesday": xbmc.getLocalizedString( 42 ), "Wednesday": xbmc.getLocalizedString( 43 ), "Thursday": xbmc.getLocalizedString( 44 ), "Friday": xbmc.getLocalizedString( 45 ), "Saturday": xbmc.getLocalizedString( 46 ), "Sunday": xbmc.getLocalizedString( 47 ), "Today": xbmc.getLocalizedString( 33006 ), "Tonight": xbmc.getLocalizedString( 33018 ), "N/A": "N/A" }
        # localized long and short date dictionary
        longdate_dict = { "Jan": xbmc.getLocalizedString( 21 ), "Feb": xbmc.getLocalizedString( 22 ), "Mar": xbmc.getLocalizedString( 23 ), "Apr": xbmc.getLocalizedString( 24 ), "May": xbmc.getLocalizedString( 25 ), "Jun": xbmc.getLocalizedString( 26 ), "Jul": xbmc.getLocalizedString( 27 ), "Aug": xbmc.getLocalizedString( 28 ), "Sep": xbmc.getLocalizedString( 29 ), "Oct": xbmc.getLocalizedString( 30 ), "Nov": xbmc.getLocalizedString( 31 ), "Dec": xbmc.getLocalizedString( 32 ), "N/A": "" }
        shortdate_dict = { "Jan": xbmc.getLocalizedString( 51 ), "Feb": xbmc.getLocalizedString( 52 ), "Mar": xbmc.getLocalizedString( 53 ), "Apr": xbmc.getLocalizedString( 54 ), "May": xbmc.getLocalizedString( 55 ), "Jun": xbmc.getLocalizedString( 56 ), "Jul": xbmc.getLocalizedString( 57 ), "Aug": xbmc.getLocalizedString( 58 ), "Sep": xbmc.getLocalizedString( 59 ), "Oct": xbmc.getLocalizedString( 60 ), "Nov": xbmc.getLocalizedString( 61 ), "Dec": xbmc.getLocalizedString( 62 ), "N/A": "" }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDay" % ( count + 1, ), longday_dict.get( forecast[ 0 ], "" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDay" % ( count + 1, ), shortday_dict.get( forecast[ 0 ], "" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Outlook" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.HighTemperature" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.LowTemperature" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindDirection" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.WindSpeed" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.%d.ShortWindDirection" % ( count + 1, ), forecast[ 9 ] )
	if( forecasts[ 0 ][ 0 ] == "CACHE" ):
            self.WEATHER_WINDOW.setProperty( "Daily.1.LongDay", longday_dict[ "Tonight" ] )
            self.WEATHER_WINDOW.setProperty( "Daily.1.ShortDay", shortday_dict[ "Tonight" ] )
            self.WEATHER_WINDOW.setProperty( "Daily.1.LongDate", "%s %s" % ( longdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.ShortDate", "%s %s" % ( shortdate_dict[ forecast[ 1 ].split( " " )[ 0 ] ], forecast[ 1 ].split( " " )[ 1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.OutlookIcon", self.WEATHER_WINDOW.getProperty( "36Hour.1.OutlookIcon" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.FanartCode", os.path.splitext( os.path.basename( self.WEATHER_WINDOW.getProperty( "36Hour.1.OutlookIcon" ) ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Daily.1.Outlook", self.WEATHER_WINDOW.getProperty( "36Hour.1.Outlook" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.HighTemperature", "N/A" )
            self.WEATHER_WINDOW.setProperty( "Daily.1.LowTemperature", self.WEATHER_WINDOW.getProperty( "36Hour.1.Temperature" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.Precipitation", self.WEATHER_WINDOW.getProperty( "36Hour.1.Precipitation" ) )
            self.WEATHER_WINDOW.setProperty( "Daily.1.WindDirection", "N/A" )
            self.WEATHER_WINDOW.setProperty( "Daily.1.WindSpeed", "N/A" )
            self.WEATHER_WINDOW.setProperty( "Daily.1.ShortWindDirection", "N/A" )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Daily.IsFetched", "true" )

    def _wunder_hourly_forecast( self ):
        # fetch hourly forecast
        forecasts = self.WeatherClient.wunder_hourly_forecast()
        # localized long and short date dictionary
        longdate_dict = { "01": xbmc.getLocalizedString( 21 ), "02": xbmc.getLocalizedString( 22 ), "03": xbmc.getLocalizedString( 23 ), "04": xbmc.getLocalizedString( 24 ), "05": xbmc.getLocalizedString( 25 ), "06": xbmc.getLocalizedString( 26 ), "07": xbmc.getLocalizedString( 27 ), "08": xbmc.getLocalizedString( 28 ), "09": xbmc.getLocalizedString( 29 ), "10": xbmc.getLocalizedString( 30 ), "11": xbmc.getLocalizedString( 31 ), "12": xbmc.getLocalizedString( 32 ) }
        shortdate_dict = { "01": xbmc.getLocalizedString( 51 ), "02": xbmc.getLocalizedString( 52 ), "03": xbmc.getLocalizedString( 53 ), "04": xbmc.getLocalizedString( 54 ), "05": xbmc.getLocalizedString( 55 ), "06": xbmc.getLocalizedString( 56 ), "07": xbmc.getLocalizedString( 57 ), "08": xbmc.getLocalizedString( 58 ), "09": xbmc.getLocalizedString( 59 ), "10": xbmc.getLocalizedString( 60 ), "11": xbmc.getLocalizedString( 61 ), "12": xbmc.getLocalizedString( 62 ) }
        # enumerate thru and set the info
        for count, forecast in enumerate( forecasts ):
            # set properties
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Time" % ( count + 1, ), forecast[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.LongDate" % ( count + 1, ), "%s %s" % ( longdate_dict.get( forecast[ 1 ].split( "/" )[ 0 ], "" ), forecast[ 1 ].split( "/" )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortDate" % ( count + 1, ), "%s %s" % ( shortdate_dict.get( forecast[ 1 ].split( "/" )[ 0 ], "" ), forecast[ 1 ].split( "/" )[ -1 ], ) )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.OutlookIcon" % ( count + 1, ), forecast[ 2 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FanartCode" % ( count + 1, ), os.path.splitext( os.path.basename( forecast[ 2 ] ) )[ 0 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Temperature" % ( count + 1, ), forecast[ 3 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Outlook" % ( count + 1, ), forecast[ 4 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.FeelsLike" % ( count + 1, ), forecast[ 5 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Precipitation" % ( count + 1, ), forecast[ 6 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Humidity" % ( count + 1, ), forecast[ 7 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindDirection" % ( count + 1, ), forecast[ 8 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.WindSpeed" % ( count + 1, ), forecast[ 9 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.ShortWindDirection" % ( count + 1, ), forecast[ 10 ] )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunrise" % ( count + 1, ), "" )
            self.WEATHER_WINDOW.setProperty( "Hourly.%d.Sunset" % ( count + 1, ), "" )
        # use this to hide info until fully fetched
        self.WEATHER_WINDOW.setProperty( "Hourly.IsFetched", "true" )

    def _exit_script( self ):
        # end script
        pass

    # __init__(self,'location=06604')

"""
class FetchInfo( Thread ):
    def __init__( self, method ):
        Thread.__init__( self )
        self.method = method

    def run( self ):
        self.method()
"""
