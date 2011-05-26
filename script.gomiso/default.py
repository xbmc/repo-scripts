import xbmc
import xbmcaddon
import os
import time
import simplejson as json

"""Main code for interaction between Gomiso (www.gomiso.com) and XBMC (www.xbmc.org)
"""

__author__ = "Mathieu Feulvarch"
__copyright__ = "Copyright 2011, Mathieu Feulvarch "
__license__ = "GPL"
__version__ = "1.3.0"
__maintainer__ = "Mathieu Feulvarch"
__email__ = "mathieu@feulvarch.fr"
__status__ = "Production"

__scriptID__ = "script.gomiso"
__settings__ = xbmcaddon.Addon(id=__scriptID__)
__language__ = __settings__.getLocalizedString
__cwd__ = __settings__.getAddonInfo('path')

BASE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib'))
LANGUAGE_RESOURCE_PATH = xbmc.translatePath(os.path.join(__cwd__, 'resources', 'language'))
sys.path.append (BASE_RESOURCE_PATH)
sys.path.append (LANGUAGE_RESOURCE_PATH)
AUTOEXEC_SCRIPT = 'xbmc.executebuiltin("XBMC.RunScript(special://home/addons/' + __scriptID__ + '/default.py,-startup)")\n'
AUTOEXEC_FILE = xbmc.translatePath('special://home/userdata/autoexec.py')
AUTOEXEC_FOLDER_PATH = xbmc.translatePath('special://home/userdata/')

addon_work_folder = os.path.join(xbmc.translatePath("special://profile/addon_data/"), __scriptID__)
tokensFile = addon_work_folder + '/tokens'
settingsFile = addon_work_folder + '/settings.xml'

#Now that we appended the directories, let's import
from gomiso import gomiso

def deleteAutostart():
#	if os.path.exists(AUTOEXEC_FILE):
#		autoExecFile = file(AUTOEXEC_FILE, 'r')
#		fileContent = autoExecFile.readlines()
#		autoExecFile.close()
#		autoExecFile = file('AUTOEXEC_FILE', 'w')
#		for line in fileContent:
#			if not line.find('time.sleep(5) #gomiso'):
#				autoExecFile.write(line)
#			elif not line.find(AUTOEXEC_SCRIPT):
#				autoExecFile.write(line)
#			else:
#				autoExecFile.write('')
#		autoExecFile.close()
#		xbmc.log('####Done')
	xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', __language__(30923), 10000, __settings__.getAddonInfo("icon")))

def setAutostart():
	bFound = False
	timeFound = False
	xbmcFound = False
	sleepFound = False
	if os.path.exists(AUTOEXEC_FILE):
		autoExecFile = file(AUTOEXEC_FILE, 'r')
		fileContent = autoExecFile.readlines()
		autoExecFile.close()
		for line in fileContent:
			if line.find(__scriptID__) > 0:
				bFound = True
			elif line.find('import time') >0:
				timeFound = True
			elif line.find('import xbmc') > 0:
				xbmcFound = True
			elif line.find('time.sleep(5) #gomiso') > 0:
				sleepFound = True
		if not bFound:
			autoExecFile = file(AUTOEXEC_FILE, 'w')
			fileContent.append('\n' + AUTOEXEC_SCRIPT)
			if not timeFound:
				autoExecFile.writelines('\nimport time')
			if not xbmcFound:
				autoExecFile.writelines('\nimport xbmc')
			if not sleepFound:
				autoExecFile.writelines('\ntime.sleep(5) #gomiso')
			autoExecFile.writelines(fileContent)            
			autoExecFile.close()
	else:
		if os.path.exists(AUTOEXEC_FOLDER_PATH):
			autoExecFile = file(AUTOEXEC_FILE, 'w')
			autoExecFile.writelines('\nimport time')
			autoExecFile.writelines('\nimport xbmc')
			autoExecFile.writelines('\ntime.sleep(5) #gomiso')
			autoExecFile.write('\n' + AUTOEXEC_SCRIPT)
			autoExecFile.close()
		else:
			os.makedirs(AUTOEXEC_FOLDER_PATH)
			autoExecFile = file(AUTOEXEC_FILE, 'w')
			autoExecFile.writelines('\nimport time')
			autoExecFile.writelines('\nimport xbmc')
			autoExecFile.writelines('\ntime.sleep(5) #gomiso')
			autoExecFile.write('\n' + AUTOEXEC_SCRIPT)
			autoExecFile.close()

def percentageRemaining(currenttime, duration):
    try:
        currentMinutes = (int(currenttime.split(':')[0]) * 60) + int(currenttime.split(':')[1])
    except:
        currentMinutes = int(0)
    try:
        durationMinutes = (int(duration.split(':')[0]) * 60) + int(duration.split(':')[1])
    except:
        durationMinutes = int(0)
    try:
        return float(currentMinutes) / float(durationMinutes) 
    except:
        return float(0.0)

#Commented as: next XBMC version will come with new autostart features (so need to find a way to get both together if possible for backward compatibility)

#We cannot have tokens file and no settings file
if os.path.isfile(tokensFile) == True:
	if os.path.isfile(settingsFile) != True:
		os.remove(tokensFile)
		__settings__.openSettings()
#And no settings file and no tokens file would force setting page to appear
elif os.path.isfile(settingsFile) != True:
	__settings__.openSettings()

#From now on, we have all needed informations to work with
username = __settings__.getSetting('Username')
password = __settings__.getSetting('Password')

#Class instanciation and authentification with application key and secret
letsGo = gomiso()
if letsGo.authentification('AgmVUNp8BgtTLQWElAnA', 'BL7xQH3Aeut68IWsOD6SGoUfsRqkC5t16jLg', username, password, tokensFile) == False:
	xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', __language__(30921), 5000, __settings__.getAddonInfo("icon")))
else:
	#Retrieving user information and display a message that authentification is ok
	json_result = json.loads(letsGo.getUserInfo())
	xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', json_result['user']['username'] + " " + __language__(30916), 5000, __settings__.getAddonInfo("icon")))

	videoThreshold = int(__settings__.getSetting("VideoThreshold"))
	if videoThreshold == 0:
		videoThreshold = 75
	elif videoThreshold == 1:
		videoThreshold = 25
	#videoThreshold=25
	submitLimit = float(videoThreshold) / 100
	checkedTitle = ''
	sleepTime = 10

	#Did we display messages on screen when playing video?
	verboseScreen = __settings__.getSetting("DisplayScreen")
	if (verboseScreen == 'true'):
		verboseScreen = True
	else:
		verboseScreen = False
	
	#Did we want autostart?
	autoStart = __settings__.getSetting("Autostart")
	if(autoStart == 'true'):
		setAutostart()
	else:
		deleteAutostart()
	
	#What display message do we want?
	displayMessage = __language__(30919)
	defaultSubmissionMessage = __settings__.getSetting("DisplayDefaultMessage")
	if(defaultSubmissionMessage == 'false'):
		displayMessage = __settings__.getSetting("DisplayMessage")
	
	#This is the main part of the program
	while (not xbmc.abortRequested):
		time.sleep(sleepTime)
		if xbmc.Player().isPlayingVideo():
			currentTitle = xbmc.getInfoLabel("VideoPlayer.Title")
			##Are we watching a TV show?
			if currentTitle != checkedTitle:
				completion = percentageRemaining(xbmc.getInfoLabel("VideoPlayer.Time"), xbmc.getInfoLabel("VideoPlayer.Duration"))
				if completion > submitLimit:
					if len(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")) >= 1:
						#Retrieve TV show information
						showname = xbmc.getInfoLabel("VideoPlayer.TvShowTitle")
						showname = showname.replace(",", '')
						season = xbmc.getInfoLabel("VideoPlayer.Season")
						episode = xbmc.getInfoLabel("VideoPlayer.Episode")
						
						#Retrieve only one entry but would be good to have a threshold level like if more than 20 entries, no submit
						json_result = json.loads(letsGo.findMedia(showname, 'tv', 1))
						if len(json_result) != 0:
							
							letsGo.checking(json_result[0]['media']['id'], season, episode, displayMessage)
							if verboseScreen:
								xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', showname + ' S' + season + 'E' + episode + ' ' + __language__(30918), 5000, __settings__.getAddonInfo("icon")))
						else:
							if verboseScreen:
								xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', showname + ' S' + season + 'E' + episode + ' ' + __language__(30917), 5000, __settings__.getAddonInfo("icon")))
						checkedTitle = currentTitle
					#Or are we watching a movie
					elif len(xbmc.getInfoLabel("VideoPlayer.Title")) >= 1:
						#Retrieve movie information
						movieName = xbmc.getInfoLabel("VideoPlayer.Title")
						movieName = movieName.replace(",", '')
						
						#Retrieve only one entry but would be good to have a threshold level like if more than 20 entries, no submit
						json_result = json.loads(letsGo.findMedia(movieName, 'movie', 1))
						if len(json_result) != 0:
							letsGo.checking(json_result[0]['media']['id'], season, episode, 'watched on XBMC with gomiso addon')
							if verboseScreen:
								xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', movieName + ' ' + __language__(30918), 5000, __settings__.getAddonInfo("icon")))
						else:
							if verboseScreen:
								xbmc.executebuiltin("XBMC.Notification(%s, %s, %i, %s)"  % ('Gomiso', movieName + ' ' + __language__(30917), 5000, __settings__.getAddonInfo("icon")))
						checkedTitle = currentTitle