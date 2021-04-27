# -*- coding: utf-8 -*-

from resources.lib import script

import logging
import xbmcaddon
import xbmcplugin
import sys

ADDON = xbmcaddon.Addon()

script.check_active_player()


