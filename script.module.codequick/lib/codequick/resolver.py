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

__all__ = ["Resolver"]

# Logger specific to this module
logger = logging.getLogger("%s.resolver" % logger_id)

# Localized string Constants
SELECT_PLAYBACK_ITEM = 25006
NO_DATA = 33077


class Resolver(Script):
    """
    This class is used to create Resolver callbacks. Resolver callbacks, are callbacks that
    return playable video urls witch kodi can play.

    Resolver inherits all methods and attributes from :class:`script.Script<codequick.script.Script>`.

    The excepted return types from the resolver callbacks are.
        * ``bytes``: Url as type bytes.
        * ``unicode``: Url as type unicode.
        * ``iterable``: List or tuple, consisting of url's, listItem's or tuple's, consisting of title and url.
        * ``dict``: Dictionary consisting of title as the key and the url as the value.
        * ``listItem``: A listitem object with required data already set e.g. label and path.

    .. note:: If multiple url's are given, a playlist will be automaticly created.

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

    def _execute_route(self, callback):
        """Execute the callback function and process the results."""
        resolved = super(Resolver, self)._execute_route(callback)
        self.__send_to_kodi(resolved)

    def create_loopback(self, url, **next_params):
        """
        Create a playlist where the second item loops back to current addon to load next video.

        Useful for faster playlist resolving by only resolving the video url as the playlist progresses.
        No need to resolve all video urls at once before playing the playlist.

        Also useful for continuous playback of videos with no foreseeable end. For example, party mode.

        :param url: Url of the first playable item.
        :type url: str or unicode

        :param next_params: [opt] Keyword arguments to add to the loopback request when accessing the next video.

        :returns: The Listitem that kodi will play.
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

    def extract_source(self, url, quality=None):
        """
        Extract video url using YoutubeDL.

        The YoutubeDL module provides access to youtube-dl video stream extractor
        witch gives access to hundreds of sites.

        Quality is 0=SD, 1=720p, 2=1080p, 3=Highest Available

        .. seealso:: https://rg3.github.io/youtube-dl/supportedsites.html

        :param url: Url to fetch video for.
        :type url: str or unicode
        :param int quality: [opt] Override youtubeDL's quality setting.

        :returns: The extracted video url
        :rtype: str

        .. note::

            Unfortunately the kodi YoutubeDL module is python2 only.
            Hopefully it will be ported to python3 when kodi gets upgraded.
        """

        def ytdl_logger(record):
            if record.startswith("ERROR:"):
                # Save error rocord for raising later, outside of the callback
                # YoutubeDL ignores errors inside callbacks
                stored_errors.append(record[7:])

            self.log(record)
            return True

        # Setup YoutubeDL module
        from YDStreamExtractor import getVideoInfo, setOutputCallback
        setOutputCallback(ytdl_logger)
        stored_errors = []

        # Atempt to extract video source
        video_info = getVideoInfo(url, quality)
        if video_info:
            if video_info.hasMultipleStreams():
                # More than one stream found, Ask the user to select a stream
                return self.__source_selection(video_info)
            else:
                return video_info.streamURL()

        # Raise any stored errors
        elif stored_errors:
            raise RuntimeError(stored_errors[0])

    def __source_selection(self, video_info):
        """
        Ask user with video stream to play.

        :param video_info: YDStreamExtractor video_info object.
        :returns: Stream url of video
        :rtype: str
        """
        display_list = []
        # Populate list with name of extractor ('YouTube') and video title.
        for stream in video_info.streams():
            data = "%s - %s" % (stream["ytdl_format"]["extractor"].title(), stream["title"])
            display_list.append(data)

        dialog = xbmcgui.Dialog()
        ret = dialog.select(self.localize(SELECT_PLAYBACK_ITEM), display_list)
        if ret >= 0:
            video_info.selectStream(ret)
            return video_info.streamURL()

    def __create_playlist(self, urls):
        """
        Create playlist for kodi and return back the first item of that playlist to play.

        :param list urls: Set of urls that will be used in the creation of the playlist.
                          List may consist of url or listitem object.

        :returns The first listitem of the playlist.
        :rtype: xbmcgui.ListItem
        """
        # Create Playlist
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        title = self._title

        # Loop each item to create playlist
        for count, url in enumerate(filter(None, urls), 1):
            # Kodi original listitem object
            if isinstance(url, xbmcgui.ListItem):
                listitem = url
            # Custom listitem object
            elif isinstance(url, Listitem):
                # noinspection PyProtectedMember
                listitem = url._close()[1]
            else:
                # Not already a listitem object
                listitem = xbmcgui.ListItem()
                if isinstance(url, (list, tuple)):
                    title, url = url
                    title = ensure_unicode(title)

                # Create listitem with new title
                listitem.setLabel(u"%s Part %i" % (title, count))
                listitem.setPath(url)

            # Populate Playlis
            playlist.add(listitem.getPath(), listitem)

        # Return the first playlist item
        return playlist[0]

    def __send_to_kodi(self, resolved):
        """
        Construct playable listitem and send to kodi.

        :param resolved: The resolved url to send back to kodi.
        """

        # Create listitem object if resolved object is a string or unicode
        if isinstance(resolved, (bytes, unicode_type)):
            listitem = xbmcgui.ListItem()
            listitem.setPath(resolved)

        # Create playlist if resolved object is a list of urls
        elif isinstance(resolved, (list, tuple)) or inspect.isgenerator(resolved):
            listitem = self.__create_playlist(resolved)

        # Create playlist if resolved is a dict of {title: url}
        elif hasattr(resolved, "items"):
            listitem = self.__create_playlist(resolved.items())

        # Directly use resoleved if its already a listitem
        elif isinstance(resolved, xbmcgui.ListItem):
            listitem = resolved

        # Extract original kodi listitem from custom listitem
        elif isinstance(resolved, Listitem):
            # noinspection PyProtectedMember
            listitem = resolved._close()[1]

        # Invalid or No url was found
        elif resolved:
            raise ValueError("resolver returned invalid url of type: '%s'" % type(resolved))
        else:
            raise ValueError(self.localize(NO_DATA))

        # Send playable listitem to kodi
        xbmcplugin.setResolvedUrl(self.handle, True, listitem)


# Now we can import the listing module
from codequick.listing import Listitem
