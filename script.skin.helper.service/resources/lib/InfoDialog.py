import sys, re
import xbmc, xbmcgui, xbmcvfs
from ArtworkUtils import *
import PluginContent as plugincontent
import threading

CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_SHOW_INFO = ( 11, )

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        self.listitem = kwargs[ "listitem" ]
        self.content = kwargs[ "content" ]

    def onInit( self ):
        self._hide_controls()
        self._show_info()
        self.bginfoThread = BackgroundInfoThread()
        self.bginfoThread.setDialog(self)
        self.bginfoThread.start()

    def _hide_controls( self ):
        #self.getControl( 110 ).setVisible( False )
        pass

    def _show_info( self ):
            
        self.listitem.setProperty("contenttype",self.content)
        
        if self.content == 'movies':
            self.listitem.setProperty("type","movie")
        
        elif self.content == 'tvshows':
            self.listitem.setProperty("type","tvshow")
            
        elif self.content == 'episodes':
            self.listitem.setProperty("type","episode")
            
        list = self.getControl( 999 )
        list.addItem(self.listitem)
        
        self.setFocus( self.getControl( 5 ) )
        
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    def _close_dialog( self, action=None ):
        self.action = action
        self.bginfoThread.stopRunning()
        self.close()

    def onClick( self, controlId ):
        if controlId == 5:
            if self.content == 'movies':
                path = self.getControl( 999 ).getSelectedItem().getProperty('dbid')
                self._close_dialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %s } }, "id": 1 }' % path)
            elif self.content == 'episodes':
                path = self.getControl( 999 ).getSelectedItem().getProperty('dbid')
                self._close_dialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %s } }, "id": 1 }' % path)
            elif self.content == 'tvshows':
                path = self.getControl( 999 ).getSelectedItem().getProperty('path')
                self._close_dialog('ActivateWindow(Videos,%s,return)' %path)
        if controlId == 997:
            selectedItem = self.getControl( 997 ).getSelectedItem()
            path = self.getControl( 997 ).getSelectedItem().getfilename()
            self._close_dialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "file": "%s" } }, "id": 1 }' % path)
        if controlId == 998:
            path = self.getControl( 998 ).getSelectedItem().getProperty('path')
            xbmc.executebuiltin(path)
            
            
    
    def onFocus( self, controlId ):
        pass

    def onAction( self, action ):
        if ( action.getId() in CANCEL_DIALOG ) or ( action.getId() in ACTION_SHOW_INFO ):
            self._close_dialog()
            
            
class BackgroundInfoThread(threading.Thread):
    #fill cast and similar lists in the background
    active = True
    infoDialog = None

    def __init__(self, *args):
        threading.Thread.__init__(self, *args)
        
    def stopRunning(self):
        self.active = False
        
    def setDialog(self, infoDialog):
        self.infoDialog = infoDialog
        
    def run(self): 
    
        list = self.infoDialog.getControl( 999 )
        
        try: #optional: recommended list
            similarlist = self.infoDialog.getControl( 997 )
            similarcontent = []
            if self.infoDialog.content == 'movies':
                similarcontent = plugincontent.SIMILARMOVIES(25,list.getSelectedItem().getProperty("imdbnumber"))
            elif self.infoDialog.content == 'tvshows':
                similarcontent = plugincontent.SIMILARSHOWS(25,list.getSelectedItem().getProperty("imdbnumber"))
            for item in similarcontent:
                if not self.active: break
                liz = createListItem(item)
                liz.setThumbnailImage(item["art"].get("poster"))
                similarlist.addItem(liz)
        except: pass

        try: #optional: cast list
            castlist = self.infoDialog.getControl( 998 )
            json = list.getSelectedItem().getProperty("json").decode("utf-8")
            castlst = eval(json).get("cast")
            downloadThumbs = xbmc.getInfoLabel("Skin.String(actorthumbslookup)").lower() == "true"
            for cast in castlst:
                if not self.active: break
                if not cast.get("thumbnail") or not xbmcvfs.exists(cast.get("thumbnail")) and downloadThumbs: 
                    artwork = getOfficialArtWork(cast["name"],None,"person")
                    cast["thumbnail"] = artwork.get("thumb","")
                liz = xbmcgui.ListItem(label=cast["name"],label2=cast["role"],iconImage=cast.get("thumbnail"))
                liz.setProperty('path', "RunScript(script.extendedinfo,info=extendedactorinfo,name=%s)"%cast["name"])
                liz.setThumbnailImage(cast.get("thumbnail"))
                castlist.addItem(liz)
        except: pass
