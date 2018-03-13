# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Library Imports
import logging
import inspect
import re

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
NO_VIDEO = 32401
NO_DATA = 33077


# Patterens to extract video url
# Copied from the Youtube-DL project
# https://github.com/rg3/youtube-dl/blob/4471affc348af40409188f133786780edd969623/youtube_dl/extractor/youtube.py#L329
VALID_YOUTUBE_URL = r"""(?x)^
(
 (?:https?://|//)                                     # http(s):// or protocol-independent URL
 (?:(?:(?:(?:\w+\.)?[yY][oO][uU][tT][uU][bB][eE](?:-nocookie)?\.com/|
    youtube\.googleapis\.com/)                        # the various hostnames, with wildcard subdomains
 (?:.*?\#/)?                                          # handle anchor (#/) redirect urls
 (?:                                                  # the various things that can precede the ID:
     (?:(?:v|embed|e)/(?!videoseries))                # v/ or embed/ or e/
     |(?:                                             # or the v= param in all its forms
         (?:(?:watch|movie)(?:_popup)?(?:\.php)?/?)?  # preceding watch(_popup|.php) or nothing (like /?v=xxxx)
         (?:\?|\#!?)                                  # the params delimiter ? or # or #!
         (?:.*?[&;])??                                # any other preceding param (like /?s=tuff&v=xxxx or
         v=                                           # ?s=tuff&amp;v=V36LpHqtcDY)
     )
 ))
 |(?:
    youtu\.be|                                        # just youtu.be/xxxx
    vid\.plus|                                        # or vid.plus/xxxx
    zwearz\.com/watch|                                # or zwearz.com/watch/xxxx
 ))
)?                                                       # all until now is optional -> you can pass the naked ID
([0-9A-Za-z_-]{11})                                      # here is it! the YouTube video ID
(?(1).+)?                                                # if we found the ID, everything can follow
$"""


class Resolver(Script):
    """
    This class is used to create Resolver callbacks. Resolver callbacks, are callbacks that
    return playable video urls witch kodi can play.

    Resolver inherits all methods and attributes from :class:`script.Script<codequick.script.Script>`.

    The possible return types from resolver callbacks are.
        * ``bytes``: Url as type bytes.
        * ``unicode``: Url as type unicode.
        * ``iterable``: List or tuple, consisting of url's, listItem's or a tuple consisting of title and url.
        * ``dict``: Dictionary consisting of title as the key and the url as the value.
        * ``listItem``: A listitem object with required data already set e.g. label and path.
        * ``generator``: A python generator that return's one or more urls.

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

    def __init__(self):
        super(Resolver, self).__init__()
        self.playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    def _execute_route(self, callback):
        """Execute the callback function and process the results."""
        resolved = super(Resolver, self)._execute_route(callback)
        self._send_to_kodi(resolved)

    def create_loopback(self, url, **next_params):
        """
        Create a playlist where the second item loops back to addon to load next video.

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

    def extract_source(self, url, quality=None, **params):
        """
        Extract video url using YoutubeDL.

        YoutubeDL provides access to hundreds of sites.

        Quality options are.
            * 0 = SD,
            * 1 = 720p,
            * 2 = 1080p,
            * 3 = Highest Available

        :param url: Url of the video source to extract the playable video from.
        :type url: str or unicode
        :param int quality: [opt] Override youtubeDL's quality setting.
        :param params: Optional Keyword arguments of youtube_dl parameters.

        :returns: The playable video url
        :rtype: str

        .. seealso::

            The list of supported sites can be found at:

            https://rg3.github.io/youtube-dl/supportedsites.html

        .. seealso::

            The list of available parameters can be found at.

            https://github.com/rg3/youtube-dl#options

        .. note::

            Unfortunately the kodi Youtube-DL module is python2 only.
            It should be ported to python3 when kodi switches to python 3 for version 19.
        """

        def ytdl_logger(record):
            if record.startswith("ERROR:"):
                # Save error rocord for raising later, outside of the callback
                # YoutubeDL ignores errors inside callbacks
                stored_errors.append("Youtube-DL: " + record[7:])

            self.log(record)
            return True

        # Setup YoutubeDL module
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
                return self._source_selection(video_info)
            else:
                return video_info.streamURL()

        # Raise any stored errors
        elif stored_errors:
            raise RuntimeError(stored_errors[0])

    def extract_youtube(self, source):
        import htmlement
        import urlquick

        # The Element class isn't been exposed directly by the C implementation
        # So the type trick is needed here
        if isinstance(source, type(htmlement.Etree.Element(None))):
            video_elem = source
        else:
            # Tempeary method to extract video url from an embeded youtube video.
            if source.startswith("http://") or source.startswith("https://"):
                source = urlquick.get(source, max_age=0).text
            try:
                video_elem = htmlement.fromstring(source)
            except RuntimeError:  # pragma: no cover
                return None

        # Search for all types of embeded videos
        video_urls = []
        video_urls.extend(video_elem.findall(".//iframe[@src]"))
        video_urls.extend(video_elem.findall(".//embed[@src]"))

        for url in video_urls:
            match = re.match(VALID_YOUTUBE_URL, url.get("src"))
            if match is not None:  # pragma: no branch
                videoid = match.group(2)
                return u"plugin://plugin.video.youtube/play/?video_id={}".format(videoid)

    def _source_selection(self, video_info):
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

    def _create_playlist(self, urls):
        """
        Create playlist for kodi and return back the first item of that playlist to play.

        :param list urls: Set of urls that will be used in the creation of the playlist.
                          List may consist of urls or listitem objects.

        :returns The first listitem of the playlist.
        :rtype: xbmcgui.ListItem
        """
        # Loop each item to create playlist
        for item in enumerate(filter(None, urls), 1):
            self._playlist_item(*item)

        # Return the first playlist item
        return self.playlist[0]

    def _playlist_item(self, count, url):
        """
        Process the playlist item and add to kodi playlist.

        :param int count: The part number of the item
        :param url: The resolved object
        :type url: str or unicode
        """
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
            else:
                title = self._title

            # Create listitem with new title
            listitem.setLabel(u"%s Part %i" % (title, count))
            listitem.setPath(url)

        # Populate Playlis
        self.playlist.add(listitem.getPath(), listitem)

    def _process_generator(self, resolved):
        """
        Populate the kodi playlist in the background from a generator.

        :param resolved: The resolved generator to fetch the rest of the videos from
        """
        for item in enumerate(filter(None, resolved), 2):
            self._playlist_item(*item)

    def _send_to_kodi(self, resolved):
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
                listitem = resolved._close()[1]

            # Create playlist if resolved object is a list of urls
            elif isinstance(resolved, (list, tuple)):
                listitem = self._create_playlist(resolved)

            # Fetch the first element of the generator and process the rest in the background
            elif inspect.isgenerator(resolved):
                listitem = self._create_playlist([next(resolved)])
                self.register_delayed_callback(self._process_generator, resolved)

            # Create playlist if resolved is a dict of {title: url}
            elif hasattr(resolved, "items"):
                listitem = self._create_playlist(resolved.items())

            else:
                # Resolved url must be invalid
                raise ValueError("resolver returned invalid url of type: '%s'" % type(resolved))
        else:
            raise ValueError(self.localize(NO_VIDEO))

        # Send playable listitem to kodi
        logger.debug("Resolved Url: %s", listitem.getPath())
        xbmcplugin.setResolvedUrl(self.handle, True, listitem)


# Now we can import the listing module
from codequick.listing import Listitem
