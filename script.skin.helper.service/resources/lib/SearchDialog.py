import threading
import InfoDialog
from Utils import *

class SearchDialog(xbmcgui.WindowXMLDialog):

    searchThread = None
    settings = None
    cwd = None
    searchString = ""
    
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.settings = xbmcaddon.Addon(id='script.skin.helper.service')
        self.cwd = ADDON_PATH
        
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
            self.removeCharacter()
        
        elif action.getId() in ACTION_SHOW_INFO:
            self.showInfo()

    def closeDialog(self,action=None):
        self.searchThread.stopRunning()
        self.action = action
        self.close()
    
    def removeCharacter(self):
        if(len(self.searchString) == 0 or self.searchString == " "):
                self.closeDialog()
        else:
            if(len(self.searchString) == 1):
                searchTerm = " "
            else:
                searchTerm = self.searchString[:-1]
            self.getControl(3010).setLabel(searchTerm)
            self.searchString = searchTerm
            self.searchThread.setSearch(searchTerm)
    
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
           self.removeCharacter()
        elif(controlID == 3057):
            self.addCharacter(" ")
        elif(controlID == 3058):
            self.getControl(3010).setLabel(" ")
            self.searchString = ""
            self.searchThread.setSearch("")
        elif(controlID == 3010):
            dialog = xbmcgui.Dialog()
            searchTerm = dialog.input(xbmc.getLocalizedString(16017), type=xbmcgui.INPUT_ALPHANUM)
            self.getControl(3010).setLabel(searchTerm)
            self.searchString = searchTerm
            self.searchThread.setSearch(searchTerm)
        elif(controlID == 3110):       
            itemList = self.getControl(3110)
            item = itemList.getSelectedItem()
            path = item.getProperty("dbid")
            self.closeDialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %s } }, "id": 1 }' % path)
        elif(controlID == 3111):
            itemList = self.getControl(3111)
            item = itemList.getSelectedItem()
            path = item.getProperty("path")
            self.closeDialog('ActivateWindow(Videos,' + path + ',return)')  
        elif(controlID == 3112):
            itemList = self.getControl(3112)
            item = itemList.getSelectedItem()
            path = item.getfilename()
            self.closeDialog('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "file": "%s" } }, "id": 1 }' % path)
        

    def addCharacter(self, char):
        searchTerm = self.searchString + char
        self.getControl(3010).setLabel(searchTerm)
        self.searchString = searchTerm
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
        listitem2 = createListItem(eval(listitem.getProperty("json")))
        listitem2.setProperty("path", listitem.getProperty("path"))
        listitem2.setProperty("json", listitem.getProperty("json"))
        info_dialog = InfoDialog.GUI( "script-skin_helper_service-CustomInfo.xml" , self.cwd, "Default", "1080i", listitem=listitem2, content=content )
        info_dialog.doModal()
        action = info_dialog.action
        del info_dialog
        if action:
            self.closeDialog(action)
    
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

            xbmc.Monitor().waitForAbort(2)

        
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
        json_response = getJSON('VideoLibrary.GetMovies', '{"properties": [%s], "limits": {"end":50}, "sort": { "method": "label" }, "filter": {"field":"title","operator":"contains","value":"%s"} }' % (fields_movies,search))
        for item in json_response:
            item = prepareListItem(item)
            liz = createListItem(item)
            liz.setProperty("json",repr(item))
            movieResultsList.addItem(liz)

        # Process TV Shows
        json_response = getJSON('VideoLibrary.GetTVShows', '{"properties": [%s], "limits": {"end":50}, "sort": { "method": "label" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }' % (fields_tvshows,search))
        for item in json_response:
            item = prepareListItem(item)
            liz = createListItem(item)
            tvshowid = str(item['tvshowid'])
            path = 'videodb://tvshows/titles/' + tvshowid + '/'
            liz.setPath(path)
            liz.setProperty("path", path)
            liz.setProperty("json",repr(item))
            seriesResultsList.addItem(liz)

        # Process episodes
        json_response = getJSON('VideoLibrary.GetEpisodes', '{ "properties": [%s], "limits": {"end":50}, "sort": { "method": "title" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }' % (fields_episodes,search))
        for item in json_response:
            item = prepareListItem(item)
            liz.setProperty("json",repr(item))
            episodeResultsList.addItem(liz)