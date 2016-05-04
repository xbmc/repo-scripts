import xbmcaddon
import xbmcgui
 
ADDON       = xbmcaddon.Addon()
LANGUAGE    = ADDON.getLocalizedString

def handleMenu(menu):
    list  = []

    for item in menu:
        list.append(item[0])

    param = xbmcgui.Dialog().contextmenu(list)

    if param < 0:
        return None

    return menu[param][1]

#build menu
isMovie   = xbmc.getCondVisibility("String.IsEqual(ListItem.DBTYPE,movie)")
isTVShow  = xbmc.getCondVisibility("String.IsEqual(ListItem.DBTYPE,tvshow)")
isEpisode = xbmc.getCondVisibility("String.IsEqual(ListItem.DBTYPE,episode)")
isMusic   = xbmc.getCondVisibility("String.IsEqual(ListItem.DBTYPE,musicvideo)")

options = []

options.append([LANGUAGE(32000), "SetFocus(90400)"])
if xbmc.getCondVisibility("System.HasAddon(script.extendedinfo)"):
    if isMovie:
        options.append([LANGUAGE(32001), "RunScript(script.extendedinfo,info=extendedinfo,dbid=%s,id=%s)" % (xbmc.getInfoLabel("ListItem.DBID"), xbmc.getInfoLabel("ListItem.Property(id)"))])
    elif isTVShow:
        options.append([LANGUAGE(32001), "RunScript(script.extendedinfo,info=extendedtvinfo,dbid=%s,id=%s)" % (xbmc.getInfoLabel("ListItem.DBID"), xbmc.getInfoLabel("ListItem.Property(id)"))])

if xbmc.getCondVisibility("System.HasAddon(plugin.program.super.favourites)"):
    if isMovie or isTVShow:
        options.append([LANGUAGE(32009), "RunScript(special://home/addons/plugin.program.super.favourites/menu_addtofaves.py)"])

if xbmc.getCondVisibility("System.HasAddon(script.simpleplaylists)"):
    if isMovie or isTVShow:
        options.append([LANGUAGE(32002), "RunPlugin(plugin://script.simpleplaylists/?mode=addCurrentUrl)"])

if xbmc.getCondVisibility("System.HasAddon(script.artwork.downloader)"):
    if isMovie:
        options.append([LANGUAGE(32003), "RunScript(script.artwork.downloader,mediatype=movie,dbid=%s)"          % xbmc.getInfoLabel("ListItem.DBID")])
        options.append([LANGUAGE(32004), "RunScript(script.artwork.downloader,mode=gui,mediatype=movie,dbid=%s)" % xbmc.getInfoLabel("ListItem.DBID")])
    elif isTVShow:
        options.append([LANGUAGE(32003), "RunScript(script.artwork.downloader,mediatype=tvshow,dbid=%s)"          % xbmc.getInfoLabel("ListItem.DBID")])
        options.append([LANGUAGE(32004), "RunScript(script.artwork.downloader,mode=gui,mediatype=tvshow,dbid=%s)" % xbmc.getInfoLabel("ListItem.DBID")])

if xbmc.getCondVisibility("System.HasAddon(script.ratingupdate)"):
    if isMovie or isTVShow:
        options.append([LANGUAGE(32005), "RunScript(script.ratingupdate,Single=Movie)"])

if xbmc.getCondVisibility('System.HasAddon(script.tvtunes) + String.IsEmpty(Window(movieinformation).Property("TvTunes_HideVideoInfoButton"))'):
    if isMovie or isTVShow or isMusic:
        options.append([LANGUAGE(32006), "RunScript(script.tvtunes,mode=solo)"])

if xbmc.getCondVisibility("System.HasAddon(script.cinemavision)"):
    if isMovie or isTVShow or isEpisode:
        options.append([LANGUAGE(32007), "SPECIALCASE1"]) #because it does 2 things

if xbmc.getCondVisibility("System.HasAddon(script.videoextras)"):
    if isMovie or isEpisode or isMusic:
        options.append([LANGUAGE(32008), "RunScript(script.videoextras,display,%s)" % (xbmc.getInfoLabel("ListItem.FilenameAndPath"))])
    elif isTVShow:
        options.append([LANGUAGE(32008), "RunScript(script.videoextras,display,%s)" % (xbmc.getInfoLabel("ListItem.Path"))])

action = handleMenu(options)

if action == 'SPECIALCASE1':
    xbmc.executebuiltin("Dialog.Close(movieinformation)")
    xbmc.executebuiltin("RunScript(script.cinemavision,experience)")
else:
    xbmc.executebuiltin('%s' % action)