# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from resources.kutil131.kodiaddon import Addon

addon = Addon()

import sys

from resources.kutil131.abs_last_fm import AbstractLastFM
from resources.kutil131.actionhandler import ActionHandler
from resources.kutil131.busyhandler import busyhandler as busy
from resources.kutil131.dialogbaselist import DialogBaseList
from resources.kutil131.itemlist import ItemList
from resources.kutil131.kodilogging import KodiLogHandler, config
from resources.kutil131.listitem import AudioItem, ListItem, VideoItem
from resources.kutil131.localdb import LocalDB
from resources.kutil131.player import VideoPlayer

# PIL uses numpy if it is available.
# numpy can NOT be loaded multiple times in a sub-interpreter.
# Since numpy is optional, force it to NEVER be imported.

sys.modules['numpy'] = None

local_db: LocalDB = LocalDB(last_fm=AbstractLastFM())
player = VideoPlayer()
