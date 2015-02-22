import xbmcplugin
import xbmcgui
import xbmc
import xbmcaddon
import shutil
import xbmcaddon
import xbmcvfs
import os
import time
import urllib
import xml.etree.ElementTree as etree
import json
import random

doDebugLog = False

__language__ = xbmc.getLocalizedString

def logMsg(msg, level = 1):
    if doDebugLog == True:
        xbmc.log(msg)

def sendClick(controlId):
    win = xbmcgui.Window( 10000 )
    time.sleep(0.5)
    xbmc.executebuiltin('SendClick('+ controlId +')')

def defaultSettings():
    # skins default settings for artist slideshow
    if xbmc.getCondVisibility("System.HasAddon(script.artistslideshow)"):
        __settings__ = xbmcaddon.Addon(id='script.artistslideshow')
        __settings__.setSetting('transparent', "true")
      
def musicSearch():
    xbmc.executebuiltin( "ActivateWindow(MusicLibrary)" )
    xbmc.executebuiltin( "SendClick(8)" )
        
def showWidget():
    win = xbmcgui.Window( 10000 )
    linkCount = 0
    xbmc.executebuiltin('Control.SetFocus(77777,0)')
    while linkCount !=10 and not xbmc.getCondVisibility("ControlGroup(77777).HasFocus"):
        time.sleep(0.1)
        if not xbmc.getCondVisibility("ControlGroup(77777).HasFocus"):
            xbmc.executebuiltin('Control.SetFocus(77777,0)')
        linkCount += 1
    
def setWidget(containerID):
    win = xbmcgui.Window( 10000 )
    win.clearProperty("activewidget")
    win.clearProperty("customwidgetcontent")
    skinStringContent = ""
    customWidget = False
    
    # workaround for numeric labels (get translated by xbmc)
    skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(submenuVisibility)")
    skinString = skinString.replace("num-","")
    if xbmc.getCondVisibility("Skin.String(widget-" + skinString + ')'):
        skinStringContent = xbmc.getInfoLabel("Skin.String(widget-" + skinString + ')')
    
    # normal method by getting the defaultID
    if skinStringContent == "":
        skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(defaultID)")
        if xbmc.getCondVisibility("Skin.String(widget-" + skinString + ')'):
            skinStringContent = xbmc.getInfoLabel("Skin.String(widget-" + skinString + ')')
       
    if skinStringContent != "":
 
        if "$INFO" in skinStringContent:
            skinStringContent = skinStringContent.replace("$INFO[Window(Home).Property(", "")
            skinStringContent = skinStringContent.replace(")]", "")
            skinStringContent = win.getProperty(skinStringContent)
            customWidget = True
        if "Activate" in skinStringContent:
            skinStringContent = skinStringContent.split(",",1)[1]
            skinStringContent = skinStringContent.replace(",return","")
            skinStringContent = skinStringContent.replace(")","")
            skinStringContent = skinStringContent.replace("\"","")
            customWidget = True
        if ":" in skinStringContent:
            customWidget = True
            
        if customWidget:
             win.setProperty("customwidgetcontent", skinStringContent)
             win.setProperty("activewidget","custom")
        else:
            win.clearProperty("customwidgetcontent")
            win.setProperty("activewidget",skinStringContent)

    else:
        win.clearProperty("activewidget")
    
    #also set spotlightwidget for enhancedhomescreen
    if xbmc.getCondVisibility("Skin.String(GadgetRows, enhanced)"):
        setSpotlightWidget(containerID)

def setSpotlightWidget(containerID):
    win = xbmcgui.Window( 10000 )
    win.clearProperty("spotlightwidgetcontent")
    skinStringContent = ""
    customWidget = False
    
    # workaround for numeric labels (get translated by xbmc)
    skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(submenuVisibility)")
    skinString = skinString.replace("num-","")
    if xbmc.getCondVisibility("Skin.String(spotlightwidget-" + skinString + ')'):
        skinStringContent = xbmc.getInfoLabel("Skin.String(spotlightwidget-" + skinString + ')')
    
    # normal method by getting the defaultID
    if skinStringContent == "":
        skinString = xbmc.getInfoLabel("Container(" + containerID + ").ListItem.Property(defaultID)")
        if xbmc.getCondVisibility("Skin.String(spotlightwidget-" + skinString + ')'):
            skinStringContent = xbmc.getInfoLabel("Skin.String(spotlightwidget-" + skinString + ')')
       
    if skinStringContent != "":
 
        if "$INFO" in skinStringContent:
            skinStringContent = skinStringContent.replace("$INFO[Window(Home).Property(", "")
            skinStringContent = skinStringContent.replace(")]", "")
            skinStringContent = win.getProperty(skinStringContent)
        if "Activate" in skinStringContent:
            skinStringContent = skinStringContent.split(",",1)[1]
            skinStringContent = skinStringContent.replace(",return","")
            skinStringContent = skinStringContent.replace(")","")
            skinStringContent = skinStringContent.replace("\"","")

        win.setProperty("spotlightwidgetcontent", skinStringContent)

    else:
        win.clearProperty("spotlightwidgetcontent")        
        
        
def setCustomContent(skinString):
    #legacy
    win = xbmcgui.Window( 10000 )
    skinStringContent = xbmc.getInfoLabel("Skin.String(" + skinString + ')')

    if "$INFO" in skinStringContent:
        skinStringContent = skinStringContent.replace("$INFO[Window(Home).Property(", "")
        skinStringContent = skinStringContent.replace(")]", "")
        skinStringContent = win.getProperty(skinStringContent)    

    if "Activate" in skinStringContent:
        skinStringContent = skinStringContent.split(",",1)[1]
        skinStringContent = skinStringContent.replace(",return","")
        skinStringContent = skinStringContent.replace(")","")
        skinStringContent = skinStringContent.replace("\"","")
           
        xbmc.executebuiltin("Skin.SetString(" + skinString + ','+ skinStringContent + ')')         

    win.setProperty("customwidgetcontent", skinStringContent)
        
def updatePlexlinks():
    win = xbmcgui.Window( 10000 )
    logMsg("update plexlinks started...")
    xbmc.executebuiltin('RunScript(plugin.video.plexbmc,skin)')
    linkCount = 0
    logMsg("updateplexlinks started...")
    
    #update plex window properties
    xbmc.sleep(3000)
    while linkCount !=10:
        plexstring = "plexbmc." + str(linkCount)
        link = win.getProperty(plexstring + ".title")
        logMsg(plexstring + ".title --> " + link)
        plexType = win.getProperty(plexstring + ".type")
        logMsg(plexstring + ".type --> " + plexType)            

        link = win.getProperty(plexstring + ".recent")
        logMsg(plexstring + ".recent --> " + link)
        link = link.replace("ActivateWindow(VideoLibrary, ", "")
        link = link.replace("ActivateWindow(VideoLibrary,", "")
        link = link.replace("ActivateWindow(MusicFiles,", "")
        link = link.replace("ActivateWindow(Pictures,", "")
        link = link.replace(",return)", "")
        win.setProperty(plexstring + ".recent.content", link)
        logMsg(plexstring + ".recent --> " + link)

        link = win.getProperty(plexstring + ".viewed")
        logMsg(plexstring + ".viewed --> " + link)
        link = link.replace("ActivateWindow(VideoLibrary, ", "")
        link = link.replace("ActivateWindow(VideoLibrary,", "")
        link = link.replace("ActivateWindow(MusicFiles,", "")
        link = link.replace("ActivateWindow(Pictures,", "")
        link = link.replace(",return)", "")
        win.setProperty(plexstring + ".viewed.content", link)
        logMsg(plexstring + ".viewed --> " + link)

        linkCount += 1
    
    xbmc.sleep(5000)
    updatePlexBackgrounds()   
        
def updatePlexBackgrounds():
    win = xbmcgui.Window( 10000 )
    logMsg("update plex backgrounds started...")        
    
    #update plex backgrounds
    linkCount = 0
    xbmc.sleep(5000)
    while linkCount !=10:
        plexstring = "plexbmc." + str(linkCount)
        randomNr = random.randrange(1,10+1)       
        plexType = win.getProperty(plexstring + ".type")
        randomimage = ""
        if plexType == "movie":
            randomimage = xbmc.getInfoLabel("Container(100" + str(linkCount) + ").ListItem(" + str(randomNr) + ").Art(fanart)")
            win.setProperty("plexfanartbg", randomimage)
        elif plexType == "artist":
            randomimage = xbmc.getInfoLabel("Container(100" + str(linkCount) + ").ListItem(" + str(randomNr) + ").Art(fanart)")
            if randomimage == "":
                randomimage = xbmc.getInfoLabel("Container(100" + str(linkCount) + ").ListItem(1).Art(fanart)")
            if randomimage == "":
                randomimage = "special://skin/extras/backgrounds/hover_my music.png"                
        elif plexType == "show":
            randomimage = xbmc.getInfoLabel("Container(100" + str(linkCount) + ").ListItem(" + str(randomNr) + ").Property(Fanart_Image)")
        elif plexType == "photo":
            randomimage = xbmc.getInfoLabel("Container(100" + str(linkCount) + ").ListItem(" + str(randomNr) + ").PicturePath")                

        if randomimage != "":
            win.setProperty(plexstring + ".background", randomimage)
            logMsg(plexstring + ".background --> " + randomimage)            

        linkCount += 1
               
def showInfoPanel():
    win = xbmcgui.Window( 10000 )
    tryCount = 0
    secondsToDisplay = "4"
    secondsToDisplay = xbmc.getInfoLabel("Skin.String(ShowInfoAtPlaybackStart)")
    while tryCount !=50 and not xbmc.getCondVisibility("Window.IsActive(fullscreeninfo)"):
        time.sleep(0.1)
        if not xbmc.getCondVisibility("Window.IsActive(fullscreeninfo)") and xbmc.getCondVisibility("Player.HasVideo"):
            xbmc.executebuiltin('Action(info)')
        tryCount += 1
    
    # close info again
    time.sleep(int(secondsToDisplay))
    if xbmc.getCondVisibility("Window.IsActive(fullscreeninfo)"):
        xbmc.executebuiltin('Action(info)')

def addShortcutWorkAround():
    win = xbmcgui.Window( 10000 )
    xbmc.executebuiltin('SendClick(301)')
    if xbmc.getCondVisibility("System.Platform.Windows"):
        xbmc.sleep(1000)
    else:
        xbmc.sleep(2000)
    xbmc.executebuiltin('SendClick(401)')

def checkExtraFanArt():
        
    lastPath = None
    win = xbmcgui.Window( 10000 )
    
    try:
        efaPath = None
        efaFound = False
        liArt = None
        liPath = xbmc.getInfoLabel("ListItem.Path")
        containerPath = xbmc.getInfoLabel("Container.FolderPath")
        
        if (liPath != None and (xbmc.getCondVisibility("Container.Content(movies)") or xbmc.getCondVisibility("Container.Content(seasons)") or xbmc.getCondVisibility("Container.Content(episodes)") or xbmc.getCondVisibility("Container.Content(tvshows)")) and not "videodb:" in liPath):
                           
            if xbmc.getCondVisibility("Container.Content(episodes)"):
                liArt = xbmc.getInfoLabel("ListItem.Art(tvshow.fanart)")
            
            # do not set extra fanart for virtuals
            if (("plugin://" in liPath) or ("addon://" in liPath) or ("sources" in liPath) or ("plugin://" in containerPath) or ("sources://" in containerPath) or ("plugin://" in containerPath)):
                win.clearProperty("ExtraFanArtPath")
                lastPath = None
            else:

                if xbmcvfs.exists(liPath + "extrafanart/"):
                    efaPath = liPath + "extrafanart/"
                else:
                    pPath = liPath.rpartition("/")[0]
                    pPath = pPath.rpartition("/")[0]
                    if xbmcvfs.exists(pPath + "/extrafanart/"):
                        efaPath = pPath + "/extrafanart/"
                        
                if xbmcvfs.exists(efaPath):
                    dirs, files = xbmcvfs.listdir(efaPath)
                    if files.count > 1:
                        efaFound = True
                        
                if (efaPath != None and efaFound == True):
                    if lastPath != efaPath:
                        win.setProperty("ExtraFanArtPath",efaPath)
                        lastPath = efaPath
                        
                else:
                    win.clearProperty("ExtraFanArtPath")
                    lastPath = None
        else:
            win.clearProperty("ExtraFanArtPath")
            lastPath = None
    
    except:
        xbmc.log("Titan skin helper: error occurred in assigning extra fanart background")
          
def focusEpisode():
    
    totalItems = 0
    curView = xbmc.getInfoLabel("Container.Viewmode") 
    viewId = int(getViewId(curView))
    
    wid = xbmcgui.getCurrentWindowId()
    window = xbmcgui.Window( wid )        
    control = window.getControl(int(viewId))
    totalItems = int(xbmc.getInfoLabel("Container.NumItems"))
        
    if (xbmc.getCondVisibility("Container.SortDirection(ascending)")):
        curItem = 1
        control.selectItem(0)
        xbmc.sleep(250)
        while (xbmc.getCondVisibility("Container.Content(episodes)") and totalItems >= curItem):
            if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png" and xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Label") != ".."):
                if curItem != 0:
                    control.selectItem(curItem)
                break
            else:
                curItem += 1
    
    elif (xbmc.getCondVisibility("Container.SortDirection(descending)")):
        curItem = totalItems
        control.selectItem(totalItems)
        xbmc.sleep(250)
        while (xbmc.getCondVisibility("Container.Content(episodes)") and curItem != 0):
            
            if (xbmc.getInfoLabel("Container.ListItem(" + str(curItem) + ").Overlay") != "OverlayWatched.png"):
                control.selectItem(curItem-1)
                break
            else:    
                curItem -= 1
            

def getViewId(viewString):
    # get all views from views-file
    viewId = None
    skin_view_file = os.path.join(xbmc.translatePath('special://skin/extras'), "views.xml")
    tree = etree.parse(skin_view_file)
    root = tree.getroot()
    for view in root.findall('view'):
        if viewString == __language__(int(view.attrib['languageid'])):
            viewId=view.attrib['value']
    
    return viewId
    

def UpdateBackgrounds():
    win = xbmcgui.Window( 10000 )
    media_array = None
    #get in progress movies
    try:
        media_array = getJSON('VideoLibrary.GetMovies','{"properties":["title","art"],"sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}}')
        if(media_array != None and media_array.has_key('movies')):
            inprogressMovies = list()
            for aMovie in media_array['movies']:
                if aMovie.has_key('art'):
                    if aMovie['art'].has_key('fanart'):
                        inprogressMovies.append(aMovie['art']['fanart'])
            
            random.shuffle(inprogressMovies)
            win.setProperty("InProgressMovieBackground",inprogressMovies[0])
    except:
        xbmc.log("Titan skin helper: error occurred in assigning inprogress movies background")
    
    media_array = None
    #get recent and unwatched movies
    try:
        media_array = getJSON('VideoLibrary.GetRecentlyAddedMovies','{"properties":["title","art","playcount"], "limits": {"end":50} }')
        if(media_array != None and media_array.has_key('movies')):
            recentMovies = list()
            unwatchedMovies = list()
            for aMovie in media_array['movies']:
               
                if aMovie.has_key('art'): 
                    if aMovie['art'].has_key('fanart'):
                        recentMovies.append(aMovie['art']['fanart'])
                        if aMovie['playcount'] == 0:
                            unwatchedMovies.append(aMovie['art']['fanart'])

            random.shuffle(recentMovies)
            win.setProperty("RecentMovieBackground",recentMovies[0])
            random.shuffle(unwatchedMovies)
            win.setProperty("UnwatchedMovieBackground",unwatchedMovies[0])
    except:
        xbmc.log("Titan skin helper: error occurred in assigning recent movies background")

    media_array = None    
    #get in progress tvshows
    try:
        media_array = getJSON('VideoLibrary.GetTVShows','{"properties":["title","art"],"sort": {"order": "descending", "method": "lastplayed"}, "filter": {"field": "inprogress", "operator": "true", "value": ""}}')
        if(media_array != None and media_array.has_key('tvshows')):
            inprogressShows = list()    
            for aShow in media_array['tvshows']:
                if aShow.has_key('art'):
                    if aShow['art'].has_key('fanart'):
                        inprogressShows.append(aShow['art']['fanart'])
        
            random.shuffle(inprogressShows)
            win.setProperty("InProgressShowsBackground",inprogressShows[0])
    except:
        xbmc.log("Titan skin helper: error occurred in assigning inprogress tvshows background")

    media_array = None
    #get recent episodes
    try:
        media_array = getJSON('VideoLibrary.GetRecentlyAddedEpisodes','{"properties":["showtitle","art","file","plot","season","episode"], "limits": {"end":10} }')
        if(media_array != None and media_array.has_key('episodes')):
            recentEpisodes = list()
            for aShow in media_array['episodes']:
                if aShow.has_key('art'):
                    if aShow['art'].has_key('tvshow.fanart'):
                        recentEpisodes.append(aShow['art']['tvshow.fanart'])

            random.shuffle(recentEpisodes)
            win.setProperty("RecentEpisodesBackground",recentEpisodes[0])
    except Exception, msg:
        xbmc.log("Titan skin helper: error occurred in assigning recent episodes background")
        xbmc.log(str(msg))

                
def getJSON(method,params):
    json_response = xbmc.executeJSONRPC('{ "jsonrpc" : "2.0" , "method" : "' + method + '" , "params" : ' + params + ' , "id":1 }')

    jsonobject = json.loads(json_response.decode('utf-8','replace'))
   
    if(jsonobject.has_key('result')):
        return jsonobject['result']
    else:
        utils.log("no result " + str(jsonobject),xbmc.LOGDEBUG)
        return None

    
def setView(containerType,viewId):

    if viewId=="00":
        win = xbmcgui.Window( 10000 )

        curView = xbmc.getInfoLabel("Container.Viewmode")
        viewId = getViewId(curView)
        
    else:
        viewId=viewId    

    if xbmc.getCondVisibility("System.HasAddon(plugin.video.netflixbmc)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.netflixbmc')

        if containerType=="MOVIES":
            __settings__.setSetting('viewIdVideos', viewId)
        elif containerType=="SERIES":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        elif containerType=="SEASONS":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        elif containerType=="EPISODES":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        else:
            __settings__.setSetting('viewIdActivity', viewId)
            
    if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        if __settings__.getSetting(xbmc.getSkinDir()+ '_VIEW_' + containerType) != "disabled":
            __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' + containerType, viewId)

def checkNotifications(notificationType):
    
    if notificationType == "weather":
        win = xbmcgui.Window(12600)
        if (win.getProperty("Alerts.RSS") != "" and win.getProperty("Current.Condition") != ""):
            dialog = xbmcgui.Dialog()
            dialog.notification(xbmc.getLocalizedString(31294), win.getProperty("Alerts"), xbmcgui.NOTIFICATION_WARNING, 8000)
    
    if notificationType == "nextaired":
        win = xbmcgui.Window(10000)
        if (win.getProperty("NextAired.TodayShow") != ""):
            dialog = xbmcgui.Dialog()
            dialog.notification(xbmc.getLocalizedString(31295), win.getProperty("NextAired.TodayShow"), xbmcgui.NOTIFICATION_WARNING, 8000)    
            
            
def showSubmenu(showOrHide,doFocus):

    win = xbmcgui.Window( 10000 )
    submenuTitle = xbmc.getInfoLabel("Container(300).ListItem.Label")
    submenu = win.getProperty("submenutype")
    submenuloading = ""
    if xbmc.getCondVisibility("Skin.HasSetting(AutoShowSubmenu)"):
        submenuloading = win.getProperty("submenuloading")

    # SHOW SUBMENU    
    if showOrHide == "SHOW":
        if submenuloading != "loading":
            if submenu != "":
                win.setProperty("submenu", "show")
                if doFocus != None:
                    win.setProperty("submenuTitle", submenuTitle)
                    xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
                    time.sleep(0.2)
                    xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
            else:
                win.setProperty("submenu", "hide")
        else:
            win.setProperty("submenuloading", "")

    #HIDE SUBMENU
    elif showOrHide == "HIDE":
        win.setProperty("submenuloading", "loading")
        win.setProperty("submenu", "hide")
        if doFocus != None:
            win.setProperty("submenu", "show")
            xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
            time.sleep(0.5)
            xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
            win.setProperty("submenuloading", "loading")
            win.setProperty("submenu", "hide")
            
