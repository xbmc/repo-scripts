import xbmc
import xbmcgui


def show_notification(title, message, severity=0, time=6000):
    # just to be sure, close any busy dialog
    xbmc.executebuiltin("Dialog.Close(busydialog)")
    # xbmc.executebuiltin("Notification(\"%s\", \"%s\")" % (title, message))
    severities = [xbmcgui.NOTIFICATION_INFO, xbmcgui.NOTIFICATION_WARNING, xbmcgui.NOTIFICATION_ERROR]
    xbmcgui.Dialog().notification(heading=title, message=message, icon=severities[severity], time=time, sound=False)


def multi_select(heading, options, auto_close=0):
    selected = xbmcgui.Dialog().multiselect(heading, options, auto_close)
    return selected


def text_viewer(heading, text):
    xbmcgui.Dialog().textviewer(heading, text)
