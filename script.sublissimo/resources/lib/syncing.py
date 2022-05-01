import xbmc
import xbmcgui
import xbmcaddon
import os
import sys

from player_controller import PlayerInstance
import script

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def create_menu(subtitle):
    initiallayout = [(_(32093), "videodb://movies/titles/"),
                          (_(32094), "videodb://tvshows/titles/"),
                          (_(32095), "videodb://"),
                          (_(32005), "")]
    if subtitle.videodbfilename:
        initiallayout.insert(0, (_(32116), subtitle.videodbfilename))
    if subtitle.videofilename:
        base = os.path.basename(subtitle.videofilename)
        initiallayout.insert(0, (_(35008) + base, subtitle.videofilename))
    return initiallayout

def retrieve_video(subtitle):
    initiallayout = create_menu(subtitle)
    choice = xbmcgui.Dialog().contextmenu([strings for strings, locations in initiallayout])
    if choice == -1 or initiallayout[choice][1] == "":
        script.show_dialog(subtitle)
    pos_locations = [locations for strings, locations in initiallayout]
    if pos_locations[choice] in (subtitle.videofilename, subtitle.videodbfilename):
        return pos_locations[choice]
    location = xbmcgui.Dialog().browse(
                  1, _(32020), 'video', '', False, False, pos_locations[choice])
    if location in pos_locations or not location:
        script.show_dialog(subtitle)
    if not subtitle.videofilename:
        subtitle.videodbfilename = location
    return location

def check_player_instances(subtitle=None):
    PlayerInstance().deactivate()
    if subtitle:
        subtitle.delete_temp_file()

def create_player(typeofinstance, subtitle):
    player = PlayerInstance().request(typeofinstance)
    location = retrieve_video(subtitle)
    player.add(subtitle)
    player.play(location)
    player.start()
    # -----Possibly needed if video is unavailable-----
    # xbmc.sleep(1000)
    # if player.isPlaying() == False:
    #     show_dialog(subtitle)
    # -------------------------------------------------
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if not PlayerInstance().in_use:
            break
        monitor.waitForAbort(1)

def play_along_file(subtitle):
    create_player("playalongfile", subtitle)

def sync_with_video(subtitle):
    # Name, long desc, Ok, More Info
    resp = xbmcgui.Dialog().yesno(_(31001), _(32060),
                                   yeslabel=_(32012), nolabel=_(32013))
    if not resp:
        # How to, long desc.
        xbmcgui.Dialog().textviewer(_(32061), _(32062))
    create_player("syncwizard", subtitle)

def synchronize_by_frame_rate(subtitle):
    create_player("syncbyframerate", subtitle)
