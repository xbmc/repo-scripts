# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

from urllib.parse import quote_plus, parse_qsl
from urllib.parse import urlparse as urlps

import os
import sys
import traceback
import datetime
import json
import requests

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

import simplecache

from play import Player
from storage import StorageManager
from menus import MenuBuilder
from youtube import YoutubeBuilder
import utils

ADDON_ID = "script.module.srgssr"
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME = REAL_SETTINGS.getAddonInfo("name")
ADDON_VERSION = REAL_SETTINGS.getAddonInfo("version")
ICON = REAL_SETTINGS.getAddonInfo("icon")
LANGUAGE = REAL_SETTINGS.getLocalizedString
TIMEOUT = 30

IDREGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+"

FAVOURITE_SHOWS_FILENAME = "favourite_shows.json"
RECENT_MEDIA_SEARCHES_FILENAME = "recently_searched_medias.json"
YOUTUBE_CHANNELS_FILENAME = "youtube_channels.json"


def get_params():
    """
    Parses the Kodi plugin URL and returns its parameters
    in a dictionary.
    """
    return dict(parse_qsl(sys.argv[2][1:]))


class SRGSSR:
    """
    Base class for all SRG SSR related plugins.
    Everything that can be done independently from the business unit
    (SRF, RTS, RSI, etc.) should be done here.
    """

    def __init__(self, plugin_handle, bu="srf", addon_id=ADDON_ID):
        self.handle = plugin_handle
        self.cache = simplecache.SimpleCache()
        self.real_settings = xbmcaddon.Addon(id=addon_id)
        self.bu = bu
        self.addon_id = addon_id
        self.icon = self.real_settings.getAddonInfo("icon")
        self.fanart = self.real_settings.getAddonInfo("fanart")
        self.language = LANGUAGE
        self.plugin_language = self.real_settings.getLocalizedString
        self.host_url = f"https://www.{bu}.ch"
        if bu == "swi":
            self.host_url = "https://play.swissinfo.ch"
        self.playtv_url = f"{self.host_url}/play/tv"
        self.apiv3_url = f"{self.host_url}/play/v3/api/{bu}/production/"
        self.data_regex = r"window.__remixContext\s*=\s*(.+?);\s*</script>"
        self.data_uri = f"special://home/addons/{self.addon_id}/resources/data"
        self.media_uri = f"special://home/addons/{self.addon_id}/resources/media"

        # Plugin options
        self.debug = self.get_boolean_setting("Enable_Debugging")
        self.prefer_hd = self.get_boolean_setting("Prefer_HD")

        # Special files:
        self.fname_favourite_shows = FAVOURITE_SHOWS_FILENAME
        self.fname_media_searches = RECENT_MEDIA_SEARCHES_FILENAME
        self.fname_youtube_channels = YOUTUBE_CHANNELS_FILENAME

        # Initialize helper classes
        self.menu_builder = MenuBuilder(self)
        self.player = Player(self)
        self.storage_manager = StorageManager(self)
        self.youtube_builder = YoutubeBuilder(self)

        # Delete temporary subtitle files urn*.vtt
        clean_dir = "special://temp"
        _, filenames = xbmcvfs.listdir(clean_dir)
        for filename in filenames:
            if filename.startswith("urn") and filename.endswith(".vtt"):
                xbmcvfs.delete(clean_dir + "/" + filename)

    def get_boolean_setting(self, setting):
        """
        Returns the boolean value of a specified setting.

        Keyword arguments
        setting  -- the setting option to check
        """
        return self.real_settings.getSetting(setting) == "true"

    def log(self, msg, level=xbmc.LOGDEBUG):
        """
        Logs a message using Kodi's logging interface.

        Keyword arguments:
        msg   -- the message to log
        level -- the logging level
        """
        if self.debug:
            if level == xbmc.LOGERROR:
                msg += " ," + traceback.format_exc()
            message = ADDON_ID + "-" + ADDON_VERSION + "-" + msg
            xbmc.log(msg=message, level=level)

    @staticmethod
    def build_url(mode=None, name=None, url=None, page_hash=None, page=None):
        """Build a URL for the Kodi plugin.

        Keyword arguments:
        mode      -- an integer representing the mode
        name      -- a string containing some information, e.g. a video id
        url       -- a plugin URL, if another plugin/script needs to called
        page_hash -- a string (used to get additional videos through the API)
        page      -- an integer used to indicate the current page in
                     the list of items
        """
        try:
            mode = str(mode)
        except Exception:
            pass
        try:
            page = str(page)
        except Exception:
            pass
        added = False
        queries = (url, mode, name, page_hash, page)
        query_names = ("url", "mode", "name", "page_hash", "page")
        purl = sys.argv[0]
        for query, qname in zip(queries, query_names):
            if query:
                add = "?" if not added else "&"
                qplus = quote_plus(query)
                purl += f"{add}{qname}={qplus}"
                added = True
        return purl

    def open_url(self, url, use_cache=True):
        """Open and read the content given by a URL.

        Keyword arguments:
        url       -- the URL to open as a string
        use_cache -- boolean to indicate if the cache provided by the
                     Kodi module SimpleCache should be used (default: True)
        """
        self.log("open_url, url = " + str(url))
        cache_response = (
            self.cache.get(f"{ADDON_NAME}.open_url, url = {url}") if use_cache else None
        )
        if not cache_response:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64; rv:136.0) "
                    "Gecko/20100101 Firefox/136.0"
                )
            }
            response = requests.get(url, headers=headers)
            if not response.ok:
                self.log(f"open_url: Failed to open url {url}")
                xbmcgui.Dialog().notification(ADDON_NAME, LANGUAGE(30100), ICON, 4000)
                return ""
            response.encoding = "UTF-8"
            self.cache.set(
                f"{ADDON_NAME}.open_url, url = {url}",
                response.text,
                expiration=datetime.timedelta(hours=2),
            )
            return response.text
        return self.cache.get(f"{ADDON_NAME}.open_url, url = {url}")

    def get_youtube_icon(self):
        path = os.path.join(
            # https://github.com/xbmc/xbmc/pull/19301
            xbmcvfs.translatePath(self.media_uri),
            "icon_youtube.png",
        )
        if os.path.exists(path):
            return path
        return self.icon

    def read_all_available_shows(self):
        """
        Downloads a list of all available shows and returns this list.

        This works for the business units 'srf', 'rts', 'rsi' and 'rtr', but
        not for 'swi'.
        """
        data = json.loads(self.open_url(self.apiv3_url + "shows"))
        return utils.try_get(data, "data", list, [])

    def get_auth_url(self, url, segment_data=None):
        """
        Returns the authenticated URL from a given stream URL.

        Keyword arguments:
        url -- a given stream URL
        """
        self.log(f"get_auth_url, url = {url}")
        spl = urlps(url).path.split("/")
        token = (
            json.loads(
                self.open_url(
                    f"https://tp.srgssr.ch/akahd/token?acl=/{spl[1]}/{spl[2]}/*",
                    use_cache=False,
                )
            )
            or {}
        )
        auth_params = token.get("token", {}).get("authparams")
        if auth_params:
            url += ("?" if "?" not in url else "&") + auth_params
        return url

    def get_subtitles(self, url, name):
        """
        Returns subtitles from an url
        Kodi does not accept m3u playlists for subtitles
        In this case a temporary with all chunks is built

        Keyword arguments:
        url      -- url with subtitle location
        name     -- name of temporary file if required
        """
        webvttbaseurl = None
        caption = None

        parsed_url = urlps(url)
        query_list = parse_qsl(parsed_url.query)
        for query in query_list:
            if query[0] == "caption":
                caption = query[1]
            elif query[0] == "webvttbaseurl":
                webvttbaseurl = query[1]

        if not caption or not webvttbaseurl:
            return None

        cap_comps = caption.split(":")
        lang = "." + cap_comps[1] if len(cap_comps) > 1 else ""
        sub_url = "https://" + webvttbaseurl + "/" + cap_comps[0]
        self.log("subtitle url: " + sub_url)
        if not sub_url.endswith(".m3u8"):
            return [sub_url]

        # Build temporary local file in case of m3u playlist
        sub_name = "special://temp/" + name + lang + ".vtt"
        if not xbmcvfs.exists(sub_name):
            m3u_base = sub_url.rsplit("/", 1)[0]
            m3u = self.open_url(sub_url, use_cache=False)
            sub_file = xbmcvfs.File(sub_name, "w")

            # Concatenate chunks and remove header on subsequent
            first = True
            for line in m3u.splitlines():
                if line.startswith("#"):
                    continue
                subs = self.open_url(m3u_base + "/" + line, use_cache=False)
                if first:
                    sub_file.write(subs)
                    first = False
                else:
                    i = 0
                    while i < len(subs) and not subs[i].isnumeric():
                        i += 1
                    sub_file.write("\n")
                    sub_file.write(subs[i:])

            sub_file.close()

        return [sub_name]

    def play_livestream(self, stream_url):
        """
        Plays a livestream, given a unauthenticated stream url.

        Keyword arguments:
        stream_url -- the stream url
        """
        auth_url = self.get_auth_url(stream_url)
        play_item = xbmcgui.ListItem("Live", path=auth_url)
        xbmcplugin.setResolvedUrl(self.handle, True, play_item)

    def manage_favourite_shows(self):
        """
        Opens a Kodi multiselect dialog to let the user choose
        his/her personal favourite show list.
        """
        show_list = self.read_all_available_shows()
        stored_favids = self.storage_manager.read_favourite_show_ids()
        names = [x["title"] for x in show_list]
        ids = [x["id"] for x in show_list]

        preselect_inds = []
        for stored_id in stored_favids:
            try:
                preselect_inds.append(ids.index(stored_id))
            except ValueError:
                pass
        ancient_ids = [x for x in stored_favids if x not in ids]

        dialog = xbmcgui.Dialog()
        # Choose your favourite shows
        selected_inds = dialog.multiselect(
            LANGUAGE(30069), names, preselect=preselect_inds
        )

        if selected_inds is not None:
            new_favids = [ids[ind] for ind in selected_inds]
            # Keep the old show ids:
            new_favids += ancient_ids

            self.storage_manager.write_favourite_show_ids(new_favids)
