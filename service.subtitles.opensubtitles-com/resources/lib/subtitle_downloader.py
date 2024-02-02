
from __future__ import division
from __future__ import absolute_import
import os
import shutil
import sys
import uuid

import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import xbmc

from resources.lib.data_collector import get_language_data, get_media_data, get_file_path, convert_language, \
    clean_feature_release_name, get_flag
from resources.lib.exceptions import AuthenticationError, ConfigurationError, DownloadLimitExceeded, ProviderError, \
    ServiceUnavailable, TooManyRequests, BadUsernameError
from resources.lib.file_operations import get_file_data
from resources.lib.os.provider import OpenSubtitlesProvider
from resources.lib.utilities import get_params, log, error
from io import open

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo(u"id")

__profile__ = xbmc.translatePath(__addon__.getAddonInfo(u"profile"))
__temp__ = xbmc.translatePath(os.path.join(__profile__, u"temp", u""))

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)


class SubtitleDownloader(object):

    def __init__(self):

        self.api_key = __addon__.getSetting(u"APIKey")
        self.username = __addon__.getSetting(u"OSuser")
        self.password = __addon__.getSetting(u"OSpass")

        log(__name__, sys.argv)

        self.sub_format = u"srt"
        self.handle = int(sys.argv[1])
        self.params = get_params()
        self.query = {}
        self.subtitles = {}
        self.file = {}

        try:
            self.open_subtitles = OpenSubtitlesProvider(self.api_key, self.username, self.password)
        except ConfigurationError, e:
            error(__name__, 32002, e)

    def handle_action(self):
        log(__name__, u"action '%s' called" % self.params[u"action"])
        if self.params[u"action"] == u"manualsearch":
            self.search(self.params[u'searchstring'])
        elif self.params[u"action"] == u"search":
            self.search()
        elif self.params[u"action"] == u"download":
            self.download()

    def search(self, query=u""):
        file_data = get_file_data(get_file_path())
        language_data = get_language_data(self.params)

        log(__name__, u"file_data '%s' " % file_data)
        log(__name__, u"language_data '%s' " % language_data)

        # if there's query passed we use it, don't try to pull media data from VideoPlayer
        if query:
            media_data = {u"query": query}
        else:
            media_data = get_media_data()
            if u"basename" in file_data:
                media_data[u"query"] = file_data[u"basename"]
            log(__name__, u"media_data '%s' " % media_data)

        self.query = dict(media_data)
        self.query.update(file_data)
        self.query.update(language_data)

        try:
            self.subtitles = self.open_subtitles.search_subtitles(self.query)
        # TODO handle errors individually. Get clear error messages to the user
        except (TooManyRequests, ServiceUnavailable, ProviderError, ValueError), e:
            error(__name__, 32001, e)

        if self.subtitles and len(self.subtitles):
            log(__name__, len(self.subtitles))
            self.list_subtitles()
        else:
            # TODO retry using guessit???
            log(__name__, u"No subtitle found")

    def download(self):
        valid = 1
        try:
            self.file = self.open_subtitles.download_subtitle(
                {u"file_id": self.params[u"id"], u"sub_format": self.sub_format})
        # TODO handle errors individually. Get clear error messages to the user
            log(__name__, u"XYXYXX download '%s' " % self.file)
        except AuthenticationError, e:
            error(__name__, 32003, e)
            valid = 0
        except BadUsernameError, e:
            error(__name__, 32214, e)
            valid = 0
        except DownloadLimitExceeded, e:
            log(__name__, "XYXYXX limit excedded, username: %s  %s" % (self.username, e) )
            if self.username==u"":
                error(__name__, 32006, e)
            else:
                error(__name__, 32004, e)
            valid = 0
        except (TooManyRequests, ServiceUnavailable, ProviderError, ValueError), e:
            error(__name__, 32001, e)
            valid = 0

        subtitle_path = os.path.join(__temp__, "%s.%s" % (str(uuid.uuid4()), self.sub_format) )
       
        if (valid==1):
            tmp_file = open(subtitle_path, u"w" + u"b")
            tmp_file.write(self.file[u"content"])
            tmp_file.close()
        

        list_item = xbmcgui.ListItem(label=subtitle_path)
        xbmcplugin.addDirectoryItem(handle=self.handle, url=subtitle_path, listitem=list_item, isFolder=False)

        return

        u"""old code"""
        # subs = Download(params["ID"], params["link"], params["format"])
        # for sub in subs:
        #    listitem = xbmcgui.ListItem(label=sub)
        #    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

    def list_subtitles(self):
        u"""TODO rewrite using new data. do not forget Series/Episodes"""
        if self.subtitles:
            for subtitle in reversed(sorted(self.subtitles, key=lambda x: (
                    bool(x[u"attributes"].get(u"from_trusted", False)),
                    x[u"attributes"].get(u"votes", 0) or 0,
                    x[u"attributes"].get(u"ratings", 0) or 0,
                    x[u"attributes"].get(u"download_count", 0) or 0))):
                attributes = subtitle[u"attributes"]
                language = convert_language(attributes[u"language"], True)
                log(__name__, attributes)
                clean_name = clean_feature_release_name(attributes[u"feature_details"][u"title"], attributes[u"release"],
                                                        attributes[u"feature_details"][u"movie_name"])
                list_item = xbmcgui.ListItem(label=language,
                                             label2=clean_name)
                list_item.setArt({
                    u"icon": unicode(int(round(float(attributes[u"ratings"]) / 2))),
                    u"thumb": get_flag(attributes[u"language"])})
                list_item.setProperty(u"sync", u"true" if (u"moviehash_match" in attributes and attributes[u"moviehash_match"]) else u"false")
                list_item.setProperty(u"hearing_imp", u"true" if attributes[u"hearing_impaired"] else u"false")
                u"""TODO take care of multiple cds id&id or something"""
                url = "plugin://%s/?action=download&id=%s" % (__scriptid__, attributes['files'][0]['file_id']) 

                xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=list_item, isFolder=False)
        xbmcplugin.endOfDirectory(self.handle)
