# coding: utf-8

"""
    weather.com api client module

    by Nuka1195, brightsr

"""

# main imports
import sys
import os

try:
    import xbmc
    DEBUG = False
except:
    DEBUG = True

import xbmcgui
import urllib2
from urllib import urlencode, unquote, quote
#import httplib, socket

try:
    import hashlib
except:
    import md5

import re
import time
import xbmcaddon, xml
import platform

import resources.lib.video_amf as AMF

WEATHER_WINDOW = xbmcgui.Window( 12600 )

def printlog( msg ):
    print "[Weather Plus] %s" % msg

# TODO: maybe use xbmc language strings for brief outlook translation
def _translate_text( text, translate ):
    # base babelfish url
    url = "http://babelfish.yahoo.com/translate_txt"
    try:
        # trick for translating T-Storms, TODO: verify if this is necessary
        text = text.replace( "T-Storms", "Thunderstorms" )
        # data dictionary
        data = { "ei": "UTF-8", "doit": "done", "fr": "bf-home", "intl": "1", "tt": "urltext", "trtext": text, "lp": translate, "btnTrTxt": "Translate" }
        # request url
        request = urllib2.Request( url, urlencode( data ) )
        # add a faked header, we use ie 8.0. it gives correct results for regex
        request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
	# request.add_header( "User-Agent", "XBMC/10.0 r35647 (Windows; Windows 7, 64-bit (WoW) build 7600; http://www.xbmc.org)" )
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
            temps = re.findall( "[low|mid|high]+ [0-9]+s", tmp_outlook )
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
            winds = re.findall( "at [0-9]+ mph", tmp_outlook )
	    # print winds
            for wind in winds:
                speeds = re.findall( "[0-9]+", wind )
                for speed in speeds:
                    wind = re.sub( speed, _localize_unit( speed, "speed" ).split( " " )[ 0 ], wind, 1 )
                tmp_outlook = re.sub( "at [0-9]+ mph", wind.replace( "mph", sid ), tmp_outlook, 1 )
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
                 # print value + " -> " + time


        # add am/pm if used
        # if ( id.endswith( "xx" ) ):
            # time = "%s %s" % ( time, value_specifier, ) 
        # return localized time
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
	    return value
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
        pattern_alert_color = "<div id=\"wx-alert-bar\" class=\"wx-alert-(.+?)\">"
        pattern_alerts = "href=\"/weather/alerts/(.+?)\""
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
        # pattern_sunrise_now = "Time Until Sunrise: <strong>(.+?)</strong>"
        # pattern_sunset_now = "Daylight Remaining: <strong>(.+?)</strong>"
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
	    '''
            try:
                # fetch state
                locstate = re.findall( pattern_locstate, htmlSource )[ 0 ].lower()
               
            except:
                pass
            '''
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
		   current_wind = "From %s at %s" % ( current_wind_buffer[ 0 ][ 0 ], _localize_unit( current_wind_buffer[ 0 ][ 1 ], "speed" ) )
		   current_winddirection = ""	   
		except:
		   pass
	    except:
		current_wind = "N/A"
		current_winddirection = "N/A"
	    current_humidity = re.findall( pattern_current_humidity, htmlSource )
	    current_dewpoint = re.findall( pattern_current_dewpoint, htmlSource )
	    try:
	        current_humidity = current_humidity[ 0 ] + "%"
		current_dewpoint = _localize_unit( current_dewpoint[ 0 ] )
	    except:
	        current_humidity = "N/A"
		current_dewpoint = "N/A"
	    current_UVIndex = re.findall( pattern_UVIndex, htmlSource )
	    try:
		current_UVIndex = current_UVIndex[ 0 ].replace("\t","").replace("\n","").strip()
	    except:
	        current_UVIndex = "N/A"
	    
            # fetch video location

            vl = re.findall( pattern_video_location, htmlSource )
            vl2 = re.findall( pattern_video_local_location, htmlSource )

            try :
                if (vl2 is not None) : 
                   self.video_local_location = vl2[0][0]
                   self.video_local_number = vl2[0][1]
                else :
                   self.video_local_location = "Not Available"
                   self.video_local_number = ""
            except :
                   self.video_local_location = "Not Available"
                   self.video_local_number = ""
            try :
                if (vl is not None) :
                   self.video_location = vl [0]
                else :
                   self.video_location = "Non US"
            except :
                self.video_location = "Non US"
            printlog( "video_location : "+ self.video_location + " Local_location : " + self.video_local_location )
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
            # print precip_title
            # fetch precip title
            precip_amount = re.findall( pattern_precip_amount, htmlSource )
            # fetch forecasts
            #outlook = re.findall( pattern_outlook, htmlSource )
            # fetch daylight
            daylight = re.findall( pattern_daylight, htmlSource )
            sunrise_ = re.findall( pattern_sunrise_now, htmlSource_5)
            sunset_ =  re.findall( pattern_sunset_now, htmlSource_5)
            try : 
               time_diff = int(sunrise_[ 0 ].split( " " )[ 3 ][:2])-localtime
            except :
               time_diff = 0
            # print str(int(sunrise_[ 0 ].split( " " )[ 3 ][:2]))+" asdasd "+ str(localtime)
            print "[Weather Plus] Timezone : " + str(localtime) + " " + str(time_diff)
            
            # fetch extra info
            pressure_ = re.findall( pattern_pressure, htmlSource, re.DOTALL )
            visibility_ = re.findall( pattern_visibility, htmlSource, re.DOTALL )
            # sun_ = re.findall( pattern_sun, htmlSource, re.DOTALL )
            # sun = []
            pressure = "N/A"
            visibility = "N/A"
            sunrise = "N/A"
            sunset = "N/A"
            
            if ( pressure_ ) :
                    pressure = "".join(pressure_[0][0].split("\n"))
                    pressure = "".join(pressure.split("\t"))
                    pressure = pressure.replace("in", "")
                    # pressure = pressure + { "pressure-up": u"\u2191", "pressure-down": u"\u2193", "pressure-steady": u"\u2192" }[ pressure_[0][1] ]
                    try : 
                       print "[Weather Plus] pressure : " + pressure_[0][1]
                    except :
                       print "[Weather Plus] there's no info about pressure-up or down"                     
            if ( visibility_ ) :
                   visibility = "".join(visibility_[0].split("\n"))
                   visibility = "".join(visibility.split("\t"))
                   visibility = visibility.replace("mi", "")
                   # print visibility
            if ( sunrise_ ) :
                   sunrise = "".join(sunrise_[0].split("\n"))
                   sunrise = "".join(sunrise.split("\t"))
                   # print sunrise
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
            print "[Weather Plus] pressure : "+pressure
            if ( pressure == "N/A" ) :
                   self.extras += [(pressure, _localize_unit(visibility, "distance"), sunrise, sunset, current_temp, current_feels_like, current_icon, current_brief, current_humidity, current_dewpoint, current_wind, current_UVIndex )]
            elif ( pressure == pressure.replace("mb", "") ) :
                   self.extras += [(_localize_unit(pressure, "pressure") + { "pressure-up": u"\u2191", "pressure-down": u"\u2193", "pressure-steady": u"\u2192" }[ pressure_[0][1] ], _localize_unit(visibility, "distance"), sunrise, sunset, current_temp, current_feels_like, current_icon, current_brief, current_humidity, current_dewpoint, current_wind, current_UVIndex)]
            else :  
                   self.extras += [(pressure + { "pressure-up": u"\u2191", "pressure-down": u"\u2193", "pressure-steady": u"\u2192" }[ pressure_[0][1] ], _localize_unit(visibility, "distance"), sunrise, sunset, current_temp, current_feels_like, current_icon, current_brief, current_humidity, current_dewpoint, current_wind, current_UVIndex)]

            # localize our extra info
            # convert outlook wind/temp values
            outlook = _normalize_outlook( outlook )
            # translate brief and outlook if user preference
            if ( self.translate is not None ):
                # we only need outlook and brief. the rest the skins or xbmc language file can handle
                # we separate each item with single pipe
                # text = "|".join( outlook )
                # separator for different info
                # text += "|||||"
                # we separate each item with single pipe
                text = "|".join( outlook )
                # translate text
                text = _translate_text( text, self.translate )
                # split text into it's original list
                # outlook = text.split( "|||||" )[ 0 ].split( "|" )
                outlook = text.split( "|" )
            for count, day in enumerate( days ):
                # make icon path
                try :
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count ] + ".png" ] )
                except :
                  print "[Weather Plus] Icon is not available"
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", "0.png" ] ) 
                # add result to our class variable
                try :
                  print "[Weather Plus] " + days[count]
                except :
                  print "[Weather Plus] days["+str(count)+"] is not available"
                  days += [ ("N/A", ) ]              
                print "[Weather Plus] " + iconpath
		print "[Weather Plus] brief = ", brief
                try :
                  print "[Weather Plus] " + brief[ count ]
                except :
                  print "[Weather Plus] brief[" +str(count)+ "] is not available"
                  brief += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + temperature_info[ count ]
                except :
                  print "[Weather Plus] temperature_info["+str(count)+"] is not available"
                  temperature_info += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + _localize_unit( temperature[ count ] )
                except :
                  print "[Weather Plus] temperature["+str(count)+"] is not available"
                  temperature += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + precip_title[ count ]
                except :
                  print "[Weather Plus] precip_title["+str(count)+"] is not available"
                  precip_title += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + precip_amount[ count ].replace( "%", "" )
                except :
                  print "[Weather Plus] precip_amount["+str(count)+"] is not available"
                  precip_amount += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + outlook[ count ]
                except :
                  print "[Weather Plus] outlook["+str(count)+"] is not available"
                  outlook += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + daylight[ count ][ 0 ]
                except :
                  print "[Weather Plus] daylight["+str(count)+"][0] is not available"
                  daylight += [ ("N/A", ) ]
                try :
                  print "[Weather Plus] " + _localize_unit( str(int(daylight[count][1].split(" ")[3].split(":")[0])-time_diff) + ":" + daylight[count][1].split(" ")[3].split(":")[1], "time"  )
                  self.forecast += [ ( days[count], iconpath, brief[ count ], temperature_info[ count ], _localize_unit( temperature[ count ] ), precip_title[ count ], precip_amount[ count ].replace( "%", "" ), outlook[ count ], daylight[ count ][ 0 ], _localize_unit( str(int(daylight[count][1].split(" ")[3].split(":")[0])-time_diff) + ":" + daylight[count][1].split(" ")[3].split(":")[1], "time"  ), ) ]
                except :
                  print "[Weather Plus] daylight["+str(count)+"][1] is not available"
                  self.forecast += [ ( days[count], iconpath, brief[ count ], temperature_info[ count ], _localize_unit( temperature[ count ] ), precip_title[ count ], precip_amount[ count ].replace( "%", "" ), outlook[ count ], daylight[ count ][ 0 ], "N/A", ) ]
            
        else:
	    print "[Weather Plus] No data fetched! Weather.com pages may have been changed."
	    self.error = 1

class ACCU_Forecast36HourParser:
    def __init__( self, htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4, translate=None ):
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
            self._get_forecast( htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4 )

    def _get_forecast( self, htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4 ):
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
				
	try:
		# fetch icons
		icon = []
		icondir = {"1":"32", "2":"30", "3":"28", "4":"30", "5":"34", "6":"28", "7":"26", "8":"26", "11":"19", "12":"11", "13":"39", "14":"39", "15":"3", "16":"37", "17":"37", "18":"12", "19":"14", "20":"14", "21":"14", "22":"16", "23":"16", "24":"25", "25":"25", "26":"25", "29":"5", "30":"36", "31":"32", "32":"23", "33":"31", "34":"29", "35":"27", "36":"27", "38":"27", "37":"33", "39":"45", "40":"45", "41":"47", "42":"47", "43":"46", "44":"46" }
		current_icon = icondir.get( re.findall( pattern_icon, htmlSource )[0] ) 
		current_icon = "/".join( [ "special://temp", "weather", "128x128", icondir.get( re.findall( pattern_icon, htmlSource )[0] ) + ".png" ] )
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
		    current_temp = _english_localize_unit( current_temp )
		    current_feel_like = _english_localize_unit( current_feel_like )
		    current_dew = _english_localize_unit( current_dew )
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
		        current_wind = current_wind.split(" ")[0]+" "+_english_localize_unit( current_wind.split(" ")[1], "speed" )
		    except:    # Calm or variable direction
		        current_wind = current_wind
			current_winddirection = ""
		    printlog ( "wind direction/speed split... Done!" )

		    precip_title = []
		    precip_amount = []

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
			  print "[Weather Plus] " + brief[ count+1 ]
			except :
			  print "[Weather Plus] iconpath is not available"
			  brief += [ ("N/A", ) ]
			try :
			  print "[Weather Plus] " + temperature_info[ count ]
			except :
			  print "[Weather Plus] temperature_info["+str(count)+"] is not available"
			  temperature_info += [ ("N/A", ) ]
			try :
			  print "[Weather Plus] " + _localize_unit( temperature[ count ] )
			except :
			  print "[Weather Plus] temperature["+str(count)+"] is not available"
			  temperature += [ ("N/A", ) ]
			try :
			  print "[Weather Plus] " + precip_title[ count ]
			except :
			  print "[Weather Plus] precip_title["+str(count)+"] is not available"
			  precip_title += [ ("N/A", ) ]
			try :
			  print "[Weather Plus] " + precip_amount[ count ].replace( "%", "" )
			except :
			  print "[Weather Plus] precip_amount["+str(count)+"] is not available"
			  precip_amount += [ "N/A" ]
			try :
			  print "[Weather Plus] " + brief[ count+ampm ]
			except :
			  print "[Weather Plus] brief["+str(count+ampm)+"] is not available"
			  brief += [ ("N/A", "N/A", "N/A", "N/A", ) ]
			try :
			  print "[Weather Plus] " + daylight[ count+ampm ][ 0 ]
			except :
			  print "[Weather Plus] daylight["+str(count+ampm)+"] is not available"
			  daylight += [ ("N/A", ) ]
			try :
			  print "[Weather Plus] " + _localize_unit( daylight[ count+ampm ][ 1 ], "time"  )
			except :
			  print "[Weather Plus] daylight["+str(count+ampm)+"] is not available"
			  daylight += [ ("00:00", ) ]

			self.forecast += [ ( days[count+ampm], iconpath, "", temperature_info[ count+ampm ], _english_localize_unit( temperature[ count+ampm ] ), precip_title[ count ], precip_amount[ count ].replace( "%", "" ), brief[ count+ampm ], daylight[ count+ampm ][ 0 ], _localize_unit( daylight[ count+ampm ][ 1 ], "time"  ), ) ]
		    printlog("ACCU_Forecast36HourParser : Done")
		    self.error = 0
		else:
		    printlog("ACCU_Forecast36HourParser : Stopped")
		    self.error = self.error + 1
		    return
	except:
	    self.error = self.error + 1
	    return

class NOAA_Forecast36HourParser:        # 36 hour and 10 day (actually 7 day) forecast parser
    def __init__( self, htmlSource, htmlSource_2, xmlSource, observSource, translate=None ):
        self.forecast = []
        self.extras = []
        self.alerts = []
        self.alertscolor = []
        self.video_location = []
        self.translate = translate
        self.sun = []

        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource, htmlSource_2, xmlSource, observSource )

    def _get_forecast( self, htmlSource, htmlSource_2, xmlSource, observSource ):
	printlog("Fetching Forecast from Noaa.gov...")
        # regex patterns
        pattern_days = "<b>(.+?): </b>"
	pattern_date = "<b>Forecast Valid:</b></a> (.+?)-"
	pattern_temperature = "Temp</font></a><br /><font style=\"font-size:18px\">([0-9]+)\&deg;</font>"
        pattern_forecast_brief = "<td class=\"weekly_weather\">(.+?)</td>"
	pattern_current_info = "<span class=\"obs_wxtmp\"> (.+?)<br />([0-9]+)\&deg;</span>"
	pattern_current_info_2 = "<span class=\"obs_wxtmp\">(.+?)<br />([0-9]+)\&deg;</span>"
	pattern_current_info_3 = "<font size=\'3\' color=\'000066\'>([^<]+)<br>[^<]+<br>(.+?)\&deg\;F<br>"
	pattern_current_windchill = "<td><b>Wind Chill</b>:</td>[^<]+<td align=\"right\">(.+?)\&deg\;F"
	pattern_current_heatindex = "<td><b>Heat Index</b>:</td>[^<]+<td align=[^>]+>(.+?)\&deg\;F"
	pattern_current_time = "Last Update:</b></a> (.+?)</span>"
	pattern_current_wind = "<td><b>Wind Speed</b>:</td>[^<]+<td align=[^>]+>(.+?)</td>"
	pattern_current_wind_2 = "<td><b>Wind Speed</b>:</td><td align=[^>]+>(.+?)<br>"
	pattern_current_humidity = "<td><b>Humidity</b>:</td>[^<]+<td align=[^>]+>(.+?) \%</td>"
	pattern_current_dew = "<td><b>Dewpoint</b>:</td>[^<]+<td align=[^>]+>(.+?)</td>"
	pattern_current_dew_2 = "<td><b>Dewpoint</b>:</td><td align=[^>]+>(.+?)</td>"
        pattern_precip_amount = "no-repeat;\">([0-9]+)\%</td><td class=\"weekly_wind\">"
        pattern_outlook = ": </b>(.+?)<br><br>"
        pattern_pressure = "<td><b>Barometer</b>:</td>[^<]+<td align=[^<]+ nowrap>(.+?)</td>"	
        pattern_pressure_2 = "<td><b>Barometer</b>:</td><td align=[^<]+ nowrap>(.+?)</td>"	                     
        pattern_visibility = "<td><b>Visibility</b>:</td>[^<]+<td align=\"right\">(.+?)</td>"	
	pattern_visibility_2 = "<td><b>Visibility</b>:</td><td align=[^<]+>(.+?)</td>"	
	pattern_sunrise = "sunrise will occur around (.+?)am"
	pattern_sunset = "sunset will occur around (.+?)pm"
	pattern_wind = "<td class=\"weekly_wind\"><img class=\"wind\" src=\"image/(.+?).png\" width=\"50\" height=\"22\" alt=\"[^\"]+\" /><br />(.+?)</td>"
	pattern_xml_high_temp = "<value>(.[0-9]+)</value>"
	pattern_xml_brief = "<weather-conditions weather-summary=\"(.+?)\"/>"	
	pattern_xml_days = "<start-valid-time period-name=\"(.+?)\">"
	pattern_icon = "<icon-link>(.+?).jpg</icon-link>"

        # fetch day title
	days_10day = re.findall( pattern_xml_days, xmlSource )
        printlog("days_10day : " + ",".join(days_10day))

 	# am or pm now?
	cor = 0
	if (days_10day[0] == "Late Afternoon" ): cor = 1
	ampm = 0
	if (days_10day[0] == "Tonight" or days_10day[0] == "Overnight"): ampm = 1
        printlog("ampm : " + str(ampm))

	# current info.
	pattern_current_icon = "<icon_url_name>(.+?).jpg"
	try:
		current_icon = re.findall( "([^\d\s]+)", re.findall( pattern_current_icon, observSource )[0] )[0]
	except:
		current_icon = "na"
	printlog( "Current Icon : %s" % current_icon )

	# fetch icons
	icon = []
	icons = re.findall( pattern_icon, xmlSource )
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
	current_icon = icondir.get( current_icon, "na" ) + ".png"
	current_icon = "/".join( [ "special://temp", "weather", "128x128", "%s" % current_icon ] )
	for count in range(0, 13-ampm):
		icon += [ icondir.get ( re.findall( "([^\d\s]+)", icons[count].split("/")[-1] )[0], "na" ) ]
	printlog("NOAA icons : " + ",".join(icon))

        # enumerate thru and combine the day with it's forecast
        if ( len( icon ) ):
	    printlog("Reforming data..")
	    # fetch today's date
	    today = re.findall( pattern_date, htmlSource )[0]
	    today = today.split(" ")[2] + " " + today.split(" ")[3].replace(",", " ")
	    printlog( "Today is %s" % today )
          
            # fetch brief description
	    current_info = re.findall( pattern_current_info, htmlSource_2 )
	    if ( len(current_info) ):
		current_brief = current_info[0][0]
	    else:
		try: 
			current_info = re.findall ( pattern_current_info_2, htmlSource_2 )
			current_brief = current_info[0][0]
		except:
			current_info = re.findall ( pattern_current_info_3, htmlSource_2 )
			current_brief = current_info[0][0]
            current_brief = current_brief.replace("'", "")

	    # brief = re.findall( pattern_forecast_brief, htmlSource_2 )   
	    brief = re.findall( pattern_xml_brief, xmlSource )   
	    # fetch wind
	    wind = re.findall( pattern_wind, htmlSource_2 )
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
            # print wind

            # fetch temperature
            current_temp = current_info[0][1]
	    try:
	        current_feel_like = re.findall( pattern_current_windchill, htmlSource )[0]
	    except:
	        try:
		    # print "******************************************************", htmlSource, re.findall( pattern_current_heatindex, htmlSource )
		    current_feel_like = re.findall( pattern_current_heatindex, htmlSource )[0]
		except:
		    current_feel_like = current_temp
	    temp = re.findall( pattern_temperature, htmlSource_2 )
	    xmltemp = re.findall( pattern_xml_high_temp, xmlSource )
	    if (ampm == 1):
		temp += [ xmltemp[ 12 ], xmltemp[ 6 ] ]
	    else:
		temp += [ xmltemp[ 6+cor ] ]
	    # last_temp = re.findall( pattern_xml_high_temp, xmlSource )[ [6, 12+cor][ampm] ]
	    temperature_info = ["High", "Low", "High", "Low"]
	    temperature = [ temp[0], temp[1], temp[2] ]

	    # fecth current infos
	    current_humidity = re.findall( pattern_current_humidity, htmlSource )[0]
	    current_winddirection = ""
	    try:
		current_dew = re.findall( pattern_current_dew, htmlSource )[0].split(" ")[0]
	    except:
		current_dew = re.findall( pattern_current_dew_2, htmlSource )[0].split(" ")[0].replace("&deg;F","")
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
	    try:
		pressure = _localize_unit( re.findall( pattern_pressure, htmlSource, re.DOTALL )[0].replace("&quot;","\"").replace("\"", "in."), "pressure" )
	    except:
		try:
		     pressure = re.findall( pattern_pressure, htmlSource, re.DOTALL )[0].replace("&quot;","\"")
		except:
			try:
				pressure = re.findall( pattern_pressure_2, htmlSource, re.DOTALL )[0].replace("&quot;","\"")
			except:
			        pressure = "N/A"
	    try:
		visibility = _localize_unit( re.findall( pattern_visibility, htmlSource, re.DOTALL )[0].replace("Miles","miles").replace("mi.","miles"), "distance" )
	    except:
		try:
		     visibility = _localize_unit( re.findall( pattern_visibility_2, htmlSource, re.DOTALL )[0].replace("Miles","miles").replace("mi.","miles"), "distance" )
		except:
		     visibility = "N/A"
            printlog("pressure, visibility : %s, %s" % ( pressure, visibility ))
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
	    current_temp = str( int(_localize_unit( current_temp )) )
	    current_feel_like = str( int(_localize_unit( current_feel_like )) )
	    current_dew = str( int(_localize_unit( current_dew )) )
	    self.extras += [( pressure, visibility, daylight[0][1], daylight[1][1], str(current_temp), current_feel_like, current_brief, current_wind, current_humidity, current_dew, current_icon, current_winddirection )]
	    days = ["Today", "Tonight", "Tomorrow", "Tomorrow Night", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]
            for count in range(0, 13):
                # make icon path
                try :
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", icon[ count + cor ] + ".png" ] )
                except :
                  printlog("Icon is not available")
                  iconpath = "/".join( [ "special://temp", "weather", "128x128", "na.png" ] ) 
		printlog( iconpath )
                # date calculation for 6 day
		date_day = int(today.split(" ")[ 1 ]) + int( (count+1)/2 )
		date_month = { "Jan":"1", 
		               "Feb":"2", 
			       "Mar":"3", 
			       "Apr":"4", 
			       "May":"5", 
			       "Jun":"6", 
			       "Jul":"7", 
			       "Aug":"8", 
			       "Sep":"9", 
			       "Oct":"10", 
			       "Nov":"11", 
			       "Dec":"12" }[ today.split(" ")[ 0 ] ]
		date_year = today.split(" ")[ 2 ]
		if ( date_day > 28 and date_month == "2" ):
			if ( int( date_year ) == int( date_year )/4 ):
				if ( int( date_year ) == int( date_year )/100 ):
					date_day = date_day - 28
				else:
					date_day = date_day - 29
			else:
				date_day = date_day - 28
		if ( date_day > 30 ):
			if ( date_month == "4" or date_month == "6" or date_month == "9" or date_month == "11" ):
				date_day = date_day - 30
				date_month = str( int(date_month) + 1 )
			elif ( date_day > 31 ):
				date_day = date_day - 30
				date_month = str( int(date_month) + 1 )
			if ( date_month == "13" ):
				date_month = "1"
				date_year = str( int(date_year) + 1 )
		date = str(date_day) + " " + date_month
                if ( count < 3 ): # just for logging
		  printlog(days[count+ampm])       # days is for 36 hour forecast ( today, tonight, tomorrow, tomorrow night ) 
		                                   # ampm = 0 : starting with "today", ampm = 1 : starting with "tonight"
		else:
		  printlog(days_10day[count+cor])  # days_10day is a date for 10 day (actually 7 day) forecast
		                                   # cor = 1 if days_10day starts with "late afternoon", skipping that.
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
                  printlog(_localize_unit( temperature[ count ] ))
                except :
                  printlog("temperature["+str(count)+"] is not available")
                  try :
			temperature += [ temp[ count ] ]
			printlog("Added : "+ _localize_unit( temperature[ count ] ))
		  except :
			temperature += [ "N/A" ]
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
		  windspeed = " ".join( [ _localize_unit( wind_temp[0], "speed" ), wind_temp[1], _localize_unit( wind_temp[1], "speed" ) ] )
		except: # if no gust
		  windspeed = _localize_unit( wind[count][1].split(" ")[0], "speed" )

		self.forecast += [ ( days[count+ampm],						# [0] 36hour.%d.Heading
		                     iconpath,							# [1] 36hour.%d.OutlookIcon or Daily.%d.OutlookIcon
				     brief[ count ],						# [2] 36hour.%d.Outlook or Daily.%d.Outlook
				     temperature_info[ count+ampm ], 
				     _localize_unit( temperature[ count ] ), 
				     precip_title[ count ], 
				     precip_amount[ count ].replace( "%", "" ), 
				     outlook[ count ], 
				     daylight[ count+ampm ][ 0 ], 
				     _localize_unit( daylight[ count+ampm ][ 1 ], "time"  ), 
				     days_10day[count+cor].replace("This Afternoon", "Today"), 
				     date, 
				     windir.get(wind[count][0]),				# [12] Daily.%d.WindDirection
				     windspeed,							# [13] Daily.%d.WindSpeed
				     wind[count][0] ) ]						# [14] Daily.%d.ShortWindDirection

#**********************************************************
#                                                         *
#         Wunderground.com Parsers                        *
#                                                         *
#**********************************************************
class WUNDER_Forecast36HourParser:
    def __init__( self, htmlSource, translate=None ):
        self.forecast = []
        self.extras = []
        self.alerts = []
        self.alertscolor = []
        self.video_location = []
        self.translate = translate
        self.sun = []

        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
	print "[Weather Plus] Fetching Forecast from Wunderground.com..."
        # regex patterns
        pattern_days = "<div class=\"titleSubtle\">(.+?)</div>"
	pattern_low_temp = "([0-9]+) \&deg;"
	pattern_high_temp = "<span class=\"b\">([0-9]+)</span> \&deg;"
	pattern_icon = "http://icons-ak.wxug.com/i/c/k/(.+?).gif"
        pattern_brief = "<div class=\"foreCondition\">([^<]+)<[^>]+>([^<]+)<"
	pattern_current_brief = "alt=\"([^\"]+)\" class=\"condIcon\""
	pattern_current_date = "<div id=\"infoTime\"><span>(.+?)</span>"
	pattern_current_temp = "<div id=\"tempActual\"><span class=\"pwsrt\" pwsid=\"[^\"]+\" pwsunit=\"english\" pwsvariable=\"tempf\" english=\"\&deg;F\" metric=\"\&deg;C\" value=\"(.+?)\""
	pattern_current_feelslike = "<span class=\"nobr\"><span class=\"b\">([^<]+)</span>\&nbsp;\&deg;"
	pattern_current_wind = "metric=\"\" value=\"(.+?)\""
	pattern_current_windspeed = "pwsvariable=\"windspeedmph\" english=\"\" metric=\"\">(.+?)</span>"
	pattern_current_humidity = "pwsvariable=\"humidity\" english=\"\" metric=\"\" value=\"(.+?)\""
	pattern_current_dew = "pwsvariable=\"dewptf\"  english=\"\&deg;F\" metric=\"\&deg;C\" value=\"(.+?)\""
	pattern_current_uvindex = "<div class=\"dataCol4\"><span class=\"b\">([^<]+)</span> out of 16</div>"
	pattern_current_time = "<div id=\"infoTime\"><span>(.+?)</span>"
        pattern_precip_amount = "no-repeat;\">([0-9]+)\%</td><td class=\"weekly_wind\">"
        pattern_outlook = "<td class=\"vaT full\">(.+?)</td>"
        pattern_pressure = "pwsvariable=\"baromin\" english=\"in\" metric=\"hPa\" value=\"([^>]+)\">"	
        pattern_visibility = "<div class=\"dataCol1\"><dfn>Visibility</dfn></div>[^<]+<div class=\"dataCol4\">[^<]+<span class=\"nobr\"><span class=\"b\">([^<]+)</span>"	
	pattern_sunrise = "<div id=\"sRise\"><span class=\"b\">(.+?)</span> AM</div>"
	pattern_sunset = "<div id=\"sSet\"><span class=\"b\">(.+?)</span> PM</div>"
	pattern_next_sunrise = "<div id=\"sRiseHr\" style=\"[^\"]+\"><span class=\"b\">(.+?)</span> AM</div>"
	pattern_next_sunset = "<div id=\"sSetHr\" style=\"[^\"]+\"><span class=\"b\">(.+?)</span> PM</div>"
	pattern_date = "<div class=\"fctDayDate\">[^,]+, ([0-9]+)</div>"
	pattern_wind = "<td class=\"weekly_wind\"><img class=\"wind\" src=\"image/(.+?).png\" width=\"50\" height=\"22\" alt=\"[^\"]+\" /><br />(.+?)</td>"
	
        # fetch info.
	raw_days = re.findall( pattern_days, htmlSource )
	high_temp = re.findall( pattern_high_temp, htmlSource )
	low_temp = re.findall( pattern_low_temp, htmlSource )
	raw_brief = re.findall( pattern_brief, htmlSource )
	raw_icons = re.findall( pattern_icon, htmlSource )
	raw_outlook = re.findall( pattern_outlook, htmlSource )
	current_date = re.findall( pattern_current_date, htmlSource )
	current_brief = re.findall( pattern_current_brief, htmlSource )
	current_temp = re.findall( pattern_current_temp, htmlSource )
	current_feelslike = re.findall( pattern_current_feelslike, htmlSource )
	current_wind = re.findall( pattern_current_wind, htmlSource )
	current_windspeed = re.findall( pattern_current_windspeed, htmlSource )
	current_pressure = re.findall( pattern_pressure, htmlSource )
	current_visibility = re.findall( pattern_visibility, htmlSource )
	current_dew = re.findall( pattern_current_dew, htmlSource )
	current_humidity = re.findall( pattern_current_humidity, htmlSource )
	current_uvindex = re.findall( pattern_current_uvindex, htmlSource )
	current_precip = "N/A"
	current_sunrise = re.findall( pattern_sunrise, htmlSource )
	current_sunset = re.findall( pattern_sunset, htmlSource )
	next_sunrise = re.findall( pattern_next_sunrise, htmlSource )
	next_sunset = re.findall( pattern_next_sunset, htmlSource )
	dates = re.findall( pattern_date, htmlSource )

	print "[Weather Plus] Wunderground.com, Fetched Raw Info :"
	print raw_days, high_temp, low_temp, raw_brief, raw_icons, raw_outlook, current_temp, current_date, dates, current_feelslike, current_wind, current_windspeed
	print current_pressure, current_visibility, current_dew, current_humidity, current_uvindex, current_sunrise, current_sunset

	try:
		days = [ raw_days[6], raw_days[7], raw_days[8] ]
		icons = [ raw_icons[3], raw_icons[4], raw_icons[5] ]
		brief = [ raw_brief[0][0], raw_brief[1][0], raw_brief[2][0] ]
		outlook = [ raw_outlook[0].replace("&deg;", ""), raw_outlook[1].replace("&deg;", ""), raw_outlook[2].replace("&deg;", "") ]
		precips = [ raw_brief[0][1], raw_brief[1][1], raw_brief[2][1] ]
		print "[Weather Plus] Icons, Briefs, Outlooks, Precips OK!"
		current_ampm = current_date[0].split(",")[0].split(" ")[1]
		current_date = current_date[0].split(",")[0].split(" ")[-1]
		print "[Weather Plus] Current Date, Time OK!"
		current_icon = raw_icons[2]
		current_brief = current_brief[0]
		print "[Weather Plus] Current Icon, Brief OK!"
		current_temp = _localize_unit( str( round( float( current_temp[0]) ) ).split(".")[0], "temp" )
		current_feelslike = _localize_unit( str( round( float( current_feelslike[0]) ) ).split(".")[0], "temp" )
		print "[Weather Plus] Current Temperature, Feels like OK!"
		try:
			current_pressure = _localize_unit( current_pressure[0], "pressure" )
		except:
			current_pressure = "N/A"
		try:
			current_visibility = _localize_unit ( current_visibility[0], "distance" )
		except:
			current_visibility = "N/A"
		print "[Weather Plus] Pressure, Visibility OK!"
		current_dew = _localize_unit( current_dew[0], "temp" )
		current_humidity = current_humidity[0]
		print "[Weather Plus] Dew point, Humidity OK!"
		uvindex_dir = {
			"0": "Low", "1": "Low", "2": "Low", "3": "Minimal", "4": "Minimal", "5": "Moderate", "6": "Moderate",
			"7": "High", "8": "High", "9": "High", 
			"10": "Very high", "11": "Very high", "12": "Very high", "13": "Very high", "14": "Very high", "15": "Very high", "16": "Very high"
			}
		try:
			current_uvindex = "%s %s" % ( current_uvindex[0].split(".")[0], uvindex_dir.get( current_uvindex[0].split(".")[0], "" ) )
		except:
			current_uvindex = "N/A"
		print "[Weather Plus] UV Index OK!"
		# current sunrise, sunset
		current_sunrise = _localize_unit( current_sunrise[0]+" AM", "time" )
		current_sunset = _localize_unit( current_sunset[0]+" PM", "time" )
		# making daylight info.
		if ( current_date != dates[0] ): 
			if ( days[0] == "Today" ):
				daylight = [ current_sunrise, current_sunset, _localize_unit( next_sunrise[0]+" AM", "time" ) ]
			else:
				daylight = [ current_sunset, _localize_unit( next_sunrise[0]+" AM", "time" ),  _localize_unit( next_sunset[0]+" PM", "time" ) ]  
		else:
			if ( days[0] == "Today" ):
				daylight = [ current_sunrise, current_sunset, _localize_unit( next_sunrise[1]+" AM", "time" ) ]
			elif ( current_ampm == "PM" ):
				daylight = [ current_sunset, _localize_unit( next_sunrise[1]+" AM", "time" ),  _localize_unit( next_sunset[1]+" PM", "time" ) ]  
			else:
				daylight = [ "N/A", _localize_unit( next_sunrise[0]+" AM", "time" ),  _localize_unit( next_sunset[0]+" PM", "time" ) ]  
				
		print "[Weather Plus] sunrise, sunset OK!"
		current_wind = int(current_wind[0])
		current_windspeed = current_windspeed[0]

		if ( current_wind < 11.25 ):
			current_wind = "N"
		elif ( current_wind < 11.25 + 22.5 * 1 ):
			current_wind = "NNE"
		elif ( current_wind < 11.25 + 22.5 * 2 ):
			current_wind = "NE"
		elif ( current_wind < 11.25 + 22.5 * 3 ):
			current_wind = "ENE"
		elif ( current_wind < 11.25 + 22.5 * 4 ):
			current_wind = "E"
		elif ( current_wind < 11.25 + 22.5 * 5 ):
			current_wind = "ESE"
		elif ( current_wind < 11.25 + 22.5 * 6 ):
			current_wind = "SE"
		elif ( current_wind < 11.25 + 22.5 * 7 ):
			current_wind = "SSE"
		elif ( current_wind < 11.25 + 22.5 * 8 ):
			current_wind = "S"
		elif ( current_wind < 11.25 + 22.5 * 9 ):
			current_wind = "SSW"
		elif ( current_wind < 11.25 + 22.5 * 10 ):
			current_wind = "SW"
		elif ( current_wind < 11.25 + 22.5 * 11 ):
			current_wind = "WSW"
		elif ( current_wind < 11.25 + 22.5 * 12 ):
			current_wind = "W"
		elif ( current_wind < 11.25 + 22.5 * 13 ):
			current_wind = "WNW"
		elif ( current_wind < 11.25 + 22.5 * 14 ):
			current_wind = "NW"
		elif ( current_wind < 11.25 + 22.5 * 15 ):
			current_wind = "NNW"

		if ( current_windspeed == "0.0" ):
			current_wind = "Calm"
		else:
			current_wind = "From %s %s" % (current_wind[0], _localize_unit(current_windspeed, "speed"))

		if ( days[0] == "Today" ):
			temperature = [ high_temp[0], low_temp[4], high_temp[1] ]
			temperature_info = [ "High", "Low", "High" ]
			daylight_title = [ "Sunrise", "Sunset", "Sunrise" ]
			days = [ "Today", "Tonight", "Tomorrow" ]
		elif ( current_ampm == "AM" ):
			temperature = [ low_temp[4], high_temp[0], low_temp[6] ]
			temperature_info = [ "Low", "High", "Low" ]
			daylight_title = [ "Sunset", "Sunrise", "Sunset" ]
			days = [ "Tonight", "Tomorrow", "Tomorrow Night" ]
   			outlook = [ "N/A", raw_outlook[0].replace("&deg;", ""), raw_outlook[1].replace("&deg;", "") ]
		else:
			temperature = [ low_temp[4], high_temp[0], low_temp[6] ]
			temperature_info = [ "Low", "High", "Low" ]
			daylight_title = [ "Sunset", "Sunrise", "Sunset" ]
			days = [ "Tonight", "Tomorrow", "Tomorrow Night" ]


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
		
		current_icon = icondir.get( current_icon, "na" )

	except:
		self.forecast = [ "ERROR", ]
		return
	
	print "[Weather Plus] Wunderground.com, Modified Info :"
	print days, temperature, brief, icons, outlook, current_date, current_icon, current_brief, current_temp, current_feelslike, current_wind, current_windspeed
	print current_pressure, current_visibility, current_dew, current_humidity, current_uvindex, current_sunrise, current_sunset

   	self.extras += [( current_pressure, current_visibility, current_sunrise, current_sunset, current_temp, current_feelslike, current_brief, current_wind, current_humidity, current_dew, "/".join( [ "special://temp", "weather", "128x128", "%s.png" % current_icon ] ), current_uvindex )]

	normalized_outlook = _normalize_outlook ( outlook )

	for count in range(0,3) :
		iconpath = "/".join( [ "special://temp", "weather", "128x128", "%s.png" % icondir.get( icons[ count ], "na" ) ] )
		if ( precips[ count ] == "\n\t\t" ):
			precip = "N/A"
		else:
			precip = precips[ count ].split("%")[0]
		try:
			self.forecast += [ ( days[count], iconpath, brief[ count ], temperature_info[ count ], _localize_unit( temperature[ count ] ), "", precip, normalized_outlook[ count ], daylight_title[ count ], daylight[ count ], "N/A", "N/A", "" ) ]	
		except:
			self.forecast = [ "ERROR", ]
			return

class WUNDER_Forecast10DayParser:
    def __init__( self, htmlSource, translate ):
	self.forecast = []
	self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
	# regex patterns
        pattern_first_heading = "<div class=\"titleSubtle\">(.+?)</div>"
	pattern_time = "<div id=\"infoTime\"><span>(.+?)</span>"
	pattern_date = "<div class=\"fctDayDate\">([^,]+), ([0-9]+)</div>"
	pattern_icon_cond = "<div class=\"fctCondIcon\"><a href=\"\" class=\"iconSwitchMed\"><img src=\"http://icons-ak.wxug.com/i/c/k/(.+?).gif\" alt=\"(.+?)\""
	pattern_hi_low = "<div class=\"fctHiLow\">[^<]+<span class=\"b\">([0-9]+)</span> [|] (.+?)\n"
	pattern_precip = "<div class=\"popValue\">(.+?)%</div>"

	# fetch info.
	print "[Weather Plus] Fetching Extended Forecast from Wunderground.com..."
	local_time = re.findall( pattern_time, htmlSource )
	dates = re.findall( pattern_date, htmlSource )
	icon_cond = re.findall( pattern_icon_cond, htmlSource )
	hi_low = re.findall( pattern_hi_low, htmlSource )
	precip = re.findall( pattern_precip, htmlSource )
	print dates, icon_cond, hi_low, precip
	
	try:
		first_heading = re.findall( pattern_first_heading, htmlSource )[6]
		current_ampm = local_time[0].split(",")[0].split(" ")[1]
		print first_heading
		today = local_time[0].split(",")[0].split(" ")[-1]
		print today
		month = local_time[0].split(" ")[4]
		print month
		month_dir = {
			"January": "1",
			"February": "2",
			"March": "3",
			"April": "4",
			"May": "5",
			"June": "6",
			"July": "7",
			"August": "8",
			"September": "9",
			"October": "10",
			"November": "11",
			"December": "12"
		}
		month_list = [ "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" ]
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
	
		month = month_dir.get( month )
		# print month

		for count in range( 0, 7 ):
			iconpath = "/".join( [ "special://temp", "weather", "128x128", "%s.png" % icondir.get( icon_cond[ count ][0], "na" ) ] )
			print iconpath, dates[count], icon_cond[count], hi_low[count], precip[count]
			if( count == 0 and today == dates[0][1] ):
				if( first_heading == "Tonight" ):
					if( current_ampm == "PM" ):				
						self.forecast += [ ( "CACHE", "%s %s" % ( month_list[int(month)-1], today ), "", "", "", "", "", "", "", "" ) ]
						continue		
			if( count != 0 ):
				if( int( dates[count][1] ) < int( dates[count-1][1] ) ):
					month = str( int(month) + 1 )
			try:
				self.forecast += [ ( ["Today", dates[count][0]][ count != 0 ], "%s %s" % ( month_list[int(month)-1], dates[count][1] ), iconpath, icon_cond[count][1], _localize_unit(hi_low[count][0], "temp"), _localize_unit(hi_low[count][1], "temp"), precip[count], "N/A", "N/A", "N/A" ) ]
			except:
				self.forecast += [ ( ["Today", dates[count][0]][ count != 0 ], "%s %s" % ( month_list[int(month)-1], dates[count][1] ), iconpath, icon_cond[count][1], _localize_unit(hi_low[count][0], "temp"), "N/A", precip[count], "N/A", "N/A", "N/A" ) ]
			print self.forecast
		
		print "[Weather Plus] Extended Forecast Done.."
		return
		
	except:
		self.forecast = [ "ERROR", ]
		return

class WUNDER_ForecastHourlyParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
	# regex patterns
	pattern_hour = "<th class=\"taC\">([^<]+)</th>"
	pattern_temp = "<div>([0-9]+) / [0-9]+</div>[^<]+<div class=\"hourlyBars\">"
	pattern_icon = "<img src=\"http://icons-ak.wxug.com/i/c/k/(.+?).gif\""
	pattern_cond = "alt=\"\" class=\"condIcon\" /></a></div>([^<]+)</td>"
	pattern_percent = "([0-9]+)[%]"
	pattern_wind = "<img src=\"http://icons-ak.wxug.com/graphics/[^.]+.gif\" width=\"[^\"]+\" height=\"[^\"]+\" alt=\"[^\"]+\" /></div>[^<]+<div>([^<]+)</div>"
	pattern_time = "<div id=\"infoTime\"><span>(.+?)</span>"

	# fetch info.
	print "[Weather Plus] Fetching Hourly Forecast from Wunderground.com..."
	raw_hour = re.findall( pattern_hour, htmlSource )
	temp = re.findall( pattern_temp, htmlSource )
	icon = re.findall( pattern_icon, htmlSource )
	cond = re.findall( pattern_cond, htmlSource )
	percent = re.findall( pattern_percent, htmlSource )
	wind = re.findall( pattern_wind, htmlSource )
	local_time = re.findall( pattern_time, htmlSource )
	# print icon, cond, percent, wind

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

	windir = {    
		    "North": "From the North",
		    "NNE": "From the North Northeast",
		    "NE": "From the Northeast",
		    "ENE": "From the East Northeast",
		    "East": "From the East",
		    "ESE": "From the East Southeast",
		    "SE": "From the Southeast",
		    "SSE": "From the South Southeast",
		    "South": "From the South",
		    "SSW": "From the South Southwest",
		    "SW": "From the Southwest",
		    "WSW": "From the West Southwest",
		    "West": "From the West",
		    "WNW": "From the West Northwest",
		    "NW": "From the Northwest",
		    "NNW": "From the North Northwest"
        }

	try:
		# making hour table
		print "[Weather Plus] Making Forecast Table.."
		current_hour = int( local_time[0].split(":")[0] )
		if ( local_time[0].split(" ")[1] == "PM" ): current_hour + 12
		hour_ampm = ""
		forecast_table = []
		for count in range(0, len(raw_hour)-1):
			iconpath_1 = "/".join( [ "special://temp", "weather", "128x128", "%s.png" % icondir.get( icon[ count ], "na" ) ] )
			iconpath_2 = "/".join( [ "special://temp", "weather", "128x128", "%s.png" % icondir.get( icon[ count+1 ], "na" ) ] )
			try:
				windspeed_1 = _localize_unit( wind[count].split(" mph ")[0], "speed" )
			except:
				windspeed_1 = wind[count].split(" mph ")[0]
			try:
				windspeed_2 = _localize_unit( wind[count+1].split(" mph ")[0], "speed" ) 
			except:
				windspeed_2 = wind[count+1].split(" mph ")[0]
			winddirection_1 = wind[count].split(" mph ")[1]
			winddirection_2 = wind[count+1].split(" mph ")[1]
			hour = raw_hour[count].replace("&nbsp;"," ")
			hour_digit = int( hour.split(" ")[0] )
			if ( hour_ampm == "" ): hour_ampm = hour.split(" ")[1]
			newhour = []
			for x in range(0, 2):
				hour_digit = hour_digit + 1
				if( hour_digit == 12 ):
					hour_ampm = [ "AM", "PM" ][ hour_ampm == "AM" ]
				elif( hour_digit > 12 ):
					hour_digit = hour_digit - 12
				newhour += [ "%d %s" % ( hour_digit, hour_ampm ) ]
		
			forecast_table += [ 
				( hour, "", iconpath_1, temp[count], cond[count].replace("\n","").replace("\t",""), "N/A", percent[ [count+8, count+24][count>7] ], percent[ [count, count+16][count>7] ], windir.get( winddirection_1, winddirection_1 ), windspeed_1, winddirection_1 ),
				( newhour[0], "", iconpath_1, str((int(temp[count])*2 + int(temp[count+1]))/3), cond[count].replace("\n","").replace("\t",""), "N/A", percent[ [count+8, count+24][count>7] ], percent[ [count, count+16][count>7] ], windir.get( winddirection_1, winddirection_1 ), windspeed_1, winddirection_1 ),
				( newhour[1], "", iconpath_2, str((int(temp[count]) + int(temp[count+1])*2)/3), cond[count+1].replace("\n","").replace("\t",""), "N/A", percent[ [count+8, count+25][count+1>7] ], percent[ [count, count+17][count>7] ], windir.get( winddirection_2, winddirection_2 ), windspeed_2, winddirection_2 )
			]
		for count in range(0, 12):
			self.forecast += [ forecast_table[count + current_hour - 1], ]
			
		print "[Weather Plus] Forecast Table : ", self.forecast
				
	except:
		return


	

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
        """
        pattern_time = "<div class=\"hbhTDTime[^>]+><div>([^<]+)</div>"
        pattern_icon = "<div class=\"hbhTDConditionIcon\"><div><img src=\"http://i.imwx.com/web/common/wxicons/[0-9]+/(gray/)?([0-9]+).gif\""
        pattern_brief = "<div class=\"hbhTDCondition\"><div><b>([^<]+)</b><br>([^<]+)</div>"
        pattern_feels = "<div class=\"hbhTDFeels\"><div>([^<]*)</div>"
        pattern_precip = "<div class=\"hbhTDPrecip\"><div>([^<]*)</div>"
        pattern_humidity = "<div class=\"hbhTDHumidity\"><div>([^<]*)</div>"
        pattern_wind = "<div class=\"hbhTDWind\"><div>([^<]*)<br>([^<]*)</div>"
        """
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

class ACCU_ForecastHourlyParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
	self.error = 0
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
        # regex patterns
	pattern_date = [ "([0-9]+)/([0-9]+)/20", "([0-9]+)-([0-9]+)-20" ]
        pattern_info = "<div class=\".+?textBold\">([^<]+)</div>"
	pattern_brief = "<div class=\".+?hbhWxText\">([^<]+)</div>"
	pattern_icon = "wxicons/31x24/(.+?).gif"
	pattern_wind = "winds/24x24/(.+?).gif"
        # fetch info
	date = re.findall( pattern_date[0], htmlSource )
        raw_info = re.findall( pattern_info, htmlSource )
	raw_brief = re.findall( pattern_brief, htmlSource )
	icon = re.findall( pattern_icon, htmlSource )
	wind = re.findall( pattern_wind, htmlSource )
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
	icondir = {"1":"32", "2":"30", "3":"28", "4":"30", "5":"34", "6":"28", "7":"26", "8":"26", "11":"19", "12":"11", "13":"39", "14":"39", "15":"3", "16":"37", "17":"37", "18":"12", "19":"14", "20":"14", "21":"14", "22":"16", "23":"16", "24":"25", "25":"25", "26":"25", "29":"25", "30":"36", "31":"32", "32":"23", "33":"31", "34":"29", "35":"27", "36":"27", "38":"27", "37":"33", "39":"45", "40":"45", "41":"47", "42":"47", "43":"46", "44":"46" }       
	# we convert wind direction to full text
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
                            "NNW": "From the North Northwest"
		}
	for count in range(0, 7):
	    info += [ ( info_[count], icondir.get( icon[count] ), brief[count], info_[count+7], info_[count+14], info_[count+21], info_[count+28], windir.get( wind[count] ), info_[count+35], info_[count+42] ) ]
	for count in range(49, 56):
	    try:
	        info += [ ( info_[count], icondir.get( icon[count-43] ), brief[count-43], info_[count+7], info_[count+14], info_[count+21], info_[count+28], windir.get( wind[count-43] ), info_[count+35], info_[count+42] ) ]
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
                # does sunrise/sunset fit in this period
                sunrise = ""
                sunset = ""
		# we want 24 hour as the math is easier
                # period = _localize_unit( item[ 0 ], "time24" )
                # set to a high number, we use this for checking next time period
                # period2 = "99:00"
                # if ( count < len( info ) - 2 ):
                #    period2 = _localize_unit( info[ count + 1 ][ 0 ], "time24" )
                #    period2 = ( period2, "24:%s" % ( period2.split( ":" )[ 1 ], ), )[ period2.split( ":" )[ 0 ] == "0" ]
                # add result to our class variable
                try:
		   self.forecast += [ ( _localize_unit( item[ 0 ], "time" ), " ".join( dates[ date_counter ] ), iconpath, _english_localize_unit( item[ 3 ].split("°")[0] ), item[ 2 ], _english_localize_unit( item[ 4 ].split("°")[0] ), item[ 9 ].replace( "%", "" ), item[ 6 ].replace( "%", "" ), item[ 7 ], _english_localize_unit( item[ 8 ], "speed" ), item[ 7 ].split( " " )[ -1 ], "", "", ) ]
		except:
		   try:
		        self.forecast += [ ( item[ 0 ], " ".join( dates[ date_counter ] ), iconpath, _english_localize_unit( item[ 3 ].split("°")[0] ), item[ 2 ], _english_localize_unit( item[ 4 ].split("°")[0] ), item[ 9 ].replace( "%", "" ), item[ 6 ].replace( "%", "" ), item[ 7 ], _english_localize_unit( item[ 8 ], "speed" ), item[ 7 ].split( " " )[ -1 ], "", "", ) ]
		   except:
		        self.error = self.error + 1
			return


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
	pattern_humid = "<td align=\"center\" width=\"3%\"><font color=\"#009900\" size=\"1\"><b>(.+?)</b></font></td>"
	pattern_precip = "<font color=\"#996633\" size=\"1\"><b>(.+?)</b></font>"
	pattern_wind = "<font color=\"#990099\" size=\"1\"><b>(.+?)</b></font>"
	pattern_winddir = "<font color=\"#666666\" size=\"1\"><b>(.+?)</b></font>"

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
                            "NNW": "From the North Northwest"
                 }   
	
	for count in range( 0, 24 ):
		hour = int( hours[ count ].replace("<b>","").replace("</b>","") )
		if( hour > 12 ):
			hour -= 12
			hour = str(hour) + ":00 PM"
		else:
			hour = str(hour) + ":00 AM"
		self.forecast += [ ( _localize_unit( hour, "time" ), dates[ count ], "special://temp/weather/128x128/na.png", temperature[ count ], "N/A", "N/A", precip[ count ], humidity[ count ], windir.get( wind_direction[ count ] ), _localize_unit( wind[ count ]+" mph", "speed" ), "" ) ]		

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
        for  i in range( 3 - len( observeds ) ):
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


class ACCU_Forecast10DayParser:
    def __init__( self, htmlSource_1, htmlSource_2, translate ):
        self.forecast = []
        self.translate = translate
	self.error = 0
        # only need to parse source if there is source
        if ( htmlSource_1 and htmlSource_2 ):
            self._get_forecast( htmlSource_1, htmlSource_2 )

    def _get_forecast( self, htmlSource_1, htmlSource_2 ):
        # regex patterns
        pattern_day = "Day_ctl0[0-9]+_lblDate\">(.+?)</span>"
	pattern_outlook = "Day_ctl0[0-9]+_lblDesc\">(.+?)</span>"
        pattern_hightemp = "Day_ctl0[0-9]+_lblHigh\">(.+?)\&deg;"
	pattern_lowtemp = "Night_ctl0[0-9]+_lblHigh\">(.+?)\&deg;"
        pattern_icon = "/wxicons/87x79_blue/([0-9]+)_int.jpg"

	icondir = {"1":"32", "2":"30", "3":"28", "4":"30", "5":"34", "6":"28", "7":"26", "8":"26", "11":"19", "12":"11", "13":"39", "14":"39", "15":"3", "16":"37", "17":"37", "18":"12", "19":"14", "20":"14", "21":"14", "22":"16", "23":"16", "24":"25", "25":"25", "26":"25", "29":"5", "30":"36", "31":"32", "32":"23", "33":"31", "34":"29", "35":"27", "36":"27", "38":"27", "37":"33", "39":"45", "40":"45", "41":"47", "42":"47", "43":"46", "44":"46" }

        # fetch info
	htmlSource = htmlSource_1
	htmlSource_en = htmlSource_2
        days = re.findall( pattern_day, htmlSource_en )
	outlook = re.findall( pattern_outlook, htmlSource )
	hightemp = re.findall( pattern_hightemp, htmlSource )
	lowtemp = re.findall( pattern_lowtemp, htmlSource )
	icon = re.findall( pattern_icon, htmlSource )
	# print htmlSource
	# enumerate thru and create heading and forecast
	try:	
	    for count, day in enumerate(days):
	    	if (count<7):
		    iconpath = "/".join( [ "special://temp", "weather", "128x128", icondir.get( icon[count] ) + ".png" ] )
		else:
		    iconpath = "/".join( [ "special://temp", "weather", "128x128", icondir.get( icon[count+7] ) + ".png" ] )
	        self.forecast += [ ( day.split(" ")[0], day.split(" ")[1], iconpath, outlook[count].title(), _english_localize_unit( hightemp[count] ), _english_localize_unit( lowtemp[count] ), "N/A", "N/A", "N/A", "N/A" ) ]
	except:
	    self.error = self.error + 1


class Forecast10DayParser:
    def __init__( self, htmlSource, translate ):
        self.forecast = []
        self.translate = translate
        # only need to parse source if there is source
        if ( htmlSource ):
            self._get_forecast( htmlSource )

    def _get_forecast( self, htmlSource ):
        # regex patterns
        # pattern_headings = "<p id=\"tdHead[A-Za-z]+\">(.*)</p>"
        # pattern_headings2 = "<OPTION value=\"windsdp\" selected>([^<]+)</OPTION>"
        # pattern_info = "<p><[^>]+>([^<]+)</a><br>([^<]+)</p>\s.*\s.*\s.*\s.*\s\[^<]+<p><img src=\"http://i.imwx.com/web/common/wxicons/[0-9]+/([0-9]+).gif[^>]+><br>([^<]+)</p>\s.*\s.*\s.*\s.*\s[^<]+<p><strong>([^<]+)</strong><br>([^<]+)</p>\s.*\s.*\s.*\s.*\s.*\s[^<]+<p>([^<]+)</p>\s.*\s.*\s.*\s.*\s.*\s.*\s.*\s[^<]+<td><p>([^<]+)</p></td>\s.*\s.*\s\[^<]+<[^<]+<[^<]+<[^<]+<strong>([^<]+</strong>[^<]+)</p>"
	pattern_heading = "<th class=\"twc-col-[0-9]+ twc-forecast-when \" id=\"twc-date-col[0-9]+\">(.+?)<span>([^:]+):"
	pattern_icon = "http://s.imwx.com/v.20100719.135915/img/wxicon/45/([0-9]+).png"
	pattern_brief = "<span class=\"fc-wx-phrase\">([^<]+)</span>"
	pattern_high_temp = "id=\"twc-wx-hi[0-9]+\">([^<]+)<"
	pattern_low_temp = "id=\"twc-wx-low[0-9]+\">([^<]+)<"
	pattern_wind = "<div class=\"fc-wind-desc\"><strong>(.+?)<br>at<br>(.+?)</strong>"
	pattern_precip = "twc-line-precip\">(.+?):<br><strong>(.+?)</strong>"
	# print htmlSource
        # fetch headings
        heading = re.findall( pattern_heading, htmlSource )
	# print heading
	headings = [( heading[0][0], heading[0][1].replace("\n","").replace("\t","").split(" ")[1] + " " + heading[0][1].replace("\n","").replace("\t","").split(" ")[2] )]
	for count in range(1, 10):
		try:
			headings += [( heading[count][0].split(" ")[0], heading[count][0].split(" ")[1] + " " + heading[count][0].split(" ")[2] )]
		except:
			headings += [( "N/A", "N/A" )]
	# print headings
	# fetch icons
	icon = re.findall( pattern_icon, htmlSource )
	# print icon
	# fetch brief
	brief = re.findall( pattern_brief, htmlSource )
	# print brief
	# fetch temperatures
	high_temp = re.findall( pattern_high_temp, htmlSource )
	# print high_temp
	low_temp = re.findall( pattern_low_temp, htmlSource )
	# print low_temp
	# fetch wind
	wind = re.findall( pattern_wind, htmlSource )
	# print wind
	# fetch precip
	precip = re.findall( pattern_precip, htmlSource )
	# print precip
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
                # try: 
		#    text = "|".join( wind )
		# except:
		#   print "[Weather Plus] No Info : 10day Wind"
                # separator for different info
                text += "|||||"
                # we separate each item with single pipe
                try:
		   text += "|".join( brief )
		except:
		   print "[Weather Plus] No Info : 10day Brief"
                # translate text
                text = _translate_text( text, self.translate )
                # split text into it's original list
                # wind = text.split( "|||||" )[ 0 ].split( "|" )
                brief = text.split( "|||||" )[ 1 ].split( "|" )
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
            static_map_ = str(static_map_).replace("http://i.imwx.com/", "http://image.weather.com").replace("[", "").replace("]","").replace("\'","")
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
            # oops print error message
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
        # set our maps object
        self.maps += ( static_map, animated_maps, "", )
        # print "self.maps", self.maps


class WeatherClient:
    Addon = xbmcaddon.Addon( id="weather.weatherplus" )
    # base urls
    BASE_URL = "http://www.weather.com"
    BASE_FORECAST_URL = "http://www.weather.com/weather/%s/%s?%s"
    BASE_ACCU_FORECAST_URL = "http://www.accuweather.com/%s/%s.aspx?cityid=%s"
    BASE_NOAA_FORECAST_URL = "http://forecast.weather.gov/MapClick.php?%s"
    BASE_NOAA_QUICK_URL = "http://forecast.weather.gov/afm/PointClick.php?%s"
    BASE_NOAA_HOURLY_URL = "http://forecast.weather.gov/MapClick.php?%s&&FcstType=digital"
    BASE_WUNDER_FORECAST_URL = "http://www.wunderground.com/%s"
    BASE_VIDEO_URL = "http://v.imwx.com/v/wxcom/%s.mov"
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
                                # user defined #64
                                ( "User Defined - (Maps & Radars)", "*", ),
                            )

    # base paths
    if ( DEBUG ):
        BASE_MAPS_PATH = os.path.join( Addon.getAddonInfo("path"), "maps" )
        BASE_SOURCE_PATH = os.path.join( Addon.getAddonInfo("path"), "source" )
    else:
        BASE_MAPS_PATH = xbmc.translatePath( "/".join( [ "special://temp", Addon.getAddonInfo("id"), "maps" ] ) )
        BASE_SOURCE_PATH = xbmc.translatePath( "/".join( [ "special://profile", "script_data", Addon.getAddonInfo("id"), "source" ] ) )
    def __init__( self, code=None, translate=None, accu_translate=None ):
        # only check for compatibility if not debugging
        if ( not DEBUG ):
            # we raise an error if not compatible
            if ( not self._compatible() ):
                raise
        # set users locale
        self.code = code
        # set users translate preference
        self.translate = translate
	self.accu_translate = accu_translate

    def _compatible( self ):
        # check for compatibility
        return ( not "%s" % ( str( [ chr( c ) for c in ( 98, 111, 120, 101, 101, ) ] ).replace( "'", "" ).replace( ", ", "" )[ 1 : -1 ], ) in xbmc.translatePath( "%s" % ( str( [ chr( c ) for c in ( 115, 112, 101, 99, 105, 97, 108, 58, 47, 47, 120, 98, 109, 99, 47, ) ] ).replace( "'", "" ).replace( ", ", "" )[ 1 : -1 ], ) ).lower() )


#***********************************************************************
#*                                                                     *
#*                                                                     *
#*              def _solve_video( self, video_title )                  *
#*                                                                     *
#*                   - solving URL for US Forecast Video               *
#*                                                                     *
#*                                                                     *
#***********************************************************************

    def _solve_video( self, video_title ):
	urls = []
	count = 1
	for title in video_title:
		#***************************
		# criticalmedia
		#***************************
		if ( title == "ABC 15 (AZ)" ):
			htmlSource = self._fetch_data( "http://www.abc15.com/dpp/weather/forecast/todays_forecast/arizona-forecast", 15 )
			pattern_video = "http://media2.abc15.com//photo/(.+?)/Arizona_Weather_Foreca(.+?)0000"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://media2.abc15.com/video/criticalmedia/"+video[0][0]+"/Arizona_Weather_Foreca"+video[0][1]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 5 (Cleveland, OH)" ):
			htmlSource = self._fetch_data( "http://www.newsnet5.com/subindex/weather", 15 )
			pattern_video = "http://media2.newsnet5.com//photo/(.+?)/(.+?)_weat(.+?)0000"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://media2.newsnet5.com/video/criticalmedia/"+video[0][0]+"/"+video[0][1]+"_weat"+video[0][2]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WANE-TV (Fort Wayne, IN)" ):
			htmlSource = self._fetch_data( "http://www.wane.com/dpp/weather/video_forecast/Daily_Video_Forecast", 15 )
			pattern_video = "http://media2.wane.com//photo/(.+?)/(.+?)_forecast(.+?)0000_"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://media2.wane.com/video/criticalmedia/"+video[0][0]+"/"+video[0][1]+"_forecast"+video[0][2]+".mp4")]
			else:
				urls += [("")]

		#***************************
		# outboundFeed?
		#***************************

		elif ( title == "Wood TV8 (Grand Rapids, MI)" ):
			htmlSource = self._fetch_data( "http://www.woodtv.com/dpp/weather/storm_team_8_forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.woodtv.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "ABC 9 (Cincinnati, OH)" ):
			htmlSource = self._fetch_data( "http://www.wcpo.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.wcpo.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "WIVB 4 (Buffalo, NY)" ):
			htmlSource = self._fetch_data( "http://www.wivb.com/dpp/weather/video_forecast/news-4-weather-watch-forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.wivb.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 10 (Phoenix, AZ)" ):
			htmlSource = self._fetch_data( "http://www.myfoxphoenix.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxphoenix.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 11 (Los Angeles, CA)" ):
			htmlSource = self._fetch_data( "http://www.myfoxla.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxla.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (Washington D.C)" ):
			htmlSource = self._fetch_data( "http://www.myfoxdc.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxdc.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 35 (Orlando, FL)" ):
			htmlSource = self._fetch_data( "http://www.myfoxorlando.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxorlando.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 13 (Tampa, FL)" ):
			htmlSource = self._fetch_data( "http://www.myfoxtampabay.com/dpp/weather/video_forecast/weather_webcast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxtampabay.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (Atlanta, GA)" ):
			htmlSource = self._fetch_data( "http://www.myfoxatlanta.com/dpp/weather/video_forecast/Atlanta-Metro-Weather-Forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxatlanta.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 32 (Chicago, IL)" ):
			htmlSource = self._fetch_data( "http://www.myfoxchicago.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxchicago.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 25 (Boston, MA)" ):
			htmlSource = self._fetch_data( "http://www.myfoxboston.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxboston.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 2 (Detroit, MI)" ):
			htmlSource = self._fetch_data( "http://www.myfoxdetroit.com/subindex/weather/forecasts", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxdetroit.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 5 (New York, NY)" ):
			htmlSource = self._fetch_data( "http://www.myfoxny.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxny.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 13 (Memphis, TN)" ):
			htmlSource = self._fetch_data( "http://www.myfoxmemphis.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxmemphis.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 7 (Austin, TX)" ):
			htmlSource = self._fetch_data( "http://www.myfoxaustin.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxaustin.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 4 (Dallas-Fort Worth, TX)" ):
			htmlSource = self._fetch_data( "http://www.myfoxdfw.com/dpp/weather/Dallas_Fort_Worth_Forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxdfw.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 26 (Houston, TX)" ):
			htmlSource = self._fetch_data( "http://www.myfoxhouston.com/subindex/weather", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED[&]componentId=(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxhouston.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "FOX 9 (Minneapolis, MN)" ):
			htmlSource = self._fetch_data( "http://www.myfoxtwincities.com/subindex/weather", 15 )
			pattern_video = "componentId[%]3D(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.myfoxtwincities.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "ABC 8 (CT)" ):
			htmlSource = self._fetch_data( "http://www.wtnh.com/dpp/weather/storm_team_8_forecast", 15 )
			pattern_video = "/feeds/outboundFeed[?]obfType=VIDEO_PLAYER_SMIL_FEED&componentId=([0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				htmlSource = self._fetch_data( "http://www.wtnh.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=%s&FLVPlaybackVersion=1.0.2" % video[0] )
				# print htmlSource
				pattern_video = "src=\"([^\"]+)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [( video[0] )]
				else:
					urls += [("")]
			else:
				urls += [("")]

		#***************************
		# Xw6mu (NBC Style)
		#***************************

		elif ( title == "NBC 4 (Los Angeles, CA)" ):
			htmlSource = self._fetch_data( "http://www.nbclosangeles.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 7 (San Diego, CA)" ):
			htmlSource = self._fetch_data( "http://www.nbcsandiego.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 12 (San Jose, CA)" ):
			htmlSource = self._fetch_data( "http://www.nbcbayarea.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 30 (Hartford, CT)" ):
			htmlSource = self._fetch_data( "http://www.nbcconnecticut.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 4 (Washington D.C)" ):
			htmlSource = self._fetch_data( "http://www.nbcwashington.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 6 (Miami, FL)" ):
			htmlSource = self._fetch_data( "http://www.nbcmiami.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 5 (Chicago, IL)" ):
			htmlSource = self._fetch_data( "http://www.nbcchicago.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 4 (New York, NY)" ):
			htmlSource = self._fetch_data( "http://www.nbcnewyork.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 10 (Philadelphia, PA)" ):
			htmlSource = self._fetch_data( "http://www.nbcphiladelphia.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]
		elif ( title == "NBC 5 (Dallas-Forth Worth, PA)" ):
			htmlSource = self._fetch_data( "http://www.nbcdfw.com/weather/", 15 )
			pattern_video = "<[!]--Video Release ExtID: (.+?)-->"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				htmlSource = self._fetch_data( "http://link.theplatform.com/s/Xw6mu/%s?mbr=true&format=SMIL&Tracking=true&Embedded=true" % video [0] )
				pattern_video = "src=\"(.+?)\""
				video = re.findall( pattern_video, htmlSource )
				if ( video ):
					urls += [ (video[0]) ]
				else:
					urls += [ ("") ]
			else:
				urls += [("")]

		#***************************
		# cdn.bimfs.com
		#***************************
		
		elif ( title == "KHOU 11 (Houston, TX)" ):
			htmlSource = self._fetch_data( "http://www.khou.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KHOU/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KHOU/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 13 (Norfolk, VA)" ):
			htmlSource = self._fetch_data( "http://www.wvec.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WVEC/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WVEC/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC (Columbia, SC)" ):
			htmlSource = self._fetch_data( "http://www.abccolumbia.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WCCB/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WCCB/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 3 (Wilmington, NC)" ):
			htmlSource = self._fetch_data( "http://www.wwaytv3.com/daily-weather-update", 15 )
			pattern_video = "url: \"http://www.wwaytv3.com/video/news/video/weather/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://www.wwaytv3.com/video/news/video/weather/"+video[0]+".flv")]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Buffalo, NY)" ):
			htmlSource = self._fetch_data( "http://www.wkbw.com/video?sec=673914", 15 )
			pattern_video = "http://cdn.bimfs.com/WKBW/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WKBW/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "ABC 11 (Louisville, KY)" ):
			htmlSource = self._fetch_data( "http://www.whas11.com/weather", 15 )
			pattern_video = "http://cdn.bimfs.com/WHAS/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WHAS/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 58 (Milwaukee, WI)" ):
			htmlSource = self._fetch_data( "http://www.cbs58.com/weather", 15 )
			pattern_video = "http://cdn.bimfs.com/WDJT/(.+?).jpg"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WDJT/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 11 (Anchorage, Alaska)" ):
			htmlSource = self._fetch_data( "http://www.ktva.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KTVA/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KTVA/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "CBS 5 (Grand Junction, CO)" ):
			htmlSource = self._fetch_data( "http://www.krextv.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KREX/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KREX/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WINK-TV (Ft. Myers, FL)" ):
			htmlSource = self._fetch_data( "http://www.winknews.com/Watch-Forecast", 15 )
			pattern_video = "\"url\": \"http://http://cdn.winknews.com/videos/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.winknews.com/videos/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "WWL-TV 4 (New Orleans, LA)" ):
			htmlSource = self._fetch_data( "http://www.wwltv.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/WWLTV/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/WWLTV/"+video[0]+".mp4")]
			else:
				urls += [("")]
		elif ( title == "KOMV 4 (St. Louis, MO)" ):
			htmlSource = self._fetch_data( "http://www.kmov.com/weather", 15 )
			pattern_video = "\"url\": \"http://cdn.bimfs.com/KMOV/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [("http://cdn.bimfs.com/KOMV/"+video[0]+".mp4")]
			else:
				urls += [("")]

		#***************************
		# rtmp (Brightcove)
		#***************************

		elif ( title == "ABC 9 (Orlando, FL)" ):
			htmlSource = self._fetch_data( "http://www.wftv.com/s/weather/",  15 )
			# pattern_contentID = "<object id=\"myExperience([0-9]+)\" class=\"BrightcoveExperience\">"
			pattern_playerId = "<param name=\"playerID\" value=\"([0-9]+)\" />"
			pattern_playerKey = "<param name=\"playerKey\" value=\"([^\"]+)\"/>"
			pattern_contentId = "<param name=\"@videoList\" value=\"([0-9]+)\" />"	
			playerId = re.findall( pattern_playerId, htmlSource )
			playerKey = re.findall( pattern_playerKey, htmlSource )
			# playerKey = "AQ~~,AAAAPmbRNRk~,eMJgSV_RKKdQQ0LxUSni2YJuJke-LF5t"
			contentId = re.findall( pattern_contentId, htmlSource )
			print playerId, playerKey, contentId
			try:
				Response = AMF.get_rtmp( playerId[0], contentId[0], playerKey[0], "7a0deda8d3000831d003e195cc4f6135920cc954" )
				if ( Response ):
					url = "rtmp://cp131655.edgefcs.net:1935/ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s&affiliateId=/%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0], Response["FLVFullLengthURL"].split("&")[1] )
					app = "app=ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0]  )
					pageUrl = "pageUrl=http://www.wftv.com/s/weather/"
					swfUrl = "swfUrl=http://admin.brightcove.com/viewer/us20110929.2031/federatedVideoUI/BrightcovePlayer.swf"
					tcUrl = "tcUrl=rtmp://cp131655.edgefcs.net:1935/ondemand?videoId=%d&lineUpId=%s&pubId=%d&playerId=%s" % ( int(Response["id"]), contentId[0], int(Response["publisherId"]), playerId[0] )
					playpath = "playpath=%s" % Response["FLVFullLengthURL"].split("&")[1]
					urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				else:
					urls += [("")]
			except:
				urls += [("")]

		#***************************
		# rtmp (flv/xxxx/xxxx/xxxx)
		#***************************

		elif ( title == "ABC 13 (Colorado Springs, CO)" ):
			htmlSource = self._fetch_data( "http://www.krdo.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.29/ondemand?_fcs_vhost=cp92584.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp92584.edgefcs.net"
				pageUrl = "pageUrl=http://www.krdo.com/weather/index.html"
				swfUrl = "swfUrl=http://www.krdo.com/_public/lib/swf/flowplayer/flowplayer.swf?0.6832529801616092"
				tcUrl = "tcUrl=rtmp://96.7.215.29/ondemand?_fcs_vhost=cp92584.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Denver, CO)" ):
			htmlSource = self._fetch_data( "http://www.thedenverchannel.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.29/ondemand?_fcs_vhost=cp12930.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp12930.edgefcs.net"
				pageUrl = "pageUrl=http://www.thedenverchannel.com/weather/index.html"
				swfUrl = "swfUrl=http://www.thedenverchannel.com/_public/lib/swf/flowplayer/flowplayer.swf?0.47480804055357473"
				tcUrl = "tcUrl=rtmp://96.7.215.29/ondemand?_fcs_vhost=cp12930.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 8 (Grand Junction, CO)" ):
			htmlSource = self._fetch_data( "http://www.kjct8.com/weather/index.html", 15 )
			pattern_video = "flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				url = "rtmp://96.7.215.36/ondemand?_fcs_vhost=cp92587.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				app = "app=ondemand?_fcs_vhost=cp92587.edgefcs.net"
				pageUrl = "pageUrl=http://www.kjct8.com/weather/index.html"
				swfUrl = "swfUrl=http://www.kjct8.com/_public/lib/swf/flowplayer/flowplayer.swf?0.4733280426739924"
				tcUrl = "tcUrl=rtmp://96.7.215.36/ondemand?_fcs_vhost=cp92587.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+video[0][2]+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				
			else:
				urls += [("")]
		elif ( title == "KIRO 7 (Seattle, WA)" ):
			htmlSource = self._fetch_data( "http://www.kirotv.com/videoforecast/index.html", 15 )
			pattern_video = "/flv/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][2]
				url = "rtmp://96.7.215.31/ondemand?_fcs_vhost=cp12926.edgefcs.net/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".768k"
				app = "app=ondemand?_fcs_vhost=cp12926.edgefcs.net"
				pageUrl = "pageUrl=http://www.kirotv.com/videoforecast/index.html"
				swfUrl = "swfUrl=http://www.kirotv.com/_public/lib/swf/flowplayer/flowplayer.rtmp.swf"
				tcUrl = "tcUrl=rtmp://96.7.215.31/ondemand?_fcs_vhost=cp12926.edgefcs.net"
				playpath = "playpath=flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".768k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]

		#***************************
		# dig.abclocal.go.com
		#***************************

		elif ( title == "ABC 6 (Philadephia, PA)" ):
			htmlSource = self._fetch_data( "http://cdn.abclocal.go.com/wpvi/xml?id=6340396", 15 )
			pattern_video = "AccuWeather</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wpvi/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wpvi/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (Los Angeles, CA)" ):
			htmlSource = self._fetch_data( "http://cdn.abclocal.go.com/kabc/xml?id=6340292", 15 )
			pattern_video = "http://dig.abclocal.go.com/kabc/video/(.+?)_weather.flv"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/kabc/video/%s_weather.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 12 (Flint, MI)" ):
			htmlSource = self._fetch_data( "http://www.abc12.com/category/214773/weather-webcast?clienttype=rssmedia", 15 )
			pattern_video = "http://wjrt.videodownload.worldnow.com/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://wjrt.videodownload.worldnow.com/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 11 (Raleigh-Durham, NC)" ):
			htmlSource = self._fetch_data( "http://abclocal.go.com/wtvd/xml?id=7095536&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/ktrk/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/ktrk/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 13 (Houston, TX)" ):
			htmlSource = self._fetch_data( "http://abclocal.go.com/ktrk/xml?id=7076499&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/ktrk/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/ktrk/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (San Francisco, CA)" ):
			htmlSource = self._fetch_data( "http://abclocal.go.com/kgo/xml?id=7095531&param1=mrss", 15 )
			pattern_video = "forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/kgo/video/(.+?).flv\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/kgo/video/%s.flv") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (Chicago, IL)" ):
			htmlSource = self._fetch_data( "http://abclocal.go.com/wls/xml?id=7095534&param1=mrss", 15 )
			pattern_video = "Forecast</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wls/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wls/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]			
		elif ( title == "ABC 7 (New York, NY)" ):
			htmlSource = self._fetch_data( "http://cdn.abclocal.go.com/wabc/xml?id=6340375", 15 )
			pattern_video = "AccuWeather</title>[^<]+<link><[^>]+></link>[^<+]<description><[^>]+></description>[^<]+<pubDate>[^<]+</pubDate>[^<]+<guid isPermaLink=\"false\">[^<]+</guid>[^<]+<media:title><[^>]+></media:title>[^<]+<media:description><[^>]+></media:description>[^<]+<media:keywords><[^>]+></media:keywords>[^<]+<media:player url=\"http://dig.abclocal.go.com/wabc/video/(.+?).mp4\" />"
			video = re.findall( pattern_video, htmlSource )
			# print htmlSource
			# print video
			if ( video ):
				urls += [ ("http://dig.abclocal.go.com/wabc/video/%s.mp4") % video[0] ]
			else:
				urls += [("")]		
	
		#***************************
		# static rtmp address
		#***************************

		elif ( title == "KELO (Sioux Falls, SD)" ):
			url = "rtmp://flash.keloland.com:80/vod/mp4:/kelo/mp4:/kelo/WeatherUpdate.mp4"
			app = "app=vod/mp4:/kelo"
			pageUrl = "pageUrl=http://www2.keloland.com/_video/_videoplayer_embed.cfm?type=weather&ap=0"
			swfUrl = "swfUrl=http://www2.keloland.com/_video/2010/flowplayer.commercial-3.2.5.swf"
			tcUrl = "tcUrl=rtmp://flash.keloland.com:80/vod/mp4:/kelo"
			playpath = "playpath=mp4:/kelo/WeatherUpdate.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "ABC 13 (Asheville, NC)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wlos/wlos_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wlos.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wlos.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wlos/wlos_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "ABC 8 (Charleston, WV)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wchs/webwx.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wchstv.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wchstv.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wchs/webwx.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "CBS 2 (Cedar Rapids, IA)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:kgan/kgan_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.kgan.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.kgan.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:kgan/kgan_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
		elif ( title == "WGME 13 (Portland, ME)" ):
			url = "rtmp://ms-1.sbgnet.com/vod/mp4:wgme/wgme_weather.mp4"
			app = "app=vod"
			pageUrl = "pageUrl=http://www.wgme.com/newsroom/wx/"
			swfUrl = "swfUrl=http://www.wgme.com/template/flashplayers/fpcomm/swf/flowplayer.rtmp.swf"
			tcUrl = "tcUrl=rtmp://ms-1.sbgnet.com/vod"
			playpath = "playpath=mp4:wgme/wgme_weather.mp4"
			urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]

		#***************************
		# video-cast, webcast
		#***************************

		# To be looked
		elif ( title == "ABC 9 (NH)" ):
			htmlSource = self._fetch_data( "http://www.wmur.com/weather/15644234/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".600k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.wmur.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.wmur.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".600k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 7 (Omaha, NE)" ):
			htmlSource = self._fetch_data( "http://www.ketv.com/weather/16777750/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.ketv.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.ketv.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 4 (Hawaii)" ):
			htmlSource = self._fetch_data( "http://www.kitv.com/weather/17136897/media.html?qs=;longname=Video-Cast;shortname=VideoCast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kitv.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kitv.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 9 (Kansas City, MO)" ):
			htmlSource = self._fetch_data( "http://www.kmbc.com/weather/15022109/media.html?qs=;longname=Forecast Video;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kmbc.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kmbc.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 5 (Oklahoma City, OK)" ):
			htmlSource = self._fetch_data( "http://www.koco.com/weather/16746239/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.koco.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.koco.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "ABC 2 (Baton Rouge, LA)" ):
			htmlSource = self._fetch_data("http://www.wbrz.com/videoplayer/playlist_rss.cfm?categories=66&items=1&cbplayer=0.18014425406210655", 15)
			pattern_video = "rtmp://hosting3.synapseip.tv/wbrz/(.+?)\""
			video = re.findall( pattern_video, htmlSource )
			if (video):
				url = "rtmp://hosting3.synapseip.tv/wbrz/%s" % video[0]
				app = "app=wbrz"
				pageUrl = "pageUrl=http://www.wbrz.com/videoplayer/?categories=66&player_width=300&player_height=220&has_playlist=false&total_playlist_items=1&items_per_page=1&will_stretch_videos=false&has_autoplay=false&auto_hide=never&show_info=false&show_companions=false&live=false&iframe=true"
				swfUrl = "swfUrl=http://www.wbrz.com/videoplayer/swf/flowplayer.commercial-3.2.5.swf?0.9569410777399932"
				tcUrl = "tcUrl=rtmp://hosting3.synapseip.tv/wbrz"
				playpath = "playpath=%s" % video[0]
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "KCCI 8 (Des Moines, IA)" ):
			htmlSource = self._fetch_data( "http://www.kcci.com/weather/15912207/media.html?qs=;longname=Video-Cast;shortname=Video-Cast", 15 )
			pattern_video = "/(.[0-9]+)/(.[0-9]+)/(.[0-9]+)_120X90.jpg\"><div class=\"id\" title=\"(.[0-9]+)\">"
			video = re.findall( pattern_video, htmlSource )		
			if ( video ): 
				code = video[0][3]
				url = "rtmp://cp12878.edgefcs.net/ondemand/flv/"+video[0][0]+"/"+video[0][1]+"/"+code+".512k"
				app = "app=ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				pageUrl = "pageUrl=http://www.kcci.com/video-cast/%s/detail.html" % code
				swfUrl = "swfUrl=http://www.kcci.com/_public/lib/swf/flowplayer/flowplayer.swf?0.8506166914004388"
				tcUrl = "tcUrl=rtmp://cp12878.edgefcs.net/ondemand/flv/%s/%s" % ( video[0][0], video[0][1] )
				playpath = "playpath="+code+".512k"
				urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
			else:
				urls += [("")]
		elif ( title == "WLKY (Louisville, KY)" ):
			htmlSource = self._fetch_data( "http://www.wlky.com/weather/16509268/media.html?qs=;longname=Webcast;shortname=Webcast;days=&ib_wxwidget=true", 15 )
			pattern_code = "<div class=\"id\" title=\"([0-9]+)\">"
			code = re.findall( pattern_code, htmlSource )	
			# print code
			if ( code ): 
				htmlSource = self._fetch_data( "http://www.wlky.com/video-cast/%s/detail.html" % code[0] )
				pattern_video = "location:\'([^']+)\'"
				video = re.findall( pattern_video, htmlSource )
				# print video, htmlSource
				if ( video ):
					url = "rtmp://cp12892.edgefcs.net/ondemand%s.600k" % video[0]
					app = "app=ondemand%s" % video[0]
					pageUrl = "pageUrl=http://www.wlky.com/video-cast/%s/detail.html" % code[0]
					swfUrl = "swfUrl=http://www.wlky.com/_public/lib/swf/flowplayer/flowplayer.swf?0.10982807221342195"
					tcUrl = "tcUrl=rtmp://cp12892.edgefcs.net/ondemand/flv/%s/%s" % ( video[0].split("/")[2], video[0].split("/")[3] )
					playpath = "playpath="+ code[0] +".600k"
					urls += [( "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) )]
				else:
					urls += [("")]
			else:
				urls += [("")]

		#***************************
		# static address
		#***************************

		elif ( title == "ABC 20 (Gainesville, FL)" ):
			url = "http://wcjb.s3.amazonaws.com/one-minute/weather.flv"
			urls += [ (url) ]
		elif ( title == "CBS 8 (Montgomery, AL)" ):
			urls += [("http://www.waka.com/media/8/forecast.wmv")]
		elif ( title == "KLAS 8 (Las Vegas, NV)" ):
			urls += [("http://ftpcontent.worldnow.com/klas/weather/weather-webcast.mov")]	

		#***************************
		# xml list
		#***************************

		elif ( title == "CBS 11 (Dallas, TX)" ):
			htmlSource = self._fetch_data( "http://video.dallas.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195124&affiliateno=971&clientgroupid=1&rnd=19294", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Los Angeles, CA)" ):
			htmlSource = self._fetch_data( "http://video.losangeles.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=193005&affiliateno=961&clientgroupid=1&rnd=775526", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Denver, CO)" ):
			htmlSource = self._fetch_data( "http://video.denver.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=202261&affiliateno=983&clientgroupid=1&rnd=390532", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Miami, FL)" ):
			htmlSource = self._fetch_data( "http://video.miami.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=197329&affiliateno=988&clientgroupid=1&rnd=440486", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Chicago, IL)" ):
			htmlSource = self._fetch_data( "http://video.chicago.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194890&affiliateno=967&clientgroupid=1&rnd=724298", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]mms://(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("mms://%s.wmv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 13 (Baltimore, MD)" ):
			htmlSource = self._fetch_data( "http://video.chicago.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194890&affiliateno=967&clientgroupid=1&rnd=724298", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS (Boston, MA)" ):
			htmlSource = self._fetch_data( "http://video.boston.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195109&affiliateno=970&clientgroupid=1&rnd=692292", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS (Detroit, MI)" ):
			htmlSource = self._fetch_data( "http://video.detroit.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=205457&affiliateno=984&clientgroupid=1&rnd=360968", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 4 (Minneapolis, MN)" ):
			htmlSource = self._fetch_data( "http://video.minneapolis.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=195093&affiliateno=969&clientgroupid=1&rnd=929708", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (New York, NY)" ):
			htmlSource = self._fetch_data( "http://video.newyork.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=191871&affiliateno=958&clientgroupid=1&rnd=22963", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 3 (Philadelphia, PA)" ):
			htmlSource = self._fetch_data( "http://video.philadelphia.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=194876&affiliateno=966&clientgroupid=1&rnd=414300", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 2 (Pittsburgh, PA)" ):
			htmlSource = self._fetch_data( "http://video.pittsburgh.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=196782&affiliateno=977&clientgroupid=1&rnd=360214", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "CBS 13 (Sacramento, CA)" ):
			htmlSource = self._fetch_data( "http://video.sacramento.cbslocal.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=196795&affiliateno=978&clientgroupid=1&rnd=92965", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KWCH 12 (Wichita, KS)" ):
			htmlSource = self._fetch_data( "http://kwch.vidcms.trb.com/alfresco/service/edge/content/ad5cec9a-524e-4b82-8c01-e0562c31b09c", 15 )
			pattern_video = "/kwch/video/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://kwch.vid.trb.com/kwch/video/%s.flv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WJTV (Jackson, MS)" ):
			htmlSource = self._fetch_data( "http://www2.wjtv.com/weather_video_forecast/", 15 )
			pattern_video = "http://fcvfile.mgnetwork.com/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://fcvfile.mgnetwork.com/%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KCTV 5 (Kansas City, MO)" ):
			htmlSource = self._fetch_data( "http://www.kctv5.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=213731&affiliateno=1041&clientgroupid=1&rnd=418997", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KRQE 13 (Albuquerque, NM)" ):
			htmlSource = self._fetch_data( "http://www.krqe.com/feeds/outboundFeed?obfType=VIDEO_PLAYER_SMIL_FEED&componentId=23080464&FLVPlaybackVersion=1.0.2", 15 )
			pattern_video = "http://media2.krqe.com/video/(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://media2.krqe.com/video/%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WBTV 3 (Charlotte, NC)" ):
			htmlSource = self._fetch_data( "http://www.wbtv.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=135991&affiliateno=92&clientgroupid=1&rnd=757820", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KXJB (Fargo, ND)" ):
			htmlSource = self._fetch_data( "http://www.valleynewslive.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=201384&affiliateno=962&clientgroupid=1&rnd=206292", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WBNS 10 (Columbus, OH)" ):
			htmlSource = self._fetch_data( "http://www.10tv.com/content/digital/feeds/video/weather.xml", 15 )
			pattern_video = "http://static.dispatch.com/videos/10tv/(.+?).flv"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://static.dispatch.com/videos/10tv/%s.flv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "KOIN 6 (Portland, OR)" ):
			htmlSource = self._fetch_data( "http://eplayer.clipsyndicate.com/pl_xml/playlist?id=21746&token=X5YExbjs9TmgPuJPTkMbOsG9Do9JAz97coMBuX2LZCE=", 15 )
			pattern_video = "<location>http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WPRI 12 (Providence, RI)" ):
			htmlSource = self._fetch_data( "http://modules.lininteractive.com/wex_video/ajax.php?pid=0&ad=1&ver=lo&siteId=20004&categoryId=20780&zone=", 15 )
			pattern_video = "http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WTVF 5 (Nashville, TN)" ):
			htmlSource = self._fetch_data( "http://www.newschannel5.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=85811&affiliateno=374&clientgroupid=1&rnd=779991", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]mms://(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("mms://%s.wmv" % video[0])]
			else:
				urls += [("")]
		elif ( title == "WHDH 7 (Boston, MA)" ):
			htmlSource = self._fetch_data( "http://wn.whdh.com/build.asp?buildtype=buildpagexmlrequest&featureType=C&featureid=72108&affiliateno=428&clientgroupid=1&rnd=433299", 15 )
			pattern_video = "<URI><[!][[]CDATA[[]http://(.+?).mp4"
			video = re.findall( pattern_video, htmlSource )
			print video
			if ( video ):
				urls += [("http://%s.mp4" % video[0])]
			else:
				urls += [("")]
		else:
			urls += [(self.Addon.getSetting("video" + str(count) + "_url"))]
		count = count + 1

	
	print urls
	return urls

    def fetch_36_forecast( self, video ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch 36 hour forecast.. *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
	printlog( "Fetching URL : " + self.BASE_FORECAST_URL % ( "local", self.code, "", ) )
	printlog( "Fetching URL : " + self.BASE_URL + "/weather/5-day/"+ self.code )
        # fetch source
        htmlSource = self._fetch_data( self.BASE_FORECAST_URL % ( "local", self.code, "", ), 15 )
        htmlSource_5 = self._fetch_data( self.BASE_URL + "/weather/5-day/"+ self.code, 15 )
        _localtime_source_ = self._fetch_data( self.BASE_URL + "/outlook/events/weddings/wxdetail/" + self.code, )
	try:
             _localtime_ = int(re.findall ("([0-9]+):([0-9]+) AM", _localtime_source_)[0][0])
	except:
	     _localtime_ = None

        # parse source for forecast
        parser = Forecast36HourParser( htmlSource, htmlSource_5, _localtime_, self.translate )
	if ( parser.error == 0 ):
		# print parser.alertscolor[0]
	        # fetch any alerts
	        alerts, alertsrss, alertsnotify = self._fetch_alerts( parser.alerts )
	        # print alerts, alertsrss, alertsnotify
	        # create video url
	        if ( self.code.startswith( "US" ) or len(self.code) == 5 ):
			# video = [self.Addon.getSetting("video1_url"), self.Addon.getSetting("video2_url"), self.Addon.getSetting("video3_url")]
			video_title = [self.Addon.getSetting("video1"), self.Addon.getSetting("video2"), self.Addon.getSetting("video3")]
			video = self._solve_video ( video_title )
		else:
			video, video_title = self._create_video( parser.video_location, parser.video_local_location, parser.video_local_number, video )
	        # print "[Weather Plus] Weather Video = "+video
	        # print "[Weather Plus] Local Video = "+video_local
	        # return forecast
	        if ( parser.alertscolor is not None ) :
	             try : 
	                 return alerts, alertsrss, alertsnotify, parser.alertscolor[0], len(parser.alerts), parser.forecast, parser.extras, video, video_title
	             except : 
	                 return alerts, alertsrss, alertsnotify, parser.alertscolor, len(parser.alerts), parser.forecast, parser.extras, video, video_title
	else:
		print "[Weather Plus] Error Code : " + str( parser.error )

    def accu_36_forecast( self, video="" ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch 36 hour forecast.. *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
        # fetch source
	addr = self.code.split(" ")[0]
	addr_en = "en-us" + self.code.split(" ")[0].lstrip( str(self.code.split("/")[0]) )
	cityID = self.code.split(" ")[1]
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "quick-look", cityID ))
        htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "quick-look", cityID ), 15 )
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "details", cityID ))	
        htmlSource_1 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "details", cityID ), 15 )
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "details2", cityID ))
	htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "details2", cityID ), 15 )
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "quick-look", cityID ))
        htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "quick-look", cityID ), 15 )
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "details2", cityID ))
	htmlSource_4 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "details2", cityID ), 15 )
	printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "satellite", cityID ))
	htmlSource_5 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "satellite", cityID ), 15 )     
        # parse source for forecast
        parser = ACCU_Forecast36HourParser( htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4, self.translate )
	# any errors?
	while ( parser.error > 0 and parser.error < 5 ):
		printlog("Failed to load webpages properly. Retrying..")
		printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "quick-look", cityID ))
	        htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "quick-look", cityID ), 0 )
		printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "details", cityID ))	
	        htmlSource_1 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "details", cityID ), 0 )
		printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr, "details2", cityID ))
		htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr, "details2", cityID ), 0 )
		printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "quick-look", cityID ))
	        htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "quick-look", cityID ), 0 )
		printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "details2", cityID ))
		htmlSource_4 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "details2", cityID ), 0 )
		# printlog("Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( addr_en, "satellite", cityID ))
		# htmlSource_5 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "satellite", cityID ), 0 )
	        parser._get_forecast( htmlSource, htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4 )
        # fetch any alerts
        alerts, alertsrss, alertsnotify = self._fetch_alerts( parser.alerts )
        # create video url
        if ( self.code.split("/")[1]=="us" ):
		self.loc = re.findall("zip: '(.[0-9]+)'", htmlSource)[0]
		video_title = [self.Addon.getSetting("video1"), self.Addon.getSetting("video2"), self.Addon.getSetting("video3")]
		video = self._solve_video ( video_title )
	else:
		try:
			self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", htmlSource_5)[0]
			video, video_title = self._create_video( parser.video_location, self.loc, "", video )
		except:
			htmlSource_5 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( addr_en, "satellite", cityID ), 0 )
			self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", htmlSource_5)[0]
			video, video_title = self._create_video( parser.video_location, self.loc, "", video )

        # print "[Weather Plus] Weather Video = "+video
        # print "[Weather Plus] Local Video = "+video_local
        # return forecast
        if ( parser.alertscolor is not None ) :
             try : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor[0], len(parser.alerts), parser.forecast, parser.extras, video, video_title
             except : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor, len(parser.alerts), parser.forecast, parser.extras, video, video_title

    def noaa_36_forecast( self, video="" ):
        # fetch source
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch 36 hour forecast.. *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
	printlog( "Fetching URL : " + self.BASE_NOAA_FORECAST_URL % ( self.code ) )
        htmlSource = self._fetch_data( self.BASE_NOAA_FORECAST_URL % ( self.code ), 15 )
	printlog( "Fetching URL : " + self.BASE_NOAA_QUICK_URL % ( self.code ) )
	htmlSource_2 = self._fetch_data( self.BASE_NOAA_QUICK_URL % ( self.code ), 15 )
	printlog( "Fetching URL : " + self.BASE_NOAA_FORECAST_URL % ( self.code + "&FcstType=dwml" ) )
	xmlSource = self._fetch_data( self.BASE_NOAA_FORECAST_URL % ( self.code + "&FcstType=dwml" ), 15 )
	pattern_observation = [ "http://www.weather.gov/data/obhistory/(.+?).html", "sid=(.+?)\&" ]
	if ( re.search( "Can not connect to Database Server", xmlSource ) ):
		printlog( "Can not connect to NOAA Xml Server!" )
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Failed to load NOAA.gov!\",240, __icon__) ")
		return
	try:
		observ = re.findall( pattern_observation[0], htmlSource )[0]
		printlog( "Weather Station : " + observ )
		observSource = self._fetch_data( "http://www.weather.gov/xml/current_obs/%s.xml" % observ, 15 )
	except:
		try:
			observ = re.findall( pattern_observation[1], htmlSource )[0]
			printlog( "Weather Station : " + observ )
			observSource = self._fetch_data( "http://www.weather.gov/xml/current_obs/%s.xml" % observ, 15 )
		except:
			printlog( "WARNING : Weather Station Not Found!.... No Current Condition Icon can be Fetched!" )
			observSource = ""
        #printlog("Area code = " + self.code )
        # parse source for forecast
        parser = NOAA_Forecast36HourParser( htmlSource, htmlSource_2, xmlSource, observSource, self.translate )
        # fetch any alerts
        alerts, alertsrss, alertsnotify = self._fetch_alerts( parser.alerts )
        # create video url
	video_title = [self.Addon.getSetting("video1"), self.Addon.getSetting("video2"), self.Addon.getSetting("video3")]
	video = self._solve_video ( video_title )
        # return forecast
        if ( parser.alertscolor is not None ) :
             try : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor[0], len(parser.alerts), parser.forecast, parser.extras, video, video_title
             except : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor, len(parser.alerts), parser.forecast, parser.extras, video, video_title

#*******************************************
#					   *
#  Wunderground.com Fetching Functions     *
#					   *
#*******************************************

    def wunder_36_forecast( self, video ):
        # fetch source
        self.wunderSource = self._fetch_data( self.BASE_WUNDER_FORECAST_URL % ( self.code ), 1 )
        print "[Weather Plus] Area code = " + self.code
        # parse source for forecast
        parser = WUNDER_Forecast36HourParser( self.wunderSource, self.translate )
	if ( parser.forecast[0] == "ERROR" ):
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Failed to load Wunderground.com!\",240, __icon__) ")
		print "[Weather Plus] ERROR : Failed to load 36 hour forecast from Wunderground.com!"
		return
        # print parser.alertscolor[0]
        # fetch any alerts
        alerts, alertsrss, alertsnotify = self._fetch_alerts( parser.alerts )
        # print alerts, alertsrss, alertsnotify
        # create video url
	video_title = [self.Addon.getSetting("video1"), self.Addon.getSetting("video2"), self.Addon.getSetting("video3")]
	video = self._solve_video ( video_title )
        # video, video_local = self._create_video( parser.video_location, parser.video_local_location, parser.video_local_number, video )
	# video = ["","",""]
	# video_title = ["","",""]
        # print "[Weather Plus] Weather Video = "+video
        # print "[Weather Plus] Local Video = "+video_local
        # return forecast
        if ( parser.alertscolor is not None ) :
             try : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor[0], len(parser.alerts), parser.forecast, parser.extras, video, video_title
             except : 
                 return alerts, alertsrss, alertsnotify, parser.alertscolor, len(parser.alerts), parser.forecast, parser.extras, video, video_title

    def wunder_10day_forecast( self ):
        # parse source for forecast
        parser = WUNDER_Forecast10DayParser( self.wunderSource, self.translate )
	# print parser.forecast
	print parser.forecast[0]
	if ( parser.forecast[0] == "ERROR" ):
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Failed to load Wunderground.com!\",240, __icon__) ")
		print "[Weather Plus] ERROR : Failed to load extended forecast from Wunderground.com!"
        # return forecast
        return parser.forecast

    def wunder_hourly_forecast( self ):
	# parse source for forecast
	pattern_url = "<a href=\"/(.+?)[&]yday=([0-9]+)[&]weekday=[^\"]+\">Hourly Forecast"
	url = re.findall( pattern_url, self.wunderSource )
	htmlSource = self._fetch_data( "http://www.wunderground.com/%s&yday=%s" % ( url[0][0], url[0][1] ), 15 )
	htmlSource = htmlSource + self._fetch_data( "http://www.wunderground.com/%s&yday=%d" % ( url[0][0], [ int(url[0][1])+1, 1 ][int(url[0][1])==365] ), 15 )
        parser = WUNDER_ForecastHourlyParser( htmlSource + self.wunderSource, self.translate )
	if ( parser.forecast[0] == "ERROR" ):
		xbmc.executebuiltin( "XBMC.Notification(\"Weather Plus\",\"Failed to load Wunderground.com!\",240, __icon__) ")
		print "[Weather Plus] ERROR : Failed to load hourly forecast from Wunderground.com!"
        # return forecast
	return parser.forecast

    def _fetch_alerts( self, urls ):
        alerts = ""
        # alertscolor = ""
        alertsrss = ""
        alertsnotify = ""
        
        if ( urls ):
            #alertscolor = urls[ 0 ][ 0 ]
            titles = []
            # enumerate thru the alert urls and add the alerts to one big string
	    count = 0
            for url in urls:
		if (count == 0):
			count = 1
			continue	
                # fetch source refresh every 15 minutes
                htmlSource = self._fetch_data( self.BASE_URL + "/weather/alerts/"+ url, 15 )
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

    def _create_video( self, location, accu_loc, local_number, video ):
        url = ""
        local_url = ""
	try:
		loc = self.code.split("/")[1]
	except:
		loc = ""
        print "[Weather Plus] Video Loc Code : " + loc

	# Korea
	if (self.code.startswith( "KS" ) or loc == "kr"):
		urls=[]
		titles=[]
	   	htmlSource = self._fetch_data( "http://news.kbs.co.kr/forecast/", 15 )
		pattern_video = "F[|]10[|]/(.+?).mp4"
		pattern_video2 = "<a href=\"/forecast/(.+?).html\">"
		video = re.findall( pattern_video, htmlSource )	
		video2 = re.findall( pattern_video2, htmlSource )	
		if ( video ): 
			url = "rtmp://newsvod.kbs.co.kr/news/mp4:/%s.mp4" % video[0]
			app = "app=news"
			pageUrl = "pageUrl=http://news.kbs.co.kr/forecast/%s.html" % video2[0]
			swfUrl = "swfUrl=http://news.kbs.co.kr/app/flash_test/m_player.swf"
			tcUrl = "tcUrl=rtmp://newsvod.kbs.co.kr/news"
			playpath = "rtmp://newsvod.kbs.co.kr/news"
			urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
			titles += ["KBS"]
		else:
			urls += [""]
			titles += [""]
		'''
		htmlSource = self._fetch_data( "http://www.ytnweather.co.kr/issue/weather_center.php", 15 )
		pattern_video = "img src=\"http://image.ytn.co.kr/general/jpg/(.+?)_b.jpg\""
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			urls += ["rtsp://nvod1.ytn.co.kr/general/mov/%s_s.wmv" % video[0]]
			titles += ["YTN"]
		else:
			urls += [""]
			titles += [""]
		'''
	   	htmlSource = self._fetch_data( "http://www.obsnews.co.kr/Autobox/250_vod_news.html", 15 )
		pattern_video = "http://www.obsnews.co.kr/news/articleView.html[?]idxno=(.[0-9]+)"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			htmlSource = self._fetch_data( "http://www.obsnews.co.kr/news/articleView.html?idxno=%s" % video[0] )
			pattern_video = "http://vod.obs.co.kr/obsnews/(.+?).wmv"
			video = re.findall( pattern_video, htmlSource )
			if ( video ):
				urls += ["http://vod.obs.co.kr/obsnews/%s.wmv" % video[0]]
				titles += ["OBS"]
			else:
				urls += [""]
				titles += [""]
		else:
			urls += [""]
			titles += [""]

	   	htmlSource = self._fetch_data( "http://www.kweather.co.kr/onkweather/onkweather_02.html?type=lifestyle", 15 )
		pattern_video = "http://www.kweather.co.kr/digital/LifeMove/(.+?).flv"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			urls += ["http://www.kweather.co.kr/digital/LifeMove/%s.flv" % video[0]]
			titles += ["Kweather"]
		else:
			urls += [""]
			titles += [""]
		'''
		htmlSource = self._fetch_data( "http://www.weather.kr/", 15 )
		pattern_video = "fct_mov_day_(.+?)_img_(.+?)_00.jpg"
		video = re.findall( pattern_video, htmlSource )	
		# print video
		if ( video ): 
			url = "rtmp://kmafms.weather.kr/KMA/mp4:%s/fct_mov_day_%s_vod_%s.mp4" % ( "오늘의날씨", video[0][0], video[0][1] )
			app = "app=KMA"
			pageUrl = "pageUrl=http://www.weather.kr/weatherinfo/today.jsp"
			swfUrl = "swfUrl=http://www.weather.kr/player/flashPlayer/vod/KITTPlayer.swf?mode=service&accessJS=true&cid=23764&isCopy=true&startTime=0&endTime=0&autoPlay=false&volume=40&width=560&height=442"
			tcUrl = "tcUrl=rtmp://kmafms.weather.kr/KMA"
			playpath = "playpath=mp4:오늘의날씨/fct_mov_day_%s_vod_%s.mp4" % ( video[0][0], video[0][1] )
			urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
			titles += ["KMA (기상청)"]
		else:
			urls += [""]
			titles += [""]
		'''

		urls += [""]
		titles += [""]
		return urls, titles
	
	# Japan
	if (self.code.startswith( "JA" ) or loc == "jp"):
		urls=[]
		titles=[]
		url = "rtmp://flv.nhk.or.jp/ondemand/flv/news/weather/weather001"
		app = "app=ondemand/flv"
		pageUrl = "pageUrl=http://www3.nhk.or.jp/weather/"
		swfUrl = "swfUrl=http://www3.nhk.or.jp/weather/news_player2.swf?automode=true&playmode=one&movie=weather001&fms=rtmp://flv.nhk.or.jp/ondemand/flv/news/weather/&debug=false"
		tcUrl = "tcUrl=rtmp://flv.nhk.or.jp/ondemand/flv"
		playpath = "playpath=news/weather/weather001"
		# extra = "extra=AAAAAAEAAAAAAAAAAAAAAAAA"
		urls += ["%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath)]
		titles += ["NHK"]
		
		urls += ["",""]
		titles += ["",""]
		return urls, titles

	# China
	if (self.code.startswith( "CH" ) or loc == "cn"):
		urls=[]
		titles=[]
		urls += ["http://v.weather.com.cn/v/c/xwlb/xwlb.flv"]
		titles += ["CCTV"]
		
		urls += ["",""]
		titles += ["",""]
		return urls, titles

	# UK
        if (self.code.startswith( "UK" ) or loc == "gb"):
	    urls = []
	    titles = []
	    print "[Weather Plus] Video Location : UK"
	    # BBC
	    url = "http://news.bbc.co.uk/weather/forecast/10209"
	    pattern_url = "<param name=\"playlist\" value=\"(.+?)\""
	    htmlSource = self._fetch_data( url, 15 )
	    url = re.findall( pattern_url, htmlSource )
	    if ( url ):
		htmlSource = self._fetch_data( url[0], 15 )
		pattern_id = "<mediator identifier=\"(.+?)\" name=\"pips\""
		id = re.findall( pattern_id, htmlSource )
		if ( id ):
			url = "http://open.live.bbc.co.uk/mediaselector/4/mtis/stream/%s" % id [0]
			htmlSource = self._fetch_data( url, 15 )
			pattern_app = "application=\"(.+?)\""
			pattern_auth = "authString=\"(.+?)\""
			pattern_playpath = "identifier=\"(.+?)\""
			app = re.findall( pattern_app, htmlSource )
			auth = re.findall( pattern_auth, htmlSource )
			playpath = re.findall( pattern_playpath, htmlSource )
			if ( app and auth and playpath ):
				swfUrl = "http://emp.bbci.co.uk/emp/worldwide/revisions/555290_554055/555290_554055_emp.swf"
				tcUrl = "rtmp://cp45414.edgefcs.net:80/ondemand"
				url = tcUrl + "?" + auth[0]
				pageUrl = "http://news.bbc.co.uk/weather/forecast/10209"
				urls += ["%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url, app[0], swfUrl, tcUrl, pageUrl, playpath[0]) ]
				titles += ["BBC"]
			
	    '''
   	    url = "rtmp://cp45414.edgefcs.net:80/ondemand/public/flash/ident/weather"
	    app = "app=ondemand"
	    pageUrl = "pageUrl=http://news.bbc.co.uk/weather/forecast/10209"
	    swfUrl = "swfUrl=http://emp.bbci.co.uk/emp/worldwide/revisions/555290_554055/555290_554055_emp.swf"
	    tcUrl = "tcUrl=rtmp://cp45414.edgefcs.net:80/ondemand"
	    playpath = "playpath=public/flash/ident/weather"
	    urls += [ "%s %s %s %s %s %s" % (url, app, pageUrl, swfUrl, tcUrl, playpath) ]
	    titles += ["BBC"]
	    '''

            urls += [ "http://static1.sky.com/feeds/skynews/latest/daily/ukweather.flv", "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "" ]
	    titles += ["SKY News (UK)", "SKY News (Europe)", ""]
            # return [url,"http://static1.sky.com/feeds/skynews/latest/weather/long.flv","http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv"], ["UK Forecast", "Long Range", "Europe Forecast"]
	    return urls, titles

        # Canada
        if (self.code.startswith("CA") or loc == "ca"):
            print "[Weather Plus] Video Location : Canada"
            accu_canada = "http://www.accuweather.com/video/1681759716/canadian-national-weather-fore.asp?channel=world"
            htmlSource = self._fetch_data( accu_canada, 15 )
            pattern_video = "http://brightcove.vo.llnwd.net/d([0-9]+)/unsecured/media/1612802193/1612802193_([0-9]+)_(.+?)-thumb.jpg"
            pattern_playerID = "name=\"playerID\" value=\"(.+?)\""
            pattern_publisherID = "name=\"publisherID\" value=\"(.+?)\""
            pattern_videoID = "name=\"\@videoPlayer\" value=\"(.+?)\""
            video_ = re.findall( pattern_video, htmlSource )
            playerID = re.findall( pattern_playerID, htmlSource )
            publisherID = re.findall( pattern_publisherID, htmlSource )
            videoID = re.findall( pattern_videoID, htmlSource )
	    try:
		if (int(video_[0][1][8:])-1000 < 10000) :
			video= video_[0][1][:8] + "0" + str(int(video_[0][1][8:])-1000)
		else :
			video= video_[0][1][:8] + str(int(video_[0][1][8:])-1000)  
		if (video is not None and video_[0][2][15:] == "cnnational") :
			url = "http://brightcove.vo.llnwd.net/d" + video_[0][0] + "/unsecured/media/1612802193/1612802193_" + video + "_" + video_[0][2] + ".mp4" + "?videoId="+videoID[0]+"&pubId="+publisherID[0]+"&playerId="+playerID[0]
		else : 
			url = ""
	    except:
		url = ""
            print url
            return [url,"http://media.twnmm.com/storage/4902859/22","http://media.twnmm.com/storage/4902671/22"], ["Accuweather.com (Canada) ", "Weather News", "Long Range"]

	# Mexico
	if (self.code.startswith("MX") or loc == "mx"):
	    print "[Weather Plus] Video Location : Mexico"

	# France
	if (self.code.startswith("FR") or loc == "fr"):
	    urls = []
	    titles = []
	    print "[Weather Plus] Video Location : France"
	    # TF1
	    resp = urllib2.urlopen("http://www.wat.tv/swfap/196832Ac6Pjyk2651740/2427284")
	    ID = re.findall( "videoId=(.[0-9]+)", resp.geturl() )
	    if (ID):
		    ID = ID [0]
		    key = "9b673b13fa4682ed14c3cfa5af5310274b514c4133e9b3a81e6e3aba00912564"
		    hextime = "%x" % time.time()
		    hextime += "0" * ( len( hextime ) - 8 )
		    token = md5.new( key + "/webhd/" + ID + hextime ).hexdigest() + "/" + hextime
		    url = "http://www.wat.tv/get/webhd/" + ID + "?token=" + token + "&context=swf2&getURL=1&version=WIN%2010,3,183,5&lieu=tf1" 
		    # print url
		    url = self._fetch_data( url, )
		    urls += [url + "|User-Agent=Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)"]
		    titles += ["TF1"]
		
	    # France 2
	    url = "http://meteo.france2.fr/bulletin.php"
	    htmlSource = self._fetch_data( url, 15 )
	    pattern_id = "http://info.francetelevisions.fr/[?]id-video=(.+?)\""
	    id = re.findall ( pattern_id, htmlSource )
	    # print id
	    if ( id ):
		url = "http://meteo.france2.fr/appftv/webservices/video/getInfosCatalogueVideo.php?id-video=%s" % id [0]
		pattern_url = "<url-video>(.[^<]+)</url-video>"
		htmlSource = self._fetch_data( url, 15 )
		url = re.findall ( pattern_url, htmlSource )
		print url, htmlSource
		if ( url ):
			url = "http://a988.v101995.c10199.e.vm.akamaistream.net/7/988/10199/3f97c7e6/ftvigrp.download.akamai.com/10199/cappuccino/production/publication/%s" % url [0]
			urls += [url]
			titles += ["France 2"]
		else:
			urls += [""]
			titles += [""]
	    else:
		urls += [""]
		titles += [""]

	    urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", ""]
	    titles += ["SKY News (Europe)", ""]
	    print urls, titles
	    return urls, titles
	    
	# Italy
	if (self.code.startswith("IT") or loc == "it"):
	    print "[Weather Plus] Video Location : Italy"
            return ["http://media.ilmeteo.it/video/oggi-tg.mp4","http://media.ilmeteo.it/video/domani-tg.mp4", "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv"], ["iL Meteo (Today)", "iL Meteo (Tomorrow)", "SKY News (Europe)"]

	urls = []
	titles = []

	# Germany
	# broken
	"""
	if (self.code.startswith("GM") or loc == "de"):
	    print "[Weather Plus] Video Location : Germany"
	    url = "http://www.wetter.de/videos/playerlayer/show/format/html/videoid/0,0,108067/playlist/47,123/modul/mediaset_video"
	    htmlSource = self._fetch_data( url, 15 )
	    pattern_url = "<filename>(.+?)</filename>"
	    url = re.findall( pattern_url, htmlSource )
	    print url, htmlSource
	    if ( url ):
		playpath = url[0].split("vod/")[1]
		pageUrl = "http://www.wetter.de/cms/wetterbericht-deutschland.html"
		swfUrl = "http://bilder.static-fra.de/wetter11/flash/rtl_player.swf?cachebuster=1316491200"
		tcUrl = "rtmp://fms.rtl.de:1935/vod/"
		app = "vod/"
		urls += [ "%s app=%s swfUrl=%s tcUrl=%s pageUrl=%s playpath=%s" % (url[0], app, swfUrl, tcUrl, pageUrl, playpath) ]
		titles += ["Wetter.de"]
	"""
	
        # Europe
        if (self.code.startswith("FR") or self.code.startswith("SP") or self.code.startswith("IT") or self.code.startswith("GM") or self.code.startswith("NL") or self.code.startswith("GR") or self.code.startswith("PO") or self.code.startswith("EI") or accu_loc.startswith("iseur")):    
            print "[Weather Plus] Video Location : Europe"
            accu_europe = "http://www.accuweather.com/video/1681759717/europe-weather-forecast.asp?channel=world"
            htmlSource = self._fetch_data( accu_europe, 15 )
            pattern_video = "http://brightcove.vo.llnwd.net/d([0-9]+)/unsecured/media/1612802193/1612802193_([0-9]+)_(.+?)-thumb.jpg"
            pattern_playerID = "name=\"playerID\" value=\"(.+?)\""
            pattern_publisherID = "name=\"publisherID\" value=\"(.+?)\""
            pattern_videoID = "name=\"\@videoPlayer\" value=\"(.+?)\""
            video_ = re.findall( pattern_video, htmlSource )
            playerID = re.findall( pattern_playerID, htmlSource )
            publisherID = re.findall( pattern_publisherID, htmlSource )
            videoID = re.findall( pattern_videoID, htmlSource )
	    # print video_
	    try:
		if (int(video_[0][1][8:])-1000 < 10000) :
			video= video_[0][1][:8] + "0" + str(int(video_[0][1][8:])-1000)
		else :
			video= video_[0][1][:8] + str(int(video_[0][1][8:])-1000)
	        if (video_[0][2][15:] == "europe") :
                        urls += ["http://brightcove.vo.llnwd.net/d" + video_[0][0] + "/unsecured/media/1612802193/1612802193_" + video + "_" + video_[0][2] + ".mp4" + "?videoId="+videoID[0]+"&pubId="+publisherID[0]+"&playerId="+playerID[0], "http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", ""]
			titles += ["Accuweather.com (Europe)", "SKY News (Europe)", ""]
	        else : 
	                urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "", ""]
			titles += ["SKY News (Europe)", "", ""]
            except:
		urls += ["http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv", "", ""]
		titles += ["SKY News (Europe)", "", ""]            
	    # print urls
            # return [url,"http://static1.sky.com/feeds/skynews/latest/weather/europeweather.flv",""], ["Accuweather.com (Europe)", "SKY News (Europe)", "No Video"]
            return urls, titles

	# Austrailia
	if (self.code.startswith("AS") or loc == "au"):
		print "[Weather Plus] Video Location : Austrailia"
		abc = "http://www.abc.net.au/news/abcnews24/weather-in-90-seconds/"
		htmlSource = self._fetch_data( abc, 15 )
		pattern_video = "http://mpegmedia.abc.net.au/news/weather/video/(.+?)video3.flv"
		video = re.findall( pattern_video, htmlSource )
		try:
			url = "http://mpegmedia.abc.net.au/news/weather/video/" + video[0] + "video3.flv"
		except:
			url = ""
		return [url, "", ""], ["ABC (Weather in 90 Seconds)", "No Video", "No video"]
        # No available video
        return ["","",""], ["","",""]

    def fetch_hourly_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch hourly forecast..  *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
	printlog( "Fetching URL : " + self.BASE_FORECAST_URL % ( "hourbyhour", self.code, "", ) )
        # fetch source
        htmlSource = self._fetch_data( self.BASE_FORECAST_URL % ( "hourbyhour", self.code, "", ), 15 )
        # parse source for forecast
        parser = ForecastHourlyParser( htmlSource, self.translate )
        # return forecast
        return parser.forecast

    def accu_fetch_hourly_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch hourly forecast..  *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
	# fetch source
	count = 0
	try:
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ) )
		htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ), 0 )
		self.code = self.code.replace( "en-us", self.accu_translate )
		pattern_date = "<option selected=\"selected\" value=\"([0-9]+)\">"
		date = re.findall( pattern_date, htmlSource_3 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ) )
		htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ) )
		htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ), 0 )	
	except:
		printlog( "Retrying..." )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ) )
		htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ), 0 )
		self.code = self.code.replace( "en-us", self.accu_translate )
		pattern_date = "<option selected=\"selected\" value=\"([0-9]+)\">"
		date = re.findall( pattern_date, htmlSource_3 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ) )
		htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ) )
		htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ), 0 )	

        # parse source for forecast
        parser = ACCU_ForecastHourlyParser( htmlSource + htmlSource_2 + htmlSource_3, self.translate )
	# any error?
	while (parser.error > 0 and parser.error < 5):
		try:
			printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ) )
			htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
		except:
			printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ) )
			htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly", self.code.split(" ")[1] ), 0 )
			date = re.findall( pattern_date, htmlSource_3 )
			printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ) )
			htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+date[1], self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ) )
		htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "hourly"+ str( int(date[1])+7 ), self.code.split(" ")[1] ), 0 )
		parser._get_forecast( htmlSource + htmlSource_2 + htmlSource_3 )
	
        # return forecast
	printlog( "Parsing Hourly Forecast.. Done!" )
        return parser.forecast

    def noaa_fetch_hourly_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch hourly forecast..  *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
        # fetch source
	printlog( "Fetching URL : %s" % self.BASE_NOAA_HOURLY_URL % ( self.code ) )
        htmlSource = self._fetch_data( self.BASE_NOAA_HOURLY_URL % ( self.code ), 15 )
	printlog( "Fetching URL : %s" % self.BASE_NOAA_QUICK_URL % ( self.code ) )
	htmlSource_2 = self._fetch_data( self.BASE_NOAA_QUICK_URL % ( self.code ), 15 )
        # parse source for forecast
        parser = NOAA_ForecastHourlyParser( htmlSource, htmlSource_2, self.translate )
        # return forecast
        return parser.forecast

    def fetch_weekend_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch weekend forecast.. *" )
        printlog( "*                                                   *" )
	printlog( "*****************************************************" )
        # fetch source
	printlog( "Fetching URL : " + self.BASE_FORECAST_URL % ( "weekend", self.code, "", ) )
        htmlSource = self._fetch_data( self.BASE_FORECAST_URL % ( "weekend", self.code, "", ), 15 )
        # parse source for forecast
        parser = ForecastWeekendParser( htmlSource, self.translate )
        # return forecast
        return parser.forecast

    def accu_fetch_10day_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch 10 day forecast..  *" )
        printlog( "*                                                   *" )
        printlog( "*****************************************************" )
        # fetch source
	code = "en-us" + self.code.split(" ")[0].lstrip( str(self.code.split("/")[0]) )
	printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast", self.code.split(" ")[1] ) )
	htmlSource_1 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast", self.code.split(" ")[1] ), 15 )
	printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast2", self.code.split(" ")[1] ) )
	htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast2", self.code.split(" ")[1] ), 15 )
	printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( code, "forecast", self.code.split(" ")[1] ) )
	htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( code, "forecast", self.code.split(" ")[1] ), 15 )
	printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( code, "forecast2", self.code.split(" ")[1] ) )
	htmlSource_4 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( code, "forecast2", self.code.split(" ")[1] ), 15 )
        # parse source for forecast
        parser = ACCU_Forecast10DayParser( htmlSource_1 + htmlSource_2, htmlSource_3 + htmlSource_4, self.translate )
	# any error?
	if (parser.error == 1):
		printlog( "Retrying to fetch..." )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast", self.code.split(" ")[1] ) )
		htmlSource_1 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast", self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast2", self.code.split(" ")[1] ) )
		htmlSource_2 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "forecast2", self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( code, "forecast", self.code.split(" ")[1] ) )
		htmlSource_3 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( code, "forecast", self.code.split(" ")[1] ), 0 )
		printlog( "Fetching URL : " + self.BASE_ACCU_FORECAST_URL % ( code, "forecast2", self.code.split(" ")[1] ) )
		htmlSource_4 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( code, "forecast2", self.code.split(" ")[1] ), 0 )
		# parser._get_forecast( htmlSource_1, htmlSource_2, htmlSource_3, htmlSource_4 )	
		parser._get_forecast( htmlSource_1, htmlSource_2 )

        # return forecast
        return parser.forecast

    def fetch_10day_forecast( self ):
        printlog( "*****************************************************" )
        printlog( "*                                                   *" )
	printlog( "* [Weather Plus] Trying to fetch 10 day forecast..  *" )
        printlog( "*                                                   *" )
        printlog( "*****************************************************" )
	printlog( "Fetching URL : " + self.BASE_FORECAST_URL % ( "tenday", self.code, "", ) )
        # fetch source
        htmlSource = self._fetch_data( self.BASE_FORECAST_URL % ( "tenday", self.code, "", ), 15 )
	# print self.BASE_FORECAST_URL % ( "tenday", self.code, "", )
        # parse source for forecast
        parser = Forecast10DayParser( htmlSource, self.translate )
        # return forecast
        return parser.forecast

    def fetch_map_list( self, provider="2", maptype=0, userfile=None, locationindex=None ):
        # set url
        url = self.BASE_URL + self.BASE_MAPS[ maptype ][ 1 ]        
        # we handle None, local and custom map categories differently
        if ( maptype == 0 ):
            # return None if none category was selected
            return None, None
        elif ( maptype == 1 ):
            # add locale to local map list if local category
            if ( provider == "2" ):
		url = url % ( "map", self.code, "", )
	    elif ( provider == "0") :
		print "[Weather Plus] Accuweather Map Location = " + self.loc
		WEATHER_WINDOW.setProperty( "Map.Location", self.loc )     # leave footprint for 'map only' call
	        zipdir = { "iseas" : "KSXX0037",
	               "isasi" : "KSxx0037",
		       "iseur" : "FRXX0076",
		       "iscan" : "CAXX0504",
		       "ismex" : "MXDF0132",
		       "iscam" : "PMXX0004",
		       "iscsa" : "CIXX0020",
		       "isafr" : "UGXX0001",
		       "ismid" : "IRXX0036" }
		loc = self.loc[:5]
		zip = zipdir.get( loc, self.loc )    # if no match, it may be US zip. so appending itself.
		"""
		if ( self.loc == "iseasia" or self.loc.startswith( "isasia" ) ):
			zip = "KSXX0037"
		elif (self.loc.startswith( "iseur" )):
			zip = "FRXX0076"
		elif (self.loc.startswith( "iscan" )):
			zip = "CAXX0504"
		elif (self.loc.startswith( "ismex" )):
			zip = "MXDF0132"
		elif (self.loc.startswith( "iscam" )):
			zip = "PMXX0004"
		elif (self.loc.startswith( "iscsam" )):
			zip = "CIXX0020"
		elif (self.loc.startswith( "isafr" )):
			zip = "UGXX0001"
		elif (self.loc.startswith( "ismide" )):
			zip = "IRXX0036"
		else:
			zip = self.loc
		"""
		url = url % ( "map", zip, "", )
	    elif ( provider == "1") :
		# print self.code
	        position = self.code.split("&")
	        htmlSource = self._fetch_data( "http://www.mapquest.com/?q=%s,%s" % ( position[3].split("=")[1], position[4].split("=")[1] ) )
		pattern_zip = "\"postalCode\":\"(.+?)\""
		zip = re.findall( pattern_zip, htmlSource )
		if (zip):
			url = url % ( "map", zip[0], "", )
		else:
			print "[Weather Plus] ERROR : Mapquest.com might have been changed"
			return None, None
        print "[Weather Plus] maptype = " + str(maptype)
        print "[Weather Plus] map_list_url = " + url
        # handle user defined maps special
        if ( maptype == ( len( self.BASE_MAPS ) - 1 ) ):
            # initialize our map list variable
            map_list = []
            # get correct location source
            category_title, titles, locationindex = self._get_user_file( userfile, locationindex )
            # if user file not found return None
            if ( category_title is None ):
                return None, None
            # enumerate thru and create map list
            for count, title in enumerate( titles ):
                # add title, we use an locationindex for later usage, since there is no html source to parse for images, we use count to know correct map to use
                map_list += [ ( str( count ), title[ 0 ], locationindex, ) ]
            # return results
            return category_title, map_list
        else:
            # fetch source, only refresh once a week
            htmlSource = self._fetch_data( url, 60 * 24 * 7, subfolder="maps" )
            # print htmlSource
            # parse source for map list
            parser = MaplistParser( htmlSource )
            # return map list
            # print parser.map_list
            return None, parser.map_list

    def _get_user_file( self, userfile, locationindex ):
        # get user defined file source
        xmlSource = self._fetch_data( userfile )
        # if no source, then file moved so return
        if ( xmlSource == "" ):
            return None, None, None
        # default pattern
        pattern = "<location id=\"%s\" title=\"(.+?)\">(.+?)</location>"
        # get location, if no location for index, use default 1, which is required
        try:
            location = re.findall( pattern % ( locationindex, ), xmlSource, re.DOTALL )[ 0 ]
        except:
            # we need to set the used location id
            locationindex = "1"
            # use default "1"
            location = re.findall( pattern % ( locationindex, ), xmlSource, re.DOTALL )[ 0 ]
        # get title of maps for list and source for images
        titles = re.findall( "<map title=\"([^\"]+)\">(.+?)</map>", location[ 1 ], re.DOTALL )
        # return results
        return location[0], titles, locationindex

    def fetch_map_urls( self, map, userfile=None, locationindex=None, provider="2" ):
        # handle user defined maps special
        if ( map.isdigit() ):
            # convert map to int() for list index
            map = int( map )
            # get correct location source
            category_title, titles, locationindex = self._get_user_file( userfile, locationindex )
            # check if map is within the index range
            if ( map >= len( titles ) ):
                map = 0
            # grab all image urls
            urls = re.findall( "<image_url>([^<]+)</image_url>", titles[ map ][ 1 ] )
            # if image urls return results
            if ( urls ):
                # only set multi image list if more than one
                urls2 = ( [], urls, )[ len( urls ) > 1 ]
                # get a legend if it is separate from inages
                try:
                    legend = re.findall( "<legend_url>([^<]*)</legend_url>", titles[ map ][ 1 ] )[ 0 ]
                except:
                    legend = ""
                # return results
                return ( [ urls[ -1 ] ], urls2, legend, )
            # no image urls, find map urls
            map = re.findall( "<map_url>([^<]+)</map_url>", titles[ map ][ 1 ] )[ 0 ]
        # set url
        if ( map.endswith( ".html" ) ):
            url = self.BASE_URL + map
            # print "made url = " + url
	elif ( provider == "0") :
	    htmlSource = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "quick-look", self.code.split(" ")[1]), 15 )
            htmlSource_5 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "satellite", self.code.split(" ")[1]), 15 )
	    zipdir = { "iseas" : "KSXX0037",
	               "isasi" : "KSxx0037",
		       "iseur" : "FRXX0076",
		       "iscan" : "CAXX0504",
		       "ismex" : "MXDF0132",
		       "iscam" : "PMXX0004",
		       "iscsa" : "CIXX0020",
		       "isafr" : "UGXX0001",
		       "ismid" : "IRXX0036" }
	    if ( self.code.split("/")[1]!="us" ):
		try:
		    self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", htmlSource_5)[0]
		except:
		    htmlSource_5 = self._fetch_data( self.BASE_ACCU_FORECAST_URL % ( self.code.split(" ")[0], "satellite", self.code.split(" ")[1]), )
 		    self.loc = re.findall("http://sirocco.accuweather.com/sat_mosaic_640x480_public/IR/(.+?).jpg", htmlSource_5)[0]
            else:
	        self.loc = WEATHER_WINDOW.getProperty( "Map.Location" )
	    loc = self.loc[:5]
	    zip = zipdir.get( loc, self.loc )    # if no match, it may be US zip. so appending itself.
	    '''
	    if ( self.loc == "iseasia" or self.loc.startswith( "isasia" ) ):
		zip = "KSXX0037"
	    elif (self.loc.startswith( "iseur" )):
		zip = "FRXX0076"
	    elif (self.loc.startswith( "iscan" )):
		zip = "CAXX0504"
	    elif (self.loc.startswith( "ismex" )):
		zip = "MXDF0132"
	    elif (self.loc.startswith( "iscam" )):
		zip = "PMXX0004"
	    elif (self.loc.startswith( "iscsam" )):
		zip = "CIXX0020"
	    elif (self.loc.startswith( "isafr" )):
		zip = "UGXX0001"
	    elif (self.loc.startswith( "ismide" )):
		zip = "IRXX0036"
	    else:
		zip = self.loc
	    '''
	    url = self.BASE_FORECAST_URL % ( "map", zip, "&mapdest=%s" % ( map, ), )
        elif ( provider == "1" ):
	    position = self.code.split("&")
            htmlSource = self._fetch_data( "http://www.mapquest.com/?q=%s,%s" % ( position[3].split("=")[1], position[4].split("=")[1] ) )
	    pattern_zip = "\"postalCode\":\"(.+?)\""
	    zip = re.findall( pattern_zip, htmlSource )
	    url = self.BASE_FORECAST_URL % ( "map", zip[0], "&mapdest=%s" % ( map, ), )
	else:
            url = self.BASE_FORECAST_URL % ( "map", self.code, "&mapdest=%s" % ( map, ), )
        # fetch source
        print "[Weather Plus] map_url = " + url
        htmlSource = self._fetch_data( url, subfolder="maps" )
        # parse source for static map and create animated map list if available
        parser = MapParser( htmlSource )
        # return maps
        return parser.maps

    def fetch_images( self, map ):
        # print "fetch_images map", map
        # are there multiple images?
        maps = map[ 1 ] or map[ 0 ]
        # initailize our return variables
        legend_path = ""
        base_path_maps = ""
        # enumerate thru and fetch images
        for count, url in enumerate( maps ):
            # used for info in progress dialog
            self.image = os.path.basename( url )
            print "[Weather Plus] Fetch image = " + self.image + " ||| url = "+ url
            # fetch map
            base_path_maps = self._fetch_data( url, -1 * ( count + 1 ), self.image, len( maps ) > 1, subfolder="" )
            # no need to continue if the first map of multi image map fails
            if ( base_path_maps == "" ):
                break
        # fetch legend if available
        if ( map[ 2 ] and base_path_maps != "" ):
            # fetch legend
            legend_path = self._fetch_data( map[ 2 ], -1, os.path.basename( map[ 2 ] ), False, subfolder="" )
            # we add the image filename back to path since we don't use a multiimage control
            legend_path = os.path.join( legend_path, os.path.basename( map[ 2 ] ) )
        # we return path to images or empty string if an error occured
        print base_path_maps
        return base_path_maps, legend_path

    def _fetch_data( self, base_url, refreshtime=0, filename=None, animated=False, subfolder="forecasts", retry=True ):
        try:
            # set proper base path
            if ( not base_url.startswith( "http://" ) ):
                # user defined maps file
                base_path = base_url
                base_refresh_path = None
            elif ( filename is None ):
                # anything else except map/radar images (basically htmlSource)
                try: 
		    base_path = os.path.join( self.BASE_SOURCE_PATH, subfolder, hashlib.md5( base_url ).hexdigest() )
		except:
		    base_path = os.path.join( self.BASE_SOURCE_PATH, subfolder, md5.new( base_url ).hexdigest() )
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
		    base_path = os.path.join( self.BASE_MAPS_PATH, subfolder, hashlib.md5( path ).hexdigest(), filename )
                    base_refresh_path = os.path.join( self.BASE_MAPS_PATH, subfolder, hashlib.md5( path ).hexdigest(), "refresh.txt" )
		except:
		    base_path = os.path.join( self.BASE_MAPS_PATH, subfolder, md5.new( path ).hexdigest(), filename )
                    base_refresh_path = os.path.join( self.BASE_MAPS_PATH, subfolder, md5.new( path ).hexdigest(), "refresh.txt" )
            # get expiration date
            expires, refresh = self._get_expiration_date( base_path, base_refresh_path, refreshtime )
	    if ( refreshtime == 0 ) : refresh = 1
            # only fetch source if it's been longer than refresh time or does not exist
            if ( not os.path.isfile( base_path ) or refresh ):
                # request base url
                request = urllib2.Request( base_url )
                # add a faked header
                request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
		# xbmc_version = xbmc.getInfoLabel( "System.BuildVersion" )
		# kernel_version = xbmc.getInfoLabel( "System.KernelVersion" )
		# request.add_header( "User-Agent", "XBMC/%s (%s; http://www.xbmc.org)" % (xbmc_version, kernel_version) )
                #request.add_header( "Connection", "Keep-Alive" )
                # request.add_header( "Accept-Encoding", "gzip, deflate" )
		# request.add_header( "Accept-Charset", "UTF-8" )
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
                self._save_data( data, base_path )
            # save the refresh.txt file
            if ( base_refresh_path is not None and ( not animated or ( animated and refreshtime == -5 ) ) and refresh ):
                self._save_data( str( expires ), base_refresh_path )
            if ( base_refresh_path ):
                data = os.path.dirname( base_path )
            # return results
            return data
        except urllib2.HTTPError, e:
            # if error 503 and this is the first try, recall function after sleeping, otherwise return ""
            if ( e.code == 503 and retry ):
                # TODO: this is so rare, but try and determine if 3 seconds is enogh
                print "Trying url %s one more time." % base_url
                time.sleep( 3 )
                # try one more time
                return self._fetch_data( base_url, refreshtime, filename, animated, subfolder, False )
            else:
                # we've already retried, return ""
                print "Second error 503 for %s, increase sleep time." % base_url
                return ""
        except:
            # oops print error message
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            # some unknown error, return ""
            return ""

    def _get_expiration_date( self, base_path, base_refresh_path, refreshtime ):
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
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
        # return expiration date
        return expires, refresh

    def _save_data( self, data, data_path ):
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
            print "ERROR: %s::%s (%d) - %s" % ( self.__class__.__name__, sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )

