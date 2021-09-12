# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from kutils.kodiaddon import Addon

addon = Addon()

from kutils.listitem import ListItem, VideoItem, AudioItem
from kutils.itemlist import ItemList
from kutils.actionhandler import ActionHandler
from kutils.busyhandler import busyhandler as busy
from kutils.kodilogging import KodiLogHandler, config
from kutils.dialogbaselist import DialogBaseList
from kutils.localdb import LocalDB
from kutils.player import VideoPlayer
from kutils.abs_last_fm import AbstractLastFM

import sys

# PIL uses numpy if it is available.
# numpy can NOT be loaded multiple times in a sub-interpreter.
# Since numpy is optional, force it to NEVER be imported.

sys.modules['numpy'] = None

local_db: LocalDB = LocalDB(last_fm=AbstractLastFM())
player = VideoPlayer()
