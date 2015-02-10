import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import re
import os
import time
import cgi
import sys
import json

# Global settings
__plugin__		= "ShareThe.TV"
__version__		= "2.0.6"
__addonID__		= "script.sharethetv"
__settings__ = xbmcaddon.Addon(__addonID__)
__language__ = __settings__.getLocalizedString
__apiurl__ = 'http://sharethe.tv/api/'

# Debugging info
print "[ADDON] '%s: version %s' initialized!" % (__plugin__, __version__)


# Send a notice.  Specify message and duration.
def sendNotice(msg, time="5000"):
	xbmc.executebuiltin('Notification(' + __plugin__ + ',' + msg + ',' + time +',' + __settings__.getAddonInfo("icon") + ')')


def debug(message):
	message = "ShareThe.TV: " + message
	if (__settings__.getSetting( "debug" ) == 'true'):
		print message.encode('ascii', 'ignore')


# Query the movie list
def getMovieLibrary():
	rpccmd = json.dumps({'jsonrpc': '2.0', 'method': 'VideoLibrary.GetMovies', 'params':{'properties': ['year', 'imdbnumber']}, 'id': 1})

	result = xbmc.executeJSONRPC(rpccmd)
	result = json.loads(result)

	try:
		error = result['error']
		debug("getMovieLibrary: " + str(error))
		sendNotice(__language__(30028))
		return None
	except KeyError:
		pass

	try:
		return result['result']['movies']
	except KeyError:
		debug("getMovieLibrary: KeyError")
		if (result['result']['limits']['total'] == 0):
			sendNotice(__language__(30029))
		else:
			sendNotice(__language__(30028))
		return None


# Build out movie XML based on getMovieLibrary() call.  Watch for special chars in title
def buildMovieXML(movies):
	debug("buildMovieXML")
	movielist = "<movies>"
	for i in range(0, len(movies)):
		movielist += "<movie>"
		movielist += "<imdb>" + movies[i]['imdbnumber'] + "</imdb>"
		movielist += "<title>" + cgi.escape(movies[i]['label']) + "</title>"
		movielist += "<year>" + str(movies[i]['year']) + "</year>"
		movielist += "</movie>"
	movielist += "</movies>"
	return movielist.encode('ascii', 'ignore')


# Build out parameters list including user/pass, and movie list
def buildParamsXML(movielist):
	debug("buildParamsXML")
	params = "<user>"
	params += "<version>" + __version__ + "</version>"
	params += "<email>" + __settings__.getSetting("email") + "</email>"
	params += "<password>" + __settings__.getSetting("password") + "</password>"
	params += movielist
	params += "</user>"
	return params


# Send the request and handle returned errors
def sendRequest(params):
	req = urllib2.Request(url=__apiurl__, data=params, headers={'Content-Type': 'application/xml'})
	try:
		response = urllib2.urlopen(req)
		sendNotice(__language__(30020))
	except urllib2.HTTPError, e:
		if e.code == 401:
			sendNotice(__language__(30021))
		elif e.code == 403:
			sendNotice(__language__(30022))
	except urllib2.URLError, e:
		sendNotice(__language__(30023))


def sendUpdate():
	if (__settings__.getSetting("email") == '' or __settings__.getSetting("password") == ''):
		sendNotice(__language__(30024))
		return

	progress = xbmcgui.DialogProgress()
	progress.create(__language__(30025), __language__(30026))

	library = getMovieLibrary()
	if (library == None):
		return

	movielist = buildMovieXML(library)
	debug('Movielist is: ' + movielist)

	params = buildParamsXML(movielist)
	
	progress.update(50, __language__(30027))
	sendRequest(params)
	progress.close()


# Main execution path
sendUpdate()

