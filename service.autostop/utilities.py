import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from common import settings


def sleepTimer():

    currval = int(settings('plstop'))
    if currval < 60 :
        newval = str(currval + 10)
    elif currval < 120 :
        newval = str(currval + 30)
    elif currval < 180 :
        newval = str(currval + 60)
    elif currval == 180 :
        newval = str('0')
    settings('plstop', newval)
    mgenlog ='Autostop sleep timer set to: ' + newval + ' mins.'
    xbmc.log(mgenlog, xbmc.LOGINFO)

    dialog = xbmcgui.Dialog()
    dialog.notification('Autostop Sleep Timer', mgenlog, xbmcgui.NOTIFICATION_INFO, 3000)


sleepTimer()

