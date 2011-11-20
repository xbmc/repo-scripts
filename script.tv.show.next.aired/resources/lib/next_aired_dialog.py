from traceback import print_exc
from time import mktime
from datetime import date
import xbmc, xbmcgui, xbmcaddon, time

__addon__ = xbmcaddon.Addon()
__cwd__ = __addon__.getAddonInfo('path')

def log(msg):
    xbmc.log( str( msg ),level=xbmc.LOGDEBUG )

class Gui( xbmcgui.WindowXML ):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__( self )
        self.nextlist  = kwargs['listing']
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
        self.listitems = {'Monday':[],'Tuesday':[],'Wednesday':[],'Thursday':[],'Friday':[],'Saturday':[],'Sunday':[]}
        self.days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        self.today = date.today()
        self.weekday = self.today.weekday()
        self.dayname = self.days[self.weekday]
        self.set_properties()
        self.fill_containers()
        self.set_focus()
                    
    def set_properties(self):
        for item in self.nextlist:
            try:
                airdays = item.get("Airtime").split(" at ")[0].split(', ')
            except:
                continue
            for day in airdays:
                listitem = self.setLabels('listitem', item, True)
                nextdate = item.get("RFC3339" , "" )[:10]
                if len(nextdate) == 10:
                    if self.is_in_current_week(nextdate):
                        self.listitems[day].append(listitem)
                else:
                    nextdate = listitem.getProperty('NextDate')
                    if len(nextdate) == 11:
                        if self.is_in_current_week(nextdate, True):
                            self.listitems[day].append(listitem)
                
    def is_in_current_week(self, strdate, alt = False):
        if alt:
            showdate = date.fromtimestamp( mktime( time.strptime( strdate, '%b/%d/%Y' ) ) )
        else:
            showdate = date.fromtimestamp( mktime( time.strptime( strdate, '%Y-%m-%d' ) ) )
        weekrange = int( ( showdate - self.today ).days )
        if weekrange >= 0 and weekrange <= 6:
            return True
        else:
            return False

    def fill_containers(self):
        for count, day in enumerate (self.days):
            self.getControl( 200 + count ).reset()
            self.getControl( 200 + count ).addItems( self.listitems[day] )

    def set_focus(self):
        if self.listitems[self.dayname] == []:
            dayFound = False
            for count, day in enumerate (self.days):
                if self.listitems[day] != []:
                    self.setFocus ( self.getControl ( 200 + count ) )
                    dayFound = True
                    break
            if dayFound == False:
                self.setFocus( self.getControl( 8 ) )
        else:
            self.setFocus( self.getControl( 200 + self.weekday ) )

    def onClick(self, controlID):
        if controlID == 8:
            self.settingsOpen = True
            __addon__.openSettings()
        elif controlID in ( 200, 201, 202, 203, 204, 205, 206, ):
            listitem = self.getControl( controlID ).getSelectedItem()
            library = listitem.getProperty('Library')
            xbmc.executebuiltin('ActivateWindow(Videos,' + library + ',return)')

    def onFocus(self, controlID):
        pass

    def onAction( self, action ):
        if action in ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close()
        if action in ( 7, 10, 92, ) and self.settingsOpen:
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

def MyDialog(tv_list, setLabels):
    w = Gui( "script-NextAired-TVGuide.xml", __cwd__, "Default" , listing=tv_list, setLabels=setLabels)
    w.doModal()
    del w
