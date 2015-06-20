# -*- coding: utf-8 -*-

""" Service Sleep Timer  (c)  2015 enen92, Solo0815

# This program is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation;
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program;
# if not, see <http://www.gnu.org/licenses/>.


"""

import time
import datetime
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os

msgdialogprogress = xbmcgui.DialogProgress()

addon_id = 'service.sleeptimer'
selfAddon = xbmcaddon.Addon(id=addon_id)
datapath = xbmc.translatePath(selfAddon.getAddonInfo('profile')).decode('utf-8')
addonfolder = xbmc.translatePath(selfAddon.getAddonInfo('path')).decode('utf-8')
debug=selfAddon.getSetting('debug_mode')

__version__ = selfAddon.getAddonInfo('version')
check_time = selfAddon.getSetting('check_time')
check_time_next = int(selfAddon.getSetting('check_time_next'))
time_to_wait = int(selfAddon.getSetting('waiting_time_dialog'))
audiochange = selfAddon.getSetting('audio_change')
audiochangerate = int(selfAddon.getSetting('audio_change_rate'))
global audio_enable
audio_enable = str(selfAddon.getSetting('audio_enable'))
video_enable = str(selfAddon.getSetting('video_enable'))
max_time_audio = int(selfAddon.getSetting('max_time_audio'))
max_time_video = int(selfAddon.getSetting('max_time_video'))
enable_screensaver = selfAddon.getSetting('enable_screensaver')
custom_cmd = selfAddon.getSetting('custom_cmd')
cmd = selfAddon.getSetting('cmd')

# Functions:
def translate(text):
    return selfAddon.getLocalizedString(text).encode('utf-8')

def _log( message ):
    print addon_id + ": " + str(message)

# print the actual playing file in DEBUG-mode
def print_act_playing_file():
    if debug == 'true':
        actPlayingFile = xbmc.Player().getPlayingFile()
        _log ( "DEBUG: File: " + str(actPlayingFile) )

# wait for abort - xbmc.sleep or time.sleep doesn't work
# and prevents Kodi from exiting
def do_next_check( iTimeToWait ):
    if debug == 'true':
        _log ( "DEBUG: next check in " + str(iTimeToWait) + " min" )
    if xbmc.Monitor().waitForAbort(int(iTimeToWait)*60):
        exit()

class service:
    def __init__(self):
        FirstCycle = True
        next_check = False

        while True:
            if FirstCycle:
                # Variables:
                enable_audio = audio_enable
                enable_video = video_enable
                maxaudio_time_in_minutes = max_time_audio
                maxvideo_time_in_minutes = max_time_video
                iCheckTime = check_time

                _log ( "started ... (" + str(__version__) + ")" )
                if debug == 'true':
                    _log ( "DEBUG: ################################################################" )
                    _log ( "DEBUG: Settings in Kodi:" )
                    _log ( 'DEBUG: enable_audio: ' + enable_audio )
                    _log ( "DEBUG: maxaudio_time_in_minutes: " + str(maxaudio_time_in_minutes) )
                    _log ( "DEBUG: enable_video: " + str(enable_video) )
                    _log ( "DEBUG: maxvideo_time_in_minutes: " + str(maxvideo_time_in_minutes) )
                    _log ( "DEBUG: check_time: " + str(iCheckTime) )
                    _log ( "DEBUG: ################################################################" )
                    # Set this low values for easier debugging!
                    _log ( "DEBUG: debug is enabled! Override Settings:" )
                    enable_audio = 'true'
                    _log ( "DEBUG: -> enable_audio: " + str(enable_audio) )
                    maxaudio_time_in_minutes = 1
                    _log ( "DEBUG: -> maxaudio_time_in_minutes: " + str(maxaudio_time_in_minutes) )
                    enable_video = 'true'
                    _log ( "DEBUG: -> enable_video: " + str(enable_audio) )
                    maxvideo_time_in_minutes = 1
                    _log ( "DEBUG: -> maxvideo_time_in_minutes: " + str(maxvideo_time_in_minutes) )
                    iCheckTime = 1
                    _log ( "DEBUG: -> check_time: " + str(iCheckTime) )
                    _log ( "DEBUG: ----------------------------------------------------------------" )

                # wait 15s before start to let Kodi finish the intro-movie
                if xbmc.Monitor().waitForAbort(15):
                    break

                max_time_in_minutes = -1
                FirstCycle = False

            idle_time = xbmc.getGlobalIdleTime()
            idle_time_in_minutes = int(idle_time)/60

            if xbmc.Player().isPlaying():

                if debug == 'true' and max_time_in_minutes == -1:
                    _log ( "DEBUG: max_time_in_minutes before calculation: " + str(max_time_in_minutes) )

                if next_check == 'true':
                    # add "diff_betwenn_idle_and_check_time" to "idle_time_in_minutes"
                    idle_time_in_minutes += int(diff_betwenn_idle_and_check_time)

                if debug == 'true' and max_time_in_minutes == -1:
                    _log ( "DEBUG: max_time_in_minutes after calculation: " + str(max_time_in_minutes) )

                if xbmc.Player().isPlayingAudio():
                    if enable_audio == 'true':
                        if debug == 'true':
                            _log ( "DEBUG: enable_audio is true" )
                            print_act_playing_file()
                        what_is_playing = "audio"
                        max_time_in_minutes = maxaudio_time_in_minutes
                    else:
                        if debug == 'true':
                            _log ( "DEBUG: Player is playing Audio, but check is disabled" )
                        do_next_check(iCheckTime)
                        continue

                elif xbmc.Player().isPlayingVideo():
                    if enable_video == 'true':
                        if debug == 'true':
                            _log ( "DEBUG: enable_video is true" )
                            print_act_playing_file()
                        what_is_playing = "video"
                        max_time_in_minutes = maxaudio_time_in_minutes
                    else:
                        if debug == 'true':
                            _log ( "DEBUG: Player is playing Video, but check is disabled" )
                        do_next_check(iCheckTime)
                        continue

                ### ToDo:
                # expand it with RetroPlayer for playing Games!!!

                else:
                    if debug == 'true':
                        _log ( "DEBUG: Player is playing, but no Audio or Video" )
                        print_act_playing_file()
                    what_is_playing = "other"
                    do_next_check(iCheckTime)
                    continue

                if debug == 'true':
                    _log ( "DEBUG: what_is_playing: " + str(what_is_playing) )

                if debug == 'true':
                    _log ( "DEBUG: idle_time: '" + str(idle_time) + "s'; idle_time_in_minutes: '" + str(idle_time_in_minutes) + "'" )
                    _log ( "DEBUG: max_time_in_minutes: " + str(max_time_in_minutes) )

                # only display the Progressdialog, if audio or video is enabled AND idle limit is reached

                # Check if what_is_playing is not "other" and idle time exceeds limit
                if ( what_is_playing != "other" and idle_time_in_minutes >= max_time_in_minutes ):

                    if debug == 'true':
                        _log ( "DEBUG: idle_time exceeds max allowed. Display Progressdialog" )

                    ret = msgdialogprogress.create(translate(30000),translate(30001))
                    secs=0
                    percent=0
                    # use the multiplier 100 to get better %/calculation
                    increment = 100*100 / time_to_wait
                    cancelled = False
                    while secs < time_to_wait:
                        secs = secs + 1
                        # divide with 100, to get the right value
                        percent = increment*secs/100
                        secs_left = str((time_to_wait - secs))
                        remaining_display = str(secs_left) + " seconds left."
                        msgdialogprogress.update(percent,translate(30001),remaining_display)
                        xbmc.sleep(1000)
                        if (msgdialogprogress.iscanceled()):
                            cancelled = True
                            if debug == 'true':
                                _log ( "DEBUG: Progressdialog cancelled" )
                            break
                    if cancelled == True:
                        iCheckTime = check_time_next
                        _log ( "Progressdialog cancelled, next check in " + str(iCheckTime) + " min" )
                        # set next_check, so that it opens the dialog after "iCheckTime"
                        next_check = True
                        msgdialogprogress.close()
                    else:
                        _log ( "Progressdialog not cancelled: stopping Player" )
                        msgdialogprogress.close()

                        # softmute audio before stop playing
                        # get actual volume
                        if audiochange == 'true':
                            resp = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume"] }, "id": 1}')
                            dct = json.loads(resp)
                            muteVol = 10

                            if (dct.has_key("result")) and (dct["result"].has_key("volume")):
                                curVol = dct["result"]["volume"]

                                for i in range(curVol - 1, muteVol - 1, -1):
                                    xbmc.executebuiltin('SetVolume(%d,showVolumeBar)' % (i))
                                    # move down slowly
                                    xbmc.sleep(audiochangerate)

                        # stop player anyway
                        xbmc.sleep(5000) # wait 5s before stopping
                        xbmc.executebuiltin('PlayerControl(Stop)')

                        if audiochange == 'true':
                            xbmc.sleep(2000) # wait 2s before changing the volume back
                            if (dct.has_key("result")) and (dct["result"].has_key("volume")):
                                curVol = dct["result"]["volume"]
                                # we can move upwards fast, because there is nothing playing
                                xbmc.executebuiltin('SetVolume(%d,showVolumeBar)' % (curVol))

                        if enable_screensaver == 'true':
                            if debug == 'true':
                                _log ( "DEBUG: Activating screensaver" )
                            xbmc.executebuiltin('ActivateScreensaver')   
                        
                        #Run a custom cmd after playback is stopped
                        if custom_cmd == 'true':
                            if debug == 'true':
                                _log ( "DEBUG: Running custom script" )
                            os.system(cmd)
                else:
                    if debug == 'true':
                        _log ( "DEBUG: Playing the stream, time does not exceed max limit" )
            else:
                if debug == 'true':
                    _log ( "DEBUG: Not playing any media file" )
                # reset max_time_in_minutes
                max_time_in_minutes = -1

            diff_between_idle_and_check_time = idle_time_in_minutes - int(iCheckTime)

            if debug == 'true' and next_check == 'true':
                _log ( "DEBUG: diff_between_idle_and_check_time: " + str(diff_between_idle_and_check_time) )

            do_next_check(iCheckTime)

service()
