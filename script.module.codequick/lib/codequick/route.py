# -*- coding: utf-8 -*-
from __future__ import absolute_import

# Standard Lib
from collections import defaultdict
from operator import itemgetter
import logging
import inspect
import hashlib
import sys
import re

# Kodi imports
import xbmcplugin

# Package imports
from codequick.storage import Cache
from codequick.script import Script
from codequick.support import logger_id, auto_sort
from codequick.utils import ensure_native_str

__all__ = ["Route", "validate_listitems"]

# Logger specific to this module
logger = logging.getLogger("%s.route" % logger_id)


def get_session_id():
    url = sys.argv[0] + sys.argv[2]
    url = url.encode("utf8") if isinstance(url, type(u"")) else url
    return hashlib.sha1(url).hexdigest()


def validate_listitems(raw_listitems):
    """Check if we have a vialid set of listitems."""

    # Convert a generator of listitems into a list of listitems
    if inspect.isgenerator(raw_listitems):
        raw_listitems = list(raw_listitems)

    # Silently ignore False values
    elif raw_listitems is False:
        return False

    if raw_listitems:
        # Check that we have valid list of listitems
        if isinstance(raw_listitems, (list, tuple)):
            # Check for an explicite False return value
            return False if len(raw_listitems) == 1 and raw_listitems[0] is False else list(filter(None, raw_listitems))
        else:
            raise ValueError("Unexpected return object: {}".format(type(raw_listitems)))
    else:
        raise RuntimeError("No items found")


def guess_content_type(mediatypes):  # type: (defaultdict) -> str
    """Guess the content type based on the mediatype set on the listitems."""
    # See if we can guess the content_type based on the mediatypes from the listitem
    if len(mediatypes) > 1:
        # Sort mediatypes by there count, and return the highest count mediatype
        mediatype = sorted(mediatypes.items(), key=itemgetter(1))[-1][0]
    elif mediatypes:
        mediatype = mediatypes.popitem()[0]
    else:
        return ""

    # Convert mediatype to a content_type, not all mediatypes can be converted directly
    if mediatype in ("video", "movie", "tvshow", "episode", "musicvideo", "song", "album", "artist"):
        return mediatype + "s"


def build_sortmethods(manualsort, autosort):  # type: (list, set) -> list
    """Merge manual & auto sortmethod together."""
    if autosort:
        # Add unsorted sort method if not sorted by date and no manually set sortmethods are given
        if not (manualsort or xbmcplugin.SORT_METHOD_DATE in autosort):
            manualsort.append(xbmcplugin.SORT_METHOD_UNSORTED)

        # Keep the order of the manually set sort methods
        # Only sort the auto sort methods
        for method in sorted(autosort):
            if method not in manualsort:
                manualsort.append(method)

    # If no sortmethods are given then set sort method to unsorted
    return manualsort if manualsort else [xbmcplugin.SORT_METHOD_UNSORTED]


def send_to_kodi(handle, session):
    """Handle the processing of the listitems."""
    # Guess the contenty type
    if session["content_type"] == -1:
        kodi_listitems = []
        folder_counter = 0.0
        mediatypes = defaultdict(int)
        for listitem in session["listitems"]:
            # Build the kodi listitem
            listitem_tuple = listitem.build()
            kodi_listitems.append(listitem_tuple)

            # Track the mediatypes used
            if "mediatype" in listitem.info:
                mediatypes[listitem.info["mediatype"]] += 1

            # Track if listitem is a folder
            if listitem_tuple[2]:
                folder_counter += 1

        # Guess content type based on set mediatypes
        session["content_type"] = guess_content_type(mediatypes)

        if not session["content_type"]:  # Fallback
            # Set content type based on type of content being listed
            isfolder = folder_counter > (len(kodi_listitems) / 2)
            session["content_type"] = "files" if isfolder else "videos"
    else:
        # Just build the kodi listitem without tracking anything
        kodi_listitems = [custom_listitem.build() for custom_listitem in session["listitems"]]

    # If redirect_single_item is set to True then redirect view to the first
    # listitem if it's the only listitem and that listitem is a folder
    if session["redirect"] and len(kodi_listitems) == 1 and kodi_listitems[0][2] is True:
        return kodi_listitems[0][0]  # return the listitem path

    # Add sort methods
    for sortMethod in session["sortmethods"]:
        xbmcplugin.addSortMethod(handle, sortMethod)

    # Sets the category for skins to display
    if session["category"]:
        xbmcplugin.setPluginCategory(handle, ensure_native_str(session["category"]))

    # Sets the plugin category for skins to display
    if session["content_type"]:
        xbmcplugin.setContent(handle, ensure_native_str(session["content_type"]))

    success = xbmcplugin.addDirectoryItems(handle, kodi_listitems, len(kodi_listitems))
    xbmcplugin.endOfDirectory(handle, success, session["update_listing"], session["cache_to_disc"])


class Route(Script):
    """
    This class is used to create "Route" callbacks. “Route" callbacks, are callbacks that
    return "listitems" which will show up as folders in Kodi.

    Route inherits all methods and attributes from :class:`codequick.Script<codequick.script.Script>`.

    The possible return types from Route Callbacks are.
        * ``iterable``: "List" or "tuple", consisting of :class:`codequick.listitem<codequick.listing.Listitem>` objects.
        * ``generator``: A Python "generator" that return's :class:`codequick.listitem<codequick.listing.Listitem>` objects.
        * ``False``: This will cause the "plugin call" to quit silently, without raising a RuntimeError.

    :raises RuntimeError: If no content was returned from callback.

    :example:
        >>> from codequick import Route, Listitem
        >>>
        >>> @Route.register
        >>> def root(_):
        >>>     yield Listitem.from_dict("Extra videos", subfolder)
        >>>     yield Listitem.from_dict("Play video", "http://www.example.com/video1.mkv")
        >>>
        >>> @Route.register
        >>> def subfolder(_):
        >>>     yield Listitem.from_dict("Play extra video", "http://www.example.com/video2.mkv")
    """

    # Change listitem type to 'folder'
    is_folder = True

    def __init__(self):
        super(Route, self).__init__()
        self.update_listing = self.params.get(u"_updatelisting_", False)
        self.category = re.sub(r"\(\d+\)$", u"", self._title).strip()
        self.cache_to_disc = self.params.get(u"_cache_to_disc_", True)
        self.redirect_single_item = False
        self.sort_methods = list()
        self.content_type = -1
        self.autosort = True

    def __call__(self, route, args, kwargs):
        cache_ttl = getattr(self, "cache_ttl", -1)
        cache = Cache("listitem_cache.sqlite", cache_ttl * 60) if cache_ttl >= 0 else None
        session_id = get_session_id()

        # Check if this plugin path is cached and valid
        if cache and session_id in cache:
            logger.debug("Listitem Cache: Hit")
            session_data = cache[session_id]
        else:
            logger.debug("Listitem Cache: Miss")

            try:
                # Execute the callback
                results = super(Route, self).__call__(route, args, kwargs)
                session_data = self._process_results(results)
                if session_data and cache:
                    cache[session_id] = session_data
                elif not session_data:
                    return None
            finally:
                if cache:
                    cache.close()

        # Send session data to kodi
        return send_to_kodi(self.handle, session_data)

    def _process_results(self, results):
        """Process the results and return a cacheable dict of session data."""
        listitems = validate_listitems(results)
        if listitems is False:
            xbmcplugin.endOfDirectory(self.handle, False)
            return None

        return {
            "listitems": listitems,
            "category": ensure_native_str(self.category),
            "update_listing": self.update_listing,
            "cache_to_disc": self.cache_to_disc,
            "sortmethods": build_sortmethods(self.sort_methods, auto_sort if self.autosort else None),
            "content_type": self.content_type,
            "redirect": self.redirect_single_item
        }

    def add_sort_methods(self, *methods, **kwargs):
        """
        Add sorting method(s).

        Any number of sort method's can be given as multiple positional arguments.
        Normally this should not be needed, as sort method's are auto detected.

        You can pass an optional keyword only argument, 'disable_autosort' to disable auto sorting.

        :param int methods: One or more Kodi sort method's.

        .. seealso:: The full list of sort methods can be found at.\n
                     https://codedocs.xyz/xbmc/xbmc/group__python__xbmcplugin.html#ga85b3bff796fd644fb28f87b136025f40
        """
        # Disable autosort if requested
        if kwargs.get("disable_autosort", False):
            self.autosort = False

        # Can't use sets here as sets don't keep order
        for method in methods:
            self.sort_methods.append(method)
