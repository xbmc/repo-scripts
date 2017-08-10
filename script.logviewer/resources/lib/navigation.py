# -*- coding: utf-8 -*-

import sys
import xbmc
import utils
import xbmcgui
import logviewer


def has_addon(addon_id):
    return xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id) == 1


def get_opts():
    headings = []
    handlers = []

    # Show log
    headings.append(utils.translate(30001))
    handlers.append(lambda: show_log(False))

    # Show old log
    headings.append(utils.translate(30002))
    handlers.append(lambda: show_log(True))

    # Upload log
    if has_addon("script.kodi.loguploader"):
        headings.append(utils.translate(30015))
        handlers.append(lambda: xbmc.executebuiltin("RunScript(script.kodi.loguploader)"))

    # Open Settings
    headings.append(utils.translate(30011))
    handlers.append(utils.open_settings)

    return headings, handlers


def show_log(old):
    content = logviewer.get_content(old, utils.get_inverted(), utils.get_lines(), True)
    logviewer.window(utils.ADDON_NAME, content, default=utils.is_default_window())


def run():
    if len(sys.argv) > 1:
        # Integration patterns below:
        # Eg: xbmc.executebuiltin("RunScript(script.logviewer, show_log)")
        method = sys.argv[1]

        if method == "show_log":
            show_log(False)
        elif method == "show_old_log":
            show_log(True)
        else:
            e = "Method %s does not exist" % method
            raise NotImplementedError(e)
    else:
        headings, handlers = get_opts()
        index = xbmcgui.Dialog().select(utils.ADDON_NAME, headings)
        if index >= 0:
            handlers[index]()
