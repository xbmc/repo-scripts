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

from collections import OrderedDict
from resources.lib.utils import rpc
from resources.lib.utils import tr

_actions = [
  ["Navigation", [
    "left"              , tr(30200),
    "right"             , tr(30201),
    "up"                , tr(30202),
    "down"              , tr(30203),
    "pageup"            , tr(30204),
    "pagedown"          , tr(30205),
    "select"            , tr(30206),
    "highlight"         , tr(30207),
    "parentfolder"      , tr(30208),
    "back"              , tr(30209),
    "previousmenu"      , tr(30210),
    "info"              , tr(30211),
    "contextmenu"       , tr(30212),
    "menu"              , tr(30213),
    "firstpage"         , tr(30214),
    "lastpage"          , tr(30215),
    "nextletter"        , tr(30216),
    "prevletter"        , tr(30217),
    "scrollup"          , tr(30218),
    "scrolldown"        , tr(30219),
    "cursorleft"        , tr(30220),
    "cursorright"       , tr(30221),

  ]],

  ["Playback", [
    "play"                    , tr(30300),
    "pause"                   , tr(30301),
    "playpause"               , tr(30302),
    "stop"                    , tr(30303),
    "skipnext"                , tr(30304),
    "skipprevious"            , tr(30305),
    "fastforward"             , tr(30306),
    "rewind"                  , tr(30307),
    "smallstepback"           , tr(30308),
    "stepforward"             , tr(30309),
    "stepback"                , tr(30310),
    "bigstepforward"          , tr(30311),
    "bigstepback"             , tr(30312),
    "chapterorbigstepforward" , tr(30313),
    "chapterorbigstepBack"    , tr(30314),
    "osd"                     , tr(30315),
    "showtime"                , tr(30316),
    "playlist"                , tr(30317),
    "fullscreen"              , tr(30318),
    "aspectratio"             , tr(30319),
    "showvideomenu"           , tr(30320),
    "createbookmark"          , tr(30330),
    "createepisodebookmark"   , tr(30331),
    "togglestereomode"        , tr(30332),
    "switchplayer"            , tr(30333),
    "playnext"                , tr(30334),
    "playerprogramselect"     , tr(30335),
    "playerresolutionselect"  , tr(30336),
    "verticalshiftup"         , tr(30337),
    "verticalshiftdown"       , tr(30338),
    "showtime"                , tr(30339),
    "nextscene"               , tr(30340),
    "previousscene"           , tr(30341),
    "videonextstream"         , tr(30342),
    "hdrtoggle"               , tr(30343),
    "stereomode"              , tr(30344),
    "nextstereomode"          , tr(30345),
    "previousstereomode"      , tr(30346),
    "stereomodetomono"        , tr(30347)
  ]],

  ["Audio", [
    "mute"               , tr(30400),
    "volumeup"           , tr(30401),
    "volumedown"         , tr(30402),
    "audionextlanguage"  , tr(30403),
    "audiodelay"         , tr(30404),
    "audiodelayminus"    , tr(30405),
    "audiodelayplus"     , tr(30406),
    "audiotoggledigital" , tr(30407),
    "volampup"           , tr(30408),
    "volampdown"         , tr(30409),
    "volumeamplification", tr(30410)
  ]],

  ["Pictures", [
    "nextpicture"       , tr(30500),
    "previouspicture"   , tr(30501),
    "rotate"            , tr(30502),
    "rotateccw"         , tr(30503),
    "zoomout"           , tr(30504),
    "zoomin"            , tr(30505),
    "zoomnormal"        , tr(30506),
    "zoomlevel1"        , tr(30507),
    "zoomlevel2"        , tr(30508),
    "zoomlevel3"        , tr(30509),
    "zoomlevel4"        , tr(30510),
    "zoomlevel5"        , tr(30511),
    "zoomlevel6"        , tr(30512),
    "zoomlevel7"        , tr(30513),
    "zoomlevel8"        , tr(30514),
    "zoomlevel9"        , tr(30515)
  ]],

  ["Subtitle", [
    "showsubtitles"     , tr(30600),
    "nextsubtitle"      , tr(30601),
    "browsesubtitle"    , tr(30602),
    "cyclesubtitle"     , tr(30603),
    "subtitledelay"     , tr(30604),
    "subtitledelayminus", tr(30605),
    "subtitledelayplus" , tr(30606),
    "subtitlealign"     , tr(30607),
    "subtitleshiftup"   , tr(30608),
    "subtitleshiftdown" , tr(30609)
  ]],

  ["PVR", [
    "channelup"              , tr(30700),
    "channeldown"            , tr(30701),
    "previouschannelgroup"   , tr(30702),
    "nextchannelgroup"       , tr(30703),
    "playpvr"          	     , tr(30704),
    "playpvrtv"		         , tr(30705),
    "playpvrradio"	         , tr(30706),
    "record"                 , tr(30707),
    "togglecommskip"		 , tr(30708),
	"showtimerrule"			 , tr(30709),
	"channelnumberseparator" , tr(30710)
  ]],

  ["Item Actions", [
    "queue"             , tr(30800),
    "delete"            , tr(30801),
    "copy"              , tr(30802),
    "move"              , tr(30803),
    "moveitemup"        , tr(30804),
    "moveitemdown"      , tr(30805),
    "rename"            , tr(30806),
    "scanitem"          , tr(30807),
    "togglewatched"     , tr(30808),
    "increaserating"    , tr(30809),
    "decreaserating"    , tr(30810),
    "setrating"         , tr(30811)
  ]],

  ["System", [
    "togglefullscreen"   , tr(30900),
    "minimize"           , tr(30901),
    "shutdown"           , tr(30902),
    "reboot"             , tr(30903),
    "hibernate"          , tr(30904),
    "suspend"            , tr(30905),
    "restartapp"         , tr(30906),
    "system.logoff"      , tr(30907),
    "quit"               , tr(30908),
    "settingsreset"      , tr(30909),
    "settingslevelchange", tr(30910),
    "togglefont"         , tr(30911),

  ]],

  ["Virtual Keyboard", [
    "enter"             , tr(31000),
    "shift"             , tr(31001),
    "symbols"           , tr(31002),
    "backspace"         , tr(31003),
    "number0"           , tr(31004),
    "number1"           , tr(31005),
    "number2"           , tr(31006),
    "number3"           , tr(31007),
    "number4"           , tr(31008),
    "number5"           , tr(31009),
    "number6"           , tr(31010),
    "number7"           , tr(31011),
    "number8"           , tr(31012),
    "number9"           , tr(31013),
    "red"               , tr(31014),
    "green"             , tr(31015),
    "yellow"            , tr(31016),
    "blue"              , tr(31017)
  ]],

  ["Other", [
    "updatelibrary(video)", tr(31100),
    "updatelibrary(music)", tr(31101),
    "cleanlibrary(video)" , tr(31102),
    "cleanlibrary(music)" , tr(31103),
    "playerprocessinfo"   , tr(31104),
    "playerdebug"         , tr(31105),
    "screenshot"          , tr(31106),
    "reloadkeymaps"       , tr(31107),
    "increasepar"         , tr(31108),
    "decreasepar"         , tr(31109),
    "nextresolution"      , tr(31110),
    "nextcalibration"     , tr(31111),
    "resetcalibration"    , tr(31112),
    "showpreset"          , tr(31113),
    "presetlist"          , tr(31114),
    "nextpreset"          , tr(31115),
    "previouspreset"      , tr(31116),
    "lockpreset"          , tr(31117),
    "randompreset"        , tr(31118)
  ]],
]


_activate_window = [
  "settings"                        , tr(31200),
  "playersettings"                  , tr(31201),
  "programssettings"                , tr(31202),
  "infoprovidersettings"            , tr(31203),
  "interfacesettings"               , tr(31204),
  "systemsettings"                  , tr(31205),
  "mediasettings"                   , tr(31206),
  "servicesettings"                 , tr(31207),
  "appearancesettings"              , tr(31208),
  "peripheralsettings"              , tr(31209),
  "libexportsettings"               , tr(31210),
  "pvrsettings"                     , tr(31211),
  "pvrrecordingsettings"            , tr(31212),
  "gamesettings"                    , tr(31213),
  "gameadvancedsettings"            , tr(31214),
  "gamecontrollers"                 , tr(31215),
  "gamevideofilter"                 , tr(31216),
  "gamevideorotation"               , tr(31217),
  "gameviewmode"                    , tr(31218),
  "skinsettings"                    , tr(31219),
  "addonbrowser"                    , tr(31220),
  "addonsettings"                   , tr(31221),
  "profilesettings"                 , tr(31222),
  "locksettings"                    , tr(31223),
  "contentsettings"                 , tr(31224),
  "profiles"                        , tr(31225),
  "systeminfo"                      , tr(31226),
  "testpattern"                     , tr(31227),
  "screencalibration"               , tr(31228),
  "loginscreen"                     , tr(31229),
  "filebrowser"                     , tr(31230),
  "networksetup"                    , tr(31231),
  "accesspoints"                    , tr(31232),
  "mediasource"                     , tr(31233),
  "startwindow"                     , tr(31234),
  "favourites"                      , tr(31235),
  "contextmenu"                     , tr(31236),
  "mediafilter"                     , tr(31237),
  "visualisationpresetlist"         , tr(31238),
  "smartplaylisteditor"             , tr(31239),
  "smartplaylistrule"               , tr(31240),
  "shutdownmenu"                    , tr(31241),
  "fullscreeninfo"                  , tr(31242),
  "subtitlesearch"                  , tr(31243),
  "weather"                         , tr(31244),
  "screensaver"                     , tr(31245),
  "pictureinfo"                     , tr(31246),
  "addoninformation"                , tr(31247),
  "musicplaylist"                   , tr(31249),
  "musicplaylisteditor"             , tr(31250),
  "musicinformation"                , tr(31251),
  "songinformation"                 , tr(31252),
  "movieinformation"                , tr(31253),
  "playerprocessinfo"               , tr(31254),
  "videomenu"                       , tr(31255),
  "videoosd"                        , tr(31256),
  "osdcmssettings"                  , tr(31257),
  "osdsubtitlesettings"             , tr(31258),
  "videotimeseek"                   , tr(31259),
  "videobookmarks"                  , tr(31260),
  "videoplaylist"                   , tr(31261),
  "pvrguideinfo"                    , tr(31262),
  "pvrrecordinginfo"                , tr(31263),
  "pvrtimersetting"                 , tr(31264),
  "pvrgroupmanager"                 , tr(31265),
  "pvrchannelmanager"               , tr(31266),
  "pvrguidesearch"                  , tr(31267),
  "pvrchannelscan"                  , tr(31268),
  "pvrupdateprogress"               , tr(31269),
  "pvrosdchannels"                  , tr(31270),
  "pvrchannelguide"                 , tr(31271),
  "tvchannels"                      , tr(31272),
  "tvrecordings"                    , tr(31273),
  "tvguide"                         , tr(31274),
  "tvtimers"                        , tr(31275),
  "tvsearch"                        , tr(31276),
  "radiochannels"                   , tr(31277),
  "radiorecordings"                 , tr(31278),
  "radioguide"                      , tr(31279),
  "radiotimers "                    , tr(31280),
  "radiotimerrules"                 , tr(31281),
  "radiosearch"                     , tr(31282),
  "pvrradiordsinfo"                 , tr(31283),
  "videos,movies"                   , tr(31284),
  "videos,movietitles"              , tr(31285),
  "videos,tvshows "                 , tr(31286),
  "videos,tvshowtitles "            , tr(31287),
  "videos,musicvideos"              , tr(31288),
  "videos,recentlyaddedmovies"      , tr(31289),
  "videos,recentlyaddedepisodes"    , tr(31290),
  "videos,recentlyaddedmusicvideos" , tr(31291),
  "games"                           , tr(31292),
  "gameosd"                         , tr(31293),
  "gamepadinput"                    , tr(31294),
  "gamevolume"                      , tr(31295)
]

_windows = [
  "global"                   , tr(30100),
  "fullscreenvideo"          , tr(30101),
  "fullscreenlivetv"         , tr(30102),
  "fullscreenradio"          , tr(30103),
  "fullscreengame"           , tr(30104),
  "home"                     , tr(30105),
  "programs"                 , tr(30106),
  "videos"                   , tr(30107),
  "music"                    , tr(30108),
  "pictures"                 , tr(30109),
  "pvr"                      , tr(30110),
  "filemanager"              , tr(30111),
  "virtualkeyboard"          , tr(30112),
  "playercontrols"           , tr(30113),
  "seekbar"                  , tr(30114),
  "musicosd"                 , tr(30115),
  "osdvideosettings"         , tr(30116),
  "osdaudiosettings"         , tr(30117),
  "visualisation"            , tr(30118),
  "slideshow"                , tr(30119)
]


def action_dict(actions, action_names):
    """Create dict of action->name sorted by name."""
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
    """Map actions to 'category name'->'action id'->'action name' dict."""
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
