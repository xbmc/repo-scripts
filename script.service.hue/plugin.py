import xbmc

from resources.lib import menu, reporting

try:
    menu.menu()
except Exception as exc:
    xbmc.log(f"[script.service.hue][EXCEPTION] Plugin exception: {exc}")
    reporting.process_exception(exc)
