import xbmc
import xbmcgui
import xbmcaddon
import json
import random
import threading
import sys
import time


def log(msg):
	xbmc.log("%s: %s" % (name,msg),level=xbmc.LOGDEBUG )
	#xbmc.log("%s: %s" % (name,msg), xbmc.LOGNOTICE)


def buildPlaylist(myEpisodes):
	# Clear Playlist
	myPlaylist.clear()

	for myEpisode in myEpisodes:
		log("Added Episode to Playlist: " + str(myEpisode['episodeId']) + " -- " + myEpisode['episodeShow'] + " - " + myEpisode['episodeName'])
		myPlaylist.add(url=myEpisode['episodeFile'])
	#


def ResetPlayCount(myEpisode):
	xbmc.Monitor().waitForAbort(5)
	log("--------- ResetPlayCount")
	log("-- Episode Id: " + str(myEpisode['episodeId']))
	log("-- Episode Name: " + str(myEpisode['episodeName']))
	log("-- Last Played: " + myEpisode['lastPlayed'])
	log("-- Play Count: " + str(myEpisode['playCount']))
	log("-- Resume Position: " + str(myEpisode['resume']['position']))
	log("-- Resume Total: " + str(myEpisode['resume']['total']))
	command = '{"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": { "episodeid": %d, "lastplayed": "%s", "playcount": %d, "resume": { "position": %d, "total": %d } }, "id": 1}' % (myEpisode['episodeId'], myEpisode['lastPlayed'], myEpisode['playCount'], myEpisode['resume']['position'], myEpisode['resume']['total'])
	response = json.loads(xbmc.executeJSONRPC(command))
	log("-- " + str(response))

  
class MyPlayer(xbmc.Player):
	def __init__(self, *args):
		xbmc.Player.__init__(self, *args)
		self.mediaStarted = False
		self.mediaEnded = False
		self.scriptStopped = False
		log("============================================================= INIT")

	def onPlayBackStarted(self):
		self.mediaStarted = True
		log("============================================================= START")

	def onPlayBackEnded(self):
		self.mediaEnded = True
		log("============================================================= END")

	def onPlayBackStopped(self):
		self.scriptStopped = True
		log("============================================================= STOP")
#


# Set some variables
addon = xbmcaddon.Addon()
addonid = addon.getAddonInfo("id")
name = addon.getAddonInfo("name")
icon = addon.getAddonInfo("icon")

busyDiag = xbmcgui.DialogBusy()
myEpisodes = []

includedShows = addon.getSetting("includedShows")



# Select Shows Settings Dialog
if len(sys.argv) > 1:
	if sys.argv[1] == "SelectShows":
		log("--------- Settings - SelectShows")
		busyDiag.create()
		listShows = []
		listPreSelect = []
		listPostSelect = []
		command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"sort": {"ignorearticle": true, "method": "label", "order": "ascending"}}, "id": 1}'
		allShows = json.loads(xbmc.executeJSONRPC(command))
		if allShows['result']['limits']['total'] > 0:
			for show in allShows['result']['tvshows']:
				listShows.append(show['label'])
				
				if not includedShows == "":
					if show['tvshowid'] in map(int, includedShows.split(", ")):
						listPreSelect.append(len(listShows) - 1)

			
		busyDiag.close()
		selectedShows = xbmcgui.Dialog().multiselect(xbmcaddon.Addon().getLocalizedString(32012), listShows, preselect=listPreSelect)

		
		if not selectedShows is None:
			for selectedShow in selectedShows:
				listPostSelect.append(allShows['result']['tvshows'][selectedShow]['tvshowid'])
			
			includedShows = ", ".join(str(i) for i in listPostSelect)
			addon.setSetting("includedShows", includedShows)

		xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonid)
		xbmc.executebuiltin('SetFocus(205)')
	quit()
#


# Display Starting Notification
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, xbmcaddon.Addon().getLocalizedString(32007), 2000, icon))
log("-------------------------------------------------------------------------")
log("Starting")
busyDiag.create()
backWindow = xbmcgui.Window()
backWindow.show()


# Get TV Episodes
if addon.getSetting("IncludeAll") == "true":
	command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "id": 1}'
	allShows = json.loads(xbmc.executeJSONRPC(command))
	
	if allShows['result']['limits']['total'] > 0:
		for show in allShows['result']['tvshows']:
			command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "properties": ["showtitle", "file", "playcount", "lastplayed", "resume"] }, "id": 1}' % (show['tvshowid'])
			allEpisodes = json.loads(xbmc.executeJSONRPC(command))
			
			if allEpisodes['result']['limits']['total'] > 0:
				for episode in allEpisodes['result']['episodes']:
					if addon.getSetting("IncludeUnwatched") == "true" or episode['playcount'] > 0:
						log("Added Episode: " + episode['label'].encode('utf-8').strip())
						myEpisodes.append({'episodeId': episode['episodeid'], 'episodeShow': episode['showtitle'].encode('utf-8').strip(), 'episodeName': episode['label'].encode('utf-8').strip(), 'episodeFile': episode['file'].encode('utf-8').strip(), 'playCount': episode['playcount'], 'lastPlayed': episode['lastplayed'], 'resume': episode['resume']})
else:
	for includedShow in map(int, includedShows.split(", ")):
		command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "properties": ["showtitle", "file", "playcount", "lastplayed", "resume"] }, "id": 1}' % includedShow
		allEpisodes = json.loads(xbmc.executeJSONRPC(command))
			
		if allEpisodes['result']['limits']['total'] > 0:
			for episode in allEpisodes['result']['episodes']:
				if addon.getSetting("IncludeUnwatched") == "true" or episode['playcount'] > 0:
					log("Added Episode: " + episode['label'].encode('utf-8').strip())
					myEpisodes.append({'episodeId': episode['episodeid'], 'episodeShow': episode['showtitle'].encode('utf-8').strip(), 'episodeName': episode['label'].encode('utf-8').strip(), 'episodeFile': episode['file'].encode('utf-8').strip(), 'playCount': episode['playcount'], 'lastPlayed': episode['lastplayed'], 'resume': episode['resume']})
		

log("Total Episodes: " + str(len(myEpisodes)))


# If no episodes, display notification and quit
if len(myEpisodes) == 0:
	log("--------- No episodes")
	xbmcgui.Dialog().ok(name, xbmcaddon.Addon().getLocalizedString(32008), xbmcaddon.Addon().getLocalizedString(32009))
	xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonid)
	quit()
else:
	log("--------- Episodes Found")
	# Get Auto Stop Check Time - Current Time + Auto Stop Check Timer
	if addon.getSetting("AutoStop") == "true":
		log("-- Auto Stop Enabled")
		log("-- Auto Stop Timer: " + addon.getSetting("AutoStopTimer"))
		log("-- Auto Stop Wait: " + addon.getSetting("AutoStopWait"))
		AutoStopCheckTime = int(time.time()) + (int(addon.getSetting("AutoStopTimer")) * 60)
		AutoStopWait = (int(addon.getSetting("AutoStopWait")) * 60)
		AutoStopDialog = xbmcgui.DialogProgress()
	#

	# Initialize our Player
	player = MyPlayer()
	
	# Create Playlist
	myPlaylist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

	# Shuffle Episodes
	random.shuffle(myEpisodes)
	
	# Build Playlist
	buildPlaylist(myEpisodes)

	# Start Player
	player.play(item=myPlaylist)
#


while (not xbmc.Monitor().waitForAbort(1)):
	if int(time.time()) >= AutoStopCheckTime:
		log("-- Auto Stop Timer Reached")
		AutoStopDialog.create(name, xbmcaddon.Addon().getLocalizedString(32015))
		while int(time.time()) < AutoStopCheckTime + AutoStopWait:
			AutoStopDialog.update(int(int(time.time() - AutoStopCheckTime) * 100 / AutoStopWait), xbmcaddon.Addon().getLocalizedString(32015), str(AutoStopWait - int(time.time() - AutoStopCheckTime)) + " " + xbmcaddon.Addon().getLocalizedString(32016))
			if AutoStopDialog.iscanceled():
				log("-- Dialog Cancelled - Breaking")
				break
			#
			xbmc.Monitor().waitForAbort(0.1)
		#
		if AutoStopDialog.iscanceled():
			log("-- Dialog Cancelled")
			AutoStopCheckTime = int(time.time()) + (int(addon.getSetting("AutoStopTimer")) * 60)
		#
		else:
			log("-- Dialog Not Cancelled")
			xbmc.executebuiltin('PlayerControl(Stop)')
		#
		AutoStopDialog.close()
		xbmc.Monitor().waitForAbort(0.2)
	#

	if player.mediaStarted:
		log("--------- mediaStarted")
		busyDiag.close()

		if 'lastEpisode' in locals():
			log("-- lastEpisode")
			if addon.getSetting("UpdatePlayCount") == "false":
				log("-- Start ResetPlayCount Thread")
				thread = threading.Thread(target=ResetPlayCount, args=(myEpisodes[lastEpisode],))
				thread.start()
			#
		#

		log("-- Started: " + myEpisodes[myPlaylist.getposition()]['episodeShow'] + " - " + myEpisodes[myPlaylist.getposition()]['episodeName'])
		if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, myEpisodes[myPlaylist.getposition()]['episodeShow'] + "\r\n" + myEpisodes[myPlaylist.getposition()]['episodeName'], 5000, icon))
		
		log("-- Playlist Position: " + str(myPlaylist.getposition()))
		
		lastEpisode = myPlaylist.getposition()
		player.mediaStarted = False
	#


	if player.mediaEnded:
		log("--------- mediaEnded")
		log("-- Playlist Position: " + str(myPlaylist.getposition()))
		
		if myPlaylist.getposition() < 0:
			log("-- Playlist Finished")
			if addon.getSetting("RepeatPlaylist") == "true":
				if addon.getSetting("ShuffleOnRepeat") == "true":
					busyDiag.create()
					log("-- Shuffling Playlist")
					if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, xbmcaddon.Addon().getLocalizedString(32010), 5000, icon))
					random.shuffle(myEpisodes)
					buildPlaylist(myEpisodes)
				#

				log("-- Restarting Playlist")
				player.play(item=myPlaylist)
			else:
				player.scriptStopped = True
		else:
			log("-- Playlist still going")
		#

		player.mediaEnded = False
	#


	if player.scriptStopped:
		log("--------- scriptStopped")
		if addon.getSetting("UpdatePlayCount") == "false" and 'lastEpisode' in locals():
			log("-- Start ResetPlayCount Thread")
			thread = threading.Thread(target=ResetPlayCount, args=(myEpisodes[lastEpisode],))
			thread.start()
		break
	#
#


# Display Stopping Notification
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, xbmcaddon.Addon().getLocalizedString(32011), 2000, icon))
backWindow.close()
log("Stopping")
log("-------------------------------------------------------------------------")
