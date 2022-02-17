import xbmcgui
import xbmc
import xbmcvfs
import xbmcaddon
import logging
import os
import sys

import loadfile
import script

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString
logger = logging.getLogger(ADDON.getAddonInfo('id'))

def ask_to_load(playingfile, filename):
    playbase = os.path.basename(playingfile)
    subbase = os.path.basename(filename)
    if len(os.path.basename(playingfile)) > 50:
        playbase = playbase[:30] + "(...)" + playbase[-10:]
        subbase  = subbase[:30] + "(...)" + subbase[-10:]
    result = xbmcgui.Dialog().yesno(_(31001), _(35003) + "\n"
                    + _(35006).ljust(11) + playbase + "\n"
                    + _(35007).ljust(11) + subbase
                    + "\n" + _(35004),
                    yeslabel=_(35000),
                    nolabel=_(35001))
    if not result:
        # xbmc.Player().stop()
        subtitle = loadfile.loader(filename)
        subtitle.videofilename = playingfile
        script.show_dialog(subtitle)
    else:
        sys.exit()

def select_from_directory_of_playing_file(playingfile):
    res = xbmcgui.Dialog().yesno(_(31001), _(35005) + "\n" + _(35004),
                        nolabel=_(35000), yeslabel=_(35002))
    if not res:
        sys.exit()
    playing_dir = os.path.dirname(playingfile) + "/"
    filename = xbmcgui.Dialog().browse(1, _(32035), 'files', ".srt|.sub", False, False, playing_dir)
    if filename == playing_dir:
        sys.exit()
    # videofilename = playingfile
    subtitle = loadfile.loader(filename)
    subtitle.videofilename = playingfile
    # xbmc.Player().stop()
    script.show_dialog(subtitle)

def find_active_subtitle():
    current_subs = xbmc.Player().getAvailableSubtitleStreams()
    playingfile = xbmc.Player().getPlayingFile()
    if playingfile.startswith("videodb"):
        xbmc.Player().stop()
        sys.exit()
    if any(current_subs):
        active_sub_lang = xbmc.Player().getSubtitles()
        lang = xbmc.convertLanguage(active_sub_lang, xbmc.ISO_639_1)
        if not lang:
            filename = os.path.splitext(playingfile)[0] + ".srt"
        else:
            filename = os.path.splitext(playingfile)[0] + "." + lang + ".srt"
        if xbmcvfs.exists(filename):
            ask_to_load(playingfile, filename)
    select_from_directory_of_playing_file(playingfile)

def check_active_player():
    if xbmc.Player().isPlayingVideo():
        find_active_subtitle()
    else:
        subtitle = loadfile.with_warning()
        script.show_dialog(subtitle)
