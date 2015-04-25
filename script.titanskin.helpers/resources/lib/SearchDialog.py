import sys
import xbmc
import xbmcgui
import xbmcaddon
import json as json
import urllib
import threading
import InfoDialog

__settings__ = xbmcaddon.Addon(id='script.titanskin.helpers')
__cwd__ = __settings__.getAddonInfo('path')

class SearchDialog(xbmcgui.WindowXMLDialog):

    searchThread = None
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        
    def onInit(self):
        self.action_exitkeys_id = [10, 13]
        
        self.searchThread = BackgroundSearchThread()
        self.searchThread.setDialog(self)
        self.searchThread.start()
        

    def onFocus(self, controlId):
        pass
        
    def onAction(self, action):

        ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
        ACTION_SHOW_INFO = ( 11, )
        ACTION_SELECT_ITEM = 7
        ACTION_PARENT_DIR = 9
        
        if action.getId() in ACTION_CANCEL_DIALOG:
            searchTerm = self.getControl(3010).getText()
            if(len(searchTerm) == 0):
                self.close()
            else:
                searchTerm = searchTerm[:-1]
                self.getControl(3010).setText(searchTerm)
                self.searchThread.setSearch(searchTerm)
        
        elif action.getId() in ACTION_SHOW_INFO:
            self.showInfo()


    def closeDialog(self):
        self.searchThread.stopRunning()
        self.close()
        
    def onClick(self, controlID):

        if(controlID == 3020):
            self.addCharacter("A")
        elif(controlID == 3021):
            self.addCharacter("B")
        elif(controlID == 3022):
            self.addCharacter("C")
        elif(controlID == 3023):
            self.addCharacter("D")
        elif(controlID == 3024):
            self.addCharacter("E")
        elif(controlID == 3025):
            self.addCharacter("F")
        elif(controlID == 3026):
            self.addCharacter("G")
        elif(controlID == 3027):
            self.addCharacter("H")
        elif(controlID == 3028):
            self.addCharacter("I")
        elif(controlID == 3029):
            self.addCharacter("J")
        elif(controlID == 3030):
            self.addCharacter("K")
        elif(controlID == 3031):
            self.addCharacter("L")
        elif(controlID == 3032):
            self.addCharacter("M")
        elif(controlID == 3033):
            self.addCharacter("N")
        elif(controlID == 3034):
            self.addCharacter("O")
        elif(controlID == 3035):
            self.addCharacter("P")
        elif(controlID == 3036):
            self.addCharacter("Q")
        elif(controlID == 3037):
            self.addCharacter("R")
        elif(controlID == 3038):
            self.addCharacter("S")
        elif(controlID == 3039):
            self.addCharacter("T")
        elif(controlID == 3040):
            self.addCharacter("U")
        elif(controlID == 3041):
            self.addCharacter("V")
        elif(controlID == 3042):
            self.addCharacter("W")
        elif(controlID == 3043):
            self.addCharacter("X")
        elif(controlID == 3044):
            self.addCharacter("Y")
        elif(controlID == 3045):
            self.addCharacter("Z")
        elif(controlID == 3046):
            self.addCharacter("0")    
        elif(controlID == 3047):
            self.addCharacter("1")  
        elif(controlID == 3048):
            self.addCharacter("2")  
        elif(controlID == 3049):
            self.addCharacter("3")  
        elif(controlID == 3050):
            self.addCharacter("4")  
        elif(controlID == 3051):
            self.addCharacter("5")  
        elif(controlID == 3052):
            self.addCharacter("6")  
        elif(controlID == 3053):
            self.addCharacter("7")  
        elif(controlID == 3054):
            self.addCharacter("8")  
        elif(controlID == 3055):
            self.addCharacter("9")  
        elif(controlID == 3056):
            searchTerm = self.getControl(3010).getText()
            searchTerm = searchTerm[:-1]
            self.getControl(3010).setText(searchTerm)
            self.searchThread.setSearch(searchTerm)
        elif(controlID == 3057):
            self.addCharacter(" ")
        elif(controlID == 3058):
            self.getControl(3010).setText("")
            self.searchThread.setSearch("")
        elif(controlID == 3010):
            searchTerm = self.getControl(3010).getText()
            self.searchThread.setSearch(searchTerm)
        elif(controlID == 3110):       
            itemList = self.getControl(3110)
            item = itemList.getSelectedItem()
            path = item.getProperty("path")
            self.closeDialog()
            xbmc.Player().play( path )
        elif(controlID == 3111):
            itemList = self.getControl(3111)
            item = itemList.getSelectedItem()
            path = item.getProperty("path")
            self.closeDialog()
            xbmc.executebuiltin('ActivateWindow(Videos,' + path + ',return)')     
        elif(controlID == 3112):
            itemList = self.getControl(3112)
            item = itemList.getSelectedItem()
            path = item.getProperty("path")
            self.closeDialog()
            xbmc.Player().play( path )          
        pass

    def addCharacter(self, char):
        searchTerm = self.getControl(3010).getText()
        searchTerm = searchTerm + char
        self.getControl(3010).setText(searchTerm)
        self.searchThread.setSearch(searchTerm)
    
    def showInfo( self ):
        items = []
        controlId = self.getFocusId()
        if controlId == 3110:
            listitem = self.getControl( controlId ).getSelectedItem()
            content = "movies"
        elif controlId == 3111:
            listitem = self.getControl( controlId ).getSelectedItem()
            content = "tvshows"
        elif controlId == 3112:
            listitem = self.getControl( controlId ).getSelectedItem()
            content = "episodes"
        info_dialog = InfoDialog.GUI( "CustomInfo.xml" , __cwd__, "default", "1080i", listitem=listitem, content=content )
        info_dialog.doModal()
        if info_dialog.action is not None:
            if info_dialog.action == 'play_movie':
                listitem = self.getControl( 3110 ).getSelectedItem()
                path = listitem.getProperty('path')
                self.closeDialog()
                xbmc.Player().play( path )
            elif info_dialog.action == 'play_trailer':
                listitem = self.getControl( 3110 ).getSelectedItem()
                path = listitem.getProperty('trailer')
                self.closeDialog()
                xbmc.Player().play( path )
            elif info_dialog.action == 'browse_tvshow':
                listitem = self.getControl( 3111 ).getSelectedItem()
                path = listitem.getProperty('path')
                self.closeDialog()
                xbmc.executebuiltin('ActivateWindow(Videos,' + path + ',return)')    
            elif info_dialog.action == 'play_episode':
                listitem = self.getControl( 3112 ).getSelectedItem()
                path = listitem.getProperty('path')
                self.closeDialog()
                xbmc.Player().play( path )
        del info_dialog

    
class BackgroundSearchThread(threading.Thread):
 
    active = True
    searchDialog = None
    searchString = ""

    def __init__(self, *args):
        xbmc.log("BackgroundSearchThread Init")
        threading.Thread.__init__(self, *args)

    def setSearch(self, searchFor):
        self.searchString = searchFor
        
    def stopRunning(self):
        self.active = False
        
    def setDialog(self, searchDialog):
        self.searchDialog = searchDialog
        
    def run(self):   
        
        lastSearchString = ""
        
        while(xbmc.abortRequested == False and self.active == True):
            currentSearch = self.searchString  
            if(currentSearch != lastSearchString):
                lastSearchString = currentSearch
                self.doSearch(currentSearch)

            xbmc.sleep(2000)

        
    def doSearch(self, searchTerm):

        movieResultsList = self.searchDialog.getControl(3110)
        while(movieResultsList.size() > 0):
            movieResultsList.removeItem(0)
        
        seriesResultsList = self.searchDialog.getControl(3111)
        while(seriesResultsList.size() > 0):
            seriesResultsList.removeItem(0)

        episodeResultsList = self.searchDialog.getControl(3112)
        while(episodeResultsList.size() > 0):
            episodeResultsList.removeItem(0)
       
        if(len(searchTerm) == 0):
            return
        
        search = urllib.quote(searchTerm)        
        
        # Process movies
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "genre", "studio", "year", "tagline", "plot", "plotoutline", "runtime", "fanart", "thumbnail", "file", "trailer", "playcount", "rating", "mpaa", "director", "writer", "art"], "limits": {"end":50}, "sort": { "method": "label" }, "filter": {"field":"title","operator":"contains","value":"%s"} }, "id": 1}' % search)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('movies')):
            for item in json_response['result']['movies']:
                movie = item['title']
                director = " / ".join(item['director'])
                writer = " / ".join(item['writer'])
                fanart = item['fanart']
                path = item['file']
                genre = " / ".join(item['genre'])
                mpaa = item['mpaa']
                playcount = str(item['playcount'])
                plot = item['plot']
                outline = item['plotoutline']
                rating = str(round(float(item['rating']),1))
                starrating = 'rating%.1d.png' % round(float(rating)/2)
                runtime = str(int((item['runtime'] / 60.0) + 0.5))
                studio = " / ".join(item['studio'])
                tagline = item['tagline']
                thumb = item['thumbnail']
                trailer = item['trailer']
                year = str(item['year'])
                listitem = xbmcgui.ListItem(label=movie, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "plotoutline", outline )
                listitem.setProperty( "duration", runtime )
                listitem.setProperty( "studio", studio )
                listitem.setProperty( "tagline", tagline )
                listitem.setProperty( "year", year )
                listitem.setProperty( "trailer", trailer )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "starrating", starrating )
                listitem.setProperty( "mpaa", mpaa )
                listitem.setProperty( "writer", writer )
                listitem.setProperty( "director", director )
                listitem.setProperty( "path", path )
                movieResultsList.addItem(listitem)

        # Process TV Shows
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "genre", "studio", "premiered", "plot", "fanart", "thumbnail", "playcount", "year", "mpaa", "episode", "rating", "art"], "limits": {"end":50}, "sort": { "method": "label" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % search)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('tvshows')):
            for item in json_response['result']['tvshows']:
                tvshow = item['title']
                episode = str(item['episode'])
                fanart = item['fanart']
                genre = " / ".join(item['genre'])
                mpaa = item['mpaa']
                playcount = str(item['playcount'])
                plot = item['plot']
                premiered = item['premiered']
                rating = str(round(float(item['rating']),1))
                starrating = 'rating%.1d.png' % round(float(rating)/2)
                studio = " / ".join(item['studio'])
                thumb = item['thumbnail']
                banner = item['art'].get('banner', '')
                poster = item['art'].get('poster', '')
                tvshowid = str(item['tvshowid'])
                path = path = 'videodb://tvshows/titles/' + tvshowid + '/'
                year = str(item['year'])
                listitem = xbmcgui.ListItem(label=tvshow, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "art(banner)", banner )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "episode", episode )
                listitem.setProperty( "mpaa", mpaa )
                listitem.setProperty( "year", year )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "premiered", premiered )
                listitem.setProperty( "studio", studio )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "starrating", starrating )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "path", path )
                listitem.setProperty( "id", tvshowid )
                seriesResultsList.addItem(listitem)

        # Process episodes
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "plot", "firstaired", "runtime", "season", "episode", "showtitle", "thumbnail", "fanart", "file", "playcount", "director", "rating", "art"], "limits": {"end":50}, "sort": { "method": "title" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % search)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('episodes')):
            for item in json_response['result']['episodes']:
                episode = item['title']
                tvshowname = item['showtitle']
                director = " / ".join(item['director'])
                fanart = item['fanart']
                episodenumber = "%.2d" % float(item['episode'])
                path = item['file']
                plot = item['plot']
                runtime = str(int((item['runtime'] / 60.0) + 0.5))
                premiered = item['firstaired']
                rating = str(round(float(item['rating']),1))
                starrating = 'rating%.1d.png' % round(float(rating)/2)
                seasonnumber = '%.2d' % float(item['season'])
                playcount = str(item['playcount'])
                thumb = item['thumbnail']
                fanart = item['fanart']
                poster = item['art']['tvshow.poster']
                listitem = xbmcgui.ListItem(label=episode, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "poster", poster )
                listitem.setProperty( "episode", episodenumber )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "starrating", starrating )
                listitem.setProperty( "director", director )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "season", seasonnumber )
                listitem.setProperty( "duration", runtime )
                listitem.setProperty( "tvshowtitle", tvshowname )
                listitem.setProperty( "premiered", premiered )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "path", path )
                episodeResultsList.addItem(listitem)
                
                
                