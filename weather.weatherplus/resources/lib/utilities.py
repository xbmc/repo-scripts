# coding: utf-8

#************************
#
#       Utilities
#
#************************

try:
    import hashlib
except:
    import md5

try:
    import xbmc
    DEBUG = False
except:
    DEBUG = True

import os, urllib2, re, sys, time
from urllib import urlencode
from math import exp
import xbmcaddon

Addon = xbmcaddon.Addon( id="weather.weatherplus" )
translator = Addon.getSetting( "translator" )
BASE_MAPS_PATH = os.path.join( Addon.getAddonInfo("path"), "maps" )
BASE_SOURCE_PATH = os.path.join( Addon.getAddonInfo("path"), "source" )
BASE_URL = "http://www.weather.com"
BASE_MAPS = ( 
                                # Main local maps (includes some regional maps) #0
                                ( "", "", ),
                                # Main local maps (includes some regional maps) #1
                                ( "Local", "/weather/%s/%s?bypassredirect=true%s", ),
                                # weather details #2
                                ( "Weather Details (Alaska)", "/maps/geography/alaskaus/index_large.html", ),
                                ( "Weather Details (Current Weather)", "/maps/maptype/currentweatherusnational/index_large.html", ),
                                ( "Weather Details (Doppler Radar)", "/maps/maptype/dopplerradarusnational/index_large.html", ),
                                ( "Weather Details (Extended Forecasts)", "/maps/maptype/tendayforecastusnational/index_large.html", ),
                                ( "Weather Details (Hawaii)", "/maps/geography/hawaiius/index_large.html", ),
                                ( "Weather Details (Satellite - US)", "/maps/maptype/satelliteusnational/index_large.html", ),
                                ( "Weather Details (Satellite - World)", "/maps/maptype/satelliteworld/index_large.html", ),
                                ( "Weather Details (Severe Alerts - US)", "/maps/maptype/severeusnational/index_large.html", ),
                                ( "Weather Details (Severe Alerts - Regional)", "/maps/maptype/severeusregional/index_large.html", ),
                                ( "Weather Details (Short Term Forecast)", "/maps/maptype/forecastsusnational/index_large.html", ),
                                ( "Weather Details (Weekly Planner)", "/maps/maptype/weeklyplannerusnational/index_large.html", ),
                                ( "Weather Details (US Regions - Current)", "/maps/maptype/currentweatherusregional/index_large.html", ),
                                ( "Weather Details (US Regions - Forecasts)", "/maps/maptype/forecastsusregional/index_large.html", ),
                                ( "Weather Details (US Regions - Central)", "/maps/geography/centralus/index_large.html", ),
                                ( "Weather Details (US Regions - East Central)", "/maps/geography/eastcentralus/index_large.html", ),
                                ( "Weather Details (US Regions - Midwest)", "/maps/geography/midwestus/index_large.html", ),
                                ( "Weather Details (US Regions - North Central)", "/maps/geography/northcentralus/index_large.html", ),
                                ( "Weather Details (US Regions - Northeast)", "/maps/geography/northeastus/index_large.html", ),
                                ( "Weather Details (US Regions - Northwest)", "/maps/geography/northwestus/index_large.html", ),
                                ( "Weather Details (US Regions - South Central)", "/maps/geography/southcentralus/index_large.html", ),
                                ( "Weather Details (US Regions - Southeast)", "/maps/geography/southeastus/index_large.html", ),
                                ( "Weather Details (US Regions - Southwest)", "/maps/geography/southwestus/index_large.html", ),
                                ( "Weather Details (US Regions - West )", "/maps/geography/westus/index_large.html", ),
                                ( "Weather Details (US Regions - West Central)", "/maps/geography/westcentralus/index_large.html", ),
                                ( "Weather Details (World - Africa & Mid East)", "/maps/geography/africaandmiddleeast/index_large.html", ),
                                ( "Weather Details (World - Asia)", "/maps/geography/asia/index_large.html", ),
                                ( "Weather Details (World - Australia)", "/maps/geography/australia/index_large.html", ),
                                ( "Weather Details (World - Central America)", "/maps/geography/centralamerica/index_large.html", ),
                                ( "Weather Details (World - Europe)", "/maps/geography/europe/index_large.html", ),
                                ( "Weather Details (World - North America)", "/maps/geography/northamerica/index_large.html", ),
                                ( "Weather Details (World - Pacific)", "/maps/geography/pacific/index_large.html", ),
                                ( "Weather Details (World - Polar)", "/maps/geography/polar/index_large.html", ),
                                ( "Weather Details (World - South America)", "/maps/geography/southamerica/index_large.html", ),
                                # activity #35
                                ( "Outdoor Activity (Lawn and Garden)", "/maps/activity/garden/index_large.html", ),
                                ( "Outdoor Activity (Aviation)", "/maps/activity/aviation/index_large.html", ),
                                ( "Outdoor Activity (Boat & Beach)", "/maps/activity/boatbeach/index_large.html", ),
                                ( "Outdoor Activity (Business Travel)", "/maps/activity/travel/index_large.html", ),
                                ( "Outdoor Activity (Driving)", "/maps/activity/driving/index_large.html", ),
                                ( "Outdoor Activity (Fall Foliage)", "/maps/activity/fallfoliage/index_large.html", ),
                                ( "Outdoor Activity (Golf)", "/maps/activity/golf/index_large.html", ),
                                ( "Outdoor Activity (Outdoors)", "/maps/activity/nationalparks/index_large.html", ),
                                ( "Outdoor Activity (Oceans)", "/maps/geography/oceans/index_large.html", ),
                                ( "Outdoor Activity (Pets)", "/maps/activity/pets/index_large.html", ),
                                ( "Outdoor Activity (Ski)", "/maps/activity/ski/index_large.html", ),
                                ( "Outdoor Activity (Special Events)", "/maps/activity/specialevents/index_large.html", ),
                                ( "Outdoor Activity (Sporting Events)", "/maps/activity/sportingevents/index_large.html", ),
                                ( "Outdoor Activity (Vacation Planner)", "/maps/activity/vacationplanner/index_large.html", ),
                                ( "Outdoor Activity (Weddings - Spring)", "/maps/activity/weddings/spring/index_large.html", ),
                                ( "Outdoor Activity (Weddings - Summer)", "/maps/activity/weddings/summer/index_large.html", ),
                                ( "Outdoor Activity (Weddings - Fall)", "/maps/activity/weddings/fall/index_large.html", ),
                                ( "Outdoor Activity (Weddings - Winter)", "/maps/activity/weddings/winter/index_large.html", ),
                                ( "Outdoor Activity (Holidays)", "/maps/activity/holidays/index_large.html", ),
                                # health and safety #54
                                ( "Health & Safety (Aches & Pains)", "/maps/activity/achesandpains/index_large.html", ),
                                ( "Health & Safety (Air Quality)", "/maps/activity/airquality/index_large.html", ),
                                ( "Health & Safety (Allergies)", "/maps/activity/allergies/index_large.html", ),
                                ( "Health & Safety (Cold & Flu)", "/maps/activity/coldandflu/index_large.html", ),
                                ( "Health & Safety (Earthquake Reports)", "/maps/maptype/earthquakereports/index_large.html", ),
                                ( "Health & Safety (Home Planner)", "/maps/activity/home/index_large.html", ),
                                ( "Health & Safety (Schoolday)", "/maps/activity/schoolday/index_large.html", ),
                                ( "Health & Safety (Severe Weather Alerts)", "/maps/maptype/severeusnational/index_large.html", ),
                                ( "Health & Safety (Skin Protection)", "/maps/activity/skinprotection/index_large.html", ),
                                ( "Health & Safety (Fitness)", "/maps/activity/fitness/index_large.html", ),
                            )

def printlog( msg ):
    print "[Weather Plus] %s" % msg

def _translate_text( text, translate, accu="", target="en" ): 
    global translator
    if( accu == "accu" ):
	translate = translate.split(" ")[0].replace("es-ar", "es").replace("es-mx", "es").replace("fr-ca", "fr").replace("pt-br", "pt").replace("zh-cn", "zh-CN").replace("zh-tw", "zh-TW")
	if( translate == "en-us" ): return text
    if( translate is None ): return text
    if( translator == "0" and accu != "accu" ):
	    # base babelfish url
	    url = "http://babelfish.yahoo.com/translate_txt"
	    try:
		# trick for translating T-Storms
		text = text.replace( "T-Storms", "Thunderstorms" )
		# data dictionary
		data = { "ei": "UTF-8", "doit": "done", "fr": "bf-home", "intl": "1", "tt": "urltext", "trtext": text, "lp": translate, "btnTrTxt": "Translate" }
		# request url
		request = urllib2.Request( url, urlencode( data ) )
		# add a faked header, we use ie 8.0. it gives correct results for regex
		request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
		# open requested url
		usock = urllib2.urlopen( request )
		# read htmlSource
		htmlSource = usock.read()
		# close socket
		usock.close()
		# find translated text
		text = re.findall( "<div id=\"result\"><div style=\"[^\"]+\">([^<]+)", htmlSource )[ 0 ]
	    except Exception, e:
		# TODO: add error checking?
		pass
    if( translator == "1" or accu == "accu" ):
	    # base babelfish url
	    url = "http://translate.google.com/translate_a/t"
	    try:
		# trick for translating T-Storms, titlecase
		text = text.replace( "T-Storms", "Thunderstorms" ).replace("|", " | ")
		# data dictionary
		data = { "client": "t", "text": text, "hl": target, "auto": "auto", "tl": translate, "sc": "1" }
		# request url
		request = urllib2.Request( url, urlencode( data ) )
		# add a faked header, we use ie 8.0. it gives correct results for regex
		request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
		# open requested url
		usock = urllib2.urlopen( request )
		# read htmlSource
		htmlSource = usock.read()
		# close socket
		usock.close()
		# find translated text
		text_raw = re.findall( "\"([^\"\[]+)\",\"([^\"]+)\"", htmlSource )
		text = ""
		for count in range(0, len(text_raw)):
		    text += text_raw[count][0]
		text = text.replace(" | ", "|").replace(" % ", "%").replace(" / ", "/").replace("\\n","").replace("\\t","").replace(" |","|")	
	    except Exception, e:
		# TODO: add error checking?
		pass
    # return translated text
    return text

def _normalize_outlook( outlook ):
    # if we're debugging xbmc module is not available
    tid = "F"
    sid = "mph"
    if ( not DEBUG ):
        tid = xbmc.getRegion( id="tempunit" )[ -1 ]
        sid = xbmc.getRegion( id="speedunit" )
    # enumerate thru and localize values
    for count, tmp_outlook in enumerate( outlook ):
        if ( tid == "C" ):
            # calculate the localized temp if C is required
            temps = re.findall( "[0-9]+F", tmp_outlook )
            for temp in temps:
                tmp_outlook = re.sub( temp, _localize_unit( temp ) + tid, tmp_outlook, 1 )
            # calculate the localized temp ranges if C is required
            temps = re.findall( "[low|mid|high|lower|upper]+ [0-9]+s", tmp_outlook )
            add = { "l": 3, "m": 6, "h": 9 }
            for temp in temps:
                new_temp = _localize_unit( str( int( re.findall( "[0-9]+", temp )[ 0 ] ) + add.get( temp[ 0 ], 3 ) ) )
                temp_int = int( float( new_temp ) / 10 ) * 10
                temp_rem = int( float( new_temp ) % 10 )
                temp_text = ( "low %ds", "mid %ds", "high %ds", )[ ( temp_rem >= 4 ) + ( temp_rem >= 6 ) ]
                tmp_outlook = re.sub( temp, temp_text % ( temp_int, ), tmp_outlook, 1 )
        if ( sid != "mph" ):
            # calculate the localized wind if C is required
            winds = re.findall( "[0-9]+ to [0-9]+ mph", tmp_outlook )
            for wind in winds:
                speeds = re.findall( "[0-9]+", wind )
                for speed in speeds:
                    wind = re.sub( speed, _localize_unit( speed, "speed" ).split( " " )[ 0 ], wind, 1 )
                tmp_outlook = re.sub( "[0-9]+ to [0-9]+ mph", wind.replace( "mph", sid ), tmp_outlook, 1 )
            winds = re.findall( "[0-9]+ mph", tmp_outlook )
            for wind in winds:
                speeds = re.findall( "[0-9]+", wind )
                for speed in speeds:
                    wind = re.sub( speed, _localize_unit( speed, "speed" ).split( " " )[ 0 ], wind, 1 )
                tmp_outlook = re.sub( "[0-9]+ mph", wind.replace( "mph", sid ), tmp_outlook, 1 )
       # add our text back to the main variable
        outlook[ count ] = tmp_outlook
    # return normalized text
    return outlook

def _localize_unit( value, unit="temp" ):
    # grab the specifier
    value_specifier = value.split( " " )[ -1 ].upper()
    # replace any invalid characters
    value = value.replace( chr(176), "" ).replace( "&deg;", "" ).replace( "mph", "" ).replace( "miles", "" ).replace( "mile", "" ).replace( "in.", "" ).replace( "F", "" ).replace( "AM", "" ).replace( "PM", "" ).replace( "am", "" ).replace( "pm", "" ).strip()
    # do not convert invalid values
    if ( not value or value.startswith( "N/A" ) ):
        return value
    # time conversion
    if ( unit == "time" or unit == "time24" ):
        # format time properly
        if ( ":" not in value ):
            value += ":00"
        # set default time
        time = value
        # set our default temp unit
        id = ( "%H:%M", "%I:%M:%S %p", )[ unit == "time" ]
        # if we're debugging xbmc module is not available
        if ( not DEBUG and unit == "time" ):
            id = xbmc.getRegion( id="time" )
            # print id
        # 24 hour ?
        if ( id.startswith( "%H" ) ):
            hour = int( value.split( ":" )[ 0 ] )
            if (hour < 0 ):
               hour += 12
            hour += ( 12 * ( value_specifier == "PM" and int( value.split( ":" )[ 0 ] ) != 12 ) )
            hour -= ( 12 * ( value_specifier == "AM" and int( value.split( ":" )[ 0 ] ) == 12 ) )
            time = "%d:%s" % ( hour, value.split( ":" )[ 1 ], )
            # print "[Weather Plus] Converting Time : "+value + " " + value_specifier+ " -> " + time
        else : 
            hour = int( value.split( ":" )[ 0 ] )
            if (hour < 0 ):
               hour += 24

            if ( hour > 12 and value_specifier == value) :
                 value_specifier = "PM"
                 hour -= 12
            elif (value_specifier == value) :
                 value_specifier = "AM"
            # hour -= ( 12 * ( value_specifier == "PM" and int( value.split( ":" )[ 0 ] ) != 12 ) )
            time = "%d:%s" % ( hour, value.split( ":" )[ 1 ], )            
            if (unit == "time") :
                 time = "%s %s" % ( time, value_specifier, ) 
	return time
    else:
        # we need a float
        try:
	    value = float( value )
	except:
	    return value
        # temp conversion
        if ( unit == "temp" or  unit == "tempdiff" ):
            # set our default temp unit
            id = "F"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = xbmc.getRegion( id="tempunit" )[ -1 ]
            # calculate the localized temp if C is required
            if ( id == "C" ):
                # C/F difference or temperature conversion
                if ( unit == "tempdiff" ):
                    # 9 degrees of F equal 5 degrees of C
                    value = round( float( 5 * value ) / 9 )
                else:
                    # convert to celcius
                    value = round( ( value - 32 ) * ( float( 5 ) / 9 ) )
            # return localized temp
            return "%s%d" % ( ( "", "+", )[ value >= 0 and unit == "tempdiff" ], value )
	# temp conversion ( F -> C )
	if ( unit == "tempf2c" ):
	    value = round( ( value - 32 ) * ( float( 5 )/ 9 ) )
	    return "%d" % value
        # speed conversion
        elif ( unit == "speed" ):
            # set our default temp unit
            id = "mph"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = xbmc.getRegion( id="speedunit" )
            # calculate the localized speed
            if ( id == "km/h" ):
                value = round( value * 1.609344 )
            elif ( id == "m/s" ):
                value = round( value * 0.45 )
            elif ( id == "ft/min" ):
                value = round( value * 88 )
            elif ( id == "ft/s" ):
                value = round( value * 1.47 )
            elif ( id == "yard/s" ):
                value = round( value * 0.4883 )
            # return localized speed
            return "%d %s" % ( value, id, )
	elif ( unit == "speedmph2kmh" ):
	    value = round( value * 1.609344 )
	    return "%d km/h" % value	
        # depth conversion
        elif ( unit == "depth" ):
            # set our default depth unit
            id = "in."
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "in.", "cm.", )[ xbmc.getRegion( id="tempunit" )[ -1 ] == "C" ]
            # calculate the localized depth
            if ( id == "cm." ):
                value = float( value * 2.54 )
            # return localized depth
            return "%.2f %s" % ( value, id, )
        # pressure conversion
        elif ( unit == "pressure" ):
            # set our default pressure unit
            id = "in."
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "in.", "mb.", )[ xbmc.getRegion( id="tempunit" )[ -1 ] == "C" ]
            # calculate the localized pressure
            if ( id == "mb." ):
                value = float( value * 33.8637526 )
            # return localized pressure
            return "%.2f %s" % ( value, id, )
        # distance conversion
        elif ( unit == "distance" ):
            # set our default distance unit
            id = "mile"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "kilometer", "mile", )[ xbmc.getRegion( id="speedunit" ) == "mph" ]
            # calculate the localized distance
            if ( id == "kilometer" ):
                value = float( value * 1.609344 )
            # pluralize for values != 1
            if ( value != 1.0 ):
                id += "s"
            # return localized distance
            return "%.1f %s" % ( value, id, )

def _english_localize_unit( value, unit="temp" ):
    # grab the specifier
    value_specifier = value.split( " " )[ -1 ].upper()
    # replace any invalid characters
    value = value.replace( chr(176), "" ).replace( "&deg;", "" ).replace( "km/h", "" ).replace( "kilometers", "" ).replace( "kilometer", "" ).replace("km", "").replace( "mb", "" ).replace( "C", "" ).replace( "AM", "" ).replace( "PM", "" ).replace( "am", "" ).replace( "pm", "" ).strip()
    # do not convert invalid values
    if ( not value or value.startswith( "N/A" ) ):
        return value
    # time conversion
    if ( unit == "time" or unit == "time24" ):
        # format time properly
        if ( ":" not in value ):
            value += ":00"
        # set default time
        time = value
        # set our default temp unit
        id = ( "%H:%M", "%I:%M:%S %p", )[ unit == "time" ]
        # if we're debugging xbmc module is not available
        if ( not DEBUG and unit == "time" ):
            id = xbmc.getRegion( id="time" )
            # print id
        # 24 hour ?
        if ( id.startswith( "%H" ) ):
            hour = int( value.split( ":" )[ 0 ] )
            if (hour < 0 ):
               hour += 12
            hour += ( 12 * ( value_specifier == "PM" and int( value.split( ":" )[ 0 ] ) != 12 ) )
            hour -= ( 12 * ( value_specifier == "AM" and int( value.split( ":" )[ 0 ] ) == 12 ) )
            time = "%d:%s" % ( hour, value.split( ":" )[ 1 ], )
            # print "[Weather Plus] Converting Time : "+value + " " + value_specifier+ " -> " + time
        else : 
            hour = int( value.split( ":" )[ 0 ] )
            if (hour < 0 ):
               hour += 24

            if ( hour > 12 and value_specifier == value) :
                 value_specifier = "PM"
                 hour -= 12
            elif (value_specifier == value) :
                 value_specifier = "AM"
            # hour -= ( 12 * ( value_specifier == "PM" and int( value.split( ":" )[ 0 ] ) != 12 ) )
            time = "%d:%s" % ( hour, value.split( ":" )[ 1 ], )            
            if (unit == "time") :
                 time = "%s %s" % ( time, value_specifier, ) 
                 # print value + " -> " + time


        # add am/pm if used
        # if ( id.endswith( "xx" ) ):
            # time = "%s %s" % ( time, value_specifier, ) 
        # return localized time
        return time
    else:
        # we need a float
        value = float( value )
        # temp conversion
        if ( unit == "temp" or  unit == "tempdiff" ):
            # set our default temp unit
            id = "C"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = xbmc.getRegion( id="tempunit" )[ -1 ]
            # calculate the localized temp if C is required
            if ( id == "F" ):
                # C/F difference or temperature conversion
                if ( unit == "tempdiff" ):
                    # 9 degrees of F equal 5 degrees of C
                    value = round( float( 9 * value ) / 5 )
                else:
                    # convert to F
                    value = round( float( value * 1.8 ) + 32 )
            # return localized temp
            return "%s%d" % ( ( "", "+", )[ value >= 0 and unit == "tempdiff" ], value )
        # speed conversion
        elif ( unit == "speed" ):
            # set our default temp unit
            id = "km/h"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = xbmc.getRegion( id="speedunit" )
            # calculate the localized speed
            if ( id == "mph" ):
                value = round( value * 0.621371 )
            elif ( id == "m/s" ):
                value = round( value * 0.277778 )
            elif ( id == "ft/min" ):
                value = round( value * 0.911344 * 60 )
            elif ( id == "ft/s" ):
                value = round( value * 0.911344 )
            elif ( id == "yard/s" ):
                value = round( value * 0.333333 * 0.911344 )
            # return localized speed
            return "%d %s" % ( value, id, )
        # depth conversion
        elif ( unit == "depth" ):
            # set our default depth unit
            id = "cm."
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "in.", "cm.", )[ xbmc.getRegion( id="tempunit" )[ -1 ] == "C" ]
            # calculate the localized depth
            if ( id == "in." ):
                value = float( value * 0.393701 )
            # return localized depth
            return "%.2f %s" % ( value, id, )
        # pressure conversion
        elif ( unit == "pressure" ):
            # set our default pressure unit
            id = "mb."
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "in.", "mb.", )[ xbmc.getRegion( id="tempunit" )[ -1 ] == "C" ]
            # calculate the localized pressure
            if ( id == "in." ):
                value = float( value * 0.02953 )
            # return localized pressure
            return "%.2f %s" % ( value, id, )
        # distance conversion
        elif ( unit == "distance" ):
            # set our default distance unit
            id = "kilometer"
            # if we're debugging xbmc module is not available
            if ( not DEBUG ):
                id = ( "kilometer", "mile", )[ xbmc.getRegion( id="speedunit" ) == "mph" ]
            # calculate the localized distance
            if ( id == "mile" ):
                value = float( value * 0.621371 )
            # pluralize for values != 1
            if ( value != 1.0 ):
                id += "s"
            # return localized distance
            return "%.1f %s" % ( value, id, )

def _fetch_data( base_url, refreshtime=0, filename=None, animated=False, subfolder="forecasts", retry=True ):
	start = time.clock()
	printlog( "_fetch_data : Fetching %s" % base_url )
	try:
	    # set proper base path
	    if ( not base_url.startswith( "http://" ) ):
		# user defined maps file
		base_path = base_url
		base_refresh_path = None
	    elif ( filename is None ):
		# anything else except map/radar images (basically htmlSource)
		try: 
		    base_path = os.path.join( BASE_SOURCE_PATH, subfolder, hashlib.md5( base_url ).hexdigest() )
		except:
		    base_path = os.path.join( BASE_SOURCE_PATH, subfolder, md5.new( base_url ).hexdigest() )
		base_refresh_path = None
	    else:
		# set proper path for md5 hash
		if ( animated ):
		    # animated maps include map name in base url, so don't use filename (each jpg would be in a seperate folder if you did)
		    path = os.path.dirname( base_url )
		else:
		    # non animated maps share same base url, so use full name
		    path = base_url
		# set base paths
		try:
		    base_path = os.path.join( BASE_MAPS_PATH, subfolder, hashlib.md5( path ).hexdigest(), filename )
		    base_refresh_path = os.path.join( BASE_MAPS_PATH, subfolder, hashlib.md5( path ).hexdigest(), "refresh.txt" )
		except:
		    base_path = os.path.join( BASE_MAPS_PATH, subfolder, md5.new( path ).hexdigest(), filename )
		    base_refresh_path = os.path.join( BASE_MAPS_PATH, subfolder, md5.new( path ).hexdigest(), "refresh.txt" )
	    # get expiration date
	    expires, refresh = _get_expiration_date( base_path, base_refresh_path, refreshtime )
	    if ( refreshtime == 0 ) : refresh = 1
	    # only fetch source if it's been longer than refresh time or does not exist
	    if ( not os.path.isfile( base_path ) or refresh ):
		# request base url
		request = urllib2.Request( base_url )
		# add a faked header
		request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
		# add cookies
		request.add_header( "Cookie", "Units=english" ) # for Wunderground.com
		# open requested url
		usock = urllib2.urlopen( request )
		# get expiration
		try:
		    expires = time.mktime( time.strptime( usock.info()[ "expires" ], "%a, %d %b %Y %H:%M:%S %Z" ) )
		except:
		    expires = -1
	    else:
		# open saved source
		usock = open( base_path, "rb" )
	    # read source
	    data = usock.read()
	    # close socket
	    usock.close()
	    # save the data
	    if ( not os.path.isfile( base_path ) or refresh ):
		_save_data( data, base_path )
	    # save the refresh.txt file
	    if ( base_refresh_path is not None and ( not animated or ( animated and refreshtime == -5 ) ) and refresh ):
		_save_data( str( expires ), base_refresh_path )
	    if ( base_refresh_path ):
		data = os.path.dirname( base_path )
	    # calc elapsed time
	    elapsed = "%f sec." % ( time.clock() - start )
	    printlog( "_fetch_data : Finishing %s (Elapsed Time : %s)" % (base_url, elapsed) )
	    # return results
	    return data
	except urllib2.HTTPError, e:
	    # if error 503 and this is the first try, recall function after sleeping, otherwise return ""
	    if ( e.code == 503 and retry ):
		# TODO: this is so rare, but try and determine if 3 seconds is enogh
		print "Trying url %s one more time." % base_url
		time.sleep( 3 )
		# try one more time
		return _fetch_data( base_url, refreshtime, filename, animated, subfolder, False )
	    else:
		# we've already retried, return ""
		print "Second error 503 for %s, increase sleep time." % base_url
		return ""
	except:
	    # oops print error message
	    print "ERROR: %s (%d) - %s" % ( sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
	    # some unknown error, return ""
	    return ""

def _get_expiration_date( base_path, base_refresh_path, refreshtime ):
	try:
	    # get the data files date if it exists
	    try:
		date = time.mktime( time.gmtime( os.path.getmtime( base_path ) ) )
	    except:
		date = 0
	    # set default expiration date
	    expires = date + ( refreshtime * 60 )
	    # if the path to the data file does not exist create it
	    if ( base_refresh_path is not None and os.path.isfile( base_refresh_path ) ):
		# open data path for writing
		file_object = open( base_refresh_path, "rb" )
		# read expiration date
		expires = float( file_object.read() )
		# close file object
		file_object.close()
	    # see if necessary to refresh source
	    refresh = ( ( time.mktime( time.gmtime() ) * ( refreshtime != 0 ) ) > expires )
	except:
	    # oops print error message
	    print "ERROR: %s (%d) - %s" % ( sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
	# return expiration date
	return expires, refresh

def _save_data( data, data_path ):
	try:
	    # if the path to the data file does not exist create it
	    if ( not os.path.isdir( os.path.dirname( data_path ) ) ):
		os.makedirs( os.path.dirname( data_path ) )
	    # open data path for writing
	    file_object = open( data_path, "wb" )
	    # write htmlSource
	    file_object.write( data )
	    # close file object
	    file_object.close()
	except:
	    # oops print error message
	    print "ERROR: %s (%d) - %s" % ( sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )

class MapParser:
    def __init__( self, htmlSource ):
        self.maps = ()
        self._get_maps( htmlSource )

    def _get_maps( self, htmlSource ):
        try:
            # initialize our animated maps list
            animated_maps = []
            # regex patterns
            pattern_maps = "<img name=\"mapImg\" src=\"([^\"]+)\""
            # fetch static map
            static_map_ = re.findall( pattern_maps, htmlSource, re.IGNORECASE )
            static_map_ = str(static_map_).replace("http://i.imwx.com/", "http://image.weather.com/").replace("[", "").replace("]","").replace("\'","")
            static_map = []
            static_map += [static_map_]
            # print "stat : ", static_map            
            # does this map support animation?
            motion = re.findall( ">Weather In Motion<", htmlSource, re.IGNORECASE )
            if ( len( motion ) ):
                # get our map
                region = os.path.splitext( os.path.basename( static_map[ 0 ] ) )[ 0 ]
                # enumerate thru and create our animated map urls
                for i in range( 1, 6 ):
                    animated_maps += [ "http://image.weather.com/looper/archive/%s/%dL.jpg" % ( region, i, ) ]
        except:
            pass
        # set our maps object
        self.maps += ( static_map, animated_maps, "", )

class MaplistParser:
    def __init__( self, htmlSource ):
        self.map_list = []
        self._get_map_list( htmlSource )

    def _get_map_list( self, htmlSource ):
        try:
            # regex patterns
            pattern_map_list = "<option.+?value=\"([^\"]+)\".*?>([^<]+)</option>"
            # fetch avaliable maps
            map_list = re.findall( pattern_map_list, htmlSource, re.IGNORECASE )
            # enumerate thru list and eliminate bogus items
            for map in map_list:
                # eliminate bogus items
                if ( len( map[ 0 ] ) > 7 ):
                    self.map_list += [ map + ( "", ) ]
        except:
            pass

def _fetch_images( map ):
	if ( map[ 0 ] == ["http://image.weather.com"] and map[ 1 ] == [] ): return "", ""
        # are there multiple images?
        maps = map[ 1 ] or map[ 0 ]
        # initailize our return variables
        legend_path = ""
        base_path_maps = ""
        # enumerate thru and fetch images
        for count, url in enumerate( maps ):
            # used for info in progress dialog
            image = os.path.basename( url )
            printlog( "Fetch image = " + image + " ||| url = "+ url )
            # fetch map
            base_path_maps = _fetch_data( url, -1 * ( count + 1 ), image, len( maps ) > 1, subfolder="" )
            # no need to continue if the first map of multi image map fails
            if ( base_path_maps == "" ):
                break
        # fetch legend if available
        if ( map[ 2 ] and base_path_maps != "" ):
            # fetch legend
            legend_path = _fetch_data( map[ 2 ], -1, os.path.basename( map[ 2 ] ), False, subfolder="" )
            # we add the image filename back to path since we don't use a multiimage control
            legend_path = os.path.join( legend_path, os.path.basename( map[ 2 ] ) )
        # we return path to images or empty string if an error occured
        # print base_path_maps
        return base_path_maps, legend_path

def _getFeelsLike( T=10, K=25, rh=80 ): 
	""" The formula to calculate the equivalent temperature related to the wind chill is: 
	W = 13.12 + 0.6215 * T - 11.37 * K**0.16 + 0.3965 * T * K**0.16 
	W: is the wind chill in degrees Celsius 
	K: is the average wind speed in km/h at a standard height of 10m height above ground
	T: is the temperature of the air in degrees Celsius 
	Wind chill is only defined for K with a minimim speed of 5 km/h,
	and is only designed for air temperature of 10C or less

	The formula to calculate the apparent temperature is:
	AT = T + 0.33 * e - 0.70 * M - 4.00
	e = rh / 100 * 6.105 * exp( 17.27 * T / (237.7 + T) )
	AT : is the apparent temperature in degrees Celsius
	T : is the air temperature in degrees Celsius
	M : is the average wind speed in m/s at a standard height of 10m above ground
	e : is the water vapor pressure (humidity)
	rh : is the percent relative humidity
	When AT < T, take T as the Feels like temperature
	Apparent Temperature is designed for air temperature of 14C or more

	Roll-over : from 10C to 14C
	Feels like temperature = T - (T-W) * (14-T)/4

	reference : http://blog.metservice.com/2010/01/feels-like/	

	getFeelsLike( tCelsius, windspeed, relative humidity )
	""" 

	FeelsLike = T 
	#Wind speeds of 5 km/h or less, the wind chill temperature is the same as the actual air temperature. 
	if ( T < 14 and K > 5 ): 
		FeelsLike = 13.12 + ( 0.6215 * T ) - ( 11.37 * K**0.16 ) + ( 0.3965 * T * K**0.16 )
		if ( T > 10 and T < 14 ):
			FeelsLike = T - ( T - FeelsLike ) * ( 14 - T ) / 4
	elif ( T >= 14 ):
		M = K * 5 / 18
		e = float(rh) / 100 * 6.105 * exp( 17.27 * T / ( 237.7 + T ) )
		AT = T + 0.33 * e - 0.70 * M - 4
		FeelsLike = ( AT, T )[ AT < T ]
	return str( int(round( FeelsLike )) ) 
