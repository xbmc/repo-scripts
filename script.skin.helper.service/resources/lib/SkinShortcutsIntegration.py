#!/usr/bin/python
# -*- coding: utf-8 -*-
from Utils import *

#This file contains methods to connect skinhelper to skinshortcuts for smartshortcuts, widgets and backgrounds
    
def addSmartShortcutDirectoryItem(entry, isFolder=True, widget=None, widget2=None):
    
    label = "$INFO[Window(Home).Property(%s.title)]" %entry
    path = "$INFO[Window(Home).Property(%s.path)]" %entry
    content = "$INFO[Window(Home).Property(%s.content)]" %entry
    image = "$INFO[Window(Home).Property(%s.image)]" %entry
    type = "$INFO[Window(Home).Property(%s.type)]" %entry

    if isFolder:
        path = sys.argv[0] + "?action=SMARTSHORTCUTS&path=" + entry
        li = xbmcgui.ListItem(label, path=path)
        li.setIconImage("DefaultFolder.png")
    else:
        li = xbmcgui.ListItem(label, path=path)
        props = {}
        props["list"] = content
        if not xbmc.getInfoLabel(type):
            type = "media"
        props["type"] = type
        props["background"] = "$INFO[Window(Home).Property(%s.image)]" %entry
        props["backgroundName"] = "$INFO[Window(Home).Property(%s.title)]" %entry
        li.setInfo( type="Video", infoLabels={ "Title": "smartshortcut" })
        li.setThumbnailImage(image)
        li.setIconImage("special://home/addons/script.skin.helper.service/fanart.jpg")
        
        if widget:
            widgettype = "$INFO[Window(Home).Property(%s.type)]" %widget
            if not xbmc.getInfoLabel(type):
                widgettype = type
            if widgettype == "albums" or widgettype == "artists" or widgettype == "songs":
                widgettarget = "music"
            else:
                widgettarget = "video"
            props["widget"] = "addon"
            props["widgetName"] = "$INFO[Window(Home).Property(%s.title)]" %widget
            props["widgetType"] = widgettype
            props["widgetTarget"] = widgettarget
            props["widgetPath"] = "$INFO[Window(Home).Property(%s.content)]" %widget
            if "plugin:" in xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" %widget):
                props["widgetPath"] = props["widgetPath"] + "&reload=$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"
            
        if widget2:
            widgettype = "$INFO[Window(Home).Property(%s.type)]" %widget2
            if not xbmc.getInfoLabel(type):
                widgettype = type
            if widgettype == "albums" or widgettype == "artists" or widgettype == "songs":
                widgettarget = "music"
            else:
                widgettarget = "video"
            props["widget.1"] = "addon"
            props["widgetName.1"] = "$INFO[Window(Home).Property(%s.title)]" %widget2
            props["widgetType.1"] = widgettype
            props["widgetTarget.1"] = widgettarget
            props["widgetPath.1"] = "$INFO[Window(Home).Property(%s.content)]" %widget2
            if "plugin:" in xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" %widget2):
                props["widgetPath.1"] = props["widgetPath.1"] + "&reload=$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"
            
        li.setInfo( type="Video", infoLabels={ "mpaa": repr(props) })
    
    li.setArt({"fanart":image})   
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=li, isFolder=isFolder)

def addSmartShortcutsSublevel(entry):
    if "emby" in entry:
        contentStrings = ["", ".recent", ".inprogress", ".unwatched", ".recentepisodes", ".inprogressepisodes", ".nextepisodes", ".recommended"]
    elif "plex" in entry:
        contentStrings = ["", ".ondeck", ".recent", ".unwatched"]
    elif "netflix.generic.suggestions" in entry:
        contentStrings = ["", ".0", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9", ".10"]
    elif "netflix" in entry:
        contentStrings = ["", ".mylist", ".recent", ".inprogress", ".suggestions", ".genres", ".recommended", ".trending"]
        
    for contentString in contentStrings:
        key = entry + contentString
        widget = None
        widget2 = None
        if contentString == "":
            #this is the main item so define our widgets
            type = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.type)]" %entry)
            if "plex" in entry:
                widget = entry + ".ondeck"
                widget2 = entry + ".recent"
            elif type == "movies" or type == "movie" or type == "artist" or "netflix" in entry:
                widget = entry + ".recent"
                widget2 = entry + ".inprogress"
            elif type == "tvshows" and "emby" in entry:
                widget = entry + ".nextepisodes"
                widget2 = entry + ".recent"
            elif (type == "homevideos" or type == "photos") and "emby" in entry:
                widget = entry + ".recent"
                widget2 = entry + ".recommended"
            else:
                widget = entry
        if xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.path)]" %key):
            addSmartShortcutDirectoryItem(key,False, widget,widget2)

def getSmartShortcuts(sublevel=None):
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    if sublevel:
        addSmartShortcutsSublevel(sublevel)
    else:
        allSmartShortcuts = WINDOW.getProperty("allSmartShortcuts")
        if allSmartShortcuts:
            for node in eval (allSmartShortcuts):
                if "emby" in node or "plex" in node or "netflix" in node:
                    #create main folder entry
                    addSmartShortcutDirectoryItem(node,True)
                else:
                    label = "$INFO[Window(Home).Property(%s.title)]" %node
                    #create final listitem entry (playlist, favorites)
                    addSmartShortcutDirectoryItem(node,False, node)
                    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getSmartShortCutsWidgetNodes():
    foundWidgets = []
    allSmartShortcuts = WINDOW.getProperty("allSmartShortcuts")
    if allSmartShortcuts:
        for node in eval (allSmartShortcuts):
            label = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.title)]" %node)
            if "emby" in node or "plex" in node or "netflix" in node:
                #create main folder entry
                path = sys.argv[0] + "?action=SMARTSHORTCUTS&path=%s"%node
                foundWidgets.append([label, path, "folder", True])
            else:
                content = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" %node)
                type = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.type)]" %node)
                foundWidgets.append([label, content, type])
    return foundWidgets
   
def getWidgets(itemstoInclude = None):
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    if itemstoInclude:
        #skinner has provided a comma seperated list of widgetitems to include in the listing
        itemstoInclude = itemstoInclude.split(",")
    else:
        #no list provided by the skinner so just show all available widgets
        itemstoInclude = ["skinplaylists", "librarydataprovider", "scriptwidgets", "extendedinfo", "smartshortcuts","pvr", "smartishwidgets", "favourites" ]
    
    #build the widget listiing...
    for widgetType in itemstoInclude:
        if widgetType == "smartshortcuts": widgets = getSmartShortCutsWidgetNodes()
        elif widgetType == "skinplaylists": widgets = getPlayListsWidgetListing()
        elif widgetType == "favourites": widgets = getFavouritesWidgetsListing()
        elif widgetType in ["pvr","smartishwidgets","static"]: widgets = getOtherWidgetsListing(widgetType)
        else: widgets = getAddonWidgetListing(widgetType)
        for widget in widgets:
            type = widget[2]
            if len(widget) > 3:
                isFolder = widget[3]
            else: isFolder = False
            if type == "movies":
                image = "DefaultMovies.png"
                mediaLibrary = "VideoLibrary"
                target = "video"
            elif type == "pvr":
                mediaLibrary = "TvChannels"
                image = "DefaultTVShows.png"
                target = "pvr"
            elif type == "tvshows":
                image = "DefaultTVShows.png"
                mediaLibrary = "VideoLibrary"
                target = "video"
            elif type == "episodes":
                image = "DefaultTVShows.png"
                mediaLibrary = "VideoLibrary"
                target = "video"
            elif type == "albums":
                image = "DefaultMusicAlbums.png"
                mediaLibrary = "MusicLibrary"
                target = "music"
            elif type == "songs":
                image = "DefaultMusicSongs.png"
                mediaLibrary = "MusicLibrary"
                target = "music"
            elif type == "artists":
                image = "DefaultMusicArtists.png"
                mediaLibrary = "MusicLibrary"
                target = "music"
            elif type == "musicvideos":
                image = "DefaultMusicVideos.png"
            else:
                image = "DefaultAddon.png"
                mediaLibrary = "VideoLibrary"
                target = "video"
            
            if isFolder:
                li = xbmcgui.ListItem(widget[0])
                li.setIconImage("DefaultFolder.png")
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=widget[1], listitem=li, isFolder=True)
            else:
                widgetpath = "ActivateWindow(%s,%s,return)" %(mediaLibrary, widget[1].split("&")[0])
                li = xbmcgui.ListItem(widget[0], path=widgetpath)
                props = {}
                props["list"] = widget[1]
                props["type"] = widget[2]
                props["background"] = image
                props["backgroundName"] = ""
                props["widgetPath"] = widget[1]
                props["widgetTarget"] = target
                props["widgetName"] = widget[0]
                props["widget"] = widgetType
                li.setInfo( type="Video", infoLabels={ "Title": "smartshortcut" })
                li.setThumbnailImage(image)
                li.setArt( {"fanart":image} )
                #we use the mpaa property to pass all properties to skinshortcuts    
                li.setInfo( type="Video", infoLabels={ "mpaa": repr(props) })
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=widgetpath, listitem=li, isFolder=False)
    
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
def getBackgrounds():
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    
    globalBackgrounds = []
    globalBackgrounds.append((ADDON.getLocalizedString(32039), "SkinHelper.AllMoviesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32040), "SkinHelper.RecentMoviesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32041), "SkinHelper.InProgressMoviesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32042), "SkinHelper.UnwatchedMoviesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32043), "SkinHelper.AllTvShowsBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32044), "SkinHelper.RecentEpisodesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32045), "SkinHelper.InProgressShowsBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32046), "SkinHelper.PicturesBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32047), "SkinHelper.AllMusicVideosBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32048), "SkinHelper.AllMusicBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32142), "SkinHelper.RecentMusicBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32113), "SkinHelper.PvrBackground"))
    
    globalBackgrounds.append((ADDON.getLocalizedString(32038), "SkinHelper.GlobalFanartBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32138), "SkinHelper.AllVideosBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32139), "SkinHelper.RecentVideosBackground"))
    globalBackgrounds.append((ADDON.getLocalizedString(32140), "SkinHelper.InProgressVideosBackground"))
    
    #wall backgrounds
    globalBackgrounds.append((ADDON.getLocalizedString(32117), "SkinHelper.AllMoviesBackground.Wall"))
    globalBackgrounds.append(("%s - %s" %(ADDON.getLocalizedString(32117),ADDON.getLocalizedString(32161)), "SkinHelper.AllMoviesBackground.Wall.BW"))
    globalBackgrounds.append(("%s (%s)" %(ADDON.getLocalizedString(32117),ADDON.getLocalizedString(32156)), "SkinHelper.AllMoviesBackground.Poster.Wall"))
    globalBackgrounds.append(("%s (%s) - %s" %(ADDON.getLocalizedString(32117),ADDON.getLocalizedString(32156),ADDON.getLocalizedString(32161)), "SkinHelper.AllMoviesBackground.Poster.Wall.BW"))
    
    globalBackgrounds.append((ADDON.getLocalizedString(32118), "SkinHelper.AllMusicBackground.Wall"))
    globalBackgrounds.append(("%s - %s" %(ADDON.getLocalizedString(32127),ADDON.getLocalizedString(32161)), "SkinHelper.AllMusicBackground.Wall.BW"))
    
    globalBackgrounds.append((ADDON.getLocalizedString(32119), "SkinHelper.AllMusicSongsBackground.Wall"))
    globalBackgrounds.append(("%s - %s" %(ADDON.getLocalizedString(32119),ADDON.getLocalizedString(32161)), "SkinHelper.AllMusicSongsBackground.Wall.BW"))
    
    globalBackgrounds.append((ADDON.getLocalizedString(32127), "SkinHelper.AllTvShowsBackground.Wall"))
    globalBackgrounds.append(("%s - %s" %(ADDON.getLocalizedString(32127),ADDON.getLocalizedString(32161)), "SkinHelper.AllTvShowsBackground.Wall.BW"))
    globalBackgrounds.append(("%s (%s)" %(ADDON.getLocalizedString(32127),ADDON.getLocalizedString(32156)), "SkinHelper.AllTvShowsBackground.Poster.Wall"))
    globalBackgrounds.append(("%s (%s) - %s" %(ADDON.getLocalizedString(32127),ADDON.getLocalizedString(32156),ADDON.getLocalizedString(32161)), "SkinHelper.AllTvShowsBackground.Poster.Wall.BW"))
    
    if xbmc.getCondVisibility("System.HasAddon(script.extendedinfo)"):
        globalBackgrounds.append((xbmc.getInfoLabel("$ADDON[script.extendedinfo 32046]") + " (TheMovieDB)", "SkinHelper.TopRatedMovies"))
        globalBackgrounds.append((xbmc.getInfoLabel("$ADDON[script.extendedinfo 32040]") + " (TheMovieDB)", "SkinHelper.TopRatedShows"))
    
    for node in globalBackgrounds:
        label = node[0]
        image = "$INFO[Window(Home).Property(%s)]" %node[1]
        if xbmc.getInfoLabel(image):
            li = xbmcgui.ListItem(label, path=image )
            li.setArt({"fanart":image})
            li.setThumbnailImage(image)
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=image, listitem=li, isFolder=False)
    
    allSmartShortcuts = WINDOW.getProperty("allSmartShortcuts")
    if allSmartShortcuts:
        for node in eval (allSmartShortcuts):
            label = "$INFO[Window(Home).Property(%s.title)]" %node
            image = "$INFO[Window(Home).Property(%s.image)]" %node
            if xbmc.getInfoLabel(image):
                li = xbmcgui.ListItem(label, path=image )
                li.setArt({"fanart":image})
                li.setThumbnailImage(image)
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=image, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))

def getPlayListsWidgetListing():
    foundWidgets = []
    #skin provided playlists
    paths = ["special://skin/playlists/","special://skin/extras/widgetplaylists/","special://skin/extras/playlists/"]
    for path in paths:
        if xbmcvfs.exists(path):
            logMsg("buildWidgetsListing processing: " + path)
            media_array = getJSON('Files.GetDirectory','{ "directory": "%s", "media": "files" }' %path)
            for item in media_array:
                if item["file"].endswith(".xsp"):
                    playlist = item["file"]
                    contents = xbmcvfs.File(item["file"], 'r')
                    contents_data = contents.read().decode('utf-8')
                    contents.close()
                    xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                    type = ""
                    label = item["label"]
                    for line in xmldata.getiterator():
                        if line.tag == "smartplaylist":
                            type = line.attrib['type']
                        if line.tag == "name":
                            label = line.text
                    try:
                        languageid = int(label)
                        label = xbmc.getLocalizedString(languageid)
                    except: pass
                    if not type: type = detectPluginContent(playlist)
                    foundWidgets.append([label, playlist, type])
    return foundWidgets
    
def getAddonWidgetListing(addonShortName):
    #gets the widget listing for an addon
    foundWidgets = []
    addonList = []
    addonList.append(["script.skin.helper.service", "scriptwidgets"])
    addonList.append(["service.library.data.provider", "librarydataprovider"])
    addonList.append(["script.extendedinfo", "extendedinfo"])
    logMsg("getAddonWidgetListing " + addonShortName)
    for addon in addonList:
        if addon[1] == addonShortName:
            logMsg("buildWidgetsListing processing: " + addon[0])
            if xbmc.getCondVisibility("System.HasAddon(%s)" %addon[0]):
                hasTMDBCredentials = False
                #extendedinfo has some login-required widgets, skip those
                if addon[0] == "script.extendedinfo":
                    exinfoaddon = xbmcaddon.Addon(id=addon[0])
                    if exinfoaddon.getSetting("tmdb_username") != "" and exinfoaddon.getSetting("tmdb_password") != "":
                        hasTMDBCredentials = True
                    del exinfoaddon
                media_array = getJSON('Files.GetDirectory','{ "directory": "plugin://%s", "media": "files" }' %addon[0])
                for item in media_array:
                    logMsg("buildWidgetsListing processing: %s - %s" %(addon[0],item["label"]))
                    content = item["file"]
                    #extendedinfo has some login-required widgets, skip those
                    if (addon[0] == "script.extendedinfo" and hasTMDBCredentials==False and ("info=starred" in content or "info=rated" in content or "info=account" in content)):
                        continue
                    #add reload param for skinhelper and libraryprovider widgets
                    if not "reload=" in content and (addon[0] == "script.skin.helper.service" or addon[0] == "service.library.data.provider"):
                        if "albums" in content or "songs" in content or "artists" in content:
                            reloadstr = "&reload=$INFO[Window(Home).Property(widgetreloadmusic)]"
                        elif ("pvr" in content or "media" in content or "favourite" in content) and not "progress" in content:
                            reloadstr = "&reload=$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"
                        else:
                            reloadstr = "&reload=$INFO[Window(Home).Property(widgetreload)]"
                        content = content + reloadstr
                    content = content.replace("&limit=100","&limit=25")
                    label = item["label"]
                    type = detectPluginContent(item["file"])
                    if type == "empty": continue
                    foundWidgets.append([label, content, type])
                if addon[1] == "extendedinfo":
                    #some additional entrypoints for extendedinfo...
                    entrypoints = ["plugin://script.extendedinfo?info=youtubeusersearch&&id=Eurogamer","plugin://script.extendedinfo?info=youtubeusersearch&&id=Engadget","plugin://script.extendedinfo?info=youtubeusersearch&&id=MobileTechReview"]
                    for entry in entrypoints:
                        content = entry
                        label = entry.split("id=")[1]
                        foundWidgets.append([label, content, "episodes"])

    return foundWidgets
    
def getFavouritesWidgetsListing():
    #widgets from favourites
    json_result = getJSON('Favourites.GetFavourites', '{"type": null, "properties": ["path", "thumbnail", "window", "windowparameter"]}')
    foundWidgets = []
    for fav in json_result:
        matchFound = False
        if "windowparameter" in fav:
            content = fav["windowparameter"]
            #check if this is a valid path with content
            if not "script://" in content.lower() and not "mode=9" in content.lower() and not "search" in content.lower() and not "play" in content.lower():
                window = fav["window"]
                label = fav["title"]
                logMsg("buildWidgetsListing processing favourite: " + label)
                type = detectPluginContent(content)
                if type and type != "empty":
                    foundWidgets.append([label, content, type])
    return foundWidgets
    
def getOtherWidgetsListing(widget):
    #some other widgets (by their direct endpoint) such as smartish widgets and PVR
    foundWidgets = []
    if widget=="pvr" and xbmc.getCondVisibility("PVR.HasTVChannels"):
        foundWidgets.append(["$ADDON[script.skin.helper.service 32153]", "pvr://channels/tv/;reload=$INFO[Window(Home).Property(widgetreload2)]", "pvr"])
        foundWidgets.append(["$ADDON[script.skin.helper.service 32170]", "plugin://script.skin.helper.service/?action=pvrchannels&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])
        foundWidgets.append(["$ADDON[script.skin.helper.service 32151]", "plugin://script.skin.helper.service/?action=pvrrecordings&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])
        foundWidgets.append(["$ADDON[script.skin.helper.service 32152]", "plugin://script.skin.helper.service/?action=nextpvrrecordings&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])
        foundWidgets.append(["$ADDON[script.skin.helper.service 32171]", "plugin://script.skin.helper.service/?action=nextpvrrecordings&reversed=true&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])
        foundWidgets.append(["$ADDON[script.skin.helper.service 32154]", "plugin://script.skin.helper.service/?action=pvrtimers&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])
        #foundWidgets.append(["$ADDON[script.skin.helper.service 32133]", "plugin://script.skin.helper.service/?action=pvrchannelgroups&limit=25&reload=$INFO[Window(home).Property(widgetreload2)]", "pvr"])   
    if widget=="smartishwidgets" and xbmc.getCondVisibility("System.HasAddon(service.smartish.widgets) + Skin.HasSetting(enable.smartish.widgets)"):
        foundWidgets.append(["Smart(ish) Movies widget", "plugin://service.smartish.widgets?type=movies&reload=$INFO[Window.Property(smartish.movies)]", "movies"])
        foundWidgets.append(["Smart(ish) Episodes widget", "plugin://service.smartish.widgets?type=episodes&reload=$INFO[Window.Property(smartish.episodes)]", "episodes"])
        foundWidgets.append(["Smart(ish) PVR widget", "plugin://service.smartish.widgets?type=pvr&reload=$INFO[Window.Property(smartish.pvr)]", "pvr"])
        foundWidgets.append(["Smart(ish) Albums widget", "plugin://service.smartish.widgets?type=albums&reload=$INFO[Window.Property(smartish.albums)]", "albums"])
    if widget=="static":
        foundWidgets.append(["$LOCALIZE[8]", "$INCLUDE[WeatherWidget]", "static"])
        foundWidgets.append(["$LOCALIZE[130]", "$INCLUDE[SystemInfoWidget]", "static"])
        foundWidgets.append(["$LOCALIZE[31196]", "$INCLUDE[skinshortcuts-submenu]", "static"])
        if xbmc.getCondVisibility("System.HasAddon(script.games.rom.collection.browser)"):
            foundWidgets.append(["RCB Most played games", "$INCLUDE[RCBWidget]", "static"])
    return foundWidgets
   
