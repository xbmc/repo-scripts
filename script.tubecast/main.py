# -*- coding: utf-8 -*-
from resources.lib import service
from resources.lib.kodi import kodilogging


kodilogging.config()
service.run()
