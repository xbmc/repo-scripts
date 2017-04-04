#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    skinshortcuts.py
    Methods to connect skinhelper to skinshortcuts for smartshortcuts, widgets and backgrounds
'''

from utils import kodi_json, log_msg, urlencode, ADDON_ID
from metadatautils import detect_plugin_content
import xbmc
import xbmcvfs
import xbmcplugin
import xbmcgui
import xbmcaddon
import sys

# extendedinfo has some login-required widgets, these must not be probed without login details
EXTINFO_CREDS = False
if xbmc.getCondVisibility("System.Hasaddon(script.extendedinfo)"):
    exinfoaddon = xbmcaddon.Addon(id="script.extendedinfo")
    if exinfoaddon.getSetting("tmdb_username") and exinfoaddon.getSetting("tmdb_password"):
        EXTINFO_CREDS = True
    del exinfoaddon


def add_directoryitem(entry, is_folder=True, widget=None, widget2=None):
    '''helper to create a listitem for our smartshortcut node'''
    label = "$INFO[Window(Home).Property(%s.title)]" % entry
    path = "$INFO[Window(Home).Property(%s.path)]" % entry
    content = "$INFO[Window(Home).Property(%s.content)]" % entry
    image = "$INFO[Window(Home).Property(%s.image)]" % entry
    mediatype = "$INFO[Window(Home).Property(%s.type)]" % entry

    if is_folder:
        path = sys.argv[0] + "?action=SMARTSHORTCUTS&path=" + entry
        listitem = xbmcgui.ListItem(label, path=path)
        listitem.setIconImage("DefaultFolder.png")
    else:
        listitem = xbmcgui.ListItem(label, path=path)
        props = {}
        props["list"] = content
        if not xbmc.getInfoLabel(mediatype):
            mediatype = "media"
        props["type"] = mediatype
        props["background"] = "$INFO[Window(Home).Property(%s.image)]" % entry
        props["backgroundName"] = "$INFO[Window(Home).Property(%s.title)]" % entry
        listitem.setInfo(type="Video", infoLabels={"Title": "smartshortcut"})
        listitem.setThumbnailImage(image)
        listitem.setIconImage("special://home/addons/script.skin.helper.service/fanart.jpg")

        if widget:
            widget_type = "$INFO[Window(Home).Property(%s.type)]" % widget
            if not xbmc.getInfoLabel(mediatype):
                widget_type = mediatype
            if widget_type in ["albums", "artists", "songs"]:
                widget_target = "music"
            else:
                widget_target = "video"
            props["widget"] = "addon"
            props["widgetName"] = "$INFO[Window(Home).Property(%s.title)]" % widget
            props["widgetType"] = widget_type
            props["widgetTarget"] = widget_target
            props["widgetPath"] = "$INFO[Window(Home).Property(%s.content)]" % widget
            if "plugin:" in xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" % widget):
                props["widgetPath"] = props["widgetPath"] + \
                    "&reload=$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"

        if widget2:
            widget_type = "$INFO[Window(Home).Property(%s.type)]" % widget2
            if not xbmc.getInfoLabel(mediatype):
                widget_type = mediatype
            if widget_type == "albums" or widget_type == "artists" or widget_type == "songs":
                widget_target = "music"
            else:
                widget_target = "video"
            props["widget.1"] = "addon"
            props["widgetName.1"] = "$INFO[Window(Home).Property(%s.title)]" % widget2
            props["widgetType.1"] = widget_type
            props["widgetTarget.1"] = widget_target
            props["widgetPath.1"] = "$INFO[Window(Home).Property(%s.content)]" % widget2
            if "plugin:" in xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" % widget2):
                props["widgetPath.1"] = props["widgetPath.1"] + \
                    "&reload=$INFO[Window(Home).Property(widgetreload)]$INFO[Window(Home).Property(widgetreload2)]"

        listitem.setInfo(type="Video", infoLabels={"mpaa": repr(props)})

    listitem.setArt({"fanart": image})
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=path, listitem=listitem, isFolder=is_folder)


def smartshortcuts_sublevel(entry):
    '''get subnodes for smartshortcut node'''
    if "emby" in entry:
        content_strings = [
            "",
            ".recent",
            ".inprogress",
            ".unwatched",
            ".recentepisodes",
            ".inprogressepisodes",
            ".nextepisodes",
            ".recommended"]
    elif "plex" in entry:
        content_strings = ["", ".ondeck", ".recent", ".unwatched"]
    elif "netflix.generic.suggestions" in entry:
        content_strings = ["", ".0", ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9", ".10"]
    elif "netflix" in entry:
        content_strings = [
            "",
            ".mylist",
            ".recent",
            ".inprogress",
            ".suggestions",
            ".genres",
            ".recommended",
            ".trending"]

    for content_string in content_strings:
        key = entry + content_string
        widget = None
        widget2 = None
        if content_string == "":
            # this is the main item so define our widgets
            mediatype = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.type)]" % entry)
            if "plex" in entry:
                widget = entry + ".ondeck"
                widget2 = entry + ".recent"
            elif mediatype == "movies" or mediatype == "movie" or mediatype == "artist" or "netflix" in entry:
                widget = entry + ".recent"
                widget2 = entry + ".inprogress"
            elif mediatype == "tvshows" and "emby" in entry:
                widget = entry + ".nextepisodes"
                widget2 = entry + ".recent"
            elif (mediatype == "homevideos" or mediatype == "photos") and "emby" in entry:
                widget = entry + ".recent"
                widget2 = entry + ".recommended"
            else:
                widget = entry
        if xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.path)]" % key):
            add_directoryitem(key, False, widget, widget2)


def get_smartshortcuts(sublevel=None):
    '''called from skinshortcuts to retrieve listing of all smart shortcuts'''
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    if sublevel:
        smartshortcuts_sublevel(sublevel)
    else:

        all_smartshortcuts = xbmc.getInfoLabel("Window(Home).Property(all_smartshortcuts)")
        win = xbmcgui.Window(10000)
        all_smartshortcuts = win.getProperty("all_smartshortcuts")

        if all_smartshortcuts:
            for node in eval(all_smartshortcuts):
                if "emby" in node or "plex" in node or "netflix" in node:
                    # create main folder entry
                    add_directoryitem(node, True)
                else:
                    # create final listitem entry (playlist, favorites)
                    add_directoryitem(node, False, node)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def smartshortcuts_widgets():
    '''get the widget nods for smartshortcuts'''
    widgets = []
    all_smartshortcuts = xbmc.getInfoLabel("Window(Home).Property(all_smartshortcuts)")
    if all_smartshortcuts:
        for node in eval(all_smartshortcuts):
            label = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.title)]" % node)
            if "emby" in node or "plex" in node or "netflix" in node:
                # create main folder entry
                path = sys.argv[0] + "?action=SMARTSHORTCUTS&path=%s" % node
                widgets.append([label, path, "folder", True])
            else:
                content = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.content)]" % node)
                media_type = xbmc.getInfoLabel("$INFO[Window(Home).Property(%s.type)]" % node)
                widgets.append([label, content, media_type])
    return widgets


def item_filter_mapping():
    '''map label to each filtertype'''
    mappings = []
    mappings.append(("scriptwidgets", xbmc.getInfoLabel("System.AddonTitle(script.skin.helper.widgets)")))
    mappings.append(("librarydataprovider", xbmc.getInfoLabel("System.AddonTitle(service.library.data.provider)")))
    mappings.append(("extendedinfo", xbmc.getInfoLabel("System.AddonTitle(script.extendedinfo)")))
    mappings.append(("smartshortcuts", "Smart Shortcuts"))
    mappings.append(("skinplaylists", "Playlists"))
    mappings.append(("favourites", "Favourites"))
    mappings.append(("static", "Static widgets"))
    return mappings


def get_item_filter_label(filterkey):
    '''gets the label for the fiven filterkey'''
    label = ""
    for item in item_filter_mapping():
        if item[0] == filterkey:
            label = item[1]
    return label


def get_widgets(item_filter="", sublevel=""):
    '''get all widgets provider by several plugins and listings'''
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    if item_filter:
        # skinner has provided a comma seperated list of widgetitems to include in the listing
        item_filters = item_filter.split(",")
    else:
        # no list provided by the skinner so just show all available widgets
        item_filters = [mapping[0] for mapping in item_filter_mapping()]

    # build the widget listiing...
    for item_filter in item_filters:
        if item_filter == "smartshortcuts":
            widgets = smartshortcuts_widgets()
        elif item_filter == "skinplaylists":
            widgets = playlists_widgets()
        elif item_filter == "favourites":
            widgets = favourites_widgets()
        elif item_filter == "static":
            widgets = static_widgets()
        elif sublevel:
            widgets = plugin_widgetlisting(item_filters[0], sublevel)
        elif item_filter == "scriptwidgets":
            widgets = plugin_widgetlisting("script.skin.helper.widgets")
        elif item_filter == "librarydataprovider":
            widgets = plugin_widgetlisting("service.library.data.provider")
        elif item_filter == "extendedinfo":
            widgets = plugin_widgetlisting("script.extendedinfo")
        else:
            # unknown filter
            continue

        if not sublevel and len(item_filters) > 1 and item_filter != "static":
            # only show main listing for this category...
            if widgets:
                label = get_item_filter_label(item_filter)
                listitem = xbmcgui.ListItem(label, iconImage="DefaultFolder.png")
                url = "plugin://script.skin.helper.service?action=widgets&path=%s" % item_filter
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=True)
        else:
            # show widgets for the selected filter...
            for widget in widgets:
                media_type = widget[2]
                if media_type == "folder":
                    is_folder = True
                elif len(widget) > 3:
                    is_folder = widget[3]
                else:
                    is_folder = False
                if media_type == "movies":
                    image = "DefaultMovies.png"
                    media_library = "Videos"
                    target = "video"
                elif media_type == "pvr":
                    media_library = "TvChannels"
                    image = "DefaultTVShows.png"
                    target = "pvr"
                elif media_type == "tvshows":
                    image = "DefaultTVShows.png"
                    media_library = "Videos"
                    target = "video"
                elif media_type == "episodes":
                    image = "DefaultTVShows.png"
                    media_library = "Videos"
                    target = "video"
                elif media_type == "albums":
                    image = "DefaultMusicAlbums.png"
                    media_library = "Music"
                    target = "music"
                elif media_type == "songs":
                    image = "DefaultMusicSongs.png"
                    media_library = "Music"
                    target = "music"
                elif media_type == "artists":
                    image = "DefaultMusicArtists.png"
                    media_library = "Music"
                    target = "music"
                elif media_type == "musicvideos":
                    image = "DefaultMusicVideos.png"
                else:
                    image = "Defaultaddon.png"
                    media_library = "Videos"
                    target = "video"

                if is_folder:
                    listitem = xbmcgui.ListItem(widget[0])
                    listitem.setIconImage("DefaultFolder.png")
                    xbmcplugin.addDirectoryItem(
                        handle=int(sys.argv[1]),
                        url=widget[1],
                        listitem=listitem, isFolder=True)
                else:
                    widgetpath = "ActivateWindow(%s,%s,return)" % (media_library, widget[1].split("&")[0])
                    listitem = xbmcgui.ListItem(widget[0], path=widgetpath)
                    props = {}
                    props["list"] = widget[1]
                    props["type"] = widget[2]
                    props["background"] = image
                    props["backgroundName"] = ""
                    props["widgetPath"] = widget[1]
                    props["widgetTarget"] = target
                    props["widgetName"] = widget[0]
                    props["widget"] = item_filter
                    listitem.setInfo(type="Video", infoLabels={"Title": "smartshortcut"})
                    listitem.setThumbnailImage(image)
                    listitem.setArt({"fanart": image})
                    # we use the mpaa property to pass all properties to skinshortcuts
                    listitem.setInfo(type="Video", infoLabels={"mpaa": repr(props)})
                    xbmcplugin.addDirectoryItem(
                        handle=int(
                            sys.argv[1]),
                        url=widgetpath,
                        listitem=listitem,
                        isFolder=False)

    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def get_skinhelper_backgrounds():
    '''retrieve listing of all backgrounds as provided by skinhelper backgrounds addon'''
    result = []
    backgrounds = xbmc.getInfoLabel("Window(Home).Property(SkinHelper.AllBackgrounds)")
    if backgrounds:
        backgrounds = eval(backgrounds)
        win = xbmcgui.Window(10000)
        for key, value in backgrounds:
            label = value
            image = "$INFO[Window(Home).Property(%s)]" % key
            if win.getProperty(key):
                result.append((label, image))
            # also check if wall images exists for this item
            wall_props = [".Wall", ".Poster.Wall", ".Wall.BW", ".Poster.Wall.BW"]
            for wall_prop in wall_props:
                image = "$INFO[Window(Home).Property(%s%s)]" % (key, wall_prop)
                if win.getProperty("%s%s" % (key, wall_prop)):
                    if ".Poster" in wall_prop:
                        newlabel = "%s: %s" % (xbmc.getInfoLabel("$ADDON[script.skin.helper.backgrounds 32030]"), label)
                    else:
                        newlabel = "%s: %s" % (xbmc.getInfoLabel("$ADDON[script.skin.helper.backgrounds 32029]"), label)
                    if ".BW" in wall_prop:
                        newlabel = "%s (%s)" % (newlabel, xbmc.getInfoLabel(
                            "$ADDON[script.skin.helper.backgrounds 32031]"))
                    result.append((newlabel, image))
                else:
                    break
        del win
    return result


def get_backgrounds():
    '''called from skinshortcuts to retrieve listing of all backgrounds'''
    xbmcplugin.setContent(int(sys.argv[1]), 'files')
    for label, image in get_skinhelper_backgrounds():
        listitem = xbmcgui.ListItem(label, path=image)
        listitem.setArt({"fanart": image})
        listitem.setThumbnailImage(image)
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=image, listitem=listitem, isFolder=False)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))


def playlists_widgets():
    '''skin provided playlists'''
    widgets = []
    import xml.etree.ElementTree as xmltree
    for playlist_path in ["special://skin/playlists/",
                          "special://skin/extras/widgetplaylists/", "special://skin/extras/playlists/"]:
        if xbmcvfs.exists(playlist_path):
            log_msg("skinshortcuts widgets processing: %s" % playlist_path)
            media_array = kodi_json('Files.GetDirectory', {"directory": playlist_path, "media": "files"})
            for item in media_array:
                if item["file"].endswith(".xsp"):
                    playlist = item["file"]
                    contents = xbmcvfs.File(item["file"], 'r')
                    contents_data = contents.read().decode('utf-8')
                    contents.close()
                    xmldata = xmltree.fromstring(contents_data.encode('utf-8'))
                    media_type = ""
                    label = item["label"]
                    for line in xmldata.getiterator():
                        if line.tag == "smartplaylist":
                            media_type = line.attrib['type']
                        if line.tag == "name":
                            label = line.text
                    try:
                        languageid = int(label)
                        label = xbmc.getLocalizedString(languageid)
                    except Exception:
                        pass
                    if not media_type:
                        media_type = detect_plugin_content(playlist)
                    widgets.append([label, playlist, media_type])
    return widgets


def plugin_widgetlisting(pluginpath, sublevel=""):
    '''get all nodes in a plugin listing'''
    widgets = []
    if sublevel:
        media_array = kodi_json('Files.GetDirectory', {"directory": pluginpath, "media": "files"})
    else:
        if not xbmc.getCondVisibility("System.HasAddon(%s)" % pluginpath):
            return []
        media_array = kodi_json('Files.GetDirectory', {"directory": "plugin://%s" % pluginpath, "media": "files"})
    for item in media_array:
        log_msg("skinshortcuts widgets processing: %s" % (item["file"]))
        content = item["file"]
        label = item["label"]
        # extendedinfo has some login-required widgets, skip those
        if ("script.extendedinfo" in pluginpath and not EXTINFO_CREDS and (
                "info=starred" in content or "info=rated" in content or "info=account" in content)):
            continue
        if item.get("filetype", "") == "file":
            continue
        media_type = detect_plugin_content(item["file"])
        if media_type == "empty":
            continue
        if media_type == "folder":
            content = "plugin://script.skin.helper.service?action=widgets&path=%s&sublevel=%s" % (
                urlencode(item["file"]), label)
        # add reload param for skinhelper and libraryprovider widgets
        if "reload=" not in content and (
                "script.skin.helper" in pluginpath or pluginpath == "service.library.data.provider"):
            if "albums" in content or "songs" in content or "artists" in content:
                reloadstr = "&reload=$INFO[Window(Home).Property(widgetreloadmusic)]"
            elif ("pvr" in content or "media" in content or "favourite" in content) and "progress" not in content:
                reloadstr = "&reload=$INFO[Window(Home).Property(widgetreload)]"\
                    "$INFO[Window(Home).Property(widgetreload2)]"
            else:
                reloadstr = "&reload=$INFO[Window(Home).Property(widgetreload)]"
            content = content + reloadstr
        content = content.replace("&limit=100", "&limit=25")
        widgets.append([label, content, media_type])
        if pluginpath == "script.extendedinfo" and not sublevel:
            # some additional entrypoints for extendedinfo...
            widgets += extendedinfo_youtube_widgets()
    return widgets


def favourites_widgets():
    '''widgets from favourites'''
    favourites = kodi_json('Favourites.GetFavourites',
                           {"type": None, "properties": ["path", "thumbnail", "window", "windowparameter"]})
    widgets = []
    if favourites:
        for fav in favourites:
            if "windowparameter" in fav:
                content = fav["windowparameter"]
                # check if this is a valid path with content
                if ("script://" not in content.lower() and "mode=9" not in content.lower() and
                        "search" not in content.lower() and "play" not in content.lower()):
                    label = fav["title"]
                    log_msg("skinshortcuts widgets processing favourite: %s" % label)
                    mediatype = detect_plugin_content(content)
                    if mediatype and mediatype != "empty":
                        widgets.append([label, content, mediatype])
    return widgets


def static_widgets():
    '''static widget nodes which are hardcoded in a skin'''
    widgets = []
    addon = xbmcaddon.Addon(ADDON_ID)
    widgets.append([xbmc.getLocalizedString(8), "$INCLUDE[WeatherWidget]", "static"])
    widgets.append([xbmc.getLocalizedString(130), "$INCLUDE[SystemInfoWidget]", "static"])
    widgets.append([addon.getLocalizedString(32025), "$INCLUDE[skinshortcuts-submenu]", "static"])
    if xbmc.getCondVisibility("System.Hasaddon(script.games.rom.collection.browser)"):
        widgets.append([addon.getLocalizedString(32026), "$INCLUDE[RCBWidget]", "static"])
    del addon
    return widgets


def extendedinfo_youtube_widgets():
    '''the youtube nodes from extendedinfo addon'''
    # some additional entrypoints for extendedinfo...
    widgets = []
    entrypoints = [
        "plugin://script.extendedinfo?info=youtubeusersearch&&id=Eurogamer",
        "plugin://script.extendedinfo?info=youtubeusersearch&&id=Engadget",
        "plugin://script.extendedinfo?info=youtubeusersearch&&id=MobileTechReview"]
    for entry in entrypoints:
        content = entry
        label = entry.split("id=")[1]
        widgets.append([label, content, "episodes"])
    return widgets


def set_skinshortcuts_property(property_name="", value="", label=""):
    '''set custom property in skinshortcuts menu editor'''
    if value or label:
        wait_for_skinshortcuts_window()
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%s)" % property_name.encode("utf-8"))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % value.encode("utf-8"))
        xbmc.executebuiltin("SendClick(404)")
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%s.name)" % property_name.encode("utf-8"))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % label.encode("utf-8"))
        xbmc.executebuiltin("SendClick(404)")
        xbmc.sleep(250)
        xbmc.executebuiltin("SetProperty(customProperty,%sName)" % property_name.encode("utf-8"))
        xbmc.executebuiltin("SetProperty(customValue,%s)" % label.encode("utf-8"))
        xbmc.executebuiltin("SendClick(404)")


def wait_for_skinshortcuts_window():
    '''wait untill skinshortcuts is active window (because of any animations that may have been applied)'''
    for i in range(40):
        if not (xbmc.getCondVisibility(
                "Window.IsActive(DialogSelect.xml) | "
                "Window.IsActive(script-skin_helper_service-ColorPicker.xml) | "
                "Window.IsActive(DialogKeyboard.xml)")):
            break
        else:
            xbmc.sleep(100)
