# -*- coding: utf-8 -*-
import xbmcaddon
import xbmcgui
import editing, shifting, advanced, syncing, stretch, synctwosubtitles, saving_and_exiting

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def show_dialog(subtitle):
    menulayout  = [(_(31000), scroll_subtitles),
                   (_(30001), editing.editing_menu),
                   (_(31002), shifting.shifting_menu),
                   (_(31003), stretch.stretch_menu),
                   (_(31004), synctwosubtitles.sync_with_other_subtitle),
                   (_(31005), syncing.sync_with_video),
                   (_(31010), syncing.synchronize_by_frame_rate),
                   (_(31011), syncing.play_along_file),
                   (_(31013), advanced.advanced_menu),
                   (_(31008), saving_and_exiting.save_the_file),
                   (_(31009), saving_and_exiting.exiting)]

    syncing.check_player_instances(subtitle)
    options = [names for names, functions in menulayout]
    response = xbmcgui.Dialog().contextmenu(options)
    menulayout[response][1](subtitle)

def scroll_subtitles(subtitle):
    xbmcgui.Dialog().select(_(32010), str(subtitle).split("\n"))
    show_dialog(subtitle)
