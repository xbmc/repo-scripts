import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
import json
import yaml
from distutils.util import strtobool

from traceback import format_exc

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')
__scriptname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__kodiversion__ = xbmc.getInfoLabel('System.BuildVersion')
__icon__ = __addon__.getAddonInfo('icon')
__ID__ = __addon__.getAddonInfo('id')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile'))
__ignoredshowsfile__ = xbmc.translatePath(os.path.join(__profile__, 'ignoredShows.yaml'))
__language__ = __addon__.getLocalizedString


def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log(("### [%s] - %s" % (__scriptname__, msg,)), level)


def getSetting(setting):
    return __addon__.getSetting(setting).strip()


def getSettingAsBoolean(setting):
    return bool(strtobool(str(__addon__.getSetting(setting)).lower()))


# Odd this is needed, it should be a testable state on Player really...
def isPlaybackPaused():
    return bool(xbmc.getCondVisibility("Player.Paused"))


def getIgnoredShowsFromConfig():

    # By default, no shows are ignored
    ignoredShows = {}

    # Update our internal list of ignored shows if there are any...
    if os.path.exists(__ignoredshowsfile__):
        log("Loading ignored shows from config file: " + __ignoredshowsfile__)
        with open(__ignoredshowsfile__, 'r') as yaml_file:
            ignoredShows = yaml.load(yaml_file)

    log("Ignored Shows loaded from config is: " + str(ignoredShows))

    return ignoredShows


def writeIgnoredShowsToConfig(ignoredShows, tvshowtitle=None, tvshowid=None):

    # Add new show to our dict of ignored shows if there is one...
    if tvshowid:
        log("Set show title " + tvshowtitle +
            ", id [" + str(tvshowid) + "], to ignore from now on.")
        ignoredShows[tvshowid] = tvshowtitle

    if not xbmcvfs.exists(__profile__):
        xbmcvfs.mkdirs(__profile__)
    # ...and dump the whole dict to our yaml file (clobber over any old file)
    with open(__ignoredshowsfile__, 'w') as yaml_file:
        log("Ignored Shows to write to config is: " + str(ignoredShows))
        yaml.dump(ignoredShows, yaml_file, default_flow_style=False)


# Check if the previous episode is present, and if so if it has been watched
def checkPreviousEpisode():

    global player_monitor

    ignoredShows = getIgnoredShowsFromConfig()

    log('Playback started!')
    command = '{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}'
    jsonobject = json.loads(xbmc.executeJSONRPC(command))
    log(str(jsonobject))

    # Only do something is we get a result for our query back from Kodi
    if(len(jsonobject['result']) == 1):

        resultitem = jsonobject['result'][0]
        log("Player running with ID: %d" % resultitem['playerid'])

        command = '{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "playerid": %d }, "id": 1}' % resultitem['playerid']
        jsonobject = json.loads(xbmc.executeJSONRPC(command))
        log(str(jsonobject))

        # Only do something is this is an episode of a TV show
        if jsonobject['result']['item']['type'] == 'episode':

            log("An Episode is playing!")

            command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": { "episodeid": %d, "properties": ["tvshowid", "showtitle", "season", "episode"] }, "id": 1}' % (
                jsonobject['result']['item']['id'])
            jsonobject = json.loads(xbmc.executeJSONRPC(command))
            log(str(jsonobject))

            # Only do something if we can get the episode details from Kodi
            if(len(jsonobject['result']) == 1):

                playingTvshowid = jsonobject['result']['episodedetails']['tvshowid']
                playingTvshowTitle = jsonobject['result']['episodedetails']['showtitle']
                playingSeason = jsonobject['result']['episodedetails']['season']
                playingEpisode = jsonobject['result']['episodedetails']['episode']
                log("Playing Info: SHOWTITLE '%s', TVSHOWID '%d', SEASON: '%d', EPISODE: '%d'" % (
                    playingTvshowTitle, playingTvshowid, playingSeason, playingEpisode))

                # Ignore first episodes...
                if(jsonobject['result']['episodedetails']['episode'] > 1):

                    command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %d, "season": %d, "properties": ["episode", "playcount"] }, "id": 1}' % (
                        jsonobject['result']['episodedetails']['tvshowid'], jsonobject['result']['episodedetails']['season'])
                    jsonobject = json.loads(xbmc.executeJSONRPC(command))
                    log(str(jsonobject))

                    # We found some episodes for this show...
                    if(len(jsonobject['result']) > 0):
                        found = False
                        playcount = 0
                        for episode in jsonobject['result']['episodes']:
                            if(episode['episode'] == (playingEpisode - 1)):
                                playcount += episode['playcount']
                                found = True

                        log("Found: " + str(found) + " playcount: " + str(playcount) +
                            " setting IgnoreIfEpisodeAbsentFromLibrary " + str(getSetting("IgnoreIfEpisodeAbsentFromLibrary")))

                        if (not found and getSettingAsBoolean("IgnoreIfEpisodeAbsentFromLibrary") != True) or (found and playcount == 0):

                            if playingTvshowid in ignoredShows:
                                log("Unplayed previous episode detected, but show set to ignore: " +
                                    playingTvshowTitle)
                            else:
                                # Only trigger the pause if the player is actually playing as other addons may also have paused the player
                                if not isPlaybackPaused():
                                    log("Pausing playback")
                                    player_monitor.pause()

                                result = xbmcgui.Dialog().select(__language__(32020), [__language__(
                                    32021), __language__(32022), __language__(32023)], preselect=0)

                                # User has requested we ignore this particular show from now on...
                                if result == 2:
                                    writeIgnoredShowsToConfig(
                                        ignoredShows, playingTvshowTitle, playingTvshowid)

                                if (result == 1 or result == 2):
                                    if isPlaybackPaused():
                                        log("Unpausing playback")
                                        player_monitor.pause()
                                else:
                                    player_monitor.stop()

                                    if(getSettingAsBoolean("ForceBrowseForShow") == True):
                                        # Jump to this shows Episode in the Kodi library
                                        command = '{"jsonrpc": "2.0", "method": "GUI.ActivateWindow", "params": { "window": "videos", "parameters": [ "videodb://2/2/%d/%d" ] }, "id": 1}' % (
                                            playingTvshowid, playingSeason)
                                        xbmc.executeJSONRPC(command)


# Manage ignored shows in settings..
def manageIgnored():

    log("Managing ignored shows...")

    dialog = xbmcgui.Dialog()

    ignoredShows = getIgnoredShowsFromConfig()

    if len(ignoredShows) < 1:
        dialog.notification(__scriptname__, __language__(
            32060), xbmcgui.NOTIFICATION_INFO, 5000)
    else:

        # Convert our dict to a list for the dialog...
        ignoredlist = []
        for key, value in list(ignoredShows.items()):
            ignoredlist.append(value)

        if ignoredlist != []:
            selected = dialog.select(
                "Select show to stop ignoring:", ignoredlist)
            if selected != -1:
                showtitle = ignoredlist[selected]
                log("User has requested we stop ignoring: " + showtitle)
                log("Ignored shows before removal is: " + str(ignoredShows))
                # find the key (tvshowid) for this show& remove from dict
                key = list(ignoredShows.keys())[
                    list(ignoredShows.values()).index(showtitle)]
                ignoredShows.pop(key, None)
                log("Ignored shows  after removal is: " + str(ignoredShows))

                # No ignored shows?  Clean up & delete the empty file..
                if len(ignoredShows) == 0:
                    if os.path.exists(__ignoredshowsfile__):
                        os.remove(__ignoredshowsfile__)
                else:
                    # write the ignored list back out
                    writeIgnoredShowsToConfig(ignoredShows)


# Listen to appropriate events for different Kodi versions
class MyPlayer(xbmc.Player):

    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)

    def onAVStarted(self):
        checkPreviousEpisode()


# RUNMODES - we're either running as a service, or we're running the tool to manage ignored shows..

# MANAGE IGNORED SHOWS
if len(sys.argv) > 1:
    try:
        if sys.argv[1].startswith('ManageIgnored'):
            manageIgnored()
    # if not, carry on, nothing to see here...
    except Exception as inst:
        log("Exception in ManageIgnored: " + format_exc(inst))

# DEFAULT - RUN AS A SERVICE & WATCH PLAYBACK EVENTS
else:
    log('Kodi ' + str(__kodiversion__) +
        ', listen to onAVStarted', xbmc.LOGINFO)

    monitor = xbmc.Monitor()
    player_monitor = MyPlayer()

    while not monitor.abortRequested():
        # Sleep/wait for abort for 10 seconds
        if monitor.waitForAbort(1):
            # Abort was requested while waiting. We should exit
            break
