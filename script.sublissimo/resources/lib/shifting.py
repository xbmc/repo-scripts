import xbmcgui
import xbmcaddon
import script
import misc
from create_classical_times import create_classical_times

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def shifting_menu(subtitle):
    menulayout = [(_(35021), forwards_by_microseconds),
                       (_(35022), backwards_by_microseconds),
                       ( _(35023), forwards_by_minutes),
                       ( _(35024), backwards_by_minutes),
                       (_(32053), shift_to_new_start),
                       (_(32005), script.show_dialog)]
    options = [names for names, functions in menulayout]
    response = xbmcgui.Dialog().contextmenu(options)
    menulayout[response][1](subtitle)

def forwards_by_microseconds(subtitle):
    #Move forwards by:
    movement = xbmcgui.Dialog().numeric(0, _(35027), defaultt="")
    if movement != "":
        subtitle.shift_subtitle(int(movement))
        xbmcgui.Dialog().ok(_(32017), _(32070).format(create_classical_times(int(movement))))
    script.show_dialog(subtitle)

def backwards_by_microseconds(subtitle):
    # Move backwards by:
    movement = xbmcgui.Dialog().numeric(0, _(35027), defaultt="")
    if movement != "":
        subtitle.shift_subtitle(int(movement)*-1)
        xbmcgui.Dialog().ok(_(32017), _(32071).format(create_classical_times(int(movement))))
    script.show_dialog(subtitle)

def forwards_by_minutes(subtitle):
    # Move forwards by:
    movement = xbmcgui.Dialog().numeric(0, _(35026), defaultt="")
    if movement != "":
        minute_movement = int(movement) * 60000
        subtitle.shift_subtitle(int(minute_movement))
        xbmcgui.Dialog().ok(_(32017), _(32070).format(create_classical_times(int(minute_movement))))
    script.show_dialog(subtitle)

def backwards_by_minutes(subtitle):
    # Move backwards by:
    movement = xbmcgui.Dialog().numeric(0, _(35026), defaultt="")
    if movement != "":
        minute_movement = int(movement) * 60000
        subtitle.shift_subtitle(int(minute_movement)*-1)
        xbmcgui.Dialog().ok(_(32017), _(32071).format(create_classical_times(int(minute_movement))))
    script.show_dialog(subtitle)

def shift_to_new_start(subtitle):
    xbmcgui.Dialog().ok(_(32068), _(32069))
    timestring = xbmcgui.Dialog().input(_(32029))
    movement = misc.decimal_timeline_with_checker(timestring)
    if movement:
        subtitle.shift_to_new_start(movement)
    script.show_dialog(subtitle)
