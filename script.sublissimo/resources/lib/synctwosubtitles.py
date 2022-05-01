import xbmcgui
import xbmcaddon
import script
import loadfile

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def sync_with_other_subtitle(subtitle):
    #Sublissimo, Long sync disclaimer, OK
    resp = xbmcgui.Dialog().yesno(_(31001), _(33000),
                    yeslabel=_(32013), nolabel= _(32012))
    if resp:
        xbmcgui.Dialog().textviewer(_(32057), _(32058))
    sync_filename = xbmcgui.Dialog().browse(1, _(32035), 'video', ".srt|.sub")
    sync_subtitle = loadfile.loader(sync_filename, for_sync=True)
    if not sync_subtitle:
        script.show_dialog(subtitle)
    subtitle_per_line, indexes = subtitle.easy_list_selector()
    sync_subtitle_per_line, sync_indexes = sync_subtitle.easy_list_selector()
    first_sub = sync_helper(subtitle, _(35019), subtitle_per_line, indexes)
    first_sync_sub = sync_helper(sync_subtitle, _(35020), sync_subtitle_per_line, sync_indexes)
    last_sub = sync_helper(subtitle, _(35019), subtitle_per_line, indexes)
    last_sync_sub = sync_helper(sync_subtitle, _(35020), sync_subtitle_per_line, sync_indexes)
    subtitle.sync_two_subtitles(sync_subtitle, indexes[first_sub], indexes[last_sub],
                           sync_indexes[first_sync_sub], sync_indexes[last_sync_sub])
    xbmcgui.Dialog().ok(_(32017), _(32050))
    script.show_dialog(subtitle)


def sync_helper(subtitle, headline, sub_per_line, indexes):
    index = xbmcgui.Dialog().select(headline, sub_per_line)
    if index == -1:
        script.show_dialog(subtitle)
    i = indexes[index]
    yes = xbmcgui.Dialog().yesno(headline, str(subtitle[i]),
                              nolabel=_(32025), yeslabel=_(32024))
    if yes:
        return index
    else:
        return sync_helper(subtitle, headline, sub_per_line, indexes)
