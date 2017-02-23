#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Smart shortcuts feature
This feature is introduced to be able to provide quick-access shortcuts to specific sections of Kodi,
such as user created playlists and favourites and entry points of some 3th party addons such as Emby and Plex.
What it does is provide some Window properties about the shortcut.
It is most convenient used with the skin shortcuts script but can offcourse be used in any part of your skin.
The most important behaviour of the smart shortcuts feature is that is pulls images from the library path
so you can have content based backgrounds.
'''

from utils import get_content_path, log_msg, log_exception, ADDON_ID
from metadatautils import detect_plugin_content, KodiDb
import xbmc
import xbmcvfs
import xbmcaddon


class SmartShortCuts():
    '''Smart shortcuts listings'''
    exit = False
    all_nodes = {}
    toplevel_nodes = []
    build_busy = False

    def __init__(self, bgupdater):
        self.bgupdater = bgupdater

    def get_smartshortcuts_nodes(self):
        '''return all smartshortcuts paths for which an image should be generated'''
        nodes = []
        for value in self.all_nodes.itervalues():
            nodes += value
        return nodes

    def build_smartshortcuts(self):
        '''build all smart shortcuts nodes - only proceed if build is not already in process'''
        if self.exit or self.build_busy:
            return
        else:
            self.build_busy = True
            # build all smart shortcuts nodes
            self.emby_nodes()
            self.playlists_nodes()
            self.favourites_nodes()
            self.plex_nodes()
            # set all toplevel nodes in window prop for exchange with skinshortcuts
            self.bgupdater.set_winprop("all_smartshortcuts", repr(self.toplevel_nodes))
            self.build_busy = False

    def emby_nodes(self):
        '''build smart shortcuts for the emby addon'''
        if not self.all_nodes.get("emby"):
            nodes = []
            if xbmc.getCondVisibility("System.HasAddon(plugin.video.emby) + Skin.HasSetting(SmartShortcuts.emby)"):
                emby_property = self.bgupdater.win.getProperty("emby.nodes.total")
                if emby_property:
                    content_strings = ["", ".recent", ".inprogress", ".unwatched", ".recentepisodes",
                                       ".inprogressepisodes", ".nextepisodes", "recommended"]
                    nodes = []
                    total_nodes = int(emby_property)
                    for count in range(total_nodes):
                        # stop if shutdown requested in the meanwhile
                        if self.exit:
                            return
                        for content_string in content_strings:
                            key = "emby.nodes.%s%s" % (count, content_string)
                            item_path = self.bgupdater.win.getProperty(
                                "emby.nodes.%s%s.path" %
                                (count, content_string)).decode("utf-8")
                            mainlabel = self.bgupdater.win.getProperty("emby.nodes.%s.title" % (count)).decode("utf-8")
                            sublabel = self.bgupdater.win.getProperty(
                                "emby.nodes.%s%s.title" %
                                (count, content_string)).decode("utf-8")
                            label = u"%s: %s" % (mainlabel, sublabel)
                            if not content_string:
                                label = mainlabel
                            if item_path:
                                content = get_content_path(item_path)
                                nodes.append(("%s.image" % key, content, label))
                                if content_string == "":
                                    if "emby.nodes.%s" % count not in self.toplevel_nodes:
                                        self.toplevel_nodes.append("emby.nodes.%s" % count)
                                    self.create_smartshortcuts_submenu(
                                        "emby.nodes.%s" % count, "special://home/addons/plugin.video.emby/icon.png")
                log_msg("Generated smart shortcuts for emby nodes: %s" % nodes)
                self.all_nodes["emby"] = nodes

    def plex_nodes(self):
        '''build smart shortcuts listing for the (legacy) plex addon'''
        if not self.all_nodes.get("plex"):
            nodes = []
            if xbmc.getCondVisibility("System.HasAddon(plugin.video.plexbmc) + Skin.HasSetting(SmartShortcuts.plex)"):
                xbmc.executebuiltin('RunScript(plugin.video.plexbmc,amberskin)')
                # wait a few seconds for the initialization to be finished
                monitor = xbmc.Monitor()
                monitor.waitForAbort(5)
                del monitor

                # get the plex setting if there are subnodes
                plexaddon = xbmcaddon.Addon(id='plugin.video.plexbmc')
                secondary_menus = plexaddon.getSetting("secondary") == "true"
                del plexaddon

                content_strings = ["", ".ondeck", ".recent", ".unwatched"]
                total_nodes = 50
                for i in range(total_nodes):
                    if not self.bgupdater.win.getProperty("plexbmc.%s.title" % i) or self.exit:
                        break
                    for content_string in content_strings:
                        key = "plexbmc.%s%s" % (i, content_string)
                        label = self.bgupdater.win.getProperty("plexbmc.%s.title" % i).decode("utf-8")
                        media_type = self.bgupdater.win.getProperty("plexbmc.%s.type" % i).decode("utf-8")
                        if media_type == "movie":
                            media_type = "movies"
                        if secondary_menus:
                            item_path = self.bgupdater.win.getProperty("plexbmc.%s.all" % i).decode("utf-8")
                        else:
                            item_path = self.bgupdater.win.getProperty("plexbmc.%s.path" % i).decode("utf-8")
                        item_path = item_path.replace("VideoLibrary", "Videos")  # fix for krypton ?
                        alllink = item_path
                        alllink = alllink.replace("mode=1", "mode=0")
                        alllink = alllink.replace("mode=2", "mode=0")
                        if content_string == ".recent":
                            label += " - Recently Added"
                            if media_type == "show":
                                media_type = "episodes"
                            if secondary_menus:
                                item_path = self.bgupdater.win.getProperty(key).decode("utf-8")
                            else:
                                item_path = alllink.replace("/all", "/recentlyAdded")
                        elif content_string == ".ondeck":
                            label += " - On deck"
                            if media_type == "show":
                                media_type = "episodes"
                            if secondary_menus:
                                item_path = self.bgupdater.win.getProperty(key).decode("utf-8")
                            else:
                                item_path = alllink.replace("/all", "/onDeck")
                        elif content_string == ".unwatched":
                            if media_type == "show":
                                media_type = "episodes"
                            label += " - Unwatched"
                            item_path = alllink.replace("/all", "/unwatched")
                        elif content_string == "":
                            if media_type == "show":
                                media_type = "tvshows"
                            if key not in self.toplevel_nodes:
                                self.toplevel_nodes.append(key)
                            self.create_smartshortcuts_submenu("plexbmc.%s" % i,
                                                               "special://home/addons/plugin.video.plexbmc/icon.png")

                        # append media_type to path
                        if "&" in item_path:
                            item_path = item_path + "&media_type=" + media_type
                        else:
                            item_path = item_path + "?media_type=" + media_type
                        content = get_content_path(item_path)
                        nodes.append(("%s.image" % key, content, label))

                        # set smart shortcuts window props
                        self.bgupdater.set_winprop("%s.label" % key, label)
                        self.bgupdater.set_winprop("%s.title" % key, label)
                        self.bgupdater.set_winprop("%s.action" % key, item_path)
                        self.bgupdater.set_winprop("%s.path" % key, item_path)
                        self.bgupdater.set_winprop("%s.content" % key, content)
                        self.bgupdater.set_winprop("%s.type" % key, media_type)

                # add plex channels as entry
                # extract path from one of the nodes as a workaround because main plex
                # addon channels listing is in error
                if nodes:
                    item_path = self.bgupdater.win.getProperty("plexbmc.0.path").decode("utf-8")
                    if not item_path:
                        item_path = self.bgupdater.win.getProperty("plexbmc.0.all").decode("utf-8")
                    item_path = item_path.split("/library/")[0]
                    item_path = item_path + "/channels/all&mode=21"
                    item_path = item_path + ", return)"
                    key = "plexbmc.channels"
                    label = "Channels"
                    content = get_content_path(item_path)
                    nodes.append(("%s.image" % key, content, label))
                    self.bgupdater.set_winprop("%s.label" % key, label)
                    self.bgupdater.set_winprop("%s.title" % key, label)
                    self.bgupdater.set_winprop("%s.action" % key, item_path)
                    self.bgupdater.set_winprop("%s.path" % key, item_path)
                    self.bgupdater.set_winprop("%s.content" % key, content)
                    self.bgupdater.set_winprop("%s.type" % key, "episodes")
                    if key not in self.toplevel_nodes:
                        self.toplevel_nodes.append(key)
                self.all_nodes["plex"] = nodes

    def playlists_nodes(self):
        '''build smart shortcuts listing for playlists'''
        nodes = []
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.playlists)"):
            # build node listing
            count = 0
            import xml.etree.ElementTree as xmltree
            paths = [('special://videoplaylists/', 'Videos'), ('special://musicplaylists/', 'Music')]
            for playlistpath in paths:
                if xbmcvfs.exists(playlistpath[0]):
                    media_array = KodiDb().files(playlistpath[0])
                    for item in media_array:
                        try:
                            label = ""
                            if item["file"].endswith(".xsp") and "Emby" not in item["file"]:
                                playlist = item["file"]
                                contents = xbmcvfs.File(playlist, 'r')
                                contents_data = contents.read()
                                contents.close()
                                xmldata = xmltree.fromstring(contents_data)
                                media_type = "unknown"
                                label = item["label"]
                                for line in xmldata.getiterator():
                                    if line.tag == "smartplaylist":
                                        media_type = line.attrib['type']
                                    if line.tag == "name":
                                        label = line.text
                                key = "playlist.%s" % count
                                item_path = "ActivateWindow(%s,%s,return)" % (playlistpath[1], playlist)
                                self.bgupdater.set_winprop("%s.label" % key, label)
                                self.bgupdater.set_winprop("%s.title" % key, label)
                                self.bgupdater.set_winprop("%s.action" % key, item_path)
                                self.bgupdater.set_winprop("%s.path" % key, item_path)
                                self.bgupdater.set_winprop("%s.content" % key, playlist)
                                self.bgupdater.set_winprop("%s.type" % key, media_type)
                                nodes.append(("%s.image" % key, playlist, label))
                                if key not in self.toplevel_nodes:
                                    self.toplevel_nodes.append(key)
                                count += 1
                        except Exception:
                            log_msg("Error while processing smart shortcuts for playlist %s  --> "
                                    "This file seems to be corrupted, please remove it from your system "
                                    "to prevent any further errors." % item["file"], xbmc.LOGWARNING)
            self.all_nodes["playlists"] = nodes

    def favourites_nodes(self):
        '''build smart shortcuts for favourites'''
        if xbmc.getCondVisibility("Skin.HasSetting(SmartShortcuts.favorites)"):
            # build node listing
            nodes = []
            favs = KodiDb().favourites()
            for count, fav in enumerate(favs):
                if fav["type"] == "window":
                    content = fav["windowparameter"]
                    # check if this is a valid path with content
                    if ("script://" not in content.lower() and
                            "mode=9" not in content.lower() and
                            "search" not in content.lower() and
                            "play" not in content.lower()):
                        item_path = "ActivateWindow(%s,%s,return)" % (fav["window"], content)
                        if "&" in content and "?" in content and "=" in content and not content.endswith("/"):
                            content += "&widget=true"
                        media_type = detect_plugin_content(content)
                        if media_type:
                            key = "favorite.%s" % count
                            self.bgupdater.set_winprop("%s.label" % key, fav["label"])
                            self.bgupdater.set_winprop("%s.title" % key, fav["label"])
                            self.bgupdater.set_winprop("%s.action" % key, item_path)
                            self.bgupdater.set_winprop("%s.path" % key, item_path)
                            self.bgupdater.set_winprop("%s.content" % key, content)
                            self.bgupdater.set_winprop("%s.type" % key, media_type)
                            if key not in self.toplevel_nodes:
                                self.toplevel_nodes.append(key)
                            nodes.append(("%s.image" % key, content, fav["label"]))
            self.all_nodes["favourites"] = nodes

    @staticmethod
    def create_smartshortcuts_submenu(win_prop, icon_image):
        '''helper to create a skinshortcuts submenu for the top level smart shortcut node'''
        try:
            if xbmcvfs.exists("special://skin/shortcuts/"):
                shortcutsfile = "special://home/addons/script.skinshortcuts/resources/shortcuts/"\
                    "info-window-home-property-%s-title.DATA.xml" % win_prop.replace(".", "-")
                templatefile = "special://home/addons/%s/resources/smartshortcuts/smartshortcuts-submenu-template.xml" \
                    % (ADDON_ID)
                # read template file
                templatefile = xbmcvfs.File(templatefile)
                data = templatefile.read()
                templatefile.close()
                # write shortcuts file
                shortcutsfile = xbmcvfs.File(shortcutsfile, "w")
                data = data.replace("WINDOWPROP", win_prop)
                data = data.replace("ICONIMAGE", icon_image)
                shortcutsfile.write(data)
                shortcutsfile.close()
        except Exception as exc:
            log_exception(__name__, exc)
