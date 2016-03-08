# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import sys
import xbmc
from resources.lib.process import start_info_actions
from resources.lib.Utils import *


class Main:

    def __init__(self):
        xbmc.log("version %s started" % ADDON_VERSION)
        HOME.setProperty("extendedinfo_running", "true")
        self._parse_argv()
        for info in self.infos:
            listitems = start_info_actions(info, self.params)
            pass_list_to_skin(name=info,
                              data=listitems,
                              prefix=self.params.get("prefix", ""),
                              limit=self.params.get("limit", 20))
        if not self.infos:
            HOME.setProperty('infodialogs.active', "true")
            from resources.lib.WindowManager import wm
            wm.open_video_list()
            HOME.clearProperty('infodialogs.active')
        HOME.clearProperty("extendedinfo_running")

    def _parse_argv(self):
        self.infos = []
        self.params = {"handle": None}
        for arg in sys.argv[1:]:
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(param.split("=")[1:]).strip().decode('utf-8')
                except:
                    pass

if (__name__ == "__main__"):
    Main()
xbmc.log('finished')
