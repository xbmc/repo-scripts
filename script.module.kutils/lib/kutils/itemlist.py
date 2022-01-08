# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcplugin
from kutils import utils
from kutils import addon

SORTS = {"none": xbmcplugin.SORT_METHOD_NONE,
         "unsorted": xbmcplugin.SORT_METHOD_UNSORTED,
         "label": xbmcplugin.SORT_METHOD_LABEL,
         "label_ignore_the": xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE,
         "label_ignore_folders": xbmcplugin.SORT_METHOD_LABEL_IGNORE_FOLDERS,
         "date": xbmcplugin.SORT_METHOD_DATE,
         "size": xbmcplugin.SORT_METHOD_SIZE,
         "file": xbmcplugin.SORT_METHOD_FILE,
         "drive_type": xbmcplugin.SORT_METHOD_DRIVE_TYPE,
         "tracknum": xbmcplugin.SORT_METHOD_TRACKNUM,
         "duration": xbmcplugin.SORT_METHOD_DURATION,
         "video_title": xbmcplugin.SORT_METHOD_VIDEO_TITLE,
         "title": xbmcplugin.SORT_METHOD_TITLE,
         "title_ignore_the": xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
         "artist": xbmcplugin.SORT_METHOD_ARTIST,
         "artist_ignore_the": xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE,
         "album": xbmcplugin.SORT_METHOD_ALBUM,
         "album_ignore_the": xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE,
         "genre": xbmcplugin.SORT_METHOD_GENRE,
         "year": xbmcplugin.SORT_METHOD_VIDEO_YEAR,
         "rating": xbmcplugin.SORT_METHOD_VIDEO_RATING,
         "program_count": xbmcplugin.SORT_METHOD_PROGRAM_COUNT,
         "playlist_order": xbmcplugin.SORT_METHOD_PLAYLIST_ORDER,
         "episode": xbmcplugin.SORT_METHOD_EPISODE,
         "sorttitle": xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE,
         "sorttitle_ignore_the": xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE_IGNORE_THE,
         "productioncode": xbmcplugin.SORT_METHOD_PRODUCTIONCODE,
         "song_rating": xbmcplugin.SORT_METHOD_SONG_RATING,
         "mpaa": xbmcplugin.SORT_METHOD_MPAA_RATING,
         "video_runtime": xbmcplugin.SORT_METHOD_VIDEO_RUNTIME,
         "studio": xbmcplugin.SORT_METHOD_STUDIO,
         "studio_ignore_the": xbmcplugin.SORT_METHOD_STUDIO_IGNORE_THE,
         "bitrate": xbmcplugin.SORT_METHOD_BITRATE,
         "listeners": xbmcplugin.SORT_METHOD_LISTENERS,
         "country": xbmcplugin.SORT_METHOD_COUNTRY,
         "dateadded": xbmcplugin.SORT_METHOD_DATEADDED,
         "fullpath": xbmcplugin.SORT_METHOD_FULLPATH,
         "lastplayed": xbmcplugin.SORT_METHOD_LASTPLAYED,
         "playcount": xbmcplugin.SORT_METHOD_PLAYCOUNT,
         "channel": xbmcplugin.SORT_METHOD_CHANNEL,
         "date_taken": xbmcplugin.SORT_METHOD_DATE_TAKEN,
         "userrating": xbmcplugin.SORT_METHOD_VIDEO_USER_RATING}


class ItemList:

    def __init__(self, items=None, content_type="", name="", sorts=None, totals=None, properties=None):
        self.name = name
        self.content_type = content_type
        self.totals = totals
        self.total_pages = 1
        self._items = items if items else []
        self.sorts = sorts if sorts else []
        self._properties = properties if properties else []
        self.local_first = True
        self.sortkey = False
        self.next_page_token = None
        self.prev_page_token = None

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __cmp__(self, other):
        return len(self) - len(other)

    def __bool__(self):
        return len(self._items) > 0

    def __repr__(self):
        return "Itemlist with length %s. Content type: %s" % (len(self._items), self.content_type)

    def __add__(self, other):
        return ItemList(items=self._items + list(other.items()),
                        content_type=self.content_type,
                        name=self.name,
                        sorts=self.sorts,
                        properties=self._properties)

    def __iadd__(self, other):
        self._items += list(other.items())
        return self

    def prettify(self):
        """
        log a formatted list of all items
        """
        for item in self._items:
            utils.log(item)

    def items(self):
        return self._items

    def append(self, item):
        self._items.append(item)

    def remove(self, index):
        self._items.remove(index)

    def set_name(self, name):
        self.name = name

    def set_content(self, content_type):
        self.content_type = content_type

    def set_totals(self, totals):
        self.totals = totals

    def set_total_pages(self, total_pages):
        self.total_pages = total_pages

    def set_sorts(self, sorts):
        self.sorts = sorts

    def set_properties(self, properties):
        self._properties = properties

    def update_properties(self, properties):
        self._properties.update({k: v for k, v in properties.items() if v})

    def set_property(self, key, value):
        self._properties[key] = value

    def get_property(self, key):
        value = self._properties.get(key)
        return value if value else ""

    def create_listitems(self):
        """
        returns list with xbmcgui listitems
        """
        return [item.get_listitem() for item in self._items] if self._items else []

    def set_plugin_list(self, handle):
        """
        populate plugin list with *handle, set sorts and content
        """
        # these fixed sortmethods are only temporary
        if self.content_type == "tvshows":
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        elif self.content_type == "episodes":
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        elif self.content_type == "movies":
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_TITLE)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
            xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_VIDEO_RATING)
        for item in self.sorts:
            xbmcplugin.addSortMethod(handle, SORTS[item])
        if self.content_type:
            xbmcplugin.setContent(handle, self.content_type)
        items = [(i.get_path(), i.get_listitem(), i.is_folder()) for i in self._items]
        xbmcplugin.addDirectoryItems(handle=handle,
                                     items=items,
                                     totalItems=len(items))
        xbmcplugin.setPluginFanart(handle, addon.FANART)
        xbmcplugin.endOfDirectory(handle)

    def sort(self):
        """
        sort based on self.sortkey and self.localfirst
        """
        self._items = sorted(self._items,
                             key=lambda k: k.get_info(self.sortkey),
                             reverse=True)
        if self.local_first:
            local_items = [i for i in self._items if i.get_info("dbid")]
            remote_items = [i for i in self._items if not i.get_info("dbid")]
            self._items = local_items + remote_items

    def reduce(self, key="job"):
        """
        remove duplicate listitems (based on property "id") and merge their property with key *key
        """
        ids = []
        merged_items = []
        for item in self._items:
            id_ = item.get_property("id")
            if id_ not in ids:
                ids.append(id_)
                merged_items.append(item)
            else:
                index = ids.index(id_)
                if key in merged_items[index]:
                    merged_items[index][key] = merged_items[index][key] + " / " + str(item[key])
        self._items = merged_items
        return self
