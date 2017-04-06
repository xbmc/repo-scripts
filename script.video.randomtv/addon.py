import xbmc
import xbmcgui
import xbmcaddon
import json
import random
import threading
import sys


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
	xbmc.sleep(5000)
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
		selectedShows = xbmcgui.Dialog().multiselect("Select TV Shows", listShows, preselect=listPreSelect)

		
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
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, "Starting", 2000, icon))
log("-------------------------------------------------------------------------")
log("Starting")
busyDiag.create()


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
	xbmcgui.Dialog().ok(name, "No available episodes to play", "Please check your settings")
	xbmc.executebuiltin('Addon.OpenSettings(%s)' % addonid)
	quit()
else:
	log("--------- Episodes Found")
	
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
	xbmc.sleep(100)
#


while (not xbmc.abortRequested):
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
		
		if addon.getSetting("RepeatPlaylist") == "true":
			if addon.getSetting("ShuffleOnRepeat") == "true":
				busyDiag.create()
				log("-- Shuffling Playlist")
				if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, "Shuffling Playlist", 5000, icon))
				random.shuffle(myEpisodes)
				buildPlaylist(myEpisodes)
			#

			log("-- Restarting Playlist")
			player.play(item=myPlaylist)
			xbmc.sleep(100)
		else:
			player.scriptStopped = True

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

	xbmc.sleep(100)
#


# Display Stopping Notification
if addon.getSetting("ShowNotifications") == "true": xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(name, "Stopping", 2000, icon))
log("Stopping")
log("-------------------------------------------------------------------------")