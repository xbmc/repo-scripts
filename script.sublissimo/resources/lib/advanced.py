import xbmcgui
import script
import xbmcaddon

ADDON = xbmcaddon.Addon()
__addon__     = xbmcaddon.Addon()
_  = __addon__.getLocalizedString

def advanced_menu(subtitle):
    menulayout = [(_(32138), change_color_codes_to_white),
                  (_(32139), change_color_codes_to_custom),
                  (_(31006), search_in_subtitle),
                  (_(31007), check_integrity),
                  (_(32005), script.show_dialog)]
    options = [names for names, functions in menulayout]
    response = xbmcgui.Dialog().contextmenu(options)
    menulayout[response][1](subtitle)

def change_color_codes_to_white(subtitle):
    subtitle.change_html_color("FFFFFFFF")
    xbmcgui.Dialog().ok(_(32017), _(32137))
    advanced_menu(subtitle)

def check_valid_hexadecimal(hex_input):
    if len(hex_input) != 8:
        return False
    letters = ["A", "B", "C", "D", "E", "F"]
    for char in hex_input:
        if not char.isdigit():
            if char not in letters:
                return False
    return True

def change_color_codes_to_custom(subtitle):
    color_code = xbmcgui.Dialog().input(_(32141))
    if not color_code:
        pass
    elif not check_valid_hexadecimal(color_code):
        xbmcgui.Dialog().ok(_(32014), _(32140))
    else:
        subtitle.change_html_color(color_code)
        xbmcgui.Dialog().ok(_(32017), _(32142) + "#" + color_code)
    advanced_menu(subtitle)

def search_in_subtitle(subtitle):
    searchstring = xbmcgui.Dialog().input(_(32023))
    found = subtitle.search_in_subtitle(searchstring)
    xbmcgui.Dialog().multiselect(_(35038), [item for sub in found for item in str(sub).split("\n")])
    advanced_menu(subtitle)

def check_integrity(subtitle):
    encodingfound, skipped_lines = subtitle.generate_problems_report()
    if encodingfound:
        topline = _(35039) + encodingfound + "\n"
    else:
        topline = _(35018)
    if len(skipped_lines) == 0:
        xbmcgui.Dialog().ok(_(32030), topline + _(32031))
        script.show_dialog(subtitle)
    else:
        if xbmcgui.Dialog().yesno(_(32030), topline + _(35040) + "\n" +
            "".join([subtitle.subtitlefile[i] + "\n" for i in skipped_lines]),
            nolabel=_(32008), yeslabel=_(35041)):
            correct_faulty_timelines(subtitle, skipped_lines)
        else:
            advanced_menu(subtitle)

def correct_faulty_timelines(subtitle, skipped_lines):
    i = xbmcgui.Dialog().select(_(32007), [subtitle.subtitlefile[i] for i in skipped_lines])
    if i == -1:
        advanced_menu(subtitle)
    new_line = xbmcgui.Dialog().input(_(32001), defaultt=subtitle.subtitlefile[skipped_lines[i]])
    subtitle.subtitlefile[skipped_lines[i]] = new_line
    xbmcgui.Dialog().select(_(32010), subtitle.subtitlefile)
    script.show_dialog(subtitle)
