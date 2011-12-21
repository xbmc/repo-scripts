import socket
import xbmc
import xbmcgui
import xbmcaddon
import platform
import unicodedata


"""
This module contains helper classes and functions to assist in the
operation of script.extrafanartdownloader
"""

### get addon info
__addon__ = xbmcaddon.Addon('script.artwork.downloader')
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__icon__ = __addon__.getAddonInfo('icon')
__localize__ = __addon__.getLocalizedString


dialog = xbmcgui.DialogProgress()

timeout = 20
socket.setdefaulttimeout(timeout)


# Fixes unicode problems
def _unicode( text, encoding='utf-8' ):
    try: text = unicode( text, encoding )
    except: pass
    return text

def _normalize_string( text ):
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text

def _log(txt, severity=xbmc.LOGDEBUG):

    """Log to txt xbmc.log at specified severity"""
    try:
        message = ('Artwork Downloader: %s' % txt)
        xbmc.log(msg=message, level=severity)
    except UnicodeEncodeError:
        try:
            message = _normalize_string('Artwork Downloader: %s' % txt)
            xbmc.log(msg=message, level=severity)
        except:
            message = ('Artwork Downloader: UnicodeEncodeError')
            xbmc.log(msg=message, level=xbmc.LOGWARNING)


def _dialog(action, percentage = 0, line0 = '', line1 = '', line2 = '', line3 = '', background = False):
    if not line0 == '':
        line0 = __addonname__ + line0
    else:
        line0 = __addonname__
    if not background:
        if action == 'create':
            dialog.create(__addonname__, line1, line2, line3)
        if action == 'update':
            dialog.update(percentage, line1, line2, line3)
        if action == 'close':
            dialog.close()
        if action == 'iscanceled':
            if dialog.iscanceled():
                return True
            else:
                return False
        if action == 'okdialog':
            xbmcgui.Dialog().ok(line0, line1, line2, line3)
    if background:
        if (action == 'create' or action == 'okdialog'):
            if line2 == '':
                msg = line1
            else:
                msg = line1 + ': ' + line2
            xbmc.executebuiltin("XBMC.Notification(%s, %s, 7500, %s)" % (line0, msg, __icon__))

# order preserving and get unique entry
def _getUniq(seq):
    seen = []
    result = []
    for item in seq:
        if item in seen: continue
        seen.append(item)
        result.append(item)
    return result