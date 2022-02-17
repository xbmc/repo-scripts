import xbmcgui
import xbmcaddon
import script
import misc

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def stretch_menu(subtitle):
    # Synchronize by frame rate, Stretch by giving new end time, Stretch by providing factor, Back
    menulayout = [(_(32119), stretch_subtitle),
                  (_(32118), stretch_by_providing_factor),
                  (_(32005), script.show_dialog)]
    options = [names for names, functions in menulayout]
    response = xbmcgui.Dialog().contextmenu(options)
    menulayout[response][1](subtitle)

def stretch_subtitle(subtitle):
    # Write new timestamp, for example
    xbmcgui.Dialog().ok(_(31001), _(32028))
    timestring = xbmcgui.Dialog().input(_(32029))
    movement = misc.decimal_timeline_with_checker(timestring)
    if movement:
        subtitle.stretch_to_new_end(movement)
        xbmcgui.Dialog().ok(_(32017), _(33072).format(timestring))
        script.show_dialog(subtitle)
    else:
        xbmcgui.Dialog().ok(_(32014), _(32056))
        stretch_menu(subtitle)

def stretch_by_providing_factor(subtitle):
    try:
        # Provide Factor
        response = xbmcgui.Dialog().input(_(32117))
        new_factor = float(response)
    except ValueError:
        stretch_by_providing_factor(subtitle)
    start_timestamp = subtitle[0].return_starting_time()
    old_timestamp = subtitle[-1].return_starting_time()
    new_timestamp = subtitle[-1].return_starting_time(new_factor)
    # New Ending, Starting time, Old ending time, New Ending time, Ok, Return
    yes = xbmcgui.Dialog().yesno(_(32107), _(34108) + str(start_timestamp) + "\n" +
                                 _(32109) + str(old_timestamp) + "\n" +
                                 _(32110) + str(new_timestamp) + "\n",
                                          yeslabel=_(32012),
                                          nolabel= _(32008))
    if yes:
        correction = new_factor * 1 - 1
        subtitle.stretch_subtitle(new_factor, correction)
    script.show_dialog(subtitle)
