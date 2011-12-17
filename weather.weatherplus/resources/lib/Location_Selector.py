# main imports
import sys
import os

import xbmc
import xbmcgui
import urllib2
from urllib import urlencode
#import md5
import re
import time
from xbmcaddon import Addon

__Settings__ = Addon(id="weather.weatherplus")

def _fetch_data( base_url, cookie=None ):
	try:
            request = urllib2.Request( base_url )
            # add a faked header
            request.add_header( "User-Agent", "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727)" )
            request.add_header( "Cookie", "intSessionZ=Location=%s" % cookie ) 
	    # open requested url
            usock = urllib2.urlopen( request )
            # read source
            data = usock.read()
            # close socket
            usock.close()
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
            print "ERROR: %s (%d) - %s" % ( sys.exc_info()[ 2 ].tb_frame.f_code.co_name, sys.exc_info()[ 2 ].tb_lineno, sys.exc_info()[ 1 ], )
            # some unknown error, return ""
            return ""

class Main:
	def __init__(self, loc=1):
		location = ""
		location_name = []
		loc, provider = loc.split("|")
		__Settings__.setSetting( "provider%s" % loc, provider )
		kb = xbmc.Keyboard("", xbmc.getLocalizedString(14024), False)
		kb.doModal()
		if (kb.isConfirmed()):
			userInput = kb.getText()
			if (userInput != ""):
				print userInput
				pDialog = xbmcgui.DialogProgress()
				ret = pDialog.create('XBMC', 'Searching...')
				pDialog.update(50)
				location = self._fetch_location(userInput, provider)
				pDialog.update(100)
				pDialog.close()
				dialog = xbmcgui.Dialog()
				for count, loca in enumerate(location):
					if ( provider == "0" ):
						location_name += [ loca[2] ]
					elif ( provider == "1" or provider == "2" ):
						location_name += [ loca[1] ]
					elif ( provider == "3" ):
						location_name += [ loca[0] ]
				select = dialog.select(xbmc.getLocalizedString(396), location_name)
				if ( select != -1 ):
					self.location = location[ select ]
					__Settings__.setSetting( "location%s_%s" % ( loc, int(provider)+1 ), location_name[ select ] )
					if ( provider == "0" ):
						__Settings__.setSetting( "code%s_%s" % ( loc, int(provider)+1 ), self.location[0] + " " + self.location[1] )
					elif ( provider == "1" or provider == "2" ):
						__Settings__.setSetting( "code%s_%s" % ( loc, int(provider)+1 ), self.location[0] )
					elif ( provider == "3" ):
						__Settings__.setSetting( "code%s_%s" % ( loc, int(provider)+1 ), self.location[1] )
				# __Settings__.openSettings()
	
	def _fetch_location(self, userInput, provider):
		location = []
		if (provider == "0"):
			pattern_location = "www.accuweather.com/(.+?)/quick-look.aspx[?]cityid=(.[0-9]+)\">(.+?)</a>"
			htmlSource = _fetch_data ( "http://www.accuweather.com/Multiple-Locations.aspx", userInput.replace(" ","+") )
			location = re.findall( pattern_location, htmlSource )
			# print location
		elif (provider == "1"):
			pattern_location = "<a href=\"http://forecast.weather.gov/MapClick.php?([^\"]+)\">([^<]+)</a>"
			htmlSource = _fetch_data ( "http://forecast.weather.gov/zipcity.php?inputstring=%s" % userInput.replace(" ","+") )
			location = re.findall( pattern_location, htmlSource )
			if ( re.search("<title>7-Day Forecast", htmlSource ) ):
				pattern_location = "/MapClick.php(.+?)lg=sp\""
				location_buffer = re.findall( pattern_location, htmlSource )
				if ( len(location_buffer) ):
					city = re.findall( "CityName=(.+?)\&", location_buffer[0] )
					state = re.findall( "state=(.+?)\&", location_buffer[0] )
					location = [ ( location_buffer[0], "%s, %s" % ( city[0], state[0] ) ) ]
				else:
					location = []							 
		elif (provider == "2"):
			pattern_location = "id=\"(.+?)\" type=\"[0-9]\">(.+?)</loc>"
			xmlSource = _fetch_data ( "http://xoap.weather.com/search/search?where=%s" % userInput.replace(" ","+") )
			location = re.findall( pattern_location, xmlSource )
		elif (provider == "3"):
			pattern_name = "name\"[:] \"(.+?)\""
			pattern_code = "l\"[:] \"(.+?)\""
			htmlSource = _fetch_data ( "http://autocomplete.wunderground.com/aq?query=%s" % userInput.replace(" ","+") )
			name = re.findall( pattern_name, htmlSource )
			code = re.findall( pattern_code, htmlSource )
			location = [ ( name[i], code[i] ) for i in range(0, len(name)) ]					
		return location

Main( loc=sys.argv[ 1 ].split( "=" )[ 1 ] )
