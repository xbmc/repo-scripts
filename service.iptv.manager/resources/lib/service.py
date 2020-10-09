# -*- coding: utf-8 -*-
"""Background service code"""

from __future__ import absolute_import, division, unicode_literals

import logging
import time

from xbmc import Monitor

from resources.lib import kodilogging, kodiutils
from resources.lib.modules.addon import Addon
from resources.lib.modules.iptvsimple import IptvSimple

kodilogging.config()
_LOGGER = logging.getLogger(__name__)


class BackgroundService(Monitor):
    """Background service code"""

    def __init__(self):
        Monitor.__init__(self)
        self._restart_required = False

    def run(self):
        """Background loop for maintenance tasks"""
        _LOGGER.debug('Service started')

        # Service loop
        while not self.abortRequested():
            # Check if we need to do an update
            if self._is_refresh_required():
                Addon.refresh()

            # Check if IPTV Simple needs to be restarted
            if IptvSimple.restart_required:
                IptvSimple.restart()

            # Stop when abort requested
            if self.waitForAbort(30):
                break

        _LOGGER.debug('Service stopped')

    @staticmethod
    def _is_refresh_required():
        """Returns if we should trigger an update based on the settings."""
        refresh_interval = kodiutils.get_setting_int('refresh_interval', 24) * 3600
        last_refreshed = kodiutils.get_setting_int('last_refreshed', 0)
        return (last_refreshed + refresh_interval) <= time.time()


def run():
    """Run the BackgroundService"""
    BackgroundService().run()
