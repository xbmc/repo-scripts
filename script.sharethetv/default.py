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

# Global settings
__plugin__		= "ShareThe.TV"
__version__		= "1.1.0"
__addonID__		= "script.sharethetv"
__settings__ = xbmcaddon.Addon(__addonID__)
__apiurl__ = 'http://sharethe.tv/api/'

# Auto exec info
AUTOEXEC_PATH = xbmc.translatePath( 'special://home/userdata/autoexec.py' )
AUTOEXEC_FOLDER_PATH = xbmc.translatePath( 'special://home/userdata/' )
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/script.sharethetv/default.py,-startup)")\n'

# Debugging info
print "[ADDON] '%s: version %s' initialized!" % (__plugin__, __version__)


# Send a notice.  Specify message and duration.
def sendNotice(msg, time):
	xbmc.executebuiltin('Notification(' + __plugin__ + ',' + msg + ',' + time +',' + __settings__.getAddonInfo("icon") + ')')


def debug(message):
	message = "ShareThe.TV: " + message
	if (__settings__.getSetting( "debug" ) == 'true'):
		print message


# Query the movie list
def getMovieLibrary():
	# imdb, title, year
	query = "SELECT movie.c09, movie.c00, movie.c07 FROM movie"
	return xbmc.executehttpapi("QueryVideoDatabase(%s)" % urllib.quote_plus(query))


# Build out movie XML based on getMovieLibrary() call.  Watch for special chars in title
def buildMovieXML(response):
	match = re.compile('<field>(.*?)</field><field>(.*?)</field><field>(.*?)</field>').findall(response)
	
	movielist = "<movies>"
	for imdb, title, year in match:
		movielist += "<movie>"
		movielist += "<imdb>" + imdb + "</imdb>"
		movielist += "<title>" + cgi.escape(title) + "</title>"
		movielist += "<year>" + year + "</year>"
		movielist += "</movie>"
	movielist += "</movies>"
	return movielist


# Build out parameters list including user/pass, and movie list
def buildParamsXML(movielist):
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
	except urllib2.URLError, e:
		try:
			if e.code == 202:
				if (__settings__.getSetting( "notifications" ) == 'true'):
					sendNotice("Library update sent.", "5000")
			elif e.code == 204:
				sendNotice("Empty movie library so not sending update.", "7000")
			elif e.code == 401:
				sendNotice("Authentication failed.", "5000")
			elif e.code == 403:
				sendNotice("Please update your addon before submitting.", "7000")
			else:
				sendNotice("Unexpected error.", "5000")
		except AttributeError:
			sendNotice("Unable to contact server but try again soon.", "5000")


def sendUpdate():
	if (__settings__.getSetting( "email" ) == '' or __settings__.getSetting( "password" ) == ''):
		sendNotice("Configure your account details before submitting.", "6000")
		return
	
	movielist = buildMovieXML(getMovieLibrary())
	debug('movielist is: ' + movielist)
	
	params = buildParamsXML(movielist)
	
	sendRequest(params)

def getMovieCount():
	query = "SELECT movie.c00 FROM movie"
	queryResult = xbmc.executehttpapi("QueryVideoDatabase(%s)" % urllib.quote_plus(query))
	count = str(queryResult.count("<field>"))
	debug("Movie count: " + count)
	return count


def waiter(seconds):
	for i in range(1, seconds):
		time.sleep(1)
		if xbmc.abortRequested == True:
			sys.exit()


def autoStart(option):
	# See if the autoexec.py file exists
	if (os.path.exists(AUTOEXEC_PATH)):
		debug('Found autoexec')
		
		# Var to check if we're in autoexec.py
		found = False
		autoexecfile = file(AUTOEXEC_PATH, 'r')
		filecontents = autoexecfile.readlines()
		autoexecfile.close()
		
		# Check if we're in it
		for line in filecontents:
			if line.find('sharethetv') > 0:
				debug('Found ourselves in autoexec')
				found = True
		
		# If the autoexec.py file is found and we're not in it,
		if (not found and option):
			debug('Adding ourselves to autoexec.py')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			filecontents.append(AUTOEXEC_SCRIPT)
			autoexecfile.writelines(filecontents)            
			autoexecfile.close()
		
		# Found that we're in it and it's time to remove ourselves
		if (found and not option):
			debug('Removing ourselves from autoexec.py')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			for line in filecontents:
				if not line.find('sharethetv') > 0:
					autoexecfile.write(line)
			autoexecfile.close()
	
	else:
		debug('autoexec.py doesnt exist')
		if (os.path.exists(AUTOEXEC_FOLDER_PATH)):
			debug('Creating autoexec.py with our autostart script')
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			autoexecfile.write (AUTOEXEC_SCRIPT.strip())
			autoexecfile.close()
		else:
			debug('Scripts folder missing, creating autoexec.py in that new folder with our script')
			os.makedirs(AUTOEXEC_FOLDER_PATH)
			autoexecfile = file(AUTOEXEC_PATH, 'w')
			autoexecfile.write (AUTOEXEC_SCRIPT.strip())
			autoexecfile.close()

startup = False

try:
    count = len(sys.argv) - 1
    if (sys.argv[1] == '-startup'):
        startup = True			
except:
    pass


# Main execution path
autorun = False
if (__settings__.getSetting( "autorun" ) == 'true' ):
	autorun = True

# If triggered from programs menu
if (not startup):
	debug('Triggered from programs menu, setting autostart option and running once')
	autoStart(autorun)
	sendUpdate()


oldCount = getMovieCount()
intervalDelay = 300
updateDelay = 60

if autorun:
	debug('Waiting to send updates')
	while 1:
		debug('Checking for library updates')
		
		newCount = getMovieCount()
		
		if oldCount == newCount:
			debug('No change in movie count')
			waiter(intervalDelay)
		else:
			
			while (oldCount != newCount):
				debug('Change in count found, sleep to let update finish')
				waiter(updateDelay)
				oldCount = newCount
				newCount = getMovieCount()
			
			debug('Counts stopped changing, sending update now')
			sendUpdate()
			waiter(intervalDelay)
		
		oldCount = newCount

