import os
import sys
import xbmc
import xbmcaddon
import xbmcgui
import api
from threading import Thread
import traceback

## A lot of the code borrowed from http://tv.i-njoy.eu/repo/ , all credit to them

CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )

_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__      = sys.modules[ "__main__" ].__addon__
__cwd__        = sys.modules[ "__main__" ].__cwd__
__profile__    = sys.modules[ "__main__" ].__profile__ 

def log(msg):
  xbmc.log("### [%s] - %s" % (__scriptname__,msg),level=xbmc.LOGDEBUG )

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        """Init main Application"""
        self.tuner         = False
        self.WINDOW        = xbmcgui.Window(10000)
        self.channel       = -1
        self.items         = []
        self.current_label = ""
        
    def onInit( self ):
        if self.setup():
            self.fetch_channels()
            self.epg = _EPG(window = self.getControl)
            self.epg.start()
            self.setFocusId(120)
            self.getControl(120).selectItem(0)
        else:
            self.close()    

    def setup(self, force=False):
        n7      = __addon__.getSetting("N7")
        warning = __addon__.getSetting("warning")

        if warning != 'done':
            dialog = xbmcgui.Dialog()
            info = dialog.yesno("N7 TV APP", _(30100), _(30101), _(30102), _(30103), _(30104))
            if info:
                __addon__.setSetting("warning", "done")
            else:
                return False

        if n7 and not force:
            self.getControl( 205 ).setLabel( n7 )
            if api.request(n7, api.DISCOVER, True):
                self.tuner = n7
                log("N7 tuner ip loaded from cache: %s" % n7)
                return True
            else:
                dialog = xbmcgui.Dialog()
                dialog.ok(_(30114), _(30105) % (n7, ))

        #Automatic scan
        dialog = xbmcgui.Dialog()
        if dialog.yesno(_(30107), _(30108),_(30109), "", _(30110), _(30111)):
            scanner = api.scan()
            if scanner.run():
                dialog = xbmcgui.Dialog()
                if len(scanner.n7) > 1:
                    pos = dialog.select(_(30106), scanner.n7)
                    n7  = scanner.n7[pos]         
                else:
                    n7 = scanner.n7[0]
                    txt = _(30112) % n7
                    xbmc.executebuiltin("Notification(%s,%s,2)" % (__scriptname__ , txt))
                __addon__.setSetting("N7", n7)
                self.tuner = n7
                log("N7 tuner selected: %s" % n7)
                self.getControl( 205 ).setLabel( n7 )
                del scanner
                return True
            else:
                xbmc.executebuiltin("Notification(%s,%s,2)" % (__scriptname__ ,_(30117)))

        #Manual IP
        n7 = dialog.numeric(3, _(30111))
        if api.request(n7, api.DISCOVER, True):
            __addon__.setSetting("N7", n7)
            txt = _(30112) % n7
            self.tuner = n7
            self.getControl( 205 ).setLabel( n7 )
            log("N7 tuner manually entered: %s" % n7)
            return True
        else:
            dialog.ok(_(30114), _(30105) % n7, _(30115))
            __addon__.setSetting("N7", "")
            xbmc.sleep(3000)
            self.close()

    def tune(self,pos):
        self.getControl(150).setVisible(True)
        focus   = self.getControl(120).getListItem(pos)
        url     = focus.getProperty("url")
        self.current_label = focus.getLabel()
        self.getControl( 206 ).setLabel( self.current_label )
        if xbmc.Player().isPlaying():
            xbmc.Player().stop()
        xbmc.sleep(500)        
        xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER).play(url, 0, 1)
        self.getControl(150).setVisible(False)
        self.channel = pos
        return self.current_label 

    def fetch_channels(self):
        """get channel list"""
        self.getControl(150).setVisible(True)
        self.getControl( 120 ).reset()
        if self.tuner:
            items = api.channel_list(self.tuner)
            self.items = items
            if items:
                for item in items:
                    listitem = xbmcgui.ListItem( label=item['title'], thumbnailImage=item['thumb'] )
                    listitem.setProperty( "thumb", item['thumb'] )
                    listitem.setProperty( "url", item['url'] )
                    self.getControl( 120 ).addItem( listitem )
            else:
                dialog = xbmcgui.Dialog()
                dialog.ok(_(30114), _(30116))
        self.getControl(150).setVisible(False)
        self.setFocusId(120)
        self.getControl(120).selectItem(0)

    def onClick( self, controlId ):
        if controlId == 120:
            pos = self.getControl(120).getSelectedPosition()
            if pos != self.channel:
                self.tune(pos)
            else:
                import player
                ui = player.PLAYER( "script-njoy-player.xml" , __cwd__ , "Default",
                                    ch_list = self.items, current_label = self.current_label,
                                    current_channel = self.channel, tune = self.tune)
                ui.doModal()
                self.getControl(120).selectItem(ui.current_pos)
                del ui                    
        elif controlId == 110:
            self.fetch_channels()
            
        elif controlId == 115:
            self.getControl(150).setVisible(True)
            self.setup(True)
            self.fetch_channels() 
            
    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG):
            self.epg.stop()
            xbmc.Player().stop()
            self.close()

class _EPG(Thread):
    """init epg class"""
    def __init__ (self, *args, **kwargs):
        Thread.__init__(self)
        self.active = True
        self.window = kwargs['window']

    def run(self):
        """main epg poller, checks every 2 seconds if focus has changed."""
        last = ''
        count = 0
        while self.active:
            try:
                focus   = self.window(120).getListItem(self.window(120).getSelectedPosition())
                thumb   = focus.getProperty("thumb")
                current = thumb.rsplit('/', 1)[1].replace('.png', '').replace('.jpg', '').replace('_', '%20')
                if last != current:
                    self.reset_epg()
                    count = 0
                else:
                    if count == 4:
                        data = api.get_internet_epg( current )
                        self.push_epg(data)
                    count += 1
                last = current
                xbmc.sleep(500)
            except:
                pass

    
    def push_epg(self, data):
        """set epg data to gui"""
        self.window(200).setLabel( data['current'].encode('utf-8') )
        self.window(201).setLabel( data['next'].encode('utf-8') )

    def reset_epg(self):
        """reset epg data in gui"""
        self.window(200).setLabel('')
        self.window(201).setLabel('')

    def stop(self):
        """stop epg polling thread"""
        self.active = False


