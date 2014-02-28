from traceback import print_exc
from time import mktime
from datetime import date, timedelta
import xbmc, xbmcgui, xbmcaddon, time

__addon__   = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__cwd__     = __addon__.getAddonInfo('path').decode("utf-8")

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class Gui( xbmcgui.WindowXML ):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__( self )
        self.nextlist = sorted(kwargs['listing'], key=lambda item: item['RFC3339'][11:15])
        self.setLabels = kwargs['setLabels']

    def onInit(self):
        num = int( __addon__.getSetting( "ThumbType" ) )
        xbmc.executebuiltin( "SetProperty(TVGuide.ThumbType,%i,Home)" % num )
        if __addon__.getSetting( "PreviewThumbs" ) == 'true':
            xbmc.executebuiltin( "SetProperty(TVGuide.PreviewThumbs,1,Home)" )
        else:
            xbmc.executebuiltin( "ClearProperty(TVGuide.PreviewThumbs,Home)" )
        if __addon__.getSetting( "BackgroundFanart" ) == 'true':
            xbmc.executebuiltin( "SetProperty(TVGuide.BackgroundFanart,1,Home)" )
        else:
            xbmc.executebuiltin( "ClearProperty(TVGuide.BackgroundFanart,Home)" )
        self.settingsOpen = False
        self.today = date.today()
        self.weekday = self.today.weekday()
        self.set_properties()
        self.fill_containers()
        self.set_focus()

    def set_properties(self):
        self.listitems = []
        for wday in range(0, 7):
            self.listitems.append([])
        day_limit = str(self.today + timedelta(days=6))
        for item in self.nextlist:
            ep_ndx = 1
            for ep in item['episodes'][1:]:
                if ep['aired'][:10] > day_limit:
                    break
                listitem = self.setLabels('listitem', item, ep_ndx)
                self.listitems[ep['wday']].append(listitem)
                ep_ndx += 1

    def fill_containers(self):
        for wday in range(0, 7):
            self.getControl(200 + wday).reset()
            self.getControl(200 + wday).addItems(self.listitems[wday])

    def set_focus(self):
        focus_to = 8
        for ndx in range(0, 7):
            wday = (self.weekday + ndx) % 7
            if self.listitems[wday]:
                focus_to = 200 + wday
                break
        self.setFocus(self.getControl(focus_to))

    def onClick(self, controlID):
        if controlID == 8:
            self.settingsOpen = True
            __addon__.openSettings()
            self.close()
        elif controlID in ( 200, 201, 202, 203, 204, 205, 206, ):
            listitem = self.getControl( controlID ).getSelectedItem()
            library = listitem.getProperty('Library')
            xbmc.executebuiltin('ActivateWindow(Videos,' + library + ',return)')

    def onFocus(self, controlID):
        pass

    def onAction( self, action ):
        if self.settingsOpen and action.getId() in ( 7, 10, 92, ):
            num = int( __addon__.getSetting( "ThumbType" ) )
            xbmc.executebuiltin( "SetProperty(TVGuide.ThumbType,%i,Home)" % num )
            if __addon__.getSetting( "PreviewThumbs" ) == 'true':
                xbmc.executebuiltin( "SetProperty(TVGuide.PreviewThumbs,1,Home)" )
            else:
                xbmc.executebuiltin( "ClearProperty(TVGuide.PreviewThumbs,Home)" )
            if __addon__.getSetting( "BackgroundFanart" ) == 'true':
                xbmc.executebuiltin( "SetProperty(TVGuide.BackgroundFanart,1,Home)" )
            else:
                xbmc.executebuiltin( "ClearProperty(TVGuide.BackgroundFanart,Home)" )
            self.settingsOpen = False
        if action.getId() in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close()

def MyDialog(tv_list, setLabels):
    w = Gui( "script-NextAired-TVGuide.xml", __cwd__, "Default" , listing=tv_list, setLabels=setLabels)
    w.doModal()
    del w

# vim: et
