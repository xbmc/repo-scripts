#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    plugin_content.py
    Hidden plugin entry point providing some helper features
'''

import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
from simplecache import SimpleCache
from utils import log_msg, KODI_VERSION, log_exception, urlencode
from metadatautils import KodiDb, Tmdb, get_clean_image, process_method_on_list
import urlparse
import sys
import os


class PluginContent:
    '''Hidden plugin entry point providing some helper features'''
    params = {}
    win = None

    def __init__(self):
        self.cache = SimpleCache()
        self.kodi_db = KodiDb()
        self.win = xbmcgui.Window(10000)
        try:
            self.params = dict(urlparse.parse_qsl(sys.argv[2].replace('?', '').lower().decode("utf-8")))
            log_msg("plugin called with parameters: %s" % self.params)
            self.main()
        except Exception as exc:
            log_exception(__name__, exc)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

        # cleanup when done processing
        self.close()

    def close(self):
        '''Cleanup Kodi Cpython instances'''
        self.cache.close()
        del self.win

    def main(self):
        '''main action, load correct function'''
        action = self.params.get("action", "")
        if self.win.getProperty("SkinHelperShutdownRequested"):
            # do not proceed if kodi wants to exit
            log_msg("%s --> Not forfilling request: Kodi is exiting" % __name__, xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))
        else:
            try:
                if hasattr(self.__class__, action):
                    # launch module for action provided by this plugin
                    getattr(self, action)()
                else:
                    # legacy (widget) path called !!!
                    self.load_widget()
            except Exception as exc:
                log_exception(__name__, exc)

    def load_widget(self):
        '''legacy entrypoint called (widgets are moved to seperate addon), start redirect...'''
        action = self.params.get("action", "")
        newaddon = "script.skin.helper.widgets"
        log_msg("Deprecated method: %s. Please reassign your widgets to get rid of this message. -"
                "This automatic redirect will be removed in the future" % (action), xbmc.LOGWARNING)
        paramstring = ""
        for key, value in self.params.iteritems():
            paramstring += ",%s=%s" % (key, value)
        if xbmc.getCondVisibility("System.HasAddon(%s)" % newaddon):
            # TEMP !!! for backwards compatability reasons only - to be removed in the near future!!
            import imp
            addon = xbmcaddon.Addon(newaddon)
            addon_path = addon.getAddonInfo('path').decode("utf-8")
            imp.load_source('plugin', os.path.join(addon_path, "plugin.py"))
            from plugin import main
            main.Main()
            del addon
        else:
            # trigger install of the addon
            if KODI_VERSION > 16:
                xbmc.executebuiltin("InstallAddon(%s)" % newaddon)
            else:
                xbmc.executebuiltin("RunPlugin(plugin://%s)" % newaddon)

    def playchannel(self):
        '''play channel from widget helper'''
        params = {"item": {"channelid": int(self.params["channelid"])}}
        self.kodi_db.set_json("Player.Open", params)

    def playrecording(self):
        '''retrieve the recording and play to get resume working'''
        recording = self.kodi_db.recording(self.params["recordingid"])
        params = {"item": {"recordingid": recording["recordingid"]}}
        self.kodi_db.set_json("Player.Open", params)
        # manually seek because passing resume to the player json cmd doesn't seem to work
        if recording["resume"].get("position"):
            for i in range(50):
                if xbmc.getCondVisibility("Player.HasVideo"):
                    break
                xbmc.sleep(50)
            xbmc.Player().seekTime(recording["resume"].get("position"))

    def launch(self):
        '''launch any builtin action using a plugin listitem'''
        if "runscript" in self.params["path"]:
            self.params["path"] = self.params["path"].replace("?", ",")
        xbmc.executebuiltin(self.params["path"])

    def playalbum(self):
        '''helper to play an entire album'''
        xbmc.executeJSONRPC(
            '{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' %
            int(self.params["albumid"]))

    def smartshortcuts(self):
        '''called from skinshortcuts to retrieve listing of all smart shortcuts'''
        import skinshortcuts
        skinshortcuts.get_smartshortcuts(self.params.get("path", ""))

    @staticmethod
    def backgrounds():
        '''called from skinshortcuts to retrieve listing of all backgrounds'''
        import skinshortcuts
        skinshortcuts.get_backgrounds()

    def widgets(self):
        '''called from skinshortcuts to retrieve listing of all widgetss'''
        import skinshortcuts
        skinshortcuts.get_widgets(self.params.get("path", ""), self.params.get("sublevel", ""))

    def resourceimages(self):
        '''retrieve listing of specific resource addon images'''
        from resourceaddons import get_resourceimages
        addontype = self.params.get("addontype", "")
        for item in get_resourceimages(addontype, True):
            listitem = xbmcgui.ListItem(item[0], label2=item[2], path=item[1], iconImage=item[3])
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),
                                        url=item[1], listitem=listitem, isFolder=False)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def extrafanart(self):
        '''helper to display extrafanart in multiimage control in the skin'''
        fanarts = eval(self.params["fanarts"])
        # process extrafanarts
        for item in fanarts:
            listitem = xbmcgui.ListItem(item, path=item)
            listitem.setProperty('mimetype', 'image/jpeg')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=item, listitem=listitem)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def genrebackground(self):
        '''helper to display images for a specific genre in multiimage control in the skin'''
        genre = self.params.get("genre").split(".")[0]
        arttype = self.params.get("arttype", "fanart")
        randomize = self.params.get("random", "false") == "true"
        mediatype = self.params.get("mediatype", "movies")
        if genre and genre != "..":
            filters = [{"operator": "is", "field": "genre", "value": genre}]
            if randomize:
                sort = {"method": "random", "order": "descending"}
            else:
                sort = {"method": "sorttitle", "order": "ascending"}
            items = getattr(self.kodi_db, mediatype)(
                sort=sort,
                filters=filters, limits=(0, 50))
            for item in items:
                image = get_clean_image(item["art"].get(arttype, ""))
                if image:
                    image = get_clean_image(item["art"][arttype])
                    listitem = xbmcgui.ListItem(image, path=image)
                    listitem.setProperty('mimetype', 'image/jpeg')
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=image, listitem=listitem)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def getcastmedia(self):
        '''helper to display get all media for a specific actor'''
        name = self.params.get("name")
        if name:
            all_items = self.kodi_db.castmedia(name)
            all_items = process_method_on_list(self.kodi_db.prepare_listitem, all_items)
            all_items = process_method_on_list(self.kodi_db.create_listitem, all_items)
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), all_items, len(all_items))
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def getcast(self):
        '''helper to get all cast for a given media item'''
        db_id = None
        all_cast = []
        all_cast_names = list()
        cache_str = ""
        download_thumbs = self.params.get("downloadthumbs", "") == "true"
        extended_cast_action = self.params.get("castaction", "") == "extendedinfo"
        tmdb = Tmdb()
        movie = self.params.get("movie")
        tvshow = self.params.get("tvshow")
        episode = self.params.get("episode")
        movieset = self.params.get("movieset")

        try:  # try to parse db_id
            if movieset:
                cache_str = "movieset.castcache-%s-%s" % (self.params["movieset"], download_thumbs)
                db_id = int(movieset)
            elif tvshow:
                cache_str = "tvshow.castcache-%s-%s" % (self.params["tvshow"], download_thumbs)
                db_id = int(tvshow)
            elif movie:
                cache_str = "movie.castcache-%s-%s" % (self.params["movie"], download_thumbs)
                db_id = int(movie)
            elif episode:
                cache_str = "episode.castcache-%s-%s" % (self.params["episode"], download_thumbs)
                db_id = int(episode)
        except Exception:
            pass

        cachedata = self.cache.get(cache_str)
        if cachedata:
            # get data from cache
            all_cast = cachedata
        else:
            # retrieve data from json api...
            if movie and db_id:
                all_cast = self.kodi_db.movie(db_id)["cast"]
            elif movie and not db_id:
                filters = [{"operator": "is", "field": "title", "value": movie}]
                result = self.kodi_db.movies(filters=filters)
                all_cast = result[0]["cast"] if result else []
            elif tvshow and db_id:
                all_cast = self.kodi_db.tvshow(db_id)["cast"]
            elif tvshow and not db_id:
                filters = [{"operator": "is", "field": "title", "value": tvshow}]
                result = self.kodi_db.tvshows(filters=filters)
                all_cast = result[0]["cast"] if result else []
            elif episode and db_id:
                all_cast = self.kodi_db.episode(db_id)["cast"]
            elif episode and not db_id:
                filters = [{"operator": "is", "field": "title", "value": episode}]
                result = self.kodi_db.episodes(filters=filters)
                all_cast = result[0]["cast"] if result else []
            elif movieset:
                if not db_id:
                    for item in self.kodi_db.moviesets():
                        if item["title"].lower() == movieset.lower():
                            db_id = item["setid"]
                if db_id:
                    json_result = self.kodi_db.movieset(db_id, include_set_movies_fields=["cast"])
                    if "movies" in json_result:
                        for movie in json_result['movies']:
                            all_cast += movie['cast']

            # optional: download missing actor thumbs
            if all_cast and download_thumbs:
                for cast in all_cast:
                    if cast.get("thumbnail"):
                        cast["thumbnail"] = get_clean_image(cast.get("thumbnail"))
                    if not cast.get("thumbnail"):
                        artwork = tmdb.get_actor(cast["name"])
                        cast["thumbnail"] = artwork.get("thumb", "")
            # lookup tmdb if item is requested that is not in local db
            if not all_cast:
                tmdbdetails = {}
                if movie and not db_id:
                    tmdbdetails = tmdb.search_movie(movie)
                elif tvshow and not db_id:
                    tmdbdetails = tmdb.search_tvshow(tvshow)
                if tmdbdetails.get("cast"):
                    all_cast = tmdbdetails["cast"]
            # save to cache
            self.cache.set(cache_str, all_cast)

        # process listing with the results...
        for cast in all_cast:
            if cast.get("name") not in all_cast_names:
                liz = xbmcgui.ListItem(label=cast.get("name"), label2=cast.get("role"),
                                       iconImage=cast.get("thumbnail"))
                if extended_cast_action:
                    url = "RunScript(script.extendedinfo,info=extendedactorinfo,name=%s)" % cast.get("name")
                    url = "plugin://script.skin.helper.service/?action=launch&path=%s" % url
                    is_folder = False
                else:
                    url = "RunScript(script.skin.helper.service,action=getcastmedia,name=%s)" % cast.get("name")
                    url = "plugin://script.skin.helper.service/?action=launch&path=%s" % urlencode(url)
                    is_folder = False
                all_cast_names.append(cast.get("name"))
                liz.setThumbnailImage(cast.get("thumbnail"))
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=liz, isFolder=is_folder)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))

    @staticmethod
    def alphabet():
        '''display an alphabet scrollbar in listings'''
        all_letters = []
        if xbmc.getInfoLabel("Container.NumItems"):
            for i in range(int(xbmc.getInfoLabel("Container.NumItems"))):
                all_letters.append(xbmc.getInfoLabel("Listitem(%s).SortLetter" % i).upper())
            start_number = ""
            for number in ["2", "3", "4", "5", "6", "7", "8", "9"]:
                if number in all_letters:
                    start_number = number
                    break
            for letter in [start_number, "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L",
                           "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]:
                if letter == start_number:
                    label = "#"
                else:
                    label = letter
                listitem = xbmcgui.ListItem(label=label)
                if letter not in all_letters:
                    lipath = "noop"
                    listitem.setProperty("NotAvailable", "true")
                else:
                    lipath = "plugin://script.skin.helper.service/?action=alphabetletter&letter=%s" % letter
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), lipath, listitem, isFolder=False)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def alphabetletter(self):
        '''used with the alphabet scrollbar to jump to a letter'''
        if KODI_VERSION > 16:
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())
        letter = self.params.get("letter", "").upper()
        jumpcmd = ""
        if letter in ["A", "B", "C", "2"]:
            jumpcmd = "2"
        elif letter in ["D", "E", "F", "3"]:
            jumpcmd = "3"
        elif letter in ["G", "H", "I", "4"]:
            jumpcmd = "4"
        elif letter in ["J", "K", "L", "5"]:
            jumpcmd = "5"
        elif letter in ["M", "N", "O", "6"]:
            jumpcmd = "6"
        elif letter in ["P", "Q", "R", "S", "7"]:
            jumpcmd = "7"
        elif letter in ["T", "U", "V", "8"]:
            jumpcmd = "8"
        elif letter in ["W", "X", "Y", "Z", "9"]:
            jumpcmd = "9"
        if jumpcmd:
            xbmc.executebuiltin("SetFocus(50)")
            for i in range(40):
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Input.ExecuteAction",\
                    "params": { "action": "jumpsms%s" }, "id": 1 }' % (jumpcmd))
                xbmc.sleep(50)
                if xbmc.getInfoLabel("ListItem.Sortletter").upper() == letter:
                    break
