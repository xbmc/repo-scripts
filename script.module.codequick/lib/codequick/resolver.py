# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
import logging
import inspect

# Kodi imports
import xbmcplugin
import xbmcgui
import xbmc

# Package imports
from codequick.script import Script
from codequick.support import build_path, logger_id
from codequick.utils import unicode_type, ensure_unicode
from codequick import localized

__all__ = ["Resolver"]

# Logger specific to this module
logger = logging.getLogger("%s.resolver" % logger_id)


class Resolver(Script):
    """
    This class is used to create "Resolver" callbacks. Resolver callbacks are callbacks that
    return playable video URL's which Kodi can play.

    Resolver inherits all methods and attributes from :class:`script.Script<codequick.script.Script>`.

    The possible return types from Resolver Callbacks are.
        * ``str``: URL as type "str".
        * ``iterable``: "List" or "tuple", consisting of URL's, "listItem's" or a "tuple" consisting of (title, URL).
        * ``dict``: "Dictionary" consisting of "title" as the key and the URL as the value.
        * ``listItem``: A :class:`codequick.Listitem<codequick.listing.Listitem>` object with required data already set e.g. "label" and "path".
        * ``generator``: A Python "generator" that return's one or more URL's.
        * ``False``: This will cause the "resolver call" to quit silently, without raising a RuntimeError.

    .. note:: If multiple URL's are given, a playlist will be automaticly created.

    :raises RuntimeError: If no content was returned from callback.
    :raises ValueError: If returned url is invalid.

    :example:
        >>> from codequick import Resolver, Route, Listitem
        >>>
        >>> @Route.register
        >>> def root(_):
        >>>     yield Listitem.from_dict("Play video", play_video,
        >>>           params={"url": "https://www.youtube.com/watch?v=RZuVTOk6ePM"})
        >>>
        >>> @Resolver.register
        >>> def play_video(plugin, url):
        >>>     # Extract a playable video url using youtubeDL
        >>>     return plugin.extract_source(url)
    """
    # Change listitem type to 'player'
    is_playable = True

    def __init__(self):
        super(Resolver, self).__init__()
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self._extra_commands = {}  # Extra options that are passed to listitem

    def __call__(self, route, args, kwargs):
        results = super(Resolver, self).__call__(route, args, kwargs)
        return self._process_results(results)

    def create_loopback(self, url, **next_params):  # Undocumented
        """
        Create a playlist where the second item loops back to add-on to load next video.

        Also useful for continuous playback of videos with no foreseeable end. For example, party mode.

        :param str url: URL of the first playable item.
        :param next_params: [opt] "Keyword" arguments to add to the loopback request when accessing the next video.

        :returns: The Listitem that Kodi will play.
        :rtype: xbmcgui.ListItem
        """
        # Video Playlist
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

        # Main Playable listitem
        main_listitem = xbmcgui.ListItem()
        main_listitem.setPath(url)

        # When called from a loopback we just add title to main listitem
        if self._title.startswith(u"_loopback_"):
            main_listitem.setLabel(self._title.split(u" - ", 1)[1])
            next_params["_title_"] = self._title
        else:
            # Create playlist for loopback calling
            # The first item is the playable listitem
            main_listitem.setLabel(self._title)
            next_params["_title_"] = u"_loopback_ - %s" % self._title
            playlist.clear()
            playlist.add(url, main_listitem)

        # Create Loopback listitem
        loop_listitem = xbmcgui.ListItem()
        loop_listitem.setLabel(next_params["_title_"])

        # Build a loopback url that callback to the addon to fetch the next video
        loopback_url = build_path(**next_params)
        loop_listitem.setPath(loopback_url)
        playlist.add(loopback_url, loop_listitem)

        # Retrun the playable listitem
        return main_listitem

    def extract_source(self, url, quality=None, **params):
        """
        Extract video URL using "YouTube.DL".

        YouTube.DL provides access to hundreds of sites.

        .. seealso::

            The list of supported sites can be found at:

            https://rg3.github.io/youtube-dl/supportedsites.html

        Quality options are.
            * 0 = SD,
            * 1 = 720p,
            * 2 = 1080p,
            * 3 = Highest Available

        :param str url: URL of the video source, where the playable video can be extracted from.
        :param int quality: [opt] Override YouTube.DL's quality setting.
        :param params: Optional "Keyword" arguments of YouTube.DL parameters.

        :returns: The playable video url
        :rtype: str

        .. seealso::

            The list of available parameters can be found at.

            https://github.com/rg3/youtube-dl#options
        """

        def ytdl_logger(record):
            if record.startswith("ERROR:"):
                # Save error rocord for raising later, outside of the callback
                # YoutubeDL ignores errors inside callbacks
                stored_errors.append("Youtube-DL: " + record[7:])

            self.log(record)
            return True

        # Setup YoutubeDL module
        # noinspection PyUnresolvedReferences
        from YDStreamExtractor import getVideoInfo, setOutputCallback, overrideParam
        setOutputCallback(ytdl_logger)
        stored_errors = []

        # Override youtube_dl parmeters
        for key, value in params.items():
            overrideParam(key, value)

        # Atempt to extract video source
        video_info = getVideoInfo(url, quality)
        if video_info:
            if video_info.hasMultipleStreams():
                # More than one stream found, Ask the user to select a stream
                video_info = self._source_selection(video_info)

            if video_info:
                # Content Lookup needs to be disabled for dailymotion videos to work
                if video_info.sourceName == "dailymotion":
                    self._extra_commands["setContentLookup"] = False

                return video_info.streamURL()

        # Raise any stored errors
        elif stored_errors:
            raise RuntimeError(stored_errors[0])

    def _source_selection(self, video_info):
        """
        Ask user whitch video stream to play.

        :param video_info: YDStreamExtractor video_info object.
        :returns: video_info object with the video pre selection.
        """
        display_list = []
        # Populate list with name of extractor ('YouTube') and video title.
        for stream in video_info.streams():
            data = "%s - %s" % (stream["ytdl_format"]["extractor"].title(), stream["title"])
            display_list.append(data)

        dialog = xbmcgui.Dialog()
        ret = dialog.select(self.localize(localized.SELECT_PLAYBACK_ITEM), display_list)
        if ret >= 0:
            video_info.selectStream(ret)
            return video_info

    def _create_playlist(self, urls):
        """
        Create playlist for kodi and return back the first item of that playlist to play.

        :param list urls: Set of urls that will be used in the creation of the playlist.
                          List may consist of urls or listitem objects.

        :returns The first listitem of the playlist.
        :rtype: xbmcgui.ListItem
        """
        # Loop each item to create playlist
        listitems = [self._process_item(*item) for item in enumerate(urls, 1)]

        # Populate Playlis
        for item in listitems[1:]:
            self.playlist.add(item.getPath(), item)

        # Return the first playlist item
        return listitems[0]

    def _process_item(self, count, url):
        """
        Process the playlist item and add to kodi playlist.

        :param int count: The part number of the item
        :param str url: The resolved object
        """
        # Kodi original listitem object
        if isinstance(url, xbmcgui.ListItem):
            return url
        # Custom listitem object
        elif isinstance(url, Listitem):
            # noinspection PyProtectedMember
            return url.build()[1]
        else:
            # Not already a listitem object
            listitem = xbmcgui.ListItem()
            if isinstance(url, (list, tuple)):
                title, url = url
                title = ensure_unicode(title)
            else:
                title = self._title

            # Create listitem with new title
            listitem.setLabel(u"%s Part %i" % (title, count) if count > 1 else title)
            listitem.setInfo("video", {"title": title})
            listitem.setPath(url)
            return listitem

    def _process_generator(self, resolved):
        """
        Populate the kodi playlist in the background from a generator.

        :param resolved: The resolved generator to fetch the rest of the videos from
        """
        for item in enumerate(filter(None, resolved), 2):
            listitem = self._process_item(*item)
            self.playlist.add(listitem.getPath(), listitem)

    def _process_results(self, resolved):
        """
        Construct playable listitem and send to kodi.

        :param resolved: The resolved url to send back to kodi.
        """
        if resolved:
            # Create listitem object if resolved is a string or unicode
            if isinstance(resolved, (bytes, unicode_type)):
                listitem = xbmcgui.ListItem()
                listitem.setPath(resolved)

            # Directly use resoleved if its already a listitem
            elif isinstance(resolved, xbmcgui.ListItem):
                listitem = resolved

            # Extract original kodi listitem from custom listitem
            elif isinstance(resolved, Listitem):
                # noinspection PyProtectedMember
                listitem = resolved.build()[1]

            # Create playlist if resolved object is a list of urls
            elif isinstance(resolved, (list, tuple)):
                listitem = self._create_playlist(resolved)

            # Fetch the first element of the generator and process the rest in the background
            elif inspect.isgenerator(resolved):
                listitem = self._process_item(1, next(resolved))
                self.register_delayed(self._process_generator, resolved)

            # Create playlist if resolved is a dict of {title: url}
            elif hasattr(resolved, "items"):
                items = resolved.items()
                listitem = self._create_playlist(items)

            else:
                # Resolved url must be invalid
                raise ValueError("resolver returned invalid url of type: '%s'" % type(resolved))

            logger.debug("Resolved Url: %s", listitem.getPath())

        elif resolved is False:
            # A empty listitem is still required even if 'resolved' is False
            # From time to time Kodi will report that 'Playback failed'
            # there is nothing that can be done about that.
            listitem = xbmcgui.ListItem()
        else:
            raise RuntimeError(self.localize(localized.NO_VIDEO))

        # Add extra parameters to listitem
        if "setContentLookup" in self._extra_commands:
            value = self._extra_commands["setContentLookup"]
            listitem.setContentLookup(value)

        # Send playable listitem to kodi
        xbmcplugin.setResolvedUrl(self.handle, bool(resolved), listitem)


# Now we can import the listing module
from codequick.listing import Listitem
