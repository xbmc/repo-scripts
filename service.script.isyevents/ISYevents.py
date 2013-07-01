'''
    ISY Event Engine for XBMC
    Copyright (C) 2012 Ryan M. Kraus

    LICENSE:
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    DESCRIPTION:
    This XBMC addon interfaces an ISY-99 type Home Automation Controller
    (from Universal Devices Incorporated) with XBMC and performs actions
    when XBMC is started or quit, a movie is started; paused; resumed;
    or ends, or music is started; paused; resumed; or ends.
    
    This addon requires the ISY Broser addon for XBMC.
    
    WRITTEN:    11/2012
'''

# CONSTANTS
__author__ = 'Humble Robot'
__version__ = '0.2.1'
__url__ = 'https://code.google.com/p/isy-events/'
__date__ = '4/2013'

# imports
# system
import sys
# xbmc
import xbmcaddon
import xbmcgui

# fetch addon information
isy_events = xbmcaddon.Addon('service.script.isyevents')
isy_browse = xbmcaddon.Addon('plugin.program.isybrowse')

# add libraries to path
library_path = isy_events.getAddonInfo('path') + '/resources/Lib/'
sys.path.append(library_path)
library_path = isy_browse.getAddonInfo('path') + '/resources/lib/'
sys.path.append(library_path)

# custom imports
import pyisy
import xb_events
import log
import event_actions

# load settings
username = isy_browse.getSetting('username')
password = isy_browse.getSetting('password')
host = isy_browse.getSetting('host')
port = int(isy_browse.getSetting('port'))
usehttps = isy_browse.getSetting('usehttps') == 'true'

# open isy connection
isy = pyisy.open(username, password, host, port, usehttps)
# verify isy opened correctly
if isy.__dummy__:
    header = log.translator(35001)
    message = log.translator(35002)
    xbmc.executebuiltin('Notification(' + header + ',' + message + ', 15000)')

# check last version run
last_ver = isy_events.getSetting('last_run_ver')
if last_ver != __version__:
    header = log.translator(36000)
    message = [log.translator(36001), log.translator(36002), log.translator(36003)]
    xbmcgui.Dialog().ok(header, message[0], message[1], message[2])
    isy_events.setSetting('last_run_ver', __version__)
    
# create xbmc event handler
xEvents = xb_events.xbmcEvents()
# add handlers
node_events = {
    'onStart': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_xbmc_start'),
    'onQuit': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_xbmc_quit'),
    'onScreenSaverOn': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_xbmc_sson'),
    'onScreenSaverOff': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_xbmc_ssoff'),
    'onPlayMovie': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_video_start'),
    'onStopMovie': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_video_end'),
    'onPauseMovie': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_video_pause'),
    'onResumeMovie': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_video_resume'),
    'onPlayMusic': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_audio_start'),
    'onStopMusic': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_audio_end'),
    'onPauseMusic': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_audio_pause'),
    'onResumeMusic': event_actions.ParseDeviceSetting(isy, isy_events, 'dev_audio_resume')}
xEvents.AddHandlers(node_events)
program_events ={
    'onStart': event_actions.ParseProgramSetting(isy, isy_events, 'prog_xbmc_start'),
    'onQuit': event_actions.ParseProgramSetting(isy, isy_events, 'prog_xbmc_quit'),
    'onScreenSaverOn': event_actions.ParseProgramSetting(isy, isy_events, 'prog_xbmc_sson'),
    'onScreenSaverOff': event_actions.ParseProgramSetting(isy, isy_events, 'prog_xbmc_ssoff'),
    'onPlayMovie': event_actions.ParseProgramSetting(isy, isy_events, 'prog_video_start'),
    'onStopMovie': event_actions.ParseProgramSetting(isy, isy_events, 'prog_video_end'),
    'onPauseMovie': event_actions.ParseProgramSetting(isy, isy_events, 'prog_video_pause'),
    'onResumeMovie': event_actions.ParseProgramSetting(isy, isy_events, 'prog_video_resume'),
    'onPlayMusic': event_actions.ParseProgramSetting(isy, isy_events, 'prog_audio_start'),
    'onStopMusic': event_actions.ParseProgramSetting(isy, isy_events, 'prog_audio_end'),
    'onPauseMusic': event_actions.ParseProgramSetting(isy, isy_events, 'prog_audio_pause'),
    'onResumeMusic': event_actions.ParseProgramSetting(isy, isy_events, 'prog_audio_resume')}
xEvents.AddHandlers(program_events)
# start events engine
xEvents.RunMainLoop()