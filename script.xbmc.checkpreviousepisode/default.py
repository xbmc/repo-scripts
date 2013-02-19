import xbmc
import xbmcaddon
import xbmcgui
import os
import simplejson

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__language__ = __addon__.getLocalizedString

global g_jumpBackSecs
g_jumpBackSecs = 0

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg,),level=xbmc.LOGDEBUG )

#log( "[%s] - Version: %s Started" % (__scriptname__,__version__))

class MyPlayer( xbmc.Player ):
  def __init__( self, *args, **kwargs ):
    xbmc.Player.__init__( self )
    #log('MyPlayer - init')
  
  def onPlayBackStarted( self ):
    #log('Playback started!')
    command='{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
    result = xbmc.executeJSONRPC( command )
    result = unicode(result, 'utf-8', errors='ignore')
    #log("RAW: %s" % result)
    jsonobject = simplejson.loads(result)
    if(len(jsonobject['result']) == 1):
        resultitem = jsonobject['result'][0]
        #log("Player running with ID: %d" % resultitem['playerid'])
        
        command='{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "playerid": %d }, "id": 1}' % resultitem['playerid']
        result = xbmc.executeJSONRPC( command )
        result = unicode(result, 'utf-8', errors='ignore')
        #log("RAW: %s" % result)
        jsonobject = simplejson.loads(result)
        if(jsonobject['result']['item']['type'] == 'episode'):
            #log("An Episode is playing!")
            
            command='{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": { "episodeid": %d, "properties": ["tvshowid", "season", "episode"] }, "id": 1}' % jsonobject['result']['item']['id']
            result = xbmc.executeJSONRPC( command )
            result = unicode(result, 'utf-8', errors='ignore')
            #log("RAW: %s" % result)
            jsonobject = simplejson.loads(result)
            if(len(jsonobject['result']) == 1):
                playingTvshowid = jsonobject['result']['episodedetails']['tvshowid']
                playingSeason = jsonobject['result']['episodedetails']['season']
                playingEpisode = jsonobject['result']['episodedetails']['episode']
                #log("Playing Info: TVSHOWID '%d', SEASON: '%d', EPISODE: '%d'" % (jsonobject['result']['episodedetails']['tvshowid'], jsonobject['result']['episodedetails']['season'], jsonobject['result']['episodedetails']['episode']))
                #Lets see if we have the previous episode
                if(jsonobject['result']['episodedetails']['episode'] > 1): #debuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuug
                    command='{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "season": %d, "properties": ["episode", "playcount"] }, "id": 1}' % (jsonobject['result']['episodedetails']['tvshowid'], jsonobject['result']['episodedetails']['season'])
                    result = xbmc.executeJSONRPC( command )
                    result = unicode(result, 'utf-8', errors='ignore')
                    #log("RAW: %s" % result)
                    jsonobject = simplejson.loads(result)
                    if(len(jsonobject['result']) > 0):
                        #log("Finding...")
                        found = False
                        playcount = 0
                        for episode in jsonobject['result']['episodes']:
                            if(episode['episode'] == (playingEpisode - 1)):
                                #log("FOUND!")
                                playcount = episode['playcount']
                                found = True
                                break
                        
                        if not found or playcount == 0:
                            #log("Stopping playback!")
                            xbmc.Player().pause()
                            if not found:
                                playon = xbmcgui.Dialog().yesno("Missing Episode", "The previous episode is missing from your library!", "Are you sure you want to play this one?")
                            else:
                                playon = xbmcgui.Dialog().yesno("Unwatched Episode", "You have not watched the previous episode!", "Are you sure you want to play this one?")
                            if(playon):
                                xbmc.Player().pause()
                            else:
                                xbmc.Player().stop()

player_monitor = MyPlayer()

while not xbmc.abortRequested:
      xbmc.sleep(100)
