#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    pvrartwork.py
    Get metadata for Kodi PVR programs
'''

from utils import get_clean_image, DialogSelect, log_msg, extend_dict, ADDON_ID, download_artwork, normalize_string
import xbmc
import xbmcgui
import xbmcvfs
from difflib import SequenceMatcher as SM
from operator import itemgetter
import re
from urllib import quote_plus
import os


class PvrArtwork(object):
    '''get artwork for kodi pvr'''

    def __init__(self, metadatautils=None):
        '''Initialize - optionaly provide our base MetadataUtils class'''
        if not metadatautils:
            from metadatautils import MetadataUtils
            self.metadatautils = MetadataUtils
        else:
            self.metadatautils = metadatautils
        self.cache = self.metadatautils.cache

    def get_pvr_artwork(self, title, channel, genre="", manual_select=False, ignore_cache=False):
        '''
            collect full metadata and artwork for pvr entries
            parameters: title (required)
            channel: channel name (required)
            year: year or date (optional)
            genre: (optional)
            the more optional parameters are supplied, the better the search results
        '''
        details = {"art": {}}
        # try cache first
        cache_str = "pvr_artwork.%s.%s" % (title.lower(), channel.lower())
        cache = self.metadatautils.cache.get(cache_str)
        if cache and not manual_select and not ignore_cache:
            log_msg("get_pvr_artwork - return data from cache - %s" % cache_str)
            details = cache
        else:
            # no cache - start our lookup adventure
            log_msg("get_pvr_artwork - no data in cache - start lookup - %s" % cache_str)

            # workaround for recordings
            recordingdetails = self.lookup_local_recording(title, channel)
            if recordingdetails and not (channel and genre):
                genre = recordingdetails["genre"]
                channel = recordingdetails["channel"]

            details["pvrtitle"] = title
            details["pvrchannel"] = channel
            details["pvrgenre"] = genre
            details["cachestr"] = cache_str
            details["media_type"] = ""
            details["art"] = {}

            # filter genre unknown/other
            if not genre or genre.split(" / ")[0] in xbmc.getLocalizedString(19499).split(" / "):
                details["genre"] = []
                genre = ""
                log_msg("genre is unknown so ignore....")
            else:
                details["genre"] = genre.split(" / ")
                details["media_type"] = self.get_mediatype_from_genre(genre)
            searchtitle = self.get_searchtitle(title, channel)

            # only continue if we pass our basic checks
            filterstr = self.pvr_proceed_lookup(title, channel, genre, recordingdetails)
            proceed_lookup = False if filterstr else True
            if not proceed_lookup and manual_select:
                # warn user about active skip filter
                proceed_lookup = xbmcgui.Dialog().yesno(
                    line1=self.metadatautils.addon.getLocalizedString(32027), line2=filterstr,
                    heading=xbmc.getLocalizedString(750))

            if proceed_lookup:

                # if manual lookup get the title from the user
                if manual_select:
                    searchtitle = xbmcgui.Dialog().input(xbmc.getLocalizedString(16017), searchtitle,
                                                         type=xbmcgui.INPUT_ALPHANUM).decode("utf-8")
                    if not searchtitle:
                        return

                # if manual lookup and no mediatype, ask the user
                if manual_select and not details["media_type"]:
                    yesbtn = self.metadatautils.addon.getLocalizedString(32042)
                    nobtn = self.metadatautils.addon.getLocalizedString(32043)
                    header = self.metadatautils.addon.getLocalizedString(32041)
                    if xbmcgui.Dialog().yesno(header, header, yeslabel=yesbtn, nolabel=nobtn):
                        details["media_type"] = "movie"
                    else:
                        details["media_type"] = "tvshow"

                # append thumb from recordingdetails
                if recordingdetails and recordingdetails.get("thumbnail"):
                    details["art"]["thumb"] = recordingdetails["thumbnail"]
                # lookup custom path
                details = extend_dict(details, self.lookup_custom_path(searchtitle, title))
                # lookup movie/tv library
                details = extend_dict(details, self.lookup_local_library(searchtitle, details["media_type"]))

                # do internet scraping if enabled
                if self.metadatautils.addon.getSetting("pvr_art_scraper") == "true":

                    log_msg(
                        "pvrart start scraping metadata for title: %s - media_type: %s" %
                        (searchtitle, details["media_type"]))

                    # prefer tmdb scraper
                    tmdb_result = self.metadatautils.get_tmdb_details(
                        "", "", searchtitle, "", "", details["media_type"],
                            manual_select=manual_select, ignore_cache=manual_select)
                    log_msg("pvrart lookup for title: %s - TMDB result: %s" % (searchtitle, tmdb_result))
                    if tmdb_result:
                        details["media_type"] = tmdb_result["media_type"]
                        details = extend_dict(details, tmdb_result)

                    # fallback to tvdb scraper
                    if (not tmdb_result or (tmdb_result and not tmdb_result.get("art")) or
                            details["media_type"] == "tvshow"):
                        tvdb_match = self.lookup_tvdb(searchtitle, channel, manual_select=manual_select)
                        log_msg("pvrart lookup for title: %s - TVDB result: %s" % (searchtitle, tvdb_match))
                        if tvdb_match:
                            # get full tvdb results and extend with tmdb
                            if not details["media_type"]:
                                details["media_type"] = "tvshow"
                            details = extend_dict(details, self.metadatautils.thetvdb.get_series(tvdb_match))
                            details = extend_dict(details, self.metadatautils.tmdb.get_videodetails_by_externalid(
                                tvdb_match, "tvdb_id"), ["poster", "fanart"])

                    # fanart.tv scraping - append result to existing art
                    if details.get("imdbnumber") and details["media_type"] == "movie":
                        details["art"] = extend_dict(
                            details["art"], self.metadatautils.fanarttv.movie(
                                details["imdbnumber"]), [
                                "poster", "fanart", "landscape"])
                    elif details.get("tvdb_id") and details["media_type"] == "tvshow":
                        details["art"] = extend_dict(
                            details["art"], self.metadatautils.fanarttv.tvshow(
                                details["tvdb_id"]), [
                                "poster", "fanart", "landscape"])

                    # append omdb details
                    if details.get("imdbnumber"):
                        details = extend_dict(
                            details, self.metadatautils.omdb.get_details_by_imdbid(
                                details["imdbnumber"]), [
                                "rating", "votes"])

                    # set thumbnail - prefer scrapers
                    thumb = ""
                    if details.get("thumbnail"):
                        thumb = details["thumbnail"]
                    elif details["art"].get("landscape"):
                        thumb = details["art"]["landscape"]
                    elif details["art"].get("fanart"):
                        thumb = details["art"]["fanart"]
                    elif details["art"].get("poster"):
                        thumb = details["art"]["poster"]
                    # use google images as last-resort fallback for thumbs - if enabled
                    elif self.metadatautils.addon.getSetting("pvr_art_google") == "true":
                        if manual_select:
                            google_title = searchtitle
                        else:
                            google_title = '%s %s' % (searchtitle, channel.lower().split(" hd")[0])
                        thumb = self.metadatautils.google.search_image(google_title, manual_select)
                    if thumb:
                        details["thumbnail"] = thumb
                        details["art"]["thumb"] = thumb
                    # extrafanart
                    if details["art"].get("fanarts"):
                        for count, item in enumerate(details["art"]["fanarts"]):
                            details["art"]["fanart.%s" % count] = item
                        if not details["art"].get("extrafanart") and len(details["art"]["fanarts"]) > 1:
                            details["art"]["extrafanart"] = "plugin://script.skin.helper.service/"\
                                "?action=extrafanart&fanarts=%s" % quote_plus(repr(details["art"]["fanarts"]))

                    # download artwork to custom folder
                    if self.metadatautils.addon.getSetting("pvr_art_download") == "true":
                        details["art"] = download_artwork(self.get_custom_path(searchtitle, title), details["art"])

            log_msg("pvrart lookup for title: %s - final result: %s" % (searchtitle, details))

        # store result in cache and return details
        # always re-store in cache to prevent the cache from expiring
        self.metadatautils.cache.set(cache_str, details)
        return details

    def manual_set_pvr_artwork(self, title, channel, genre):
        '''manual override artwork options'''

        details = self.get_pvr_artwork(title, channel, genre)
        cache_str = details["cachestr"]

        # show dialogselect with all artwork options
        from utils import manual_set_artwork
        changemade, artwork = manual_set_artwork(details["art"], "pvr")
        if changemade:
            details["art"] = artwork
            # save results in cache
            self.metadatautils.cache.set(cache_str, details)

    def pvr_artwork_options(self, title, channel, genre):
        '''show options for pvr artwork'''
        if not channel and genre:
            channel, genre = self.get_pvr_channel_and_genre(title)
        ignorechannels = self.metadatautils.addon.getSetting("pvr_art_ignore_channels").split("|")
        ignoretitles = self.metadatautils.addon.getSetting("pvr_art_ignore_titles").split("|")
        options = []
        options.append(self.metadatautils.addon.getLocalizedString(32028))  # Refresh item (auto lookup)
        options.append(self.metadatautils.addon.getLocalizedString(32029))  # Refresh item (manual lookup)
        options.append(self.metadatautils.addon.getLocalizedString(32036))  # Choose art
        if channel in ignorechannels:
            options.append(self.metadatautils.addon.getLocalizedString(32030))  # Remove channel from ignore list
        else:
            options.append(self.metadatautils.addon.getLocalizedString(32031))  # Add channel to ignore list
        if title in ignoretitles:
            options.append(self.metadatautils.addon.getLocalizedString(32032))  # Remove title from ignore list
        else:
            options.append(self.metadatautils.addon.getLocalizedString(32033))  # Add title to ignore list
        options.append(self.metadatautils.addon.getLocalizedString(32034))  # Open addon settings
        header = self.metadatautils.addon.getLocalizedString(32035)
        dialog = xbmcgui.Dialog()
        ret = dialog.select(header, options)
        del dialog
        if ret == 0:
            # Refresh item (auto lookup)
            self.get_pvr_artwork(title=title, channel=channel, genre=genre, ignore_cache=True, manual_select=False)
        elif ret == 1:
            # Refresh item (manual lookup)
            self.get_pvr_artwork(title=title, channel=channel, genre=genre, ignore_cache=True, manual_select=True)
        elif ret == 2:
            # Choose art
            self.manual_set_pvr_artwork(title, channel, genre)
        elif ret == 3:
            # Add/remove channel to ignore list
            if channel in ignorechannels:
                ignorechannels.remove(channel)
            else:
                ignorechannels.append(channel)
            ignorechannels_str = "|".join(ignorechannels)
            self.metadatautils.addon.setSetting("pvr_art_ignore_channels", ignorechannels_str)
            self.get_pvr_artwork(title=title, channel=channel, genre=genre, ignore_cache=True, manual_select=False)
        elif ret == 4:
            # Add/remove title to ignore list
            if title in ignoretitles:
                ignoretitles.remove(title)
            else:
                ignoretitles.append(title)
            ignoretitles_str = "|".join(ignoretitles)
            self.metadatautils.addon.setSetting("pvr_art_ignore_titles", ignoretitles_str)
            self.get_pvr_artwork(title=title, channel=channel, genre=genre, ignore_cache=True, manual_select=False)
        elif ret == 5:
            # Open addon settings
            xbmc.executebuiltin("Addon.OpenSettings(%s)" % ADDON_ID)

    def pvr_proceed_lookup(self, title, channel, genre, recordingdetails):
        '''perform some checks if we can proceed with the lookup'''
        filters = []
        if not title:
            filters.append("Title is empty")
        for item in self.metadatautils.addon.getSetting("pvr_art_ignore_titles").split("|"):
            if item and item.lower() == title.lower():
                filters.append("Title is in list of titles to ignore")
        for item in self.metadatautils.addon.getSetting("pvr_art_ignore_channels").split("|"):
            if item and item.lower() == channel.lower():
                filters.append("Channel is in list of channels to ignore")
        for item in self.metadatautils.addon.getSetting("pvr_art_ignore_genres").split("|"):
            if genre and item and item.lower() in genre.lower():
                filters.append("Genre is in list of genres to ignore")
        if self.metadatautils.addon.getSetting("pvr_art_ignore_commongenre") == "true":
            # skip common genres like sports, weather, news etc.
            genre = genre.lower()
            kodi_strings = [19516, 19517, 19518, 19520, 19548, 19549, 19551,
                            19552, 19553, 19554, 19555, 19556, 19557, 19558, 19559]
            for kodi_string in kodi_strings:
                kodi_string = xbmc.getLocalizedString(kodi_string).lower()
                if (genre and (genre in kodi_string or kodi_string in genre)) or kodi_string in title:
                    filters.append("Common genres like weather/sports are set to be ignored")
        if self.metadatautils.addon.getSetting("pvr_art_recordings_only") == "true" and not recordingdetails:
            filters.append("PVR Artwork is enabled for recordings only")
        if filters:
            filterstr = " - ".join(filters)
            log_msg("PVR artwork - filter active for title: %s - channel %s --> %s" % (title, channel, filterstr))
            return filterstr
        else:
            return ""

    @staticmethod
    def get_mediatype_from_genre(genre):
        '''guess media type from genre for better matching'''
        media_type = ""
        if "movie" in genre.lower() or "film" in genre.lower():
            media_type = "movie"
        if "show" in genre.lower():
            media_type = "tvshow"
        if not media_type:
            # Kodi defined movie genres
            kodi_genres = [19500, 19507, 19508, 19602, 19603, 19502, 19503, 19501]
            for kodi_genre in kodi_genres:
                if genre in xbmc.getLocalizedString(kodi_genre):
                    media_type = "movie"
                    break
        if not media_type:
            # Kodi defined tvshow genres
            kodi_genres = [19505, 19516, 19517, 19518, 19520, 19532, 19533, 19534, 19535, 19548, 19549,
                           19550, 19551, 19552, 19553, 19554, 19555, 19556, 19557, 19558, 19559]
            for kodi_genre in kodi_genres:
                if genre in xbmc.getLocalizedString(kodi_genre):
                    media_type = "tvshow"
                    break
        return media_type

    def get_searchtitle(self, title, channel):
        '''common logic to get a proper searchtitle from crappy titles provided by pvr'''
        if not isinstance(title, unicode):
            title = title.decode("utf-8")
        title = title.lower()
        # split characters - split on common splitters
        splitters = self.metadatautils.addon.getSetting("pvr_art_splittitlechar").decode("utf-8").split("|")
        if channel:
            splitters.append(" %s" % channel.lower())
        for splitchar in splitters:
            title = title.split(splitchar)[0]
        # replace common chars and words
        title = re.sub(self.metadatautils.addon.getSetting("pvr_art_replace_by_space").decode("utf-8"), ' ', title)
        title = re.sub(self.metadatautils.addon.getSetting("pvr_art_stripchars").decode("utf-8"), '', title)
        title = title.strip()
        return title

    def lookup_local_recording(self, title, channel):
        '''lookup actual recordings to get details for grouped recordings
           also grab a thumb provided by the pvr
        '''
        cache = self.metadatautils.cache.get("recordingdetails.%s%s" % (title, channel))
        if cache:
            return cache
        details = {}
        recordings = self.metadatautils.kodidb.recordings()
        for item in recordings:
            if (title == item["title"] or title in item["file"]) and (channel == item["channel"] or not channel):
                # grab thumb from pvr
                if item.get("art"):
                    details["thumbnail"] = get_clean_image(item["art"].get("thumb"))
                # ignore tvheadend thumb as it returns the channellogo
                elif item.get("icon") and "imagecache" not in item["icon"]:
                    details["thumbnail"] = get_clean_image(item["icon"])
                details["channel"] = item["channel"]
                details["genre"] = " / ".join(item["genre"])
                break
        self.metadatautils.cache.set("recordingdetails.%s%s" % (title, channel), details)
        return details

    def lookup_tvdb(self, searchtitle, channel, manual_select=False):
        '''helper to select a match on tvdb'''
        tvdb_match = None
        searchtitle = searchtitle.lower()
        tvdb_result = self.metadatautils.thetvdb.search_series(searchtitle, True)
        searchchannel = channel.lower().split("hd")[0].replace(" ", "")
        match_results = []
        if tvdb_result:
            for item in tvdb_result:
                item["score"] = 0
                if not item["seriesName"]:
                    continue  # seriesname can be None in some conditions
                itemtitle = item["seriesName"].lower()
                network = item["network"].lower().replace(" ", "")
                # high score if channel name matches
                if network in searchchannel or searchchannel in network:
                    item["score"] += 800
                # exact match on title - very high score
                if searchtitle == itemtitle:
                    item["score"] += 1000
                # match title by replacing some characters
                if re.sub('\*|,|.\"|\'| |:|;', '', searchtitle) == re.sub('\*|,|.\"|\'| |:|;', '', itemtitle):
                    item["score"] += 750
                # add SequenceMatcher score to the results
                stringmatchscore = SM(None, searchtitle, itemtitle).ratio()
                if stringmatchscore > 0.7:
                    item["score"] += stringmatchscore * 500
                # prefer items with native language as we've searched with localized info enabled
                if item["overview"]:
                    item["score"] += 250
                # prefer items with artwork
                if item["banner"]:
                    item["score"] += 1
                if item["score"] > 500 or manual_select:
                    match_results.append(item)
            # sort our new list by score
            match_results = sorted(match_results, key=itemgetter("score"), reverse=True)
            if match_results and manual_select:
                # show selectdialog to manually select the item
                listitems = []
                for item in match_results:
                    thumb = "http://thetvdb.com/banners/%s" % item["banner"] if item["banner"] else ""
                    listitem = xbmcgui.ListItem(label=item["seriesName"], iconImage=thumb, label2=item["overview"])
                    listitems.append(listitem)
                dialog = DialogSelect(
                    "DialogSelect.xml",
                    "",
                    listing=listitems,
                    window_title="%s - TVDB" %
                    xbmc.getLocalizedString(283))
                dialog.doModal()
                selected_item = dialog.result
                del dialog
                if selected_item != -1:
                    tvdb_match = match_results[selected_item]["id"]
                else:
                    match_results = []
            if not tvdb_match and match_results:
                # just grab the first item as best match
                tvdb_match = match_results[0]["id"]
        return tvdb_match

    def get_custom_path(self, searchtitle, title):
        '''locate custom folder on disk as pvrart location'''
        title_path = ""
        custom_path = self.metadatautils.addon.getSetting("pvr_art_custom_path")
        if custom_path and self.metadatautils.addon.getSetting("pvr_art_custom") == "true":
            delim = "\\" if "\\" in custom_path else "/"
            dirs = xbmcvfs.listdir(custom_path)[0]
            for strictness in [1, 0.95, 0.9, 0.8]:
                if title_path:
                    break
                for directory in dirs:
                    if title_path:
                        break
                    directory = directory.decode("utf-8")
                    curpath = os.path.join(custom_path, directory) + delim
                    for item in [title, searchtitle]:
                        match = SM(None, item, directory).ratio()
                        if match >= strictness:
                            title_path = curpath
                            break
            if not title_path and self.metadatautils.addon.getSetting("pvr_art_download") == "true":
                title_path = os.path.join(custom_path, normalize_string(title)) + delim
        return title_path

    def lookup_custom_path(self, searchtitle, title):
        '''looks up a custom directory if it contains a subdir for our title'''
        details = {}
        details["art"] = {}
        title_path = self.get_custom_path(searchtitle, title)
        if title_path and xbmcvfs.exists(title_path):
            # we have found a folder for the title, look for artwork
            files = xbmcvfs.listdir(title_path)[1]
            for item in files:
                item = item.decode("utf-8")
                if item in ["banner.jpg", "clearart.png", "poster.png", "fanart.jpg", "landscape.jpg"]:
                    key = item.split(".")[0]
                    details["art"][key] = title_path + item
                elif item == "logo.png":
                    details["art"]["clearlogo"] = title_path + item
                elif item == "thumb.jpg":
                    details["art"]["thumb"] = title_path + item
            # extrafanarts
            efa_path = title_path + "extrafanart/"
            if xbmcvfs.exists(title_path + "extrafanart"):
                files = xbmcvfs.listdir(efa_path)[1]
                details["art"]["fanarts"] = []
                if files:
                    details["art"]["extrafanart"] = efa_path
                    for item in files:
                        item = efa_path + item.decode("utf-8")
                        details["art"]["fanarts"].append(item)
        return details

    def lookup_local_library(self, title, media_type):
        '''lookup the title in the local video db'''
        details = {}
        filters = [{"operator": "is", "field": "title", "value": title}]
        if not media_type or media_type == "tvshow":
            kodi_items = self.metadatautils.kodidb.tvshows(filters=filters, limits=(0, 1))
            if kodi_items:
                details = kodi_items[0]
                details["media_type"] = "tvshow"
        if not details and (not media_type or media_type == "movie"):
            kodi_items = self.metadatautils.kodidb.movies(filters=filters, limits=(0, 1))
            if kodi_items:
                details = kodi_items[0]
                details["media_type"] = "movie"
        if details:
            for artkey, artvalue in details["art"].iteritems():
                details["art"][artkey] = get_clean_image(artvalue)
            # todo: check extrafanart ?
        return details
