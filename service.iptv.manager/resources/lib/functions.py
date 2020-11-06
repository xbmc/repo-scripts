# -*- coding: utf-8 -*-
"""Functions code"""

from __future__ import absolute_import, division, unicode_literals

import logging

from resources.lib import kodilogging, kodiutils
from resources.lib.modules.addon import Addon
from resources.lib.modules.contextmenu import ContextMenu
from resources.lib.modules.iptvsimple import IptvSimple

kodilogging.config()
_LOGGER = logging.getLogger(__name__)


def setup_iptv_simple():
    """Setup IPTV Simple"""
    reply = kodiutils.yesno_dialog(message=kodiutils.localize(30700))  # Are you sure...
    if reply:
        if IptvSimple.setup():
            kodiutils.ok_dialog(message=kodiutils.localize(30701))  # The configuration of IPTV Simple is completed!
        else:
            kodiutils.ok_dialog(message=kodiutils.localize(30702))  # The configuration of IPTV Simple has failed!

    # Open settings again
    kodiutils.open_settings()


def refresh():
    """Refresh the channels and EPG"""
    Addon.refresh(True)

    # Open settings again
    kodiutils.open_settings()


def play_from_contextmenu():
    """Play an item from the Context Menu in Kodi 18"""
    stream = ContextMenu.get_direct_uri()
    if stream is None:
        kodiutils.ok_dialog(message=kodiutils.localize(30706))
        return

    _LOGGER.debug('Playing using direct URI: %s', stream)
    kodiutils.execute_builtin('PlayMedia', stream)


def open_settings():
    """Open the settings for IPTV Manager"""
    kodiutils.open_settings()


def run(args):
    """Run the function"""
    function = args[1]
    function_map = {
        'setup-iptv-simple': setup_iptv_simple,
        'refresh': refresh,
        'play_from_contextmenu': play_from_contextmenu,
        'open_settings': open_settings,
    }
    try:
        # TODO: allow to pass *args to the function so we can also pass arguments
        _LOGGER.debug('Routing to function: %s', function)
        function_map.get(function)()
    except (TypeError, IndexError):
        _LOGGER.error('Could not route to %s', function)
        raise
