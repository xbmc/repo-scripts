import sys, re
import xbmc, xbmcgui, xbmcvfs
import ArtworkUtils as artutils
import PluginContent as plugincontent
from Utils import *
import threading

CANCEL_DIALOG  = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_SHOW_INFO = ( 11, )

class GUI( xbmcgui.WindowXMLDialog ):
    
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self )
        params = kwargs[ "params" ]
        logMsg( repr(params) )
        if params.get("MOVIEID"):
            item = getJSON('VideoLibrary.GetMovieDetails', '{ "movieid": %s, "properties": [ %s ] }' %(params["MOVIEID"],fields_movies))
            self.content = "movies"
        elif params.get("MUSICVIDEOID"):
            item = getJSON('VideoLibrary.GetMusicVideoDetails', '{ "musicvideoid": %s, "properties": [ %s ] }' %(params["MUSICVIDEOID"],fields_musicvideos))
            self.content = "musicvideos"
        elif params.get("EPISODEID"):
            item = getJSON('VideoLibrary.GetEpisodeDetails', '{ "episodeid": %s, "properties": [ %s ] }' %(params["EPISODEID"],fields_episodes))
            self.content = "episodes"
        elif params.get("TVSHOWID"):
            item = getJSON('VideoLibrary.GetTVShowDetails', '{ "tvshowid": %s, "properties": [ %s ] }' %(params["TVSHOWID"],fields_tvshows))
            self.content = "tvshows"
        elif params.get("ALBUMID"):
            item = getJSON('AudioLibrary.GetAlbumDetails', '{ "albumid": %s, "properties": [ %s ] }' %(params["ALBUMID"],fields_albums))
            self.content = "albums"
        elif params.get("SONGID"):
            item = getJSON('AudioLibrary.GetSongDetails', '{ "songid": %s, "properties": [ %s ] }' %(params["SONGID"],fields_songs))
            self.content = "songs"
        elif params.get("RECORDINGID"):
            item = getJSON('PVR.GetRecordingDetails', '{ "recordingid": %s, "properties": [ %s ]}' %( params["RECORDINGID"], fields_pvrrecordings))
            artwork = artutils.getPVRThumbs(item["title"],item["channel"],"recordings",item["file"])
            item["art"] = artwork
            for key, value in artwork.iteritems():
                if not item.get(key):
                    item[key] = value
            if artwork.get("tmdb_type") == "movies":
                self.content = "movies"
            elif artwork.get("tmdb_type") == "tv":
                self.content = "episodes"
            else:
                self.content = "tvrecordings"
        else:
            item = None
            self.listitem = None
        
        if item:        
            liz = prepareListItem(item)
            liz = createListItem(item)
            self.listitem = liz
            self.lastwidgetcontainer = params.get("lastwidgetcontainer","")
            WINDOW.setProperty("SkinHelper.WidgetContainer","999")

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
        self.listitem.setProperty("type",self.content[:-1])
            
        list = self.getControl( 999 )
        list.addItem(self.listitem)
        
        self.setFocus( self.getControl( 5 ) )
        
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )

    def _close_dialog( self, action=None ):
        self.action = action
        self.bginfoThread.stopRunning()
        WINDOW.setProperty("SkinHelper.WidgetContainer",self.lastwidgetcontainer)
        self.close()

    def onClick( self, controlId ):
        if controlId == 5:
            type = self.getControl( 999 ).getSelectedItem().getProperty('dbtype')
            id = self.getControl( 999 ).getSelectedItem().getProperty('dbid')
            logMsg("type: %s - id: %s" %(type,id))
            if type and id and self.content != "tvshows":
                self._close_dialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "%sid": %s } }, "id": 1 }' % (type,id))
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
                item = plugincontent.prepareListItem(item)
                liz = plugincontent.createListItem(item)
                liz.setThumbnailImage(item["art"].get("poster"))
                similarlist.addItem(liz)
        except Exception as e:
            plugincontent.logMsg("ERROR in InfoDialog - getrecommendedmedia ! --> " + str(e), 0)

        try: #optional: cast list
            castlist = self.infoDialog.getControl( 998 )
            castitems = []
            downloadThumbs = xbmc.getInfoLabel("Skin.String(actorthumbslookup)").lower() == "true"
            if self.infoDialog.content == 'movies':
                castitems = plugincontent.getCast(movie=list.getSelectedItem().getLabel().decode("utf-8"),downloadThumbs=downloadThumbs,listOnly=True)
            elif self.infoDialog.content == 'tvshows':
                castitems = plugincontent.getCast(tvshow=list.getSelectedItem().getLabel().decode("utf-8"),downloadThumbs=downloadThumbs,listOnly=True)
            elif self.infoDialog.content == 'episodes':
                castitems = plugincontent.getCast(episode=list.getSelectedItem().getLabel().decode("utf-8"),downloadThumbs=downloadThumbs,listOnly=True)
            for cast in castitems:
                liz = xbmcgui.ListItem(label=cast.get("name"),label2=cast.get("role"),iconImage=cast.get("thumbnail"))
                liz.setProperty('IsPlayable', 'false')
                url = "RunScript(script.extendedinfo,info=extendedactorinfo,name=%s)"%cast.get("name")
                liz.setProperty("path",url)
                liz.setThumbnailImage(cast.get("thumbnail"))
                castlist.addItem(liz)
                    
        except Exception as e:
            plugincontent.logMsg("ERROR in InfoDialog - getcast ! --> " + str(e), 0)
