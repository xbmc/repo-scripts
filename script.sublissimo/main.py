# -*- coding: utf-8 -*-

from resources.lib import loading

import logging
import xbmcaddon
import xbmcplugin
import sys

ADDON = xbmcaddon.Addon()

loading.check_active_player()
