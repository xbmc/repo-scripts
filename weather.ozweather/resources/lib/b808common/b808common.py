# -*- coding: utf-8 -*-

### Common Code for bossanova808 addons
### By bossanova808 2015
### Free in all senses....

### VERSION 0.2.2

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs
import xbmcgui
import urllib
import sys
import os
import platform
import socket

from traceback import format_exc

################################################################################
################################################################################
### LOGGING FUNCTIONS

################################################################################
# Log a message to the XBMC Log, and an exception if supplied
#
# call log() to log only if degbug logging is on
# call logNotice() is you want print out regardless of debug settings

def log(message, inst=None, level=xbmc.LOGDEBUG):
    
    if isinstance (message,str):
        message = message.decode("utf-8")
        message = u'### %s - %s ### %s' % (ADDONNAME,VERSION, message)
    else:
        message = u'### %s - %s ### %s' % (ADDONNAME,VERSION, message)

    if inst is None:
      xbmc.log(message.encode("utf-8"), level )
    else:
      xbmc.log(message.encode("utf-8"), level )
      xbmc.log("### " + ADDONNAME + "-" + VERSION +  " ### Exception:" + format_exc(inst), level )

#log something even if debug logging is off - for important stuff only!

def logNotice(message, inst=None):
    log(message, inst, level = xbmc.LOGNOTICE)


################################################################################
# Trigger a toast pop up on screen
# & log the message to the XBMC Log about the popup if debugging

def notify(messageLine1, messageLine2 = "", time = 4000):
  imagepath = os.path.join(CWD ,"icon.png")
  notifyString = "XBMC.Notification(" + messageLine1 +"," + messageLine2+","+str(time)+","+imagepath+")"
  log("XBMC Notificaton Requested: [" + notifyString +"]")
  xbmc.executebuiltin( notifyString )

################################################################################
# Log an addon startup message to the XBMC log

def footprints(startup=True):

  if startup:
    logNotice( ADDONNAME + " (Author: " + AUTHOR + ") Starting ...")
    #log the detemined system type
    logNotice("uname is: " + str(uname))
    logNotice("System is " + SYSTEM)
    logNotice("Kodi Version #: " + str(VERSION_NUMBER))      
    logNotice("Kodi Version  : " + XBMC_VERSION)    
    logNotice( "Addon arguments as: " + str(sys.argv))
  else:
    logNotice( ADDONNAME + " (Author: " + AUTHOR + ") Exiting ....")


################################################################################
################################################################################
### MIXED UTILITY FUNCTIONS

################################################################################
# Log the users local IP address if possible

def logLocalIP():
    #log the local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #connect to google DNS as it's always up...
        s.connect(('8.8.8.8',80))
        logNotice("Local IP is " + str(s.getsockname()[0]))
        s.close()
    except:
        pass

################################################################################
# Front pad a string with 0s out to 9 chars long

def frontPadTo9Chars(shortStr):
    while len(shortStr)<9:
        shortStr = "0" + shortStr
    return shortStr

################################################################################
# Reverse the key value pairs in a dict

def swap_dictionary(original_dict):
   return dict([(v, k) for (k, v) in original_dict.iteritems()])


################################################################################
# send a JSON command to XBMC and log the human description, json string, and
# the result returned

def sendXBMCJSON (humanDescription, jsonstr):
     log(humanDescription + " [" + jsonstr +"]")
     result = xbmc.executeJSONRPC(jsonstr)
     log("JSON result: "  + str(result))

##############################################################################
# Convert number of seconds to summat nice for screen 00:00 etc

def getInHMS(seconds):
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    if hours == 0:
        return "%02d:%02d" % (minutes, seconds)
    return "%02d:%02d:%02d" % (hours, minutes, seconds)

##############################################################################
# properly unquote text coming back from e.g. LMS

def unquoteUni(text):

    try:
        import urllib.parse
        return urllib.parse.unquote(text, encoding=self.charset)
    except ImportError:
        #import urllib
        #return urllib.unquote(text)
        _hexdig = '0123456789ABCDEFabcdef'
        _hextochr = dict((a+b, chr(int(a+b,16))) for a in _hexdig for b in _hexdig)
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        res = text.split('%')
        for i in xrange(1, len(res)):
            item = res[i]
            try:
                res[i] = _hextochr[item[:2]] + item[2:]
            except KeyError:
                res[i] = '%' + item
            except UnicodeDecodeError:
                res[i] = unichr(int(item[:2], 16)) + item[2:]
        return "".join(res)

##############################################################################
# Parses the parameter stings (arrives in sys.argv[2])
# into a dict

def getParams():
        param=[]
        paramstring=sys.argv[2]
        if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                splitparams={}
                splitparams=pairsofparams[i].split('=')
                if (len(splitparams))==2:
                    param[splitparams[0]]=splitparams[1]

        log("Parameters parsed: " + str(param))
        return param

##############################################################################
# Build a plugin URL with urlencoded parameters

def buildPluginURL(params):
    return PLUGINSTUB + urllib.urlencode(params)

################################################################################
# Strip given chararacters from all members of a given list

def stripList(l, chars):
    return([x.strip(chars) for x in l])

################################################################################
# Set a property on a window.
# To clear a property, provide a blank value ""

def setProperty(window, name, value = ""):
    window.setProperty(name, value)
    log("Set property name: [%s] - value:[%s]" % (name,value))

################################################################################
# Try and sett the window mode to thumbnail mode....
# This is increasing less useful....

def getThumbnailModeID():
    VIEW_MODES = {
        'thumbnail': {
            'skin.confluence': 500,
            'skin.aeon.nox': 551,
            'skin.confluence-vertical': 500,
            'skin.jx720': 52,
            'skin.pm3-hd': 53,
            'skin.rapier': 50,
            'skin.simplicity': 500,
            'skin.slik': 53,
            'skin.touched': 500,
            'skin.transparency': 53,
            'skin.xeebo': 55,
        }
    }


    skin = xbmc.getSkinDir()
    try:
        thumbID = VIEW_MODES['thumbnail'][skin]
    except:
        thumbID = VIEW_MODES['thumbnail']['skin.confluence']

    return thumbID

################################################################################
################################################################################
### CONSTANTS & SETTINGS

#create an add on instation and store the reference
ADDON       = xbmcaddon.Addon()

#if we've been imported from the plugin we need the magic ID
if 'plugin' in sys.argv[0]:
    THIS_PLUGIN = int(sys.argv[1])
    PLUGINSTUB = sys.argv[0]+"?"

#store some handy constants
ADDONNAME   = ADDON.getAddonInfo('name')
ADDONID     = ADDON.getAddonInfo('id')
AUTHOR      = ADDON.getAddonInfo('author')
VERSION     = ADDON.getAddonInfo('version')
CWD         = ADDON.getAddonInfo('path')
LANGUAGE    = ADDON.getLocalizedString
USERAGENT   = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"


# Set up the paths
RESOURCES_PATH = xbmc.translatePath( os.path.join( CWD, 'resources' ))
LIB_PATH = xbmc.translatePath(os.path.join( RESOURCES_PATH, "lib" ))
DATA_PATH = xbmc.translatePath("special://profile/addon_data/" + ADDONID )
CLASS_PATH = xbmc.translatePath(os.path.join ( LIB_PATH, "classes" ))
#extend the python path
sys.path.append( CLASS_PATH )
sys.path.append( LIB_PATH )

#32 or 64 bit?
is_64bits = sys.maxsize > 2**32

#need to work out what system we're on, default to linux
SYSTEM="linux"

#ok try and get uname info - this is a bit tetchy - platform.uname() fails on Raspbmc
#but os.uname() fails on Windows....platform is the better one to use if possible,
#so try that first, otherwise fall back to os.uname()

try:
  uname = platform.uname()
except:
  uname = os.uname()

if xbmc.getCondVisibility( "System.Platform.OSX" ):
  SYSTEM = "osx"
elif xbmc.getCondVisibility( "System.Platform.IOS" ):
  SYSTEM = "ios"
elif xbmc.getCondVisibility( "System.Platform.ATV2" ):
  SYSTEM = "atv2"
elif xbmc.getCondVisibility( "System.Platform.Windows" ):
  SYSTEM = "windows"
elif xbmc.getCondVisibility( "System.Platform.Linux.RaspberryPi" ):
  SYSTEM = "arm"
elif xbmc.getCondVisibility( "System.Platform.Android" ):
  SYSTEM = "android"


XBMC_VERSION = None
VERSION_NUMBER = None

VERSION_NUMBER = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[0:4])
if VERSION_NUMBER >= 12.9:
    XBMC_VERSION = "G*" 
if VERSION_NUMBER >= 13.9:
    XBMC_VERSION = "H*" 
if VERSION_NUMBER >= 14.9:
    XBMC_VERSION = "I*" 
if VERSION_NUMBER >= 15.9:
    XBMC_VERSION = "J*"
if VERSION_NUMBER >= 16.9:
    XBMC_VERSION = "K*" 
if VERSION_NUMBER >= 17.9:
    XBMC_VERSION = "L*"     
if VERSION_NUMBER >= 18.9:
    XBMC_VERSION = "M*"
if VERSION_NUMBER >= 19.9:
    XBMC_VERSION = "N*"
if VERSION_NUMBER >= 20.9:
    XBMC_VERSION = "O*"
if VERSION_NUMBER >= 21.9:
    XBMC_VERSION = "P*"        
if VERSION_NUMBER >= 22.9:
    XBMC_VERSION = ">P" 



