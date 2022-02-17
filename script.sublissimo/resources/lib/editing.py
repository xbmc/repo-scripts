import xbmcgui
import script
import xbmcaddon

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

dial = xbmcgui.Dialog()

def editing_menu(subtitle):
    menulayout = [(_(32001), edit_lines),
                  (_(32002), delete_first_subtitle),
                  (_(32003), delete_last_subtitle),
                  (_(32004), select_subtitle_to_delete),
                  (_(32005), script.show_dialog)]
    options = [names for names, functions in menulayout]
    response = xbmcgui.Dialog().contextmenu(options)
    menulayout[response][1](subtitle)

def edit_lines(subtitle):
    subtitle_in_strings, indexes = subtitle.easy_list_selector()
    i = dial.select(_(32035), subtitle_in_strings)
    if i != -1:
        new_line = dial.input(_(32001), defaultt="\n".join(subtitle[indexes[i]].textlines))
        subtitle.change_text(indexes[i], new_line)
    editing_menu(subtitle)

def delete_first_subtitle(subtitle):
    if dial.yesno(_(32006), str(subtitle[0]),nolabel= _(32025), yeslabel= _(32024)):
        del subtitle[0]
    editing_menu(subtitle)

def delete_last_subtitle(subtitle):
    if dial.yesno(_(32006), str(subtitle[-1]),nolabel= _(32025), yeslabel= _(32024)):
        del subtitle[-1]
    editing_menu(subtitle)

def select_subtitle_to_delete(subtitle):
    subtitle_in_strings, indexes = subtitle.easy_list_selector()
    i = dial.select( _(35025), subtitle_in_strings)
    if i != -1:
        if dial.yesno(_(32006), str(subtitle[indexes[i]]),nolabel= _(32025), yeslabel= _(32024)):
            del subtitle[indexes[i]]
    editing_menu(subtitle)
