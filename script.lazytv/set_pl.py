from resources.lazy_lib import *
_addon_ = xbmcaddon.Addon("script.lazytv")
selected_pl = playlist_selection_window()
_addon_.setSetting(id="default_spl",value=selected_pl)
_addon_.setSetting(id="populate_by",value="1")