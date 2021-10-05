import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

#xbmc.log('Name of script: ' + str(sys.argv[0]), xbmc.LOGNOTICE)
#xbmc.log('Number of arguments: ' + str(len(sys.argv)), xbmc.LOGNOTICE)
#xbmc.log('The arguments are: ' + str(sys.argv), xbmc.LOGNOTICE)


def settings(setting, value = None):
    # Get or add addon setting
    if value:
        xbmcaddon.Addon().setSetting(setting, value)
    else:
        return xbmcaddon.Addon().getSetting(setting)


def sleepTimer():

    currval = int(settings('plstop'))
    if currval < 60 :
        newval = str(currval + 10)
    elif currval < 120 :
        newval = str(currval + 30)
    elif currval == 120 :
        newval = str('0')
    settings('plstop', newval)
    mgenlog ='Autostop sleep timer set to: ' + newval + ' mins.'
    xbmc.log(mgenlog, xbmc.LOGINFO)

    dialog = xbmcgui.Dialog()
    dialog.notification('Autostop Sleep Timer', mgenlog, xbmcgui.NOTIFICATION_INFO, 3000)


sleepTimer()