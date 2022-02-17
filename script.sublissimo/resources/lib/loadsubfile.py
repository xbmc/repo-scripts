import xbmcgui
import xbmc
import xbmcaddon
import sys

import script
import loadfile
import syncing
from player_controller import SearchFrameRate

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

videodbfilename = None

def load_sub_subtitlefile(filename):
    frame_rate = sub_frame_rate_menu(filename)
    if not frame_rate:
        return None, None
    return frame_rate, videodbfilename

def retrieve_video():
    initiallayout = [(_(32093), "videodb://movies/titles/"),
                     (_(32094), "videodb://tvshows/titles/"),
                     (_(32095), "videodb://"),
                     (_(32005), "")]
    choice = xbmcgui.Dialog().contextmenu([strings for strings, locations in initiallayout])
    if choice == -1 or initiallayout[choice][1] == "":
        return None
    pos_locations = [locations for strings, locations in initiallayout]
    location = xbmcgui.Dialog().browse(
                1, _(32020), 'video', '', False, False, pos_locations[choice])
    if location in pos_locations:
        return None
    global videodbfilename
    videodbfilename = location
    return location


def sub_frame_rate_menu(filename):
    options = ["23.976", "24", "25", "29.976", "30", _(32127), _(32104), _(32129)]
    menuchoice = xbmcgui.Dialog().select(_(32105), options)
    if menuchoice == -1:
        return None
    if menuchoice == 5:
        try:
            frame_rate = float(xbmcgui.Dialog().input(_(32127)))
            return frame_rate
        except ValueError:
            return sub_frame_rate_menu(filename)
    if menuchoice == 6:
        frame_rate = search_frame_rate(filename)
        return frame_rate
    if menuchoice == 7:
        response = xbmcgui.Dialog().yesno(_(32130), _(32131),
                         yeslabel=_(32012), nolabel=_(32128))
        if response:
            return sub_frame_rate_menu(filename)
        return None
    frame_rate = float(options[menuchoice])
    return frame_rate

def search_frame_rate(filename):
    if xbmc.Player().isPlayingVideo():
        newplayer = SearchFrameRate()
        frame_rate = newplayer.get_frame_rate_from_playing_file()
        response = xbmcgui.Dialog().yesno(_(32106), _(32120) + str(frame_rate),
                                                    yeslabel=_(32089),
                                                    nolabel=_(32126))
        if response:
            return frame_rate
        return sub_frame_rate_menu(filename)
    return search_frame_rate_by_starting(filename)

def search_frame_rate_by_starting(filename):
    location = retrieve_video()
    if not location:
        return sub_frame_rate_menu(filename)
    newplayer = SearchFrameRate()
    newplayer.play(location)
    frame_rate = newplayer.get_frame_rate()
    if not frame_rate:
        return sub_frame_rate_menu(filename)
    response = xbmcgui.Dialog().yesno(_(32106), _(32120) + str(frame_rate),
                                                yeslabel=_(32089),
                                                nolabel=_(32126))
    if response:
        return frame_rate
    return sub_frame_rate_menu(filename)
