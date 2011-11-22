"""
    Weather plugin
"""

#main imports
import sys
import urllib, os.path, xbmc, re, htmlentitydefs, time

# Script constants
__plugin__ = "Weather Plus"
__pluginname__ = "Weather Plus"
__author__ = "brightsr (original sources by nuka1195)"
__url__ = "http://code.google.com/p/xbmc-addons/"
__svn_url__ = "http://xbmc-addons.googlecode.com/svn/branches/dharma/weather.weatherplus"
__version__ = "2.5.2"

# Start the main plugin

xbmc.log( "[PLUGIN] '%s: Version - %s' initialized!" % ( __plugin__, __version__ ), xbmc.LOGNOTICE )     

if ( __name__ == "__main__" ):
    from xbmcplugin_weather import Main
    Main()
    
