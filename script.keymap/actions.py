# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

_actions = [
  ["Navigation", [
    "left"              , "Move Left",
    "right"             , "Move Right",
    "up"                , "Move Up",
    "down"              , "Move Down",
    "pageup"            , "Page Up",
    "pagedown"          , "Page Down",
    "select"            , "Select Item",
    "highlight"         , "Highlight Item",
    #"parentdir"         , "NAV_BACK",       # backward compatibility
    #"close"             , "NAV_BACK", # backwards compatibility
    "parentfolder"      , "Parent Directory",
    "back"              , "Back",
    "previousmenu"      , "Previous Menu",
    "info"              , "Show Info",
    "contextmenu"       , "Context Menu",
    "firstpage"         , "First Page",
    "lastpage"          , "Last Page",
    "nextletter"        , "Next Letter",
    "prevletter"        , "Previous Letter",
  ]],

  ["Playback", [
    "play"              , "Play",
    "pause"             , "Pause",
    "playpause"         , "Play/Pause",
    "stop"              , "Stop",
    "skipnext"          , "Next",
    "skipprevious"      , "Previous",
    "fastforward"       , "Fast Forward",
    "rewind"            , "Rewind",
    "smallstepback"     , "Small Step Back",
    "stepforward"       , "Step Forward",
    "stepback"          , "Step Back",
    "bigstepforward"    , "Big Step Forward",
    "bigstepback"       , "Big Step Back",
    "chapterorbigstepforward", "Next Chapter or Big Step Forward",
    "chapterorbigstepBack"   , "Previous Chapter or Big Step Back",
    "osd"               , "Show OSD",
    "showtime"          , "Show current play time",
    "playlist"          , "Show Playlist",
    "fullscreen"        , "Toggle Fullscreen",
    "aspectratio"       , "Change Aspect Ratio",
    "showvideomenu"     , "Go to DVD Video Menu",
    "playercontrol(repeat)"   , "Toggle Repeat",
    "playercontrol(repeatone)", "Repeat One",
    "playercontrol(repeatall)", "Repeat All",
    "playercontrol(repeatoff)", "Repeat Off",
    "playercontrol(random)"   , "Toggle Random",
    "playercontrol(randomon)" , "Random On",
    "playercontrol(randomoff)", "Random Off",
    "createbookmark"          , "Create Bookmark",
    "createepisodebookmark"   , "Create Episode Bookmark",
    "togglestereomode"        , "Toggle 3D/Stereoscopic mode",
    "switchplayer"            , "Switch Player",
  ]],

  ["Audio", [
    "mute"              , "Mute",
    "volumeup"          , "Volume Up",
    "volumedown"        , "Volume Down",
    "audionextlanguage" , "Next Language",
    "audiodelay"        , "Delay",
    "audiodelayminus"   , "Delay Minus",
    "audiodelayplus"    , "Delay Plus",
    "audiotoggledigital", "Toggle Digital/Analog",
  ]],

  ["Pictures", [
    "nextpicture"       , "Next Picture",
    "previouspicture"   , "Previous Picture",
    "rotate"            , "Rotate Picture",
    "rotateccw"         , "Rotate Picture CCW",
    "zoomout"           , "Zoom Out",
    "zoomin"            , "Zoom In ",
    "zoomnormal"        , "Zoom level Normal",
    "zoomlevel1"        , "Zoom level 1",
    "zoomlevel2"        , "Zoom level 2",
    "zoomlevel3"        , "Zoom level 3",
    "zoomlevel4"        , "Zoom level 4",
    "zoomlevel5"        , "Zoom level 5",
    "zoomlevel6"        , "Zoom level 6",
    "zoomlevel7"        , "Zoom level 7",
    "zoomlevel8"        , "Zoom level 8",
    "zoomlevel9"        , "Zoom level 9",
  ]],

  ["Subtitle", [
    "showsubtitles"     , "Show Subtitles",
    "nextsubtitle"      , "Next Subtitle",
    "subtitledelay"     , "Delay",
    "subtitledelayminus", "Delay Minus",
    "subtitledelayplus" , "Delay Plus",
    "subtitlealign"     , "Align",
    #"subtitleshiftup"   , "SUBTITLE_VSHIFT_UP", #?
    #"subtitleshiftdown" , "SUBTITLE_VSHIFT_DOWN", #?
  ]],

  ["PVR", [
    "channelup"             , "Channel Up",
    "channeldown"           , "Channel Down",
    "previouschannelgroup"  , "Previous channel group",
    "nextchannelgroup"      , "Next channel group",
    "record"                , "Record",
  ]],

  ["Item Actions", [
    "queue"             , "Queue item",
    "delete"            , "Delete item",
    "copy"              , "Copy item",
    "move"              , "Move item",
    "moveitemup"        , "Move item up",
    "moveitemdown"      , "Move item down",
    "rename"            , "Rename item",
    "scanitem"          , "Scan item",
    "togglewatched"     , "Toggle watched status",
    #"increaserating"    , "INCREASE_RATING", #unused
    #"decreaserating"    , "DECREASE_RATING", #unused
  ]],

  ["System", [
    "togglefullscreen"  , "Toggle Fullscreen",
    "minimize"          , "Minimize",
    "shutdown"          , "Shutdown",
    "reboot"            , "Reboot",
    "hibernate"         , "Hibernate",
    "suspend"           , "Suspend",
    "restartapp"        , "Restart XBMC",
    "system.logoff"     , "Log off",
    "quit"              , "Quit XBMC",
  ]],

  ["Virtual Keyboard", [
    "enter"             , "Enter",
    "shift"             , "Shift",
    "symbols"           , "Symbols",
    "backspace"         , "Backspace ",
    "number0"           , "0",
    "number1"           , "1",
    "number2"           , "2",
    "number3"           , "3",
    "number4"           , "4",
    "number5"           , "5",
    "number6"           , "6",
    "number7"           , "7",
    "number8"           , "8",
    "number9"           , "9",
    "red"               , "Teletext Red",
    "green"             , "Teletext Green",
    "yellow"            , "Teletext Yellow",
    "blue"              , "Teletext Blue",
  ]],

  ["Other", [
    "updatelibrary(video)", "Update Video Library",
    "updatelibrary(music)", "Update Music Library",
    "cleanlibrary(video)",  "Clean Video Library",
    "cleanlibrary(music)", "Clean Music Library",
    "codecinfo"         , "Show codec info",
    "screenshot"        , "Take screenshot",
    "reloadkeymaps"     , "Reload keymaps",
    "increasepar"       , "Increase PAR",
    "decreasepar"       , "Decrease PAR",
    "nextresolution"    , "Change resolution",
    "nextcalibration"   , "Next calibration",
    "resetcalibration"  , "Reset calibration",
    "showpreset"        , "Show current visualisation preset",
    "presetlist"        , "Show visualisation preset list",
    "nextpreset"        , "Next visualisation preset",
    "previouspreset"    , "Previous visualisation preset",
    "lockpreset"        , "Lock current visualisation preset ",
    "randompreset"      , "Switch to a new random preset",
  ]],

  #["Analog", [
  #  "scrollup"          , "SCROLL_UP",
  #  "scrolldown"        , "SCROLL_DOWN",
  #  "cursorleft"        , "CURSOR_LEFT",
  #  "cursorright"       , "CURSOR_RIGHT",
  #  "analogmove"        , "ANALOG_MOVE",
  #  "analogfastforward" , "ANALOG_FORWARD",
  #  "analogrewind"      , "ANALOG_REWIND",
  #  "analogseekforward" , "ANALOG_SEEK_FORWARD",
  #  "analogseekback"    , "ANALOG_SEEK_BACK",
  #  "leftclick"         , "MOUSE_LEFT_CLICK",
  #  "rightclick"        , "MOUSE_RIGHT_CLICK",
  #  "middleclick"       , "MOUSE_MIDDLE_CLICK",
  #  "doubleclick"       , "MOUSE_DOUBLE_CLICK",
  #  "wheelup"           , "MOUSE_WHEEL_UP",
  #  "wheeldown"         , "MOUSE_WHEEL_DOWN",
  #  "mousedrag"         , "MOUSE_DRAG",
  #  "mousemove"         , "MOUSE_MOVE",
  #]]

  #"verticalshiftup"   , "VSHIFT_UP",
  #"verticalshiftdown" , "VSHIFT_DOWN",
  #"increasevisrating" , "VIS_RATE_PRESET_PLUS",
  #"decreasevisrating" , "VIS_RATE_PRESET_MINUS",
  #"nextscene"         , "NEXT_SCENE",
  #"previousscene"     , "PREV_SCENE",
  #"jumpsms2"          , "JUMP_SMS2",
  #"jumpsms3"          , "JUMP_SMS3",
  #"jumpsms4"          , "JUMP_SMS4",
  #"jumpsms5"          , "JUMP_SMS5",
  #"jumpsms6"          , "JUMP_SMS6",
  #"jumpsms7"          , "JUMP_SMS7",
  #"jumpsms8"          , "JUMP_SMS8",
  #"jumpsms9"          , "JUMP_SMS9",
  #"filter"            , "FILTER",
  #"filterclear"       , "FILTER_CLEAR",
  #"filtersms2"        , "FILTER_SMS2",
  #"filtersms3"        , "FILTER_SMS3",
  #"filtersms4"        , "FILTER_SMS4",
  #"filtersms5"        , "FILTER_SMS5",
  #"filtersms6"        , "FILTER_SMS6",
  #"filtersms7"        , "FILTER_SMS7",
  #"filtersms8"        , "FILTER_SMS8",
  #"filtersms9"        , "FILTER_SMS9",
  #"guiprofile"        , "GUIPROFILE_BEGIN",
  #"volampup"          , "VOLAMP_UP",
  #"volampdown"        , "VOLAMP_DOWN",
  #"mplayerosd"        , "SHOW_MPLAYER_OSD", #?
  #"hidesubmenu"       , "OSD_HIDESUBMENU", #depricated
  #"osdleft"           , "OSD_SHOW_LEFT",
  #"osdright"          , "OSD_SHOW_RIGHT",
  #"osdup"             , "OSD_SHOW_UP",
  #"osddown"           , "OSD_SHOW_DOWN",
  #"osdselect"         , "OSD_SHOW_SELECT",
  #"osdvalueplus"      , "OSD_SHOW_VALUE_PLUS",
  #"osdvalueminus"     , "OSD_SHOW_VALUE_MIN",
]


_activate_window = [
  "settings"                 , "Settings",
  "picturessettings"         , "Pictures Settings",
  "programssettings"         , "Programs Settings",
  "weathersettings"          , "Weather Settings",
  "musicsettings"            , "Music Settings",
  "systemsettings"           , "System Settings",
  "videossettings"           , "Videos Settings",
  "servicesettings"          , "Service Settings",
  "appearancesettings"       , "Appearance Settings",
  "pvrsettings"              , "PVR Settings",
  "skinsettings"             , "Skin Settings",
  "addonbrowser"             , "Addon Browser",
  "addonsettings"            , "Addon Settings",
  "profilesettings"          , "Profile Settings",
  "locksettings"             , "Lock Settings",
  "contentsettings"          , "Content Settings",
  "profiles"                 , "Profiles",
  "systeminfo"               , "System info",
  "testpattern"              , "Test Pattern",
  "screencalibration"        , "Screen Calibration",
  "loginscreen"              , "Login Screen",
  "filebrowser"              , "Filebrowser",
  "networksetup"             , "Networksetup",
  "accesspoints"             , "Access Points",
  "mediasource"              , "Mediasource Dialog",
  "startwindow"              , "Start",
  "favourites"               , "Favourites",
  "contextmenu"              , "Context Menu",
  "peripherals"              , "Peripheral manager",
  "peripheralsettings"       , "Peripherals settings",
  "mediafilter"              , "Media filter",
  "visualisationpresetlist"  , "Vis. Preset List",
  "filestackingdialog"       , "Filestacking Dialog",
  "smartplaylisteditor"      , "Smart Playlist Editor",
  "smartplaylistrule"        , "Smart Playlist Rule",
  "shutdownmenu"             , "Shutdown Menu",
  "fullscreeninfo"           , "Fullscreen Info",
  "subtitlesearch"           , "Subtitle Search",
  "weather"                  , "Weather",
  "screensaver"              , "Screensaver",
  "pictureinfo"              , "Picture Info",
  "addoninformation"         , "Addon Info",
  "musicplaylist"            , "Music Playlist",
  "musicfiles"               , "Music Files",
  "musiclibrary"             , "Music Library",
  "musicplaylisteditor"      , "Music Playlist Editor",
  "musicinformation"         , "Music Info",
  "musicoverlay"             , "Music Overlay",
  "songinformation"          , "Song Info",
  "karaoke"                  , "Karaoke Lyrics",
  "karaokeselector"          , "Karaoke Song Selector",
  "karaokelargeselector"     , "Karaoke Selector",
  "movieinformation"         , "Video Info",
  "videofiles"               , "Video Files",
  "videooverlay"             , "Video Overlay",
  "videomenu"                , "Video Menu",
  "videoosd"                 , "Video OSD",
  "videotimeseek"            , "Video Time Seek",
  "videobookmarks"           , "Video Bookmarks",
  "videoplaylist"            , "Video Playlist",
  "pvrguideinfo"             , "PVR Guide Info",
  "pvrrecordinginfo"         , "PVR Recording Info",
  "pvrtimersetting"          , "PVR Timer Setting",
  "pvrgroupmanager"          , "PVR Group Manager",
  "pvrchannelmanager"        , "PVR Channel Manager",
  "pvrguidesearch"           , "PVR Guide Search",
  "pvrchannelscan"           , "PVR Channel Scan",
  "pvrupdateprogress"        , "PVR Update Progress",
  "pvrosdchannels"           , "PVR OSD Channels",
  "pvrosdguide"              , "PVR OSD Guide",
  "pvrosddirector"           , "PVR OSD Director",
  "pvrosdcutter"             , "PVR OSD Cutter",
  "tvchannels"               , "TV Channels",
  "tvrecordings"             , "TV Recordings",
  "tvguide"                  , "TV Guide",
  "tvtimers"                 , "TV Timers",
  "tvsearch"                 , "TV Search",
  "radiochannels"            , "Radio Channels",
  "radiorecordings"          , "Radio Recordings",
  "radioguide"               , "Radio Guide",
  "radiotimers "             , "Radio Timers",
  "radiosearch"              , "Radio Search",
  "videos,movies"            , "Movies",
  "videos,movietitles"       , "Movie Titles",
  "videos,tvshows "          , "TV Shows",
  "videos,tvshowtitles "     , "TV Show Titles",
  "videos,musicvideos"       , "Music Videos",
  "videos,recentlyaddedmovies"      , "Recently Added Movies",
  "videos,recentlyaddedepisodes"    , "Recently Added Episodes",
  "videos,recentlyaddedmusicvideos" , "Recently Added Music Videos"
]

_windows = [
  "global"                   , "Global",
  "fullscreenvideo"          , "Fullscreen Video",
  "fullscreenlivetv"         , "Fullscreen Live TV",
  "home"                     , "Home",
  "programs"                 , "Programs",
  "videos"                   , "Videos",
  "music"                    , "Music",
  "pictures"                 , "Pictures",
  "pvr"                      , "PVR",
  "filemanager"              , "Filemanager",
  "pvrosdteletext"           , "OSD Teletext",
  "virtualkeyboard"          , "Virtual Keyboard",
  "playercontrols"           , "Player Controls",
  "seekbar"                  , "Seek bar",
  "musicosd"                 , "Music OSD",
  "osdvideosettings"         , "Video OSD Settings",
  "osdaudiosettings"         , "Audio OSD Settings",
  "visualisation"            , "Visualisation",
  "slideshow"                , "Slideshow"
]

from collections_backport import OrderedDict
from utils import rpc
import xbmc


def action_dict(actions, action_names):
    """Create dict of action->name sorted by name"""
    return OrderedDict(sorted(zip(actions, action_names), key=lambda t: t[1]))


def _get_run_addon_actions():
    addons = []
    addon_types = ['xbmc.python.pluginsource', 'xbmc.python.script']
    for addon_type in addon_types:
        response = rpc('Addons.GetAddons', type=addon_type, properties=['name', 'enabled'])
        res = response['result']
        if 'addons' in res:
            addons.extend([a for a in res['addons'] if a['enabled']])
    actions = ['runaddon(%s)' % a['addonid'] for a in addons]
    names = ['Launch %s' % a['name'] for a in addons]
    return action_dict(actions, names)


def _get_activate_window_actions():
    all_windows = _activate_window + _windows[2:] #don't include "global"
    actions = ["activatewindow(%s)" % w_id for w_id in all_windows[0::2]]
    names = ["Open %s" % w for w in all_windows[1::2]]
    return action_dict(actions, names)


def _get_action_dict():
    """ Map actions to 'category name'->'action id'->'action name' dict"""
    d = OrderedDict()
    for elem in _actions:
        category = elem[0]
        actions = elem[1][0::2]
        names = elem[1][1::2]
        d[category] = OrderedDict(zip(actions, names))

    d["Windows"] = _get_activate_window_actions()
    d["Add-ons"] = _get_run_addon_actions()
    return d


ACTIONS = _get_action_dict()
WINDOWS = OrderedDict(zip(_windows[0::2], _windows[1::2]))
