
import os
import shutil
import sys
import uuid

import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.data_collector import get_language_data, get_media_data, get_file_path, convert_language, \
    clean_feature_release_name, get_flag
from resources.lib.exceptions import AuthenticationError, ConfigurationError, DownloadLimitExceeded, ProviderError, \
    ServiceUnavailable, TooManyRequests
from resources.lib.file_operations import get_file_data
from resources.lib.os.provider import OpenSubtitlesProvider
from resources.lib.utilities import get_params, log, error

__addon__ = xbmcaddon.Addon()
__scriptid__ = __addon__.getAddonInfo("id")

__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, "temp", ""))

if xbmcvfs.exists(__temp__):
    shutil.rmtree(__temp__)
xbmcvfs.mkdirs(__temp__)


class SubtitleDownloader:

    def __init__(self):

        self.api_key = __addon__.getSetting("APIKey")
        self.username = __addon__.getSetting("OSuser")
        self.password = __addon__.getSetting("OSpass")

        log(__name__, sys.argv)

        self.sub_format = "srt"
        self.handle = int(sys.argv[1])
        self.params = get_params()
        self.query = {}
        self.subtitles = {}
        self.file = {}

        try:
            self.open_subtitles = OpenSubtitlesProvider(self.api_key, self.username, self.password)
        except ConfigurationError as e:
            error(__name__, 32002, e)

    def handle_action(self):
        log(__name__, "action '%s' called" % self.params["action"])
        if self.params["action"] == "manualsearch":
            self.search(self.params['searchstring'])
        elif self.params["action"] == "search":
            self.search()
        elif self.params["action"] == "download":
            self.download()

    def search(self, query=""):
        file_data = get_file_data(get_file_path())
        language_data = get_language_data(self.params)

        log(__name__, "file_data '%s' " % file_data)
        log(__name__, "language_data '%s' " % language_data)

        # if there's query passed we use it, don't try to pull media data from VideoPlayer
        if query:
            media_data = {"query": query}
        else:
            media_data = get_media_data()
            if "basename" in file_data:
                media_data["query"] = file_data["basename"]
            log(__name__, "media_data '%s' " % media_data)

        self.query = {**media_data, **file_data, **language_data}

        try:
            self.subtitles = self.open_subtitles.search_subtitles(self.query)
        # TODO handle errors individually. Get clear error messages to the user
        except (TooManyRequests, ServiceUnavailable, ProviderError, ValueError) as e:
            error(__name__, 32001, e)

        if self.subtitles and len(self.subtitles):
            log(__name__, len(self.subtitles))
            self.list_subtitles()
        else:
            # TODO retry using guessit???
            log(__name__, "No subtitle found")

    def download(self):
        valid = 1
        try:
            self.file = self.open_subtitles.download_subtitle(
                {"file_id": self.params["id"], "sub_format": self.sub_format})
        # TODO handle errors individually. Get clear error messages to the user
            log(__name__, "XYXYXX download '%s' " % self.file)
        except AuthenticationError as e:
            error(__name__, 32003, e)
            valid = 0
        except DownloadLimitExceeded as e:
            log(__name__, f"XYXYXX limit excedded, username: {self.username}  {e}")
            if self.username=="":
                error(__name__, 32006, e)
            else:
                error(__name__, 32004, e)
            valid = 0
        except (TooManyRequests, ServiceUnavailable, ProviderError, ValueError) as e:
            error(__name__, 32001, e)
            valid = 0

        subtitle_path = os.path.join(__temp__, f"{str(uuid.uuid4())}.{self.sub_format}")
       
        if (valid==1):
            tmp_file = open(subtitle_path, "w" + "b")
            tmp_file.write(self.file["content"])
            tmp_file.close()
        

        list_item = xbmcgui.ListItem(label=subtitle_path)
        xbmcplugin.addDirectoryItem(handle=self.handle, url=subtitle_path, listitem=list_item, isFolder=False)

        return

        """old code"""
        # subs = Download(params["ID"], params["link"], params["format"])
        # for sub in subs:
        #    listitem = xbmcgui.ListItem(label=sub)
        #    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=sub, listitem=listitem, isFolder=False)

    def list_subtitles(self):
        """TODO rewrite using new data. do not forget Series/Episodes"""
        for subtitle in self.subtitles:
            attributes = subtitle["attributes"]
            language = convert_language(attributes["language"], True)
            log(__name__, attributes)
            clean_name = clean_feature_release_name(attributes["feature_details"]["title"], attributes["release"],
                                                    attributes["feature_details"]["movie_name"])
            list_item = xbmcgui.ListItem(label=language,
                                         label2=clean_name)
            list_item.setArt({
                "icon": str(int(round(float(attributes["ratings"]) / 2))),
                "thumb": get_flag(attributes["language"])})
            list_item.setProperty("sync", "true" if ("moviehash_match" in attributes and attributes["moviehash_match"]) else "false")
            list_item.setProperty("hearing_imp", "true" if attributes["hearing_impaired"] else "false")
            """TODO take care of multiple cds id&id or something"""
            url = f"plugin://{__scriptid__}/?action=download&id={attributes['files'][0]['file_id']}"

            xbmcplugin.addDirectoryItem(handle=self.handle, url=url, listitem=list_item, isFolder=False)
        xbmcplugin.endOfDirectory(self.handle)
