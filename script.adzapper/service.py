# -*- coding: utf-8 -*-
import os
import sys
import urllib
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.timer import TimerWindow

ADDON = xbmcaddon.Addon(id='script.adzapper')

def jsonrpc(query):
    querystring = {"jsonrpc": "2.0", "id": 1}
    querystring.update(query)
    try:
        response = json.loads(xbmc.executeJSONRPC(json.dumps(querystring, encoding='utf-8')))
        return response
    except TypeError as e:
        raise self.JsonExecException('Error executing JSON RPC: %s' % e.message)
    return None

def getPlayer():
    props = {'player': None, 'playerid': None, 'media': None, 'id': None, 'channel': None}
    query = {
            "method": "Player.GetActivePlayers",
            }
    res = jsonrpc(query)
    if 'result' in res and res['result']:
        res = res['result'][0]
        props['player'] = res['type']
        props['playerid'] = res['playerid']

        query = {
                "method": "Player.GetItem",
                "params": {"properties": ["title", "season", "episode", "file", "channel"],
                           "playerid": props['playerid']},
                "id": "VideoGetItem"
                }
        res = jsonrpc(query)
        if 'result' in res:
            res = res['result'].get('item')
            props['media'] = res['type']
            props['channel'] = res['channel']            
            if 'id' in res: props['id'] = res['id']
    return props
    
def switchToChannelId(playerProperties, channelId, channel):

    if playerProperties['player'] == 'audio' or (playerProperties['player'] == 'video' and playerProperties['media'] != 'channel'):

        # stop all other players except pvr

        log('player:%s media:%s @id:%s is running' % (playerProperties['player'], playerProperties['media'], playerProperties['playerid']))
        query = {
            "method": "Player.Stop",
            "params": {"playerid": playerProperties['playerid']},
        }
        res = jsonrpc(query)
        if 'result' in res and res['result'] == "OK":
            handler.notifyLog('Player stopped')

    log('Currently playing channelid %s (%s), switch to id %s' % (playerProperties['id'], playerProperties['channel'], channelId))
    query = {
        "method": "Player.Open",
        "params": {"item": {"channelid": channelId}}
    }
    res = jsonrpc(query)
    if 'result' in res and res['result'] == 'OK':
        log('Switched to channel \'%s\'' % (channel))
    else:
        log('Couldn\'t switch to channel \'%s\'' % (channel))


# Class to detect when something in the system has changed
class ADZapperMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        log("Monitor: Notification of settings change received")
        Settings.reloadSettings()


##################################
# Main of the AD zapper service
##################################
if __name__ == '__main__':
    log("Service Started")

    # Construct the monitor to detect system changes
    monitor = ADZapperMonitor()

    secondsUntilRezap = -1
    timerCancelled = True

    while not monitor.abortRequested():
        showTimerWindow = False

        # Check if we need to prompt the user to enter a new set of rezap values
        adzapperPrompt = xbmcgui.Window(10000).getProperty("ADZapperPrompt")
        if adzapperPrompt not in ["", None]:
            xbmcgui.Window(10000).clearProperty("ADZapperPrompt")
            log("Request to display prompt detected")
            if xbmc.getCondVisibility('Pvr.IsPlayingTv'):
                showTimerWindow = True
                log("Live TV is playing -> show timer window")
            else:
                log("Live TV is NOT playing -> skip showing timer window")
                
        # Check if we need to warn the user that the rezap is near :-)
        if secondsUntilRezap == Settings.getWarningLength():
            log("Nearing rezap time, display dialog")
            showTimerWindow = True

        # Show timer window?
        if showTimerWindow and (xbmc.getCondVisibility('Pvr.IsPlayingTv')):
            # store channel when no timer is running
            if secondsUntilRezap == -1:
                try:
                    #rezapurl = xbmc.Player().getPlayingFile()
                    plrPropsRezap = getPlayer()
                    log("timer not running, stored values (id: %s, channel: %s) for rezap" % (plrPropsRezap['id'],plrPropsRezap['channel']),xbmc.LOGINFO)
                except:
                    log("Failed to get current channelid & channel: %s" % traceback.format_exc(), xbmc.LOGERROR)            
        
            # Need to display the window using the existing values
            viewer = TimerWindow.createTimerWindow(plrPropsRezap['channel'], secondsUntilRezap)

            viewer.show()
            # Tidy up any duplicate presses of the remote button before we run
            # the progress
            xbmcgui.Window(10000).clearProperty("ADZapperPrompt")
            viewer.runProgress()

            # Now read the values entered for the rezap timers
            timerCancelled, secondsUntilRezap = viewer.getTimerValues()
            del viewer

        if secondsUntilRezap > 0:
            # Reduce the remaining timer by one second
            secondsUntilRezap = secondsUntilRezap - 1

        # Check if it is time to rezap
        if (not timerCancelled) and (secondsUntilRezap == 0):
            # Clear all the values first
            secondsUntilRezap = -1
            timerCancelled = True
            
            # do we currently playing live tv?
            if xbmc.getCondVisibility('Pvr.IsPlayingTv'):
                # live tv is playing -> execute rezap to old channel
                log("rezap timer over, rezap to id: %s, channel: %s" % (plrPropsRezap['id'],plrPropsRezap['channel']),xbmc.LOGINFO)               
                xbmcgui.Dialog().notification(ADDON.getLocalizedString(32001).encode('utf-8'), plrPropsRezap['channel'], ADDON.getAddonInfo('icon'), 3000, False)
                plrProps = getPlayer()
                switchToChannelId(plrProps, plrPropsRezap['id'], plrPropsRezap['channel'])               

        # Sleep/wait for abort for the correct interval
        if monitor.waitForAbort(1):
            # Abort was requested while waiting
            break

    del monitor

    log("Service Ended")
