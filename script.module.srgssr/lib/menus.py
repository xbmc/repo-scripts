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

from urllib.parse import quote_plus

import datetime
import json
import re
import xbmcgui
import xbmcplugin

import utils


class MenuBuilder:
    """Handles menu-related functionality for the plugin."""

    def __init__(self, srgssr_instance):
        self.srgssr = srgssr_instance
        self.handle = srgssr_instance.handle

    def build_main_menu(self, identifiers=[]):
        """
        Builds the main menu of the plugin:

        Keyword arguments:
        identifiers  -- A list of strings containing the identifiers
                        of the menus to display.
        """
        self.srgssr.log("build_main_menu")

        def display_item(item):
            return item in identifiers and self.srgssr.get_boolean_setting(item)

        main_menu_list = [
            {
                # All shows
                "identifier": "All_Shows",
                "name": self.srgssr.plugin_language(30050),
                "mode": 10,
                "displayItem": display_item("All_Shows"),
                "icon": self.srgssr.icon,
            },
            {
                # Favourite shows
                "identifier": "Favourite_Shows",
                "name": self.srgssr.plugin_language(30051),
                "mode": 11,
                "displayItem": display_item("Favourite_Shows"),
                "icon": self.srgssr.icon,
            },
            {
                # Newest favourite shows
                "identifier": "Newest_Favourite_Shows",
                "name": self.srgssr.plugin_language(30052),
                "mode": 12,
                "displayItem": display_item("Newest_Favourite_Shows"),
                "icon": self.srgssr.icon,
            },
            {
                # Homepage
                "identifier": "Homepage",
                "name": self.srgssr.plugin_language(30060),
                "mode": 200,
                "displayItem": display_item("Homepage"),
                "icon": self.srgssr.icon,
            },
            {
                # Topics
                "identifier": "Topics",
                "name": self.srgssr.plugin_language(30058),
                "mode": 13,
                "displayItem": display_item("Topics"),
                "icon": self.srgssr.icon,
            },
            {
                # Shows by date
                "identifier": "Shows_By_Date",
                "name": self.srgssr.plugin_language(30057),
                "mode": 17,
                "displayItem": display_item("Shows_By_Date"),
                "icon": self.srgssr.icon,
            },
            {
                # Live TV
                "identifier": "Live_TV",
                "name": self.srgssr.plugin_language(30072),
                "mode": 26,
                "displayItem": False,  # currently not supported
                "icon": self.srgssr.icon,
            },
            {
                # SRF.ch live
                "identifier": "SRF_Live",
                "name": self.srgssr.plugin_language(30070),
                "mode": 18,
                "displayItem": False,  # currently not supported
                "icon": self.srgssr.icon,
            },
            {
                # Search
                "identifier": "Search",
                "name": self.srgssr.plugin_language(30085),
                "mode": 27,
                "displayItem": display_item("Search"),
                "icon": self.srgssr.icon,
            },
            {
                # YouTube
                "identifier": f"{self.srgssr.bu.upper()}_YouTube",
                "name": self.srgssr.plugin_language(30074),
                "mode": 30,
                "displayItem": display_item(f"{self.srgssr.bu.upper()}_YouTube"),
                "icon": self.srgssr.get_youtube_icon(),
            },
        ]
        folders = [item for item in main_menu_list if item["identifier"] in identifiers]
        self.build_folder_menu(folders)

    def build_folder_menu(self, folders):
        """
        Builds a menu from a list of folder dictionaries. Each dictionary
        must have the key 'name' and can have the keys 'identifier', 'mode',
        'displayItem', 'icon', 'purl' (a dictionary to build the plugin url).
        """
        for item in folders:
            if item.get("displayItem"):
                list_item = xbmcgui.ListItem(label=item["name"])
                list_item.setProperty("IsPlayable", "false")
                list_item.setArt({"thumb": item["icon"], "fanart": self.srgssr.fanart})
                purl_dict = item.get("purl", {})
                mode = purl_dict.get("mode") or item.get("mode")
                uname = purl_dict.get("name") or item.get("identifier")
                purl = self.srgssr.build_url(mode=mode, name=uname)
                xbmcplugin.addDirectoryItem(
                    handle=self.handle, url=purl, listitem=list_item, isFolder=True
                )

    def build_menu_apiv3(
        self,
        queries,
        mode=1000,
        page=1,
        page_hash=None,
        is_show=False,
        whitelist_ids=None,
    ):
        """
        Builds a menu based on the API v3, which is supposed to be more stable

        Keyword arguments:
        queries       -- the query string or a list of several queries
        mode          -- mode for the URL of the next folder
        page          -- current page; if page is set to 0, do not build
                         a next page button
        page_hash     -- cursor for fetching the next items
        is_show       -- indicates if the menu contains only shows
        whitelist_ids -- list of ids that should be displayed, if it is set
                         to `None` it will be ignored
        """
        if isinstance(queries, list):
            # Build a combined and sorted list for several queries
            items = []
            for query in queries:
                data = json.loads(self.srgssr.open_url(self.srgssr.apiv3_url + query))
                if data:
                    data = (
                        utils.try_get(data, ["data", "data"], list, [])
                        or utils.try_get(data, ["data", "medias"], list, [])
                        or utils.try_get(data, ["data", "results"], list, [])
                        or utils.try_get(data, "data", list, [])
                    )
                    for item in data:
                        items.append(item)

            items.sort(key=lambda item: item["date"], reverse=True)
            for item in items:
                self.build_entry_apiv3(
                    item, is_show=is_show, whitelist_ids=whitelist_ids
                )
            return

        if page_hash:
            cursor = page_hash
        else:
            cursor = None

        if cursor:
            symb = "&" if "?" in queries else "?"
            url = f"{self.srgssr.apiv3_url}{queries}{symb}next={cursor}"
            data = json.loads(self.srgssr.open_url(url))
        else:
            data = json.loads(self.srgssr.open_url(self.srgssr.apiv3_url + queries))
        cursor = utils.try_get(data, "next") or utils.try_get(data, ["data", "next"])

        try:
            data = data["data"]
        except Exception:
            self.srgssr.log("No media found.")
            return

        items = (
            utils.try_get(data, "data", list, [])
            or utils.try_get(data, "medias", list, [])
            or utils.try_get(data, "results", list, [])
            or data
        )

        for item in items:
            self.build_entry_apiv3(item, is_show=is_show, whitelist_ids=whitelist_ids)

        if cursor:
            if page in (0, "0"):
                return

            # Next page urls containing the string 'urns=' do not work
            # properly. So in this case prevent the next page button from
            # being created. Note that might lead to not having a next
            # page butten where there should be one.
            if "urns=" in cursor:
                return

            if page:
                url = self.srgssr.build_url(
                    mode=mode, name=queries, page=int(page) + 1, page_hash=cursor
                )
            else:
                url = self.srgssr.build_url(
                    mode=mode, name=queries, page=2, page_hash=cursor
                )

            next_item = xbmcgui.ListItem(
                label=">> " + self.srgssr.language(30073)
            )  # Next page
            next_item.setProperty("IsPlayable", "false")
            xbmcplugin.addDirectoryItem(self.handle, url, next_item, isFolder=True)

    def build_all_shows_menu(self, favids=None):
        """
        Builds a list of folders containing the names of all the current
        shows.

        Keyword arguments:
        favids -- A list of show ids (strings) representing the favourite
                  shows. If such a list is provided, only the folders for
                  the shows on that list will be build. (default: None)
        """
        self.srgssr.log("build_all_shows_menu")
        self.build_menu_apiv3("shows", is_show=True, whitelist_ids=favids)

    def build_favourite_shows_menu(self):
        """
        Builds a list of folders for the favourite shows.
        """
        self.srgssr.log("build_favourite_shows_menu")
        self.build_all_shows_menu(
            favids=self.srgssr.storage_manager.read_favourite_show_ids()
        )

    def build_topics_menu(self):
        """
        Builds a menu containing the topics from the SRGSSR API.
        """
        self.build_menu_apiv3("topics")

    def build_newest_favourite_menu(self, page=1):
        """
        Builds a Kodi list of the newest favourite shows.

        Keyword arguments:
        page -- an integer indicating the current page on the
                list (default: 1)
        """
        self.srgssr.log("build_newest_favourite_menu")
        show_ids = self.srgssr.storage_manager.read_favourite_show_ids()
        queries = []
        for sid in show_ids:
            queries.append("videos-by-show-id?showId=" + sid)
        return self.build_menu_apiv3(queries)

    def build_homepage_menu(self):
        """
        Builds the homepage menu.
        """
        self.build_menu_from_page(
            self.srgssr.playtv_url,
            (
                "state",
                "loaderData",
                "play-now",
                "initialData",
                "pacPageConfigs",
                "landingPage",
                "sections",
            ),
        )

    def build_menu_from_page(self, url, path):
        """
        Builds a menu by extracting some content directly from a website.

        Keyword arguments:
        url     -- the url of the website
        path    -- the path to the relevant data in the json (as tuple
                   or list of strings)
        """
        html = self.srgssr.open_url(url)
        m = re.search(self.srgssr.data_regex, html)
        if not m:
            self.srgssr.log("build_menu_from_page: No data found in html")
            return
        content = m.groups()[0]
        try:
            js = json.loads(content)
        except Exception:
            self.srgssr.log("build_menu_from_page: Invalid json")
            return
        data = utils.try_get(js, path, list, [])
        if not data:
            self.srgssr.log("build_menu_from_page: Could not find any data in json")
            return
        for elem in data:
            try:
                id = elem["id"]
                section_type = elem["sectionType"]
                title = utils.try_get(elem, ("representation", "title"))
                if section_type in (
                    "MediaSection",
                    "ShowSection",
                    "MediaSectionWithShow",
                ):
                    if (
                        section_type == "MediaSection"
                        and not title
                        and utils.try_get(elem, ("representation", "name"))
                        == "HeroStage"
                    ):
                        title = self.srgssr.language(30053)
                    if not title:
                        continue
                    list_item = xbmcgui.ListItem(label=title)
                    list_item.setArt(
                        {
                            "thumb": self.srgssr.icon,
                            "fanart": self.srgssr.fanart,
                        }
                    )
                    if section_type == "MediaSection":
                        name = f"media-section?sectionId={id}"
                    elif section_type == "ShowSection":
                        name = f"show-section?sectionId={id}"
                    elif section_type == "MediaSectionWithShow":
                        name = f"media-section-with-show?sectionId={id}"
                    url = self.srgssr.build_url(mode=1000, name=name, page=1)
                    xbmcplugin.addDirectoryItem(
                        self.handle, url, list_item, isFolder=True
                    )
            except Exception:
                pass

    def build_episode_menu(
        self, video_id_or_urn, include_segments=True, segment_option=False
    ):
        """
        Builds a list entry for a episode by a given video id.
        The segment entries for that episode can be included too.
        The video id can be an id of a segment. In this case an
        entry for the segment will be created.

        Keyword arguments:
        video_id_or_urn  -- the video id or the urn
        include_segments -- indicates if the segments (if available) of the
                            video should be included in the list
                            (default: True)
        segment_option   -- Which segment option to use.
                            (default: False)
        """
        self.srgssr.log(f"build_episode_menu, video_id_or_urn = {video_id_or_urn}")
        if ":" in video_id_or_urn:
            json_url = (
                "https://il.srgssr.ch/integrationlayer/2.0/"
                f"mediaComposition/byUrn/{video_id_or_urn}.json"
            )
            video_id = video_id_or_urn.split(":")[-1]
        else:
            json_url = (
                f"https://il.srgssr.ch/integrationlayer/2.0/"
                f"{self.srgssr.bu}/mediaComposition/video/"
                f"{video_id_or_urn}.json"
            )
            video_id = video_id_or_urn
        self.srgssr.log(f"build_episode_menu. Open URL {json_url}")

        # TODO: we might not want to catch this error
        # (error is better than empty menu)
        try:
            json_response = json.loads(self.srgssr.open_url(json_url))
        except Exception:
            self.srgssr.log(
                f"build_episode_menu: Cannot open json for {video_id_or_urn}."
            )
            return

        chapter_urn = utils.try_get(json_response, "chapterUrn")
        segment_urn = utils.try_get(json_response, "segmentUrn")

        chapter_id = chapter_urn.split(":")[-1] if chapter_urn else None
        segment_id = segment_urn.split(":")[-1] if segment_urn else None

        if not chapter_id:
            self.srgssr.log(
                f"build_episode_menu: No valid chapter URN \
                available for video_id {video_id}"
            )
            return

        show_image_url = utils.try_get(json_response, ["show", "imageUrl"])
        show_poster_image_url = utils.try_get(json_response, ["show", "posterImageUrl"])

        json_chapter_list = utils.try_get(
            json_response, "chapterList", data_type=list, default=[]
        )
        json_chapter = None
        for ind, chapter in enumerate(json_chapter_list):
            if utils.try_get(chapter, "id") == chapter_id:
                json_chapter = chapter
                break
        if not json_chapter:
            self.srgssr.log(
                f"build_episode_menu: No chapter ID found \
                for video_id {video_id}"
            )
            return

        # TODO: Simplify
        json_segment_list = utils.try_get(
            json_chapter, "segmentList", data_type=list, default=[]
        )
        if video_id == chapter_id:
            if include_segments:
                # Generate entries for the whole video and
                # all the segments of this video.
                self.build_entry(
                    json_chapter,
                    show_image_url=show_image_url,
                    show_poster_image_url=show_poster_image_url,
                )

                for segment in json_segment_list:
                    self.build_entry(
                        segment,
                        show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url,
                    )
            else:
                if segment_option and json_segment_list:
                    # Generate a folder for the video
                    self.build_entry(
                        json_chapter,
                        is_folder=True,
                        show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url,
                    )
                else:
                    # Generate a simple playable item for the video
                    self.build_entry(
                        json_chapter,
                        show_image_url=show_image_url,
                        show_poster_image_url=show_poster_image_url,
                    )
        else:
            json_segment = None
            for segment in json_segment_list:
                if utils.try_get(segment, "id") == segment_id:
                    json_segment = segment
                    break
            if not json_segment:
                self.srgssr.log(
                    f"build_episode_menu: No segment ID found \
                    for video_id {video_id}"
                )
                return
            # Generate a simple playable item for the video
            self.build_entry(
                json_segment,
                show_image_url=show_image_url,
                show_poster_image_url=show_poster_image_url,
            )

    def build_entry_apiv3(self, data, is_show=False, whitelist_ids=None):
        """
        Builds a entry from a APIv3 JSON data entry.

        Keyword arguments:
        data            -- The JSON entry
        whitelist_ids   -- If not `None` only items with an id that is in that
                           list will be generated (default: None)
        """
        urn = data["urn"]
        self.srgssr.log(f"build_entry_apiv3: urn = {urn}")
        title = utils.try_get(data, "title")

        # Add the date & time to the title for upcoming livestreams:
        if utils.try_get(data, "type") == "SCHEDULED_LIVESTREAM":
            dt = utils.try_get(data, "date")
            if dt:
                dt = utils.parse_datetime(dt)
            if dt:
                dts = dt.strftime("(%d.%m.%Y, %H:%M)")
                title = dts + " " + title

        media_id = utils.try_get(data, "id")
        if whitelist_ids is not None and media_id not in whitelist_ids:
            return
        description = utils.try_get(data, "description")
        lead = utils.try_get(data, "lead")
        image_url = utils.try_get(data, "imageUrl")
        poster_image_url = utils.try_get(data, "posterImageUrl")
        show_image_url = utils.try_get(data, ["show", "imageUrl"])
        show_poster_image_url = utils.try_get(data, ["show", "posterImageUrl"])
        duration = utils.try_get(data, "duration", int, default=None)
        if duration:
            duration //= 1000
        date = utils.try_get(data, "date")
        kodi_date_string = date
        dto = utils.parse_datetime(date)
        kodi_date_string = dto.strftime("%Y-%m-%d") if dto else None
        label = title or urn
        list_item = xbmcgui.ListItem(label=label)
        list_item.setInfo(
            "video",
            {
                "title": title,
                "plot": description or lead,
                "plotoutline": lead or description,
                "duration": duration,
                "aired": kodi_date_string,
            },
        )
        if is_show:
            poster = (
                show_poster_image_url or poster_image_url or show_image_url or image_url
            )
        else:
            poster = (
                image_url or poster_image_url or show_poster_image_url or show_image_url
            )
        list_item.setArt(
            {
                "thumb": image_url,
                "poster": poster,
                "fanart": show_image_url or self.srgssr.fanart,
                "banner": show_image_url or image_url,
            }
        )
        url = self.srgssr.build_url(mode=100, name=urn)
        is_folder = True

        xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=is_folder)

    def build_menu_by_urn(self, urn):
        """
        Builds a menu from an urn.

        Keyword arguments:
        urn     -- The urn (e.g. 'urn:srf:show:<id>' or 'urn:rts:video:<id>')
        """
        id = urn.split(":")[-1]
        if "show" in urn:
            self.build_menu_apiv3(f"videos-by-show-id?showId={id}")
        elif "swisstxt" in urn:
            # Do not include segments for livestreams,
            # they fail to play.
            self.build_episode_menu(urn, include_segments=False)
        elif "video" in urn:
            self.build_episode_menu(id)
        elif "topic" in urn:
            self.build_menu_from_page(
                self.srgssr.playtv_url,
                (
                    "state",
                    "loaderData",
                    "play-now",
                    "initialData",
                    "pacPageConfigs",
                    "topicPages",
                    urn,
                    "sections",
                ),
            )

    def build_entry(
        self,
        json_entry,
        is_folder=False,
        fanart=None,
        urn=None,
        show_image_url=None,
        show_poster_image_url=None,
    ):
        """
        Builds an list item for a video or folder by giving the json part,
        describing this video.

        Keyword arguments:
        json_entry              -- the part of the json describing the video
        is_folder               -- indicates if the item is a folder
                                   (default: False)
        fanart                  -- fanart to be used instead of default image
        urn                     -- override urn from json_entry
        show_image_url          -- url of the image of the show
        show_poster_image_url   -- url of the poster image of the show
        """
        self.srgssr.log("build_entry")
        title = utils.try_get(json_entry, "title")
        vid = utils.try_get(json_entry, "id")
        description = utils.try_get(json_entry, "description")
        lead = utils.try_get(json_entry, "lead")
        image_url = utils.try_get(json_entry, "imageUrl")
        poster_image_url = utils.try_get(json_entry, "posterImageUrl")
        if not urn:
            urn = utils.try_get(json_entry, "urn")

        # RTS image links have a strange appendix '/16x9'.
        # This needs to be removed from the URL:
        image_url = re.sub(r"/\d+x\d+", "", image_url)

        duration = utils.try_get(json_entry, "duration", data_type=int, default=None)
        if duration:
            duration = duration // 1000
        else:
            duration = utils.get_duration(utils.try_get(json_entry, "duration"))

        date_string = utils.try_get(json_entry, "date")
        dto = utils.parse_datetime(date_string)
        kodi_date_string = dto.strftime("%Y-%m-%d") if dto else None

        list_item = xbmcgui.ListItem(label=title)
        list_item.setInfo(
            "video",
            {
                "title": title,
                "plot": description or lead,
                "plotoutline": lead,
                "duration": duration,
                "aired": kodi_date_string,
            },
        )

        if not fanart:
            fanart = image_url

        poster = (
            image_url or poster_image_url or show_poster_image_url or show_image_url
        )
        list_item.setArt(
            {
                "thumb": image_url,
                "poster": poster,
                "fanart": show_image_url or fanart,
                "banner": show_image_url or image_url,
            }
        )

        subs = utils.try_get(json_entry, "subtitleList", data_type=list, default=[])
        if subs:
            subtitle_list = [
                utils.try_get(x, "url")
                for x in subs
                if utils.try_get(x, "format") == "VTT"
            ]
            if subtitle_list:
                list_item.setSubtitles(subtitle_list)
            else:
                self.srgssr.log(f"No WEBVTT subtitles found for video id {vid}.")

        # TODO:
        # Prefer urn over vid as it contains already all data
        # (bu, media type, id) and will be used anyway for the stream lookup
        # name = urn if urn else vid
        name = vid

        if is_folder:
            list_item.setProperty("IsPlayable", "false")
            url = self.srgssr.build_url(mode=21, name=name)
        else:
            list_item.setProperty("IsPlayable", "true")
            # TODO: Simplify this, use URN instead of video id everywhere
            if "swisstxt" in urn:
                url = self.srgssr.build_url(mode=50, name=urn)
            else:
                url = self.srgssr.build_url(mode=50, name=name)
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, isFolder=is_folder)

    def build_dates_overview_menu(self):
        """
        Builds the menu containing the folders for episodes of
        the last 10 days.
        """
        self.srgssr.log("build_dates_overview_menu")

        def folder_name(dato):
            """
            Generates a Kodi folder name from an date object.

            Keyword arguments:
            dato -- a date object
            """
            weekdays = (
                self.srgssr.language(30060),  # Monday
                self.srgssr.language(30061),  # Tuesday
                self.srgssr.language(30062),  # Wednesday
                self.srgssr.language(30063),  # Thursday
                self.srgssr.language(30064),  # Friday
                self.srgssr.language(30065),  # Saturday
                self.srgssr.language(30066),  # Sunday
            )
            today = datetime.date.today()
            if dato == today:
                name = self.srgssr.language(30058)  # Today
            elif dato == today + datetime.timedelta(-1):
                name = self.srgssr.language(30059)  # Yesterday
            else:
                name = "%s, %s" % (weekdays[dato.weekday()], dato.strftime("%d.%m.%Y"))
            return name

        current_date = datetime.date.today()
        number_of_days = 7

        for i in range(number_of_days):
            dato = current_date + datetime.timedelta(-i)
            list_item = xbmcgui.ListItem(label=folder_name(dato))
            list_item.setArt({"thumb": self.srgssr.icon, "fanart": self.srgssr.fanart})
            name = dato.strftime("%d-%m-%Y")
            purl = self.srgssr.build_url(mode=24, name=name)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=purl, listitem=list_item, isFolder=True
            )

        choose_item = xbmcgui.ListItem(label=self.srgssr.language(30071))  # Choose date
        choose_item.setArt({"thumb": self.srgssr.icon, "fanart": self.srgssr.fanart})
        purl = self.srgssr.build_url(mode=25)
        xbmcplugin.addDirectoryItem(
            handle=self.handle, url=purl, listitem=choose_item, isFolder=True
        )

    def pick_date(self):
        """
        Opens a date choosing dialog and lets the user input a date.
        Redirects to the date menu of the chosen date.
        In case of failure or abortion redirects to the date
        overview menu.
        """
        date_picker = xbmcgui.Dialog().numeric(
            1, self.srgssr.language(30071), None
        )  # Choose date
        if date_picker is not None:
            date_elems = date_picker.split("/")
            try:
                day = int(date_elems[0])
                month = int(date_elems[1])
                year = int(date_elems[2])
                chosen_date = datetime.date(year, month, day)
                name = chosen_date.strftime("%d-%m-%Y")
                self.build_date_menu(name)
            except (ValueError, IndexError):
                self.srgssr.log("pick_date: Invalid date chosen.")
                self.build_dates_overview_menu()
        else:
            self.build_dates_overview_menu()

    def build_date_menu(self, date_string):
        """
        Builds a list of episodes of a given date.

        Keyword arguments:
        date_string -- a string representing date in the form %d-%m-%Y,
                       e.g. 12-03-2017
        """
        self.srgssr.log(f"build_date_menu, date_string = {date_string}")

        # Note: We do not use `build_menu_apiv3` here because the structure
        # of the response is quite different from other typical responses.
        # If it is possible to integrate this into `build_menu_apiv3` without
        # too many changes, it might be a good idea.
        mode = 60
        elems = date_string.split("-")
        query = (
            f"tv-program-guide?date={elems[2]}-{elems[1]}-{elems[0]}"
            f"&businessUnits={self.srgssr.bu}"
        )
        js = json.loads(self.srgssr.open_url(self.srgssr.apiv3_url + query))
        data = utils.try_get(js, "data", list, [])
        for item in data:
            if not isinstance(item, dict):
                continue
            channel = utils.try_get(item, "channel", data_type=dict, default={})
            name = utils.try_get(channel, "title")
            if not name:
                continue
            image = utils.try_get(channel, "imageUrl")
            list_item = xbmcgui.ListItem(label=name)
            list_item.setProperty("IsPlayable", "false")
            list_item.setArt({"thumb": image, "fanart": image})
            channel_date_id = name.replace(" ", "-") + "_" + date_string
            cache_id = self.srgssr.addon_id + "." + channel_date_id
            programs = utils.try_get(item, "programList", data_type=list, default=[])
            self.srgssr.cache.set(cache_id, programs)
            self.srgssr.log(f"build_date_menu: Cache set with id = {cache_id}")
            url = self.srgssr.build_url(mode=mode, name=cache_id)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True
            )

    def build_specific_date_menu(self, cache_id):
        """
        Builds a list of available videos from a specific channel
        and specific date given by cache_id from `build_date_menu`.

        Keyword arguments:
        cache_id -- cache id set by `build_date_menu`
        """
        self.srgssr.log(f"build_specific_date_menu, cache_id = {cache_id}")
        program_list = self.srgssr.cache.get(cache_id)

        # videos might be listed multiple times, but we only
        # want them a single time:
        already_seen = set()
        for pitem in program_list:
            media_urn = utils.try_get(pitem, "mediaUrn")
            if not media_urn or "video" not in media_urn:
                continue
            if media_urn in already_seen:
                continue
            already_seen.add(media_urn)
            name = utils.try_get(pitem, "title")
            image = utils.try_get(pitem, "imageUrl")
            subtitle = utils.try_get(pitem, "subtitle")
            list_item = xbmcgui.ListItem(label=name)
            list_item.setInfo("video", {"plotoutline": subtitle})
            list_item.setArt({"thumb": image, "fanart": image})
            url = self.srgssr.build_url(mode=100, name=media_urn)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True
            )

    def build_search_menu(self):
        """
        Builds a menu for searches.
        """
        items = [
            {
                # 'Search videos'
                "name": self.srgssr.language(30112),
                "mode": 28,
                "show": True,
                "icon": self.srgssr.icon,
            },
            {
                # 'Recently searched videos'
                "name": self.srgssr.language(30116),
                "mode": 70,
                "show": True,
                "icon": self.srgssr.icon,
            },
        ]
        for item in items:
            if not item["show"]:
                continue
            list_item = xbmcgui.ListItem(label=item["name"])
            list_item.setProperty("IsPlayable", "false")
            list_item.setArt({"thumb": item["icon"], "fanart": self.srgssr.fanart})
            url = self.srgssr.build_url(item["mode"])
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True
            )

    def build_recent_search_menu(self):
        """
        Lists folders for the most recent searches.
        """
        recent_searches = self.srgssr.storage_manager.read_searches(
            self.srgssr.fname_media_searches
        )
        mode = 28
        for search in recent_searches:
            list_item = xbmcgui.ListItem(label=search)
            list_item.setProperty("IsPlayable", "false")
            list_item.setArt({"thumb": self.srgssr.icon})
            url = self.srgssr.build_url(mode=mode, name=search)
            xbmcplugin.addDirectoryItem(
                handle=self.handle, url=url, listitem=list_item, isFolder=True
            )

    def build_search_media_menu(self, mode=28, name="", page=1, page_hash=""):
        """
        Sets up a search for media. If called without name, a dialog will
        show up for a search input. Then the search will be performed and
        the results will be shown in a menu.

        Keyword arguments:
        mode       -- the plugins mode (default: 28)
        name       -- the search name (default: '')
        page       -- the page number (default: 1)
        page_hash  -- the page hash when coming from a previous page
                      (default: '')
        """
        self.srgssr.log(
            f"build_search_media_menu, mode = {mode}, \
            name = {name}, page = {page}, page_hash = {page_hash}"
        )
        media_type = "video"
        if name:
            # `name` is provided by `next_page` folder or
            # by previously performed search
            query_string = name
            if not page_hash:
                # `name` is provided by previously performed search, so it
                # needs to be processed first
                query_string = quote_plus(query_string)
                query = f"search/media?searchTerm={query_string}"
        else:
            dialog = xbmcgui.Dialog()
            query_string = dialog.input(self.srgssr.language(30115))
            if not query_string:
                self.srgssr.log("build_search_media_menu: No input provided")
                return

            self.srgssr.storage_manager.write_search(
                self.srgssr.fname_media_searches, query_string
            )
            query_string = quote_plus(query_string)
            query = f"search/media?searchTerm={query_string}"

        query = f"{query}&mediaType={media_type}&includeAggregations=false"
        cursor = page_hash if page_hash else ""
        return self.build_menu_apiv3(query, page_hash=cursor)
