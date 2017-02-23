#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.backgrounds
    a helper service for Kodi skins providing rotating backgrounds
'''

import thread
import random
import os
from datetime import timedelta
from utils import log_msg, log_exception, get_content_path, urlencode, ADDON_ID
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui
from simplecache import SimpleCache
from conditional_backgrounds import get_cond_background
from smartshortcuts import SmartShortCuts
from wallimages import WallImages
from metadatautils import KodiDb, get_clean_image


class BackgroundsUpdater():
    '''Background service providing rotating backgrounds to Kodi skins'''
    exit = False
    all_backgrounds = {}
    all_backgrounds2 = {}
    all_backgrounds_labels = []
    backgrounds_delay = 0
    walls_delay = 30
    enable_walls = False
    all_backgrounds_keys = {}
    prefetch_images = 30  # number of images to cache in memory for each library path
    pvr_bg_recordingsonly = False
    custom_picturespath = ""
    winprops = {}

    def __init__(self):
        self.cache = SimpleCache()
        self.kodidb = KodiDb()
        self.win = xbmcgui.Window(10000)
        self.addon = xbmcaddon.Addon(ADDON_ID)
        self.kodimonitor = xbmc.Monitor()
        self.smartshortcuts = SmartShortCuts(self)
        self.wallimages = WallImages(self)

    def stop(self):
        '''stop running our background service '''
        log_msg("BackgroundsUpdater - stop called", xbmc.LOGNOTICE)
        self.smartshortcuts.exit = True
        self.wallimages.exit = True
        self.exit = True
        xbmc.sleep(100)  # allow threads to process the stop request
        del self.smartshortcuts
        del self.wallimages
        del self.win
        del self.kodimonitor
        del self.addon

    def run(self):
        '''called to start our background service '''
        log_msg("BackgroundsUpdater - started", xbmc.LOGNOTICE)
        self.winpropcache()
        self.get_config()
        backgrounds_task_interval = 0
        walls_task_interval = 0
        delayed_task_interval = 112

        while not self.kodimonitor.abortRequested():

            # Process backgrounds only if we're not watching fullscreen video
            if xbmc.getCondVisibility(
                "![Window.IsActive(fullscreenvideo) | Window.IsActive(script.pseudotv.TVOverlay.xml) | "
                    "Window.IsActive(script.pseudotv.live.TVOverlay.xml)] | "
                    "Window.IsActive(script.pseudotv.live.EPG.xml)"):

                # background stuff like reading the skin settings and generating smart shortcuts
                if delayed_task_interval >= 120:
                    delayed_task_interval = 0
                    self.get_config()
                    self.report_allbackgrounds()
                    self.smartshortcuts.build_smartshortcuts()
                    self.winpropcache(True)

                # force refresh smart shortcuts on request
                if self.win.getProperty("refreshsmartshortcuts"):
                    self.win.clearProperty("refreshsmartshortcuts")
                    self.smartshortcuts.build_smartshortcuts()

                # Update home backgrounds every interval (if enabled by skinner)
                if self.backgrounds_delay and backgrounds_task_interval >= self.backgrounds_delay:
                    backgrounds_task_interval = 0
                    self.update_backgrounds()

                # Update wall images every interval (if enabled by skinner)
                if self.enable_walls and self.walls_delay and (walls_task_interval >= self.walls_delay):
                    walls_task_interval = 0
                    thread.start_new_thread(self.wallimages.update_wallbackgrounds, ())
                    self.wallimages.update_manualwalls()

            self.kodimonitor.waitForAbort(1)
            backgrounds_task_interval += 1
            walls_task_interval += 1
            delayed_task_interval += 1

        # abort requested
        self.stop()

    def get_config(self):
        '''gets various settings for the script as set by the skinner or user'''

        # set all backgrounds in global cache for quick startup
        self.winpropcache(True)

        # skinner (or user) enables the random fanart images by setting the randomfanartdelay skin string
        try:
            self.backgrounds_delay = int(xbmc.getInfoLabel("Skin.String(SkinHelper.RandomFanartDelay)"))
        except Exception:
            pass

        self.walls_delay = int(self.addon.getSetting("wallimages_delay"))
        self.wallimages.max_wallimages = int(self.addon.getSetting("max_wallimages"))
        self.pvr_bg_recordingsonly = self.addon.getSetting("pvr_bg_recordingsonly") == "true"
        self.enable_walls = xbmc.getCondVisibility("Skin.HasSetting(SkinHelper.EnableWallBackgrounds)")
        if self.addon.getSetting("enable_custom_images_path") == "true":
            self.custom_picturespath = self.addon.getSetting("custom_images_path")
        else:
            self.custom_picturespath = ""
        try:
            # skinner can enable manual wall images generation so check for these settings
            # store in memory so wo do not have to query the skin settings too often
            if self.walls_delay:
                for key in self.all_backgrounds_keys.iterkeys():
                    limitrange = xbmc.getInfoLabel("Skin.String(%s.EnableWallImages)" % key)
                    if limitrange:
                        self.wallimages.manual_walls[key] = int(limitrange)
        except Exception as exc:
            log_exception(__name__, exc)

    def report_allbackgrounds(self):
        '''sets a list of all known backgrounds as winprop to be retrieved from skinshortcuts'''
        if self.all_backgrounds_labels:
            self.set_winprop("SkinHelper.AllBackgrounds", repr(self.all_backgrounds_labels))

    def set_winprop(self, key, value):
        '''sets a window property and writes it to our global list'''
        self.winprops[key] = value
        if isinstance(value, unicode):
            value = value.encode("utf-8")
        self.win.setProperty(key, value)

    def winpropcache(self, setcache=False):
        '''sets/gets the current window props in a global cache to load them immediately at startup'''
        if setcache:
            self.cache.set("skinhelper.backgrounds", self.winprops)
        else:
            cache = self.cache.get("skinhelper.backgrounds")
            if cache:
                for key, value in cache.iteritems():
                    if value:
                        if isinstance(value, unicode):
                            value = value.encode("utf-8")
                        self.win.setProperty(key.encode("utf-8"), value)

    def get_images_from_vfspath(self, lib_path):
        '''get all images from the given vfs path'''
        result = []
        # safety check: check if no library windows are active to prevent any addons setting the view
        if (xbmc.getCondVisibility("Window.IsMedia") and "plugin" in lib_path) or self.exit:
            return result

        lib_path = get_content_path(lib_path)

        if "plugin.video.emby" in lib_path and "browsecontent" in lib_path and "filter" not in lib_path:
            lib_path = lib_path + "&filter=random"

        items = self.kodidb.get_json("Files.GetDirectory", returntype="", optparam=("directory", lib_path),
                                     fields=["title", "art", "thumbnail", "fanart"],
                                     sort={"method": "random", "order": "descending"},
                                     limits=(0, self.prefetch_images))

        for media in items:
            image = {}
            if media['label'].lower() == "next page":
                continue
            if media.get('art'):
                if media['art'].get('fanart'):
                    image["fanart"] = get_clean_image(media['art']['fanart'])
                elif media['art'].get('tvshow.fanart'):
                    image["fanart"] = get_clean_image(media['art']['tvshow.fanart'])
                elif media['art'].get('artist.fanart'):
                    image["fanart"] = get_clean_image(media['art']['artist.fanart'])
                if media['art'].get('thumb'):
                    image["thumbnail"] = get_clean_image(media['art']['thumb'])
            if not image.get('fanart') and media.get("fanart"):
                image["fanart"] = get_clean_image(media['fanart'])
            if not image.get("thumbnail") and media.get("thumbnail"):
                image["thumbnail"] = get_clean_image(media["thumbnail"])

            # only append items which have a fanart image
            if image.get("fanart"):
                # also append other art to the dict
                image["title"] = media.get('title', '')
                if not image.get("title"):
                    image["title"] = media.get('label', '')
                image["landscape"] = get_clean_image(media.get('art', {}).get('landscape', ''))
                image["poster"] = get_clean_image(media.get('art', {}).get('poster', ''))
                image["clearlogo"] = get_clean_image(media.get('art', {}).get('clearlogo', ''))
                result.append(image)
        random.shuffle(result)
        return result

    def get_pictures(self):
        '''get images we can use as pictures background'''
        images = []
        # load the pictures from the custom path or from all picture sources
        if self.custom_picturespath:
            # load images from custom path
            files = xbmcvfs.listdir(self.custom_picturespath)[1]
            random.shuffle(files)
            # pick max 20 images from path
            for file in files[:20]:
                if file.lower().endswith(".jpg") or file.lower().endswith(".png"):
                    image = os.path.join(self.custom_picturespath, file.decode("utf-8"))
                    images.append({"fanart": image, "title": file.decode("utf-8")})
        else:
            # load pictures from all picture sources
            media_array = self.kodidb.get_json('Files.GetSources', optparam=("media", "pictures"))
            randomdirs = []
            for source in media_array:
                if 'file' in source:
                    if "plugin://" not in source["file"]:
                        dirs = xbmcvfs.listdir(source["file"])[0]
                        random.shuffle(dirs)  # randomize output
                        if dirs:
                            # pick 10 subdirectories
                            for randomdir in dirs[:10]:
                                randomdir = os.path.join(source["file"], randomdir.decode("utf-8"))
                                randomdirs.append(randomdir)
                        # append root to dirs so we can also list images in the root
                        randomdirs.append(source["file"])
                        # pick 5 images from each dir
                        for item in randomdirs:
                            files2 = xbmcvfs.listdir(item)[1]
                            random.shuffle(files2)
                            for count, filename in enumerate(files2):
                                if (filename.endswith(".jpg") or filename.endswith(".png")) and count < 6:
                                    filename = filename.decode("utf-8")
                                    image = os.path.join(item, filename)
                                    images.append({"fanart": image, "title": filename})
        return images

    def set_background(self, win_prop, lib_path, fallback_image="", label=None):
        '''set the window property for the background image'''
        image = None
        if win_prop in self.all_backgrounds2:
            # pick one random image from the small list using normal random function
            if len(self.all_backgrounds2[win_prop]) > 0:
                image = random.choice(self.all_backgrounds2[win_prop])
        elif win_prop in self.all_backgrounds and len(self.all_backgrounds[win_prop]) > 0:
            # list is already in memory and still contains images, grab the next item in line
            image = self.all_backgrounds[win_prop][0]
            # delete image from list when we've used it so we have truly randomized images
            del self.all_backgrounds[win_prop][0]
        else:
            # no images in memory - load them from vfs
            if isinstance(lib_path, list):
                images = self.get_global_backgrounds(lib_path)
            elif lib_path == "pictures":
                images = self.get_pictures()
            elif lib_path == "pvr":
                images = self.get_pvr_backgrounds()
            else:
                images = self.get_images_from_vfspath(lib_path)
            # store images in memory
            if len(images) < self.prefetch_images:
                # this path did not return enough images so we store it in a different list
                # which will not be flushed
                self.all_backgrounds2[win_prop] = images
                if images:
                    image = random.choice(images)
            else:
                # normal approach: store the current set of images in a list
                # images are taken from that list one-by-one untill it's empty
                # once empty a fresh pair of images will be retrieved for the path
                # this way we have fully randomized images while there's no need
                # to store a big pile of data in memory
                image = images[0]
                del images[0]
                self.all_backgrounds[win_prop] = images
            # also store the key + label in a list for skinshortcuts - only if the path actually has images
            if image:
                if not any(win_prop in item for item in self.all_backgrounds_labels):
                    if label and isinstance(label, int):
                        label = xbmc.getInfoLabel("$ADDON[%s %s]" % (ADDON_ID, label))
                    elif not label:
                        label = win_prop
                    self.all_backgrounds_labels.append((win_prop, label))
        # set the image
        if image:
            for key, value in image.iteritems():  # image is actually a dict
                if key == "fanart":
                    self.set_winprop(win_prop, value)
                else:  # set additional image properties
                    self.set_winprop("%s.%s" % (win_prop, key), value)
        else:
            # no image - use fallback_image
            self.set_winprop(win_prop, fallback_image)

    def get_global_backgrounds(self, keys):
        '''get random backgrounds from multiple other collections'''
        images = []
        for key in keys:
            if key in self.all_backgrounds and self.all_backgrounds[key]:
                images += self.all_backgrounds[key]
        random.shuffle(images)
        return images

    def get_pvr_backgrounds(self):
        '''get the images for pvr items by using the skinhelper widgets as source'''
        images = []
        widgetreload = self.win.getProperty("widgetreload2")
        rec_images = self.get_images_from_vfspath(
            "plugin://script.skin.helper.widgets/?mediatype=pvr"
            "&action=recordings&limit=50&reload=%s" % widgetreload)
        if rec_images:  # result can be None
            images = rec_images
        if not self.pvr_bg_recordingsonly:
            tv_images = self.get_images_from_vfspath(
                "plugin://script.skin.helper.widgets/?mediatype=pvr"
                "&action=channels&limit=25&reload=%s" % widgetreload)
            if tv_images:  # result can be None
                images += tv_images
        return images

    def update_backgrounds(self):
        '''update all our provided backgrounds'''

        # conditional background
        self.win.setProperty("SkinHelper.ConditionalBackground", get_cond_background())

        # movies backgrounds
        if xbmc.getCondVisibility("Library.HasContent(movies)"):
            # random/all movies
            self.set_background("SkinHelper.AllMoviesBackground", "videodb://movies/titles/", label=32010)
            # in progress movies
            self.set_background(
                "SkinHelper.InProgressMoviesBackground",
                "videodb://movies/titles/?xsp=%s" %
                urlencode(
                    '{"limit":50,"order":{"direction":"ascending","method":"random"},'
                    '"rules":{"and":[{"field":"inprogress","operator":"true","value":[]}]},"type":"movies"}'),
                label=32012)
            # recent movies
            self.set_background("SkinHelper.RecentMoviesBackground", "videodb://recentlyaddedmovies/", label=32011)
            # unwatched movies
            self.set_background(
                "SkinHelper.UnwatchedMoviesBackground",
                "videodb://movies/titles/?xsp=%s" %
                urlencode(
                    '{"limit":50,"order":{"direction":"ascending","method":"random"},'
                    '"rules":{"and":[{"field":"playcount","operator":"is","value":0}]},"type":"movies"}'), label=32013)

        # tvshows backgrounds
        if xbmc.getCondVisibility("Library.HasContent(tvshows)"):
            # random/all tvshows
            self.set_background("SkinHelper.AllTvShowsBackground", "videodb://tvshows/titles/", label=32014)
            # in progress tv shows
            self.set_background(
                "SkinHelper.InProgressShowsBackground",
                "videodb://tvshows/titles/?xsp=%s" %
                urlencode(
                    '{"limit":50,"order":{"direction":"ascending","method":"random"},'
                    '"rules":{"and":[{"field":"inprogress","operator":"true","value":[]}]},"type":"tvshows"}'),
                label=32016)
            # recent episodes
            self.set_background("SkinHelper.RecentEpisodesBackground", "videodb://recentlyaddedepisodes/", label=32015)

        # all musicvideos
        if xbmc.getCondVisibility("Library.HasContent(musicvideos)"):
            self.set_background("SkinHelper.AllMusicVideosBackground", "videodb://musicvideos/titles", label=32018)

        # all music
        if xbmc.getCondVisibility("Library.HasContent(music)"):
            # music artists
            self.set_background("SkinHelper.AllMusicBackground", "musicdb://artists/", label=32019)
            # recent albums
            self.set_background(
                "SkinHelper.RecentMusicBackground", "musicdb://recentlyaddedalbums/", label=32023)
            # random songs
            self.set_background(
                "SkinHelper.AllMusicSongsBackground", "musicdb://songs/", label=32022)

        # tmdb backgrounds (extendedinfo)
        if xbmc.getCondVisibility("System.HasAddon(script.extendedinfo)"):
            self.set_background(
                "SkinHelper.TopRatedMovies",
                "plugin://script.extendedinfo/?info=topratedmovies",
                label=32020)
            self.set_background(
                "SkinHelper.TopRatedShows",
                "plugin://script.extendedinfo/?info=topratedtvshows",
                label=32021)

        # pictures background
        self.set_background("SkinHelper.PicturesBackground", "pictures", label=32017)

        # pvr background
        if xbmc.getCondVisibility("PVR.HasTvChannels"):
            self.set_background("SkinHelper.PvrBackground", "pvr", label=32024)

        # smartshortcuts backgrounds
        for node in self.smartshortcuts.get_smartshortcuts_nodes():
            self.set_background(node[0], node[1], label=node[2])

        # global backgrounds
        self.set_background("SkinHelper.GlobalFanartBackground",
                            ["SkinHelper.AllMoviesBackground", "SkinHelper.AllTvShowsBackground",
                             "SkinHelper.AllMusicVideosBackground", "SkinHelper.AllMusicBackground"],
                            label=32009)
        self.set_background("SkinHelper.AllVideosBackground",
                            ["SkinHelper.AllMoviesBackground", "SkinHelper.AllTvShowsBackground",
                             "SkinHelper.AllMusicVideosBackground"], label=32025)
        self.set_background(
            "SkinHelper.AllVideosBackground2", [
                "SkinHelper.AllMoviesBackground", "SkinHelper.AllTvShowsBackground"], label=32026)
        self.set_background(
            "SkinHelper.RecentVideosBackground",
            ["SkinHelper.RecentMoviesBackground", "SkinHelper.RecentEpisodesBackground"], label=32027)
        self.set_background(
            "SkinHelper.InProgressVideosBackground",
            ["SkinHelper.InProgressMoviesBackground", "SkinHelper.InProgressShowsBackground"], label=32028)
