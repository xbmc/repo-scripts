# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
from collections import MutableMapping
from time import strptime, strftime
import logging
import os
import re

# Kodi imports
import xbmcplugin
import xbmcgui

# Package imports
from codequick.script import Script
from codequick.support import auto_sort, build_path, logger_id, dispatcher
from codequick.utils import safe_path, ensure_unicode, ensure_native_str, unicode_type, long_type

__all__ = ["Listitem", "Art", "Info", "Stream", "Context", "Property", "Params"]

# Logger specific to this module
logger = logging.getLogger("%s.listitem" % logger_id)

# Listitem thumbnail locations
local_image = ensure_native_str(os.path.join(Script.get_info("path"), u"resources", u"media", u"{}"))
global_image = ensure_native_str(os.path.join(Script.get_info("path_global"), u"resources", u"media", u"{}"))

# Prefetch fanart/icon for use later
_fanart = Script.get_info("fanart")
fanart = ensure_native_str(_fanart) if os.path.exists(safe_path(_fanart)) else None
icon = ensure_native_str(Script.get_info("icon"))

# Stream type map to ensure proper stream value types
stream_type_map = {"duration": int,
                   "channels": int,
                   "aspect": float,
                   "height": int,
                   "width": int}

# Listing sort methods & sort mappings.
# Skips infolables that have no sortmethod and type is string. As by default they will be string anyway
infolable_map = {"artist": (None, xbmcplugin.SORT_METHOD_ARTIST_IGNORE_THE),
                 "studio": (ensure_native_str, xbmcplugin.SORT_METHOD_STUDIO_IGNORE_THE),
                 "title": (ensure_native_str, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE),
                 "album": (ensure_native_str, xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE),
                 "code": (ensure_native_str, xbmcplugin.SORT_METHOD_PRODUCTIONCODE),
                 "count": (int, xbmcplugin.SORT_METHOD_PROGRAM_COUNT),
                 "rating": (float, xbmcplugin.SORT_METHOD_VIDEO_RATING),
                 "mpaa": (ensure_native_str, xbmcplugin.SORT_METHOD_MPAA_RATING),
                 "year": (int, xbmcplugin.SORT_METHOD_VIDEO_YEAR),
                 "listeners": (int, xbmcplugin.SORT_METHOD_LISTENERS),
                 "tracknumber": (int, xbmcplugin.SORT_METHOD_TRACKNUM),
                 "episode": (int, xbmcplugin.SORT_METHOD_EPISODE),
                 "country": (ensure_native_str, xbmcplugin.SORT_METHOD_COUNTRY),
                 "genre": (None, xbmcplugin.SORT_METHOD_GENRE),
                 "date": (ensure_native_str, xbmcplugin.SORT_METHOD_DATE),
                 "size": (long_type, xbmcplugin.SORT_METHOD_SIZE),
                 "sortepisode": (int, None),
                 "sortseason": (int, None),
                 "userrating": (int, None),
                 "discnumber": (int, None),
                 "playcount": (int, None),
                 "overlay": (int, None),
                 "season": (int, None),
                 "top250": (int, None),
                 "setid": (int, None),
                 "dbid": (int, None)}

# Convenient function for adding to autosort set
auto_sort_add = auto_sort.add

# Map quality values to it's related video resolution, used by 'strea.hd'
quality_map = ((768, 576), (1280, 720), (1920, 1080), (3840, 2160))  # SD, 720p, 1080p, 4K

# Re.sub to remove formatting from label strings
strip_formatting = re.compile("\[[^\]]+?\]").sub

# Localized string Constants
YOUTUBE_CHANNEL = 32001
RELATED_VIDEOS = 32201
RECENT_VIDEOS = 32002
ALLVIDEOS = 32003
NEXT_PAGE = 33078
SEARCH = 137


class Params(MutableMapping):
    def __init__(self):
        self.raw_dict = {}

    def __getitem__(self, key):
        """
        Return the item from dictionary with given key. Raises a KeyError if key is not in the map.

        .. note:: All string values will be converted to unicode when returned.

        :param str key: The key required for requested value.
        :return: The saved value.
        :raise KeyError: If key is not in the dictionary.
        """
        value = self.raw_dict[key]
        return value.decode("utf8") if isinstance(value, bytes) else value

    def __setitem__(self, key, value):
        """
        Add a value to dictionary with given key.

        :param str key: The name to set.
        :param value: The value to add to key.
        """
        self.raw_dict[key] = value

    def __delitem__(self, key):
        """
        Remove key from dictionary.

        :param str key: The key to remove from dictionary.
        :raises KeyError: If key is not in the dictionary.
        """
        del self.raw_dict[key]

    def __contains__(self, key):
        return key in self.raw_dict

    def __len__(self):
        return len(self.raw_dict)

    def __iter__(self):
        return iter(self.raw_dict)

    def __str__(self):
        return str(self.raw_dict)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.raw_dict)


class Art(Params):
    """
    Dictionary like object that allows you to add various images. e.g. thumb, fanart.

    This class inherits all methods from :class:`collections.MutableMapping`.

    Expected art values are.
        * thumb
        * poster
        * banner
        * fanart
        * clearart
        * clearlogo
        * landscape
        * icon

    :example:
        >>> item = Listitem()
        >>> item.art["icon"] = "http://www.example.ie/icon.png"
        >>> item.art["fanart"] = "http://www.example.ie/fanart.jpg"
        >>> item.art.local_thumb("thumbnail.png")
    """

    def __init__(self, listitem):
        super(Art, self).__init__()
        self._listitem = listitem

    def __setitem__(self, key, value):
        if value:
            self.raw_dict[key] = ensure_native_str(value)
        else:
            logger.debug("Ignoring empty art value: '%s'", key)

    def local_thumb(self, image):
        """
        Set the thumbnail image to a image file, located in the add-on resources/media directory.
        
        :param image: Filename of the image.
        :type image: str or unicode
        """
        # Here we can't be sure if 'image' only contains ascii characters
        # So ensure_native_str is needed
        self.raw_dict["thumb"] = local_image.format(ensure_native_str(image))

    def global_thumb(self, image):
        """
        Set the thumbnail image to a image file, located in the codequick resources/media directory.
        
        The available global thumbnail images are.
            * next.png        - Arrow pointing to the right.
            * videos.png      - Circle with a play button in the middle.
            * search.png      - An image of a magnifying glass.
            * search_new.png  - A magnifying glass with plus symbol in the middle.
            * playlist.png    - Image of three bulleted lines.
            * recent.png      - Image of a clock.

        :param image: Filename of the image.
        :type image: str or unicode
        """
        # Here we know that 'image' should only contain ascii characters
        # So there is no neeed to use ensure_native_str
        self.raw_dict["thumb"] = global_image.format(image)

    def _close(self):
        if fanart and "fanart" not in self.raw_dict:
            self.raw_dict["fanart"] = fanart
        if "thumb" not in self.raw_dict:
            self.raw_dict["thumb"] = icon
        self._listitem.setArt(self.raw_dict)


class Info(Params):
    """
    Dictionary like object that allows you to add listitem infoLabels

    InfoLabels are like metadata for listitems. e.g. duration, genre, size, rating and or plot.
    They are also used for sorting purposes, sort methods will be automaticly selected.

    Some infolabels need to be of a given type e.g. size as long, rating as float.
    For the most part, this conversion will be done automatically.

    Example of what would happen is.
        * 'duration' would be converted to ``int`` and 'SORT_METHOD_VIDEO_RUNTIME' sort method will be selected.
        * 'size' would be converted to ``long`` and 'SORT_METHOD_SIZE' sort method will be selected.

    .. seealso:: The full list of listitem infoLabels can be found at.\n
        https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14

    .. note:: Duration infolabel value, can be either in seconds or as a 'hh:mm:ss' string.

    This class inherits all methods from :class:`collections.MutableMapping`.

    :examples:
        >>> item = Listitem()
        >>> item.info['genre'] = 'Science Fiction'
        >>> item.info['size'] = 256816
    """

    def __init__(self, listitem):
        super(Info, self).__init__()
        self._listitem = listitem

    def __setitem__(self, key, value):
        if value is None or value == "":
            logger.debug("Ignoring empty infolable: '%s'", key)
            return None

        # Convert duration into an integer
        elif key == "duration":
            auto_sort_add(xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
            self.raw_dict[key] = self._duration(value)
        else:
            # The sort method to set and the type that the infolabel should be
            type_converter, sort_type = infolable_map.get(key, (None, None))

            # Convert value to required type needed for this infolabel
            if type_converter:
                try:
                    value = type_converter(value)
                except ValueError:
                    msg = "value of '%s' for infolabel '%s', is not of type '%s'"
                    raise TypeError(msg % (value, key, type_converter))
                else:
                    self.raw_dict[key] = value

            elif isinstance(value, str):
                self.raw_dict[key] = value
            elif isinstance(value, unicode_type):
                # Only executes on python 2
                self.raw_dict[key] = value.encode("utf8")
            elif isinstance(value, bytes):
                # Only executes on python 3
                self.raw_dict[key] = value.decode("utf8")
            else:
                self.raw_dict[key] = value

            if sort_type:
                # Set the associated sort method for this infolabel
                auto_sort_add(sort_type)

    def date(self, date, date_format):
        """
        Set the date of the listitem.
        
        :param date: The date for the listitem.
        :type date: str or unicode
        :param str date_format: The format of the date as a strftime directive e.g. 'june 27, 2017' => '%B %d, %Y'
        
        .. seealso:: The List of date formats can be found at.\n
                    https://docs.python.org/2/library/time.html#time.strftime

        :example:
            >>> item = Listitem()
            >>> item.info.date('june 27, 2017', '%B %d, %Y')
        """
        converted_date = strptime(ensure_native_str(date), date_format)
        self.raw_dict["date"] = strftime("%d.%m.%Y", converted_date)  # 01.01.2017
        self.raw_dict["aired"] = strftime("%Y-%m-%d", converted_date)  # 2017-01-01
        self.raw_dict["year"] = strftime("%Y", converted_date)  # 2017
        auto_sort_add(xbmcplugin.SORT_METHOD_VIDEO_YEAR)
        auto_sort_add(xbmcplugin.SORT_METHOD_DATE)

    @staticmethod
    def _duration(duration):
        """
        Converts duration from a string of 'hh:mm:ss' into seconds.

        :param duration: The duration of stream.
        :type duration: int or str or unicode
        :returns: The duration converted to seconds.
        :rtype: int
        """
        if isinstance(duration, (str, unicode_type)):
            if ":" in duration or ";" in duration:
                # Split Time By Marker and Convert to Integer
                time_parts = duration.replace(";", ":").split(":")
                time_parts.reverse()
                duration = 0
                counter = 1

                # Multiply Each 'Time Delta' Segment by it's Seconds Equivalent
                for part in time_parts:
                    duration += int(part) * counter
                    counter *= 60
            else:
                # Convert to Interger
                duration = int(duration)

        return duration

    def _close(self, content_type):
        self._listitem.setInfo(content_type, self.raw_dict)


class Property(Params):
    def __init__(self, listitem):
        super(Property, self).__init__()
        self._listitem = listitem

    def __setitem__(self, key, value):
        if value:
            self.raw_dict[key] = ensure_unicode(value)
        else:
            logger.debug("Ignoring empty property: '%s'", key)

    def _close(self):
        for key, value in self.raw_dict:
            self._listitem.setProperty(key, value)


class Stream(Params):
    """
    Dictionary like object that allows you to add stream details. e.g. video_codec, audio_codec.

    Expected stream values are.
        * video_codec        - string (h264)
        * aspect             - float (1.78)
        * width              - integer (1280)
        * height             - integer (720)
        * channels           - integer (2)
        * audio_codec        - string (AAC)
        * audio_language     - string (en)
        * subtitle_language  - string (en)

    Type convertion will be done automatically so manual convertion is not required.

    This class inherits all methods from :class:`collections.MutableMapping`.

    :example:
        >>> item = Listitem()
        >>> item.stream['video_codec'] = 'h264'
        >>> item.stream['audio_codec'] = 'aac'
    """

    def __init__(self, listitem):
        super(Stream, self).__init__()
        self._listitem = listitem

    def __setitem__(self, key, value):
        if value is None:
            logger.debug("Ignoring empty stream detail value for: '%s'", key)
            return None

        # Ensure that value is of required type
        type_converter = stream_type_map.get(key, ensure_native_str)
        try:
            value = type_converter(value)
        except ValueError:
            msg = "Value of '%s' for stream info '%s', is not of type '%s'"
            raise TypeError(msg % (value, key, type_converter))
        else:
            self.raw_dict[key] = value

    def hd(self, quality, aspect=None):
        """
        Convenient method to set required stream info to show SD/HD/4K logos.

        The values witch are set are 'width', 'height' and 'aspect'.
        When no aspect ratio is given, then a ratio of '1.78'(16:9) is set when the quality is HD or greater.

        Quality options are.
            * 0 = 480p
            * 1 = 720p
            * 2 = 1080p
            * 3 = 4K.

        :param int quality: Quality of the stream.
        :param float aspect: [opt] The aspect ratio of the video.

        :example:
            >>> item = Listitem()
            >>> item.stream.hd(2, aspect=1.78) # 1080p
        """
        # Skip if value is None(Unknown), useful when passing a variable with unkown value
        if quality is None:
            return None

        # Set video resolution
        try:
            self.raw_dict["width"], self.raw_dict["height"] = quality_map[quality]
        except IndexError:
            raise ValueError("quality id must be within range (0 to 3): '{}'".format(quality))

        # Set the aspect ratio if one is given
        if aspect:
            self["aspect"] = aspect

        # Or set the aspect ratio to 16:9 for HD content and above
        elif self.raw_dict["height"] >= 720:
            self.raw_dict["aspect"] = 1.78

    def _close(self):
        video = {}
        subtitle = {}
        audio = {"channels": 2}
        # Populate the above dictionary with the appropriate key/value pairs
        for key, value in self.raw_dict.items():
            rkey = key.split("_")[-1]
            if key in ("video_codec", "aspect", "width", "height", "duration"):
                video[rkey] = value
            elif key in ("audio_codec", "audio_language", "channels"):
                audio[rkey] = value
            elif key == "subtitle_language":
                subtitle[rkey] = value
            else:
                raise KeyError("unknown stream detail key: '{}'".format(key))

        # Now we are ready to send the stream info to kodi
        if audio:
            self._listitem.addStreamInfo("audio", audio)
        if video:
            self._listitem.addStreamInfo("video", video)
        if subtitle:
            self._listitem.addStreamInfo("subtitle", subtitle)


class Context(list):
    """
    This class inherits all methods from the build-in data type :class:`list`.

    This is a list containing tuples consisting of label/function pairs.

    .. seealso:: The full list of built-in functions can be found at.\n
                 http://kodi.wiki/view/List_of_Built_In_Functions
    """

    def __init__(self, listitem):
        super(Context, self).__init__()
        self._listitem = listitem

    def related(self, callback, **query):
        """
        Convenient method to add a related videos context menu item.

        All this really does is set the label of the menu item for you.
        
        :param callback: The function that will be called when menu item is activated.
        :param query: [opt] Keyword arguments that will be passed on to callback function.
        """
        self.container(Script.localize(RELATED_VIDEOS), callback, **query)

    def container(self, label, callback, **query):
        """
        Convenient method to add a context menu item.

        :param label: The label of the context menu item.
        :param callback: The function that will be called when menu item is activated.
        :param query: [opt] Keyword arguments that will be passed on to callback function.
        """
        command = "XBMC.Container.Update(%s)" % build_path(callback.route.path, query)
        self.append((label, command))

    def _close(self):
        if self:
            self._listitem.addContextMenuItems(self)


class Listitem(object):
    """
    The listitem control is used for creating folder/video items within kodi.

    :param str content_type: [opt] Type of content been listed. e.g. video, music, pictures.
    """

    def __init__(self, content_type="video"):
        self.content_type = content_type
        self.callback = ""

        #: The underlining kodi listitem object, for advanced use.
        self.listitem = listitem = xbmcgui.ListItem()

        self.info = Info(listitem)
        """
        Dictionary like object for adding infoLabels.
        See :class:`listing.Info<codequick.listing.Info>` for more details.
        """

        self.art = Art(listitem)
        """
        Dictionary like object for adding listitem art.
        See :class:`listing.Art<codequick.listing.Art>` for more details.
        """

        self.stream = Stream(listitem)
        """
        Dictionary like object for adding stream details.
        See :class:`listing.Stream<codequick.listing.Stream>` for more details.
        """

        self.context = Context(listitem)
        """
        Dictionary like object for context menu items.
        See :class:`listing.Context<codequick.listing.Context>` for more details.
        """

        self.params = Params()
        """
        Dictionary like object for parameters that will be passed to the callback object.

        :example:
            >>> item = Listitem()
            >>> item.params['videoid'] = 'kqmdIV_gBfo'
        """

        self.property = Property(listitem)
        """
        Dictionary like object that allows you to add listitem properties. e.g. StartOffset

        Some of these are treated internally by Kodi, such as the 'StartOffset' property,
        which is the offset in seconds at which to start playback of an item. Others may be used
        in the skin to add extra information, such as 'WatchedCount' for tvshow items.

        :examples:
            >>> item = Listitem()
            >>> item.property['StartOffset'] = '256.4'
        """

    @property
    def label(self):
        """
        The listitem label property.

        .. seealso:: A full list of label formating options can be found at.\n
                     http://kodi.wiki/view/Label_Formatting

        :example:
            >>> item = Listitem()
            >>> item.label = "Video Title"
        """
        return ensure_unicode(self.listitem.getLabel())

    @label.setter
    def label(self, label):
        """Sets the listitem's label."""
        self.listitem.setLabel(label)
        unformatted_label = strip_formatting("", label)
        self.params["_title_"] = unformatted_label
        self.info["title"] = unformatted_label

    def set_callback(self, callback, *args, **kwargs):
        """
        Set the callback object.

        The callback object can be any registered Route/Resolver callback function or class.
        Or callback can be a playable url.

        :param callback: The function to callback or a playable url.
        :param args: Positional arguments that will be passed to callback.
        :param kwargs: Keyword arguments that will be passed to callback.
        """
        if args:
            # Convert positional arguments to keyword arguments
            args_map = callback.route.args_to_kwargs(args)
            kwargs.update(args_map)

        self.callback = callback
        self.params.update(kwargs)

    # noinspection PyProtectedMember
    def _close(self):
        callback = self.callback
        if hasattr(callback, "route"):
            self.listitem.setProperty("isplayable", str(callback.route.is_playable).lower())
            self.listitem.setProperty("folder", str(callback.route.is_folder).lower())
            path = build_path(callback.route.path, self.params.raw_dict)
            isfolder = callback.route.is_folder
        else:
            self.listitem.setProperty("isplayable", "true" if callback else "false")
            self.listitem.setProperty("folder", "false")
            path = callback
            isfolder = False

        if isfolder:
            # Set Kodi icon image if not already set
            if "icon" not in self.art.raw_dict:
                self.art.raw_dict["icon"] = "DefaultFolder.png"
        else:
            # Set Kodi icon image if not already set
            if "icon" not in self.art.raw_dict:
                self.art.raw_dict["icon"] = "DefaultVideo.png"

            # Add mediatype if not already set
            if "mediatype" not in self.info.raw_dict and self.content_type in ("video", "music"):
                self.info.raw_dict["mediatype"] = self.content_type

            # Add Video Specific Context menu items
            self.context.append(("$LOCALIZE[13347]", "XBMC.Action(Queue)"))
            self.context.append(("$LOCALIZE[13350]", "XBMC.ActivateWindow(videoplaylist)"))

            # Close video related datasets
            self.stream._close()

        # Add label as plot if no plot is found
        if "plot" not in self.info:
            self.info["plot"] = self.label

        # Close common datasets
        self.listitem.setPath(path)
        self.property._close()
        self.context._close()
        self.info._close(self.content_type)
        self.art._close()

        # Return a tuple compatible with 'xbmcplugin.addDirectoryItems'
        return path, self.listitem, isfolder

    @classmethod
    def from_dict(cls, label, callback, params=None, info=None, art=None, stream=None, properties=None, context=None):
        """
        Constructor to create a listitem.

        This method will create and populate a listitem from a set of given values.

        :type label: str or unicode
        :param label: The listitem's label.
        :param callback: The callback function or playable path.
        :param dict params: Dictionary of parameters that will be passed to the callback function.
        :param dict info: Dictionary of listitem infoLabels.
        :param dict art: Dictionary of listitem's art.
        :param dict stream: Dictionary of stream details.
        :param dict properties: Dictionary of listitem properties.
        :param list context: List of context menu item(s) containing tuples of label/command pairs.

        :return: A listitem object.
        :rtype: Listitem
        """
        item = cls()
        item.set_callback(callback)
        item.label = label

        if params:
            item.params.update(params)
        if info:
            item.info.update(info)
        if art:
            item.art.update(art)
        if stream:
            item.stream.update(stream)
        if properties:
            item.property.update(properties)
        if context:
            item.context.extend(context)

        return item

    @classmethod
    def next_page(cls, **params):
        """
        Constructor for adding Next Page.

        Add a listitem that will link to the next page of items. The current running callback will be called with
        all of the params that are given here.

        :param params: Keyword arguments of params that will be added to the current set of callback params.

        :example:
            >>> item = Listitem()
            >>> item.next_page(url="http://example.com/videos?page2")
        """
        # Add support params to callback params
        params["_updatelisting_"] = True
        params["_title_"] = dispatcher.support_params.get(u"_title_", u"")
        params["_nextpagecount_"] = dispatcher.support_params.get(u"_nextpagecount_", 1) + 1

        # Create listitem instance
        item = cls()
        label = u"%s %i" % (Script.localize(NEXT_PAGE), params["_nextpagecount_"])
        item.info["plot"] = "Show the next page of content."
        item.label = "[B]%s[/B]" % label
        item.art.global_thumb("next.png")
        item.params.update(params)
        item.set_callback(dispatcher.callback, **params)
        return item

    @classmethod
    def youtube(cls, content_id, label=None, enable_playlists=True):
        """
        Constructor to add a youtube channel to addon.

        This listitem will list all videos from a youtube channel or playlist. All videos also have a
        related videos option via context menu. If content_id is a channel id and enable_playlists
        is ``True`` then a link to the channel playlists will also be added to the list of videos.

        :param content_id: Channel id or playlist id of video content.
        :type content_id: str or unicode

        :param label: [opt] Label of listitem. (default => 'All Videos').
        :type label: str or unicode

        :param bool enable_playlists: [opt] Set to ``False`` to disable linking to channel playlists.
                                      (default => ``True``)

        :example:
            >>> item = Listitem()
            >>> item.youtube("UC4QZ_LsYcvcq7qOsOhpAX4A")
        """
        # Youtube exists, Creating listitem link
        item = cls()
        item.label = label if label else Script.localize(ALLVIDEOS)
        item.art.global_thumb("videos.png")
        item.params["contentid"] = content_id
        item.params["enable_playlists"] = False if content_id.startswith("PL") else enable_playlists
        item.set_callback(YTPlaylist)
        return item

    @classmethod
    def recent(cls, callback, **params):
        """
        Constructor for adding Recent Folder.

        This is really more of a convenience method that creates the listitem with name, thumbnail and plot
        already preset for the user.

        :param callback: The callback function.
        :type callback: :class:`types.FunctionType`
        :param params: Keyword arguments of parameters that will be passed to the callback function.
        """
        # Create listitem instance
        item = cls()
        item.label = Script.localize(RECENT_VIDEOS)
        item.info["plot"] = "Show the most recent videos."
        item.art.global_thumb("recent.png")
        item.set_callback(callback, **params)
        return item

    @classmethod
    def search(cls, callback, **params):
        """
        Constructor to add saved search Support to addon.

        This will first link to a sub folder that lists all saved search terms.
        From here, search terms can be created or removed.
        When a selection is made, the callback function that was given will be executed with all params forwarded on.
        Except with one extra param, 'search_query' witch is the search term that was selected.

        :param callback: Function that will be called when the listitem is activated.
        :param params: Keyword arguments that will be farwarded on to callback.
        :raises ValueError: If the given callback function does not have a 'search_query' parameter.
        """
        # Check that callback function has required parameter(search_query).
        if "search_query" not in callback.route.arg_names():
            raise ValueError("callback function is missing required argument: 'search_query'")

        item = cls()
        item.label = u"[B]%s[/B]" % Script.localize(SEARCH)
        item.art.global_thumb("search.png")
        item.info["plot"] = "Search for video content."
        item.set_callback(SavedSearches, route=callback.route.path, **params)
        return item


# Import callback functions required for listitem constructs
from codequick.youtube import Playlist as YTPlaylist
from codequick.search import SavedSearches
