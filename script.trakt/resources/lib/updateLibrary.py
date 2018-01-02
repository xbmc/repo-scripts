# -*- coding: utf-8 -*-
"""Module used to run update library"""

import xbmc
import xbmcaddon
import xbmcgui
from resources.lib import utilities
from resources.lib import kodiUtilities
from resources.lib import globals
import logging

logger = logging.getLogger(__name__)

__addon__ = xbmcaddon.Addon("script.trakt")

def updateLibraryCheck(media_type, summary_info, watched_time, total_time):
    """Check if a video should be rated and if so running the Update Library"""
    logger.debug("Update Library Check called for '%s'" % media_type)
    if not kodiUtilities.getSettingAsBool("update_library_%s" % media_type):
        logger.debug("'%s' is configured to not run an Update Library after watching." % media_type)
        return
    if summary_info is None:
        logger.debug("Summary information is empty, aborting.")
        return
    watched = (watched_time / total_time) * 100
    if watched >= kodiUtilities.getSettingAsFloat("update_library_min_view_time"):
            UpdateLibraryRun()
    else:
        logger.debug("'%s' does not meet minimum view time for updating library (watched: %0.2f%%, minimum: %0.2f%%)" % (media_type, watched, kodiUtilities.getSettingAsFloat("update_library_min_view_time")))

def UpdateLibraryRun():
    """Launches the update library progress"""
    logger.debug("Update Library - Start.")
    xbmc.executebuiltin('UpdateLibrary(video)')