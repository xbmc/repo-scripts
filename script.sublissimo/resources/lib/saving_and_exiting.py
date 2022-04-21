import xbmcgui
import xbmcaddon
import xbmc
import sys
import xbmcvfs
import script
import misc, syncing

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def save_the_file(subtitle, playing=False, from_exit=False):
    #save w. edited, save current, save custom, back, exit w/o saving
    choice = xbmcgui.Dialog().contextmenu([_(32038), _(32039), _(32040),
                                           _(32005), _(32041)])
    if choice == 0:
        new_file_name = subtitle.filename[:-4] + "_edited.srt"
    if choice == 1:
        new_file_name = subtitle.filename[:-4] + ".srt"
    if choice == 2:
        new_file_name = xbmcgui.Dialog().input(_(32042), defaultt=subtitle.filename[:-4] + ".srt")
    if choice in (-1, 3):
        script.show_dialog(subtitle)
    if choice == 4:
        syncing.check_player_instances(subtitle)
        sys.exit()
    subtitle.write_file(new_file_name)
    subtitle.changed = False
    if playing:
        reload_new_subtitle(subtitle, new_file_name)
    else:
        exit_after_saving(subtitle, from_exit, new_file_name)

def reload_new_subtitle(subtitle, new_file_name):
    xbmc.Player().setSubtitles(new_file_name)
    subtitle.delete_temp_file()
    syncing.check_player_instances(subtitle)
    # succes, file saved to:
    xbmcgui.Dialog().ok(_(32017), _(32123) + str(new_file_name))
    xbmc.Player().pause()
    sys.exit()

def exit_after_saving(subtitle, from_exit, new_file_name):
    if xbmcvfs.exists(new_file_name):
        # written to, to use select in kodi sub menu
        xbmcgui.Dialog().ok(_(32043), new_file_name + _(32044))
    else:
        #Error, File not written
        xbmcgui.Dialog().ok(_(32014), _(32045))
    syncing.check_player_instances(subtitle)
    if from_exit:
        sys.exit()
    script.show_dialog(subtitle)

def exiting(subtitle):
    syncing.check_player_instances(subtitle)
    if subtitle.changed:
        ret = xbmcgui.Dialog().yesno(_(32046), _(32047),
                                      nolabel=_(32048), yeslabel=_(32049))
        if ret:
            save_the_file(subtitle, playing=False, from_exit=True)
    sys.exit()
