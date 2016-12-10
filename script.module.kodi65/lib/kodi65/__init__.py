# -*- coding: utf8 -*-

# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from kodiaddon import Addon
addon = Addon()

from listitem import ListItem, VideoItem, AudioItem
from itemlist import ItemList
from actionhandler import ActionHandler
from busyhandler import busyhandler as busy
from kodilogging import KodiLogHandler, config
from dialogbaselist import DialogBaseList
from localdb import LocalDB
from player import VideoPlayer

local_db = LocalDB()
player = VideoPlayer()
