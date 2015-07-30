import xbmcaddon
import xbmcplugin
import xbmc
import xbmcgui
import os
import threading
import json
import inspect

import Utils as utils

from ClientInformation import ClientInformation
from NextUpInfo import NextUpInfo
from StillWatchingInfo import StillWatchingInfo

# service class for playback monitoring
class Player( xbmc.Player ):

    # Borg - multiple instances, shared state
    _shared_state = {}
    
    xbmcplayer = xbmc.Player()
    clientInfo = ClientInformation()
    
    addonName = clientInfo.getAddonName()
    addonId = clientInfo.getAddonId()
    addon = xbmcaddon.Addon(id=addonId)

    logLevel = 0
    currenttvshowid = None
    currentepisodeid = None
    playedinarow = 1
    
    def __init__( self, *args ):
        
        self.__dict__ = self._shared_state
        self.logMsg("Starting playback monitor service", 1)
        
    def logMsg(self, msg, lvl=1):
        
        self.className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, self.className), msg, int(lvl))      
    
    def json_query(self, query, ret):
    	try:
    		xbmc_request = json.dumps(query)
    		result = xbmc.executeJSONRPC(xbmc_request)
    		result = unicode(result, 'utf-8', errors='ignore')
    		if ret:
    			return json.loads(result)['result']
    
    		else:
    			return json.loads(result)
    	except:
    		xbmc_request = json.dumps(query)
    		result = xbmc.executeJSONRPC(xbmc_request)
    		result = unicode(result, 'utf-8', errors='ignore')
    		self.logMsg(json.loads(result),1)
    		return json.loads(result)
    def iStream_fix(self, show_npid, showtitle, episode_np, season_np):
    
    	# streams from iStream dont provide the showid and epid for above
    	# they come through as tvshowid = -1, but it has episode no and season no and show name
    	# need to insert work around here to get showid from showname, and get epid from season and episode no's
    	# then need to ignore prevcheck
    	self.logMsg('fixing strm, data follows...')
    	self.logMsg('show_npid = ' +str(show_npid))
    	self.logMsg('showtitle = ' +str(showtitle))
    	self.logMsg('episode_np = ' +str(episode_np))
    	self.logMsg('season_np = ' + str(season_np))
    	
	show_request_all       = {"jsonrpc": "2.0","method": "VideoLibrary.GetTVShows","params": {"properties": ["title"]},"id": "1"}
	eps_query              = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["season","episode","runtime","resume","playcount","tvshowid","lastplayed","file"],"tvshowid": "1"},"id": "1"}
    	
    	ep_npid = " "
    	
    	redo = True
    	count = 0
    	while redo and count < 2: 				# this ensures the section of code only runs twice at most [ only runs once fine ?
    		redo = False
    		count += 1
    		if show_npid == -1 and showtitle and episode_np and season_np:
    			prevcheck = False
    			tmp_shows = self.json_query(show_request_all,True)
    			self.logMsg('tmp_shows = ' + str(tmp_shows))
    			if 'tvshows'in tmp_shows:
    				for x in tmp_shows['tvshows']:
    					if x['label'] == showtitle:
    						show_npid = x['tvshowid']
    						eps_query['params']['tvshowid'] = show_npid
    						tmp_eps = self.json_query(eps_query,True)
    						self.logMsg('tmp eps = '+ str(tmp_eps))
    						if 'episodes' in tmp_eps:
    							for y in tmp_eps['episodes']:
    								if (y['season']) == season_np and (y['episode']) == episode_np:
    									ep_npid = y['episodeid']
    									self.logMsg('playing epid stream = ' + str(ep_npid))
    
    	return show_npid, ep_npid
    
    def findNextEpisode(self, result):
        self.logMsg("Find next episode called", 1)
        position = 0
        for episode in result[ "result" ][ "episodes" ]:
            # find position of current episode
            if self.currentepisodeid == episode["episodeid"]:
               # found a match so add 1 for the next and get out of here
               position = position + 1
               break
            else:
               # no match found continue
               position = position + 1
        # now return the episode
        self.logMsg("Find next episode found next episode in position: "+str(position), 1)  
        try:
            episode = result[ "result" ][ "episodes" ][position]
        except:
            # no next episode found
            episode = None
        
        return episode
         
    
    def autoPlayPlayback(self):
        currentFile = xbmc.Player().getPlayingFile()
    
        # Get the active player
        result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
        result = unicode(result, 'utf-8', errors='ignore')
        self.logMsg( "Got active player "+ result ,2)
        result = json.loads(result)
        
        # Seems to work too fast loop whilst waiting for it to become active
        while result["result"] == []:
            result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}' )
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg( "Got active player "+ result ,2)
            result = json.loads(result)
        
        if result.has_key('result') and result["result"][0] != None:
            playerid = result[ "result" ][ 0 ][ "playerid" ]
            
            # Get details of the playing media
            self.logMsg( "Getting details of playing media" ,1)
            result = xbmc.executeJSONRPC( '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": ' + str( playerid ) + ', "properties": ["showtitle", "tvshowid", "episode", "season", "playcount"] } }' )
            result = unicode(result, 'utf-8', errors='ignore')
            self.logMsg( "Got details of playing media" + result,2)
            
            result = json.loads(result)
            if result.has_key( 'result' ):
                type = result[ "result" ][ "item" ][ "type" ]
                if type == "episode":
                    # Get the next up episode
                    addonSettings = xbmcaddon.Addon(id='service.nextup.notification')
                    playMode = addonSettings.getSetting("autoPlayMode")
                    tvshowid = result[ "result" ][ "item" ][ "tvshowid" ]
                    currentepisodenumber = result[ "result" ][ "item" ][ "episode" ]
                    currentseasonid = result[ "result" ][ "item" ][ "season" ]
                    currentshowtitle = result[ "result" ][ "item" ][ "showtitle" ]
                    tvshowid = result[ "result" ][ "item" ][ "tvshowid" ]
                    
                    # I am a STRM ###
                    if tvshowid == -1:
                    	tvshowid, episodeid = self.iStream_fix(tvshowid,currentshowtitle,currentepisodenumber,currentseasonid)
                    	currentepisodeid = episodeid
                    else:
                        currentepisodeid = result[ "result" ][ "item" ][ "id" ]
                    
                    self.currentepisodeid = currentepisodeid
                    self.logMsg( "Getting details of next up episode for tvshow id: "+str(tvshowid) ,1)
                    if self.currenttvshowid != tvshowid: 
                        self.currenttvshowid = tvshowid
                        self.playedinarow = 1
                    includeWatched = addonSettings.getSetting("includeWatched") == "true"
                    if includeWatched == True:                 
                        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", "dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}' %tvshowid)
                    else:
                        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "sort": {"method":"episode"}, "filter": {"field": "playcount", "operator": "lessthan", "value":"1"}, "properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", "dateadded", "lastplayed" , "streamdetails"], "limits":{"start":1,"end":2}}, "id": "1"}' %tvshowid)    
                        
                    if result:      
                        result = unicode(result, 'utf-8', errors='ignore')
                        result = json.loads(result)
                        self.logMsg( "Got details of next up episode %s" % str(result),2)
                        xbmc.sleep( 100 )
                        
                        # Find the next unwatched and the newest added episodes
                        if result.has_key( "result" ) and result[ "result" ].has_key( "episodes" ):
                            if includeWatched == True:
                                episode = self.findNextEpisode(result)
                            else:
                                episode = result[ "result" ][ "episodes" ][0]
                                
                            if episode == None:
                                 # no episode get out of here
                                 return   
                            self.logMsg( "episode details %s" % str(episode),2)
                            episodeid =  episode["episodeid"]
                            includePlaycount = True
                            if includeWatched == True:
                                includePlaycount = True
                            else:
                                includePlaycount = episode[ "playcount" ] == 0
                            if includePlaycount and currentepisodeid != episodeid:
                                    # we have a next up episode
                                    nextUpPage = NextUpInfo("script-nextup-notification-NextUpInfo.xml", addonSettings.getAddonInfo('path'), "default", "1080i")
                                    nextUpPage.setItem(episode)
                                    stillWatchingPage = StillWatchingInfo("script-nextup-notification-StillWatchingInfo.xml", addonSettings.getAddonInfo('path'), "default", "1080i")
                                    stillWatchingPage.setItem(episode)
                                    playTime = xbmc.Player().getTime()
                                    totalTime = xbmc.Player().getTotalTime()
                                    playedinarownumber = addonSettings.getSetting("playedInARow")
                                    self.logMsg( "played in a row settings %s" % str(playedinarownumber),2)                                    
                                    self.logMsg( "played in a row %s" % str(self.playedinarow),2)
                                    if int(self.playedinarow) <= int(playedinarownumber):
                                        self.logMsg( "showing next up page as played in a row is %s" % str(self.playedinarow),2)            
                                        nextUpPage.show()
                                    else:
                                        self.logMsg( "showing still watching page as played in a row %s" % str(self.playedinarow),2)                                    
                                        stillWatchingPage.show()
                                    playTime = xbmc.Player().getTime()
                                    totalTime = xbmc.Player().getTotalTime()
                                    while xbmc.Player().isPlaying() and (totalTime-playTime > 1) and not nextUpPage.isCancel() and not nextUpPage.isWatchNow() and not stillWatchingPage.isStillWatching() and not stillWatchingPage.isCancel():
                                        xbmc.sleep(100)
                                        try:
                                                playTime = xbmc.Player().getTime()
                                                totalTime = xbmc.Player().getTotalTime()
                                        except:
                                                pass
                                            
                                    if int(self.playedinarow) <= int(playedinarownumber):
                                        nextUpPage.close()
                                        shouldPlayDefault = not nextUpPage.isCancel()
                                        shouldPlayNonDefault = nextUpPage.isWatchNow() 
                                    else:
                                        stillWatchingPage.close()
                                        shouldPlayDefault = stillWatchingPage.isStillWatching()
                                        shouldPlayNonDefault = stillWatchingPage.isStillWatching()
                                    
                                    if nextUpPage.isWatchNow() or stillWatchingPage.isStillWatching():
                                        self.playedinarow = 1
                                    else:
                                        self.playedinarow = self.playedinarow + 1
                                    if (shouldPlayDefault and playMode =="0") or (shouldPlayNonDefault and playMode=="1"):
                                        self.logMsg( "playing media episode id %s" % str(episodeid),2)
                                        # Play media
                                        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", "params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }' )
            
